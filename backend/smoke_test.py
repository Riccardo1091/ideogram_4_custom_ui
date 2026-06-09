"""
CLI Entrypoint for smoke testing the Ideogram 4 local runtime environment.
"""

import sys
import logging
from pathlib import Path

# Add root folder to sys.path so we can run direct scripts
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.engine.model_registry import ModelRegistry
from backend.engine.diagnostics import Diagnostics
from backend.engine.int8_fast_runtime import Int8FastRuntime
from backend.schemas import GenerationRequest
from backend.presets import resolve_parameters

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("SmokeTest")

def run_smoke_test():
    logger.info("=== IDEOGRAM 4 LOCAL SYSTEM SMOKE TEST ===")
    
    # 1. Config Validation
    logger.info("Verifying configuration settings...")
    for name, path in ModelRegistry.get_paths().items():
        logger.info(f"{name}: {path}")
    logger.info(f"Output folder: {settings.output_path}")
    
    report = settings.validate()
    for component, exists in report.items():
        status = "FOUND" if exists else "MISSING"
        logger.info(f" - {component}: {status}")
        
    # 2. Hardware Diagnostics
    diag = Diagnostics.get_cuda_info()
    logger.info(f"CUDA Available: {diag['cuda_available']}")
    if diag["cuda_available"]:
        logger.info(f"GPU Name: {diag['gpu_name']}")
        logger.info(f"Total VRAM: {diag['vram_total']} GB")
        
    # 3. Instantiate & Warmup Runtime
    runtime = Int8FastRuntime()
    runtime.warmup()
    
    # 4. Resolve Parameters & Run Test Request
    preset_params = resolve_parameters("default")
    test_request = GenerationRequest(
        prompt="A vibrant modern UI layout showing clean lines and glowing colors, high detail, retro-futuristic style",
        json_mode=False,
        preset="default",
        width=1024,
        height=1024,
        seed=12345,
        steps=preset_params["steps"],
        mu=preset_params["mu"],
        std=preset_params["std"]
    )
    
    logger.info("Running sample generation...")
    result = runtime.generate(test_request)
    
    if result.success:
        logger.info("Generation SUCCEEDED!")
        logger.info(f"Job ID: {result.job_id}")
        logger.info(f"Image saved to URL: {result.image_url}")
        logger.info(f"Time taken: {result.time_taken:.2f} seconds")
    else:
        logger.error(f"Generation FAILED: {result.error}")
        
    logger.info("=== SMOKE TEST COMPLETE ===")

if __name__ == "__main__":
    run_smoke_test()
