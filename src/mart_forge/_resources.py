"""Resource path resolution for both editable and wheel installs."""

from pathlib import Path

_PKG_DIR = Path(__file__).parent


def get_resource_root() -> Path:
    """Return the root containing templates/, skills/, docs/, scripts/.

    In wheel install: these are force-included under the mart_forge/ package dir.
    In editable/dev install: they live at the repository root (two levels up from src/mart_forge/).
    """
    if (_PKG_DIR / "templates").is_dir():
        return _PKG_DIR
    repo_root = _PKG_DIR.parent.parent
    if (repo_root / "templates").is_dir():
        return repo_root
    raise FileNotFoundError(
        "Cannot locate framework resources (templates/, skills/, docs/). "
        "Ensure mart-forge is installed correctly."
    )
