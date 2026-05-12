"""Core behavior tests for MCP client server config building."""

import os

import pytest

from medrix_flow.config.extensions_config import ExtensionsConfig, McpServerConfig
from medrix_flow.mcp.client import build_server_params, build_servers_config


def test_build_server_params_stdio_success():
    config = McpServerConfig(
        type="stdio",
        command="npx",
        args=["-y", "my-mcp-server"],
        env={"API_KEY": "secret"},
    )

    params = build_server_params("my-server", config)

    assert params == {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "my-mcp-server"],
        "env": {"API_KEY": "secret"},
    }


def test_build_server_params_stdio_requires_command():
    config = McpServerConfig(type="stdio", command=None)

    with pytest.raises(ValueError, match="requires 'command' field"):
        build_server_params("broken-stdio", config)


@pytest.mark.parametrize("transport", ["sse", "http"])
def test_build_server_params_http_like_success(transport: str):
    config = McpServerConfig(
        type=transport,
        url="https://example.com/mcp",
        headers={"Authorization": "Bearer token"},
    )

    params = build_server_params("remote-server", config)

    assert params == {
        "transport": transport,
        "url": "https://example.com/mcp",
        "headers": {"Authorization": "Bearer token"},
    }


@pytest.mark.parametrize("transport", ["sse", "http"])
def test_build_server_params_http_like_requires_url(transport: str):
    config = McpServerConfig(type=transport, url=None)

    with pytest.raises(ValueError, match="requires 'url' field"):
        build_server_params("broken-remote", config)


def test_build_server_params_rejects_unsupported_transport():
    config = McpServerConfig(type="websocket")

    with pytest.raises(ValueError, match="unsupported transport type"):
        build_server_params("bad-transport", config)


def test_build_server_params_rejects_shell_command():
    config = McpServerConfig(type="stdio", command="bash", args=["-lc", "echo hi"])

    with pytest.raises(ValueError, match="not allowed"):
        build_server_params("bad-shell", config)


def test_build_server_params_rejects_inline_eval_flags(monkeypatch):
    monkeypatch.setattr("medrix_flow.mcp.security.shutil.which", lambda _cmd: "/usr/bin/python3")
    config = McpServerConfig(type="stdio", command="python3", args=["-c", "print('hi')"])

    with pytest.raises(ValueError, match="blocked inline-eval flags"):
        build_server_params("bad-inline-eval", config)


def test_build_servers_config_returns_empty_when_no_enabled_servers():
    extensions = ExtensionsConfig(
        mcp_servers={
            "disabled-a": McpServerConfig(enabled=False, type="stdio", command="echo"),
            "disabled-b": McpServerConfig(enabled=False, type="http", url="https://example.com"),
        },
        skills={},
    )

    assert build_servers_config(extensions) == {}


def test_build_servers_config_skips_invalid_server_and_keeps_valid_ones():
    extensions = ExtensionsConfig(
        mcp_servers={
            "valid-stdio": McpServerConfig(enabled=True, type="stdio", command="npx", args=["server"]),
            "invalid-stdio": McpServerConfig(enabled=True, type="stdio", command=None),
            "disabled-http": McpServerConfig(enabled=False, type="http", url="https://disabled.example.com"),
        },
        skills={},
    )

    result = build_servers_config(extensions)

    assert "valid-stdio" in result
    assert result["valid-stdio"]["transport"] == "stdio"
    assert "invalid-stdio" not in result
    assert "disabled-http" not in result


def test_mcp_cache_detects_same_mtime_same_size_content_change(monkeypatch, tmp_path):
    import medrix_flow.mcp.cache as cache

    config_path = tmp_path / "extensions_config.json"
    config_path.write_text("alpha", encoding="utf-8")
    monkeypatch.setattr(
        ExtensionsConfig,
        "resolve_config_path",
        classmethod(lambda cls, config_path=None: config_path or tmp_path / "extensions_config.json"),
    )

    cache.reset_mcp_tools_cache()
    first_signature = cache._get_config_signature()
    assert first_signature is not None

    config_path.write_text("bravo", encoding="utf-8")
    os.utime(config_path, ns=(first_signature.mtime_ns, first_signature.mtime_ns))

    second_signature = cache._get_config_signature()
    assert second_signature is not None
    assert second_signature.mtime_ns == first_signature.mtime_ns
    assert second_signature.size == first_signature.size
    assert second_signature.content_hash != first_signature.content_hash

    cache._cache_initialized = True
    cache._config_signature = first_signature
    try:
        assert cache._is_cache_stale() is True
    finally:
        cache.reset_mcp_tools_cache()
