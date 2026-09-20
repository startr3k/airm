"""Configuration and the paths derived from it."""

from __future__ import annotations

from pathlib import Path

from mindforge_assess import config


def test_the_data_root_can_be_stated_rather_than_derived(monkeypatch, tmp_path) -> None:
    """Walking up from `__file__` only finds the repo for an editable install. Installed
    properly -- as in the container -- the package sits in site-packages and the walk
    lands somewhere like /usr/local/lib/backend, so the root has to be overridable.
    """
    import importlib

    monkeypatch.setenv("MINDFORGE_ROOT", str(tmp_path))
    module = importlib.reload(config)
    try:
        assert module.REPO_ROOT == tmp_path
        assert module.FRAMEWORK_DIR == tmp_path / "backend" / "framework"
        assert module.EVALS_DIR == tmp_path / "backend" / "evals"
    finally:
        monkeypatch.delenv("MINDFORGE_ROOT")
        importlib.reload(config)


def test_without_the_override_the_root_is_still_derived() -> None:
    """The default must keep working for development, where nothing sets it."""
    import mindforge_assess

    package_dir = Path(mindforge_assess.__file__).resolve().parent
    assert config.REPO_ROOT == package_dir.parents[2]
    assert (config.FRAMEWORK_DIR / "pack.v1.json").is_file()
