"""
Defines default settings for Turbo, Default, and Quality presets.
"""

from typing import Dict, Any, Optional

PRESETS: Dict[str, Dict[str, Any]] = {
    "turbo": {
        "steps": 12,
        "mu": 0.5,
        "std": 1.75
    },
    "default": {
        "steps": 20,
        "mu": 0.0,
        "std": 1.75
    },
    "quality": {
        "steps": 48,
        "mu": 0.0,
        "std": 1.5
    }
}

def resolve_parameters(
    preset_name: str,
    override_steps: Optional[int] = None,
    override_mu: Optional[float] = None,
    override_std: Optional[float] = None
) -> Dict[str, Any]:
    """Resolves parameters based on the preset and overrides."""
    clean_name = preset_name.lower()
    if clean_name not in PRESETS:
        clean_name = "default"
    
    preset_vals = PRESETS[clean_name].copy()
    
    if override_steps is not None:
        preset_vals["steps"] = override_steps
    if override_mu is not None:
        preset_vals["mu"] = override_mu
    if override_std is not None:
        preset_vals["std"] = override_std
        
    return preset_vals
