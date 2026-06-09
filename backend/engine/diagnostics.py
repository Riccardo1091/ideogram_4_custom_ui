"""
Interrogates hardware environment (CUDA, VRAM, GPU details) and model path validity.
"""

import torch
from typing import Dict, Any, Optional
from backend.engine.model_registry import ModelRegistry

class Diagnostics:
    @staticmethod
    def get_cuda_info() -> Dict[str, Any]:
        """Queries current CUDA compatibility and GPU resources."""
        cuda_avail = torch.cuda.is_available()
        gpu_name = None
        vram_total = 0.0
        vram_free = 0.0
        
        if cuda_avail:
            gpu_name = torch.cuda.get_device_name(0)
            # Fetch memory in Gigabytes
            vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            # Estimated free VRAM
            vram_free = vram_total - (torch.cuda.memory_allocated(0) / (1024**3))
            
        return {
            "cuda_available": cuda_avail,
            "gpu_name": gpu_name,
            "vram_total": round(vram_total, 2) if cuda_avail else None,
            "vram_free": round(vram_free, 2) if cuda_avail else None,
        }

    @classmethod
    def get_full_report(cls, selected_runtime: str) -> Dict[str, Any]:
        """Assembles a comprehensive diagnostics dictionary."""
        cuda = cls.get_cuda_info()
        models = ModelRegistry.check_files()
        
        # Determine overall readiness
        all_models_present = all(models.values())
        is_ready = cuda["cuda_available"] and all_models_present
        
        return {
            "status": "ready" if is_ready else "not_configured",
            "cuda_available": cuda["cuda_available"],
            "gpu_name": cuda["gpu_name"],
            "vram_total": cuda["vram_total"],
            "vram_free": cuda["vram_free"],
            "model_validation": models,
            "selected_runtime": selected_runtime,
            "ready": is_ready
        }
