"""Validation utilities for Isaac Sim prims and assets."""

from pathlib import Path


def validate_asset_exists(asset_path: str) -> None:
    """Validate that a USD asset file exists.

    Args:
        asset_path: Path to the USD asset file

    Raises:
        FileNotFoundError: If the asset file does not exist
    """
    path = Path(asset_path)
    if not path.exists():
        raise FileNotFoundError(f"USD asset not found: {asset_path}")


def validate_prim_exists(stage, prim_path: str):
    """Validate that a prim exists and return it.

    Args:
        stage: USD stage to search
        prim_path: Path to the prim

    Returns:
        The validated Usd.Prim

    Raises:
        RuntimeError: If the prim does not exist or is invalid
    """
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsValid():
        raise RuntimeError(f"Prim not found: {prim_path}")
    return prim
