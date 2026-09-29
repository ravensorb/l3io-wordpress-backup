"""Shared fixtures for the architecture contract tests."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def built_distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Build a wheel and an sdist with the project's own backend.

    hatchling is invoked in process rather than through ``uv build`` so the
    contract checks need no network and no build-environment resolution; the
    file selection under test is the backend's, which is the same either way.
    """
    from hatchling.build import build_sdist, build_wheel

    out = tmp_path_factory.mktemp("dist")
    with contextlib.chdir(PROJECT_ROOT):
        wheel = out / build_wheel(str(out))
        sdist = out / build_sdist(str(out))
    return wheel, sdist
