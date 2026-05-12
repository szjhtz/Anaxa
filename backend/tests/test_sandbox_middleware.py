from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from medrix_flow.sandbox.middleware import SandboxMiddleware


def test_after_agent_keeps_sandbox_for_thread_reuse():
    provider = MagicMock()
    middleware = SandboxMiddleware(lazy_init=True)

    with patch("medrix_flow.sandbox.middleware.get_sandbox_provider", return_value=provider):
        result = middleware.after_agent(
            {"sandbox": {"sandbox_id": "aio-1"}},
            SimpleNamespace(context={"sandbox_id": "aio-1"}),
        )

    assert result is None
    provider.release.assert_not_called()
