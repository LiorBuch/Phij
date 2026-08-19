from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]
    cwd: Path = ROOT


CHECKS = (
    Check("JavaScript lint", ("pnpm", "-r", "lint")),
    Check("Python lint", ("uvx", "ruff", "check", "apps/server", "services/camera", "scripts")),
    Check("JavaScript typecheck", ("pnpm", "-r", "typecheck")),
    Check(
        "Server typecheck",
        (
            "uvx",
            "--python",
            "3.9",
            "--with",
            "fastapi",
            "--with",
            "pydantic-settings",
            "--from",
            "mypy<2",
            "mypy",
            "--config-file",
            "pyproject.toml",
            "app",
        ),
        ROOT / "apps/server",
    ),
    Check(
        "Camera typecheck",
        (
            "uvx",
            "--python",
            "3.9",
            "--from",
            "mypy<2",
            "mypy",
            "--config-file",
            "pyproject.toml",
            "src",
        ),
        ROOT / "services/camera",
    ),
    Check("JavaScript tests", ("pnpm", "-r", "test")),
    Check(
        "Server tests",
        (
            "uvx",
            "--python",
            "3.9",
            "--from",
            "pytest",
            "--with",
            "fastapi",
            "--with",
            "pydantic-settings",
            "--with",
            "httpx",
            "pytest",
        ),
        ROOT / "apps/server",
    ),
    Check(
        "Camera tests",
        ("uvx", "--python", "3.9", "--from", "pytest", "pytest"),
        ROOT / "services/camera",
    ),
    Check("JavaScript build", ("pnpm", "-r", "build")),
    Check("Compose validation", ("docker", "compose", "config", "--quiet")),
)


def require_commands() -> None:
    missing = sorted({check.command[0] for check in CHECKS if shutil.which(check.command[0]) is None})
    if missing:
        names = ", ".join(missing)
        raise SystemExit(f"Missing required command(s): {names}")


def main() -> int:
    require_commands()
    for index, check in enumerate(CHECKS, start=1):
        print(f"\n[{index}/{len(CHECKS)}] {check.name}", flush=True)
        result = subprocess.run(check.command, cwd=check.cwd, check=False)
        if result.returncode != 0:
            print(f"\nFAILED: {check.name}", file=sys.stderr)
            return result.returncode

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
