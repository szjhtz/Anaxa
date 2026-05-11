#!/usr/bin/env python3
"""Idempotent local setup wizard for Anaxa developers/operators."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
HARNESS_ROOT = BACKEND_ROOT / "packages" / "harness"

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(HARNESS_ROOT))

from medrix_flow.setup import ensure_setup_files, get_setup_config_data  # noqa: E402


def main() -> int:
    print("==========================================")
    print("  Anaxa Setup Wizard")
    print("==========================================")
    print()

    try:
        created = ensure_setup_files(PROJECT_ROOT)
    except Exception as exc:
        print(f"✗ Failed to prepare setup files: {exc}")
        return 1

    if created:
        print("Created configuration files:")
        for path in created:
            print(f"  + {path.relative_to(PROJECT_ROOT)}")
    else:
        print("All setup files already exist.")

    try:
        config = get_setup_config_data()
        print()
        print(f"Configured models: {len(config.models)}")
        print(f"Configured tool key slots: {len(config.tool_keys)}")
    except Exception as exc:
        print()
        print(f"⚠ Setup files exist, but configuration could not be loaded yet: {exc}")
        print("  Use the workspace setup page or edit config.yaml / .env before starting services.")

    print()
    print("Next steps:")
    print("  1. make install")
    print("  2. make dev")
    print("  3. Open http://localhost:6200 and configure models in the UI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
