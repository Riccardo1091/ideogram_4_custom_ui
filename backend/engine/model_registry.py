"""
Registers and checks the paths of model components needed for Ideogram 4 inference.
"""

from pathlib import Path
from typing import Dict, Optional
from backend.config import settings

class ModelRegistry:
    @staticmethod
    def resolve_path(base_dir: Path, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return base_dir / p

    @staticmethod
    def get_paths() -> Dict[str, Path]:
        """Returns the resolved paths of all required model assets."""
        models_dir = Path(settings.models_path)
        return {
            "main_model": ModelRegistry.resolve_path(models_dir, settings.main_model),
            "uncond_model": ModelRegistry.resolve_path(models_dir, settings.uncond_model),
            "text_encoder": ModelRegistry.resolve_path(models_dir, settings.text_encoder),
            "vae": ModelRegistry.resolve_path(models_dir, settings.vae),
        }

    @staticmethod
    def check_files() -> Dict[str, bool]:
        """Checks if files exist and returns a dict mapping model names to boolean status."""
        paths = ModelRegistry.get_paths()
        return {name: path.exists() for name, path in paths.items()}

    @classmethod
    def get_missing_files(cls) -> Dict[str, Path]:
        """Returns dictionary of components that are missing."""
        paths = cls.get_paths()
        return {name: path for name, path in paths.items() if not path.exists()}
