"""
Local REST API backend for Ideogram 4 using FastAPI.
Delegates validation, config parsing, history reading, and model inference.
"""

import time
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List

from backend.config import settings
from backend.schemas import GenerationRequest, GenerationResult, HealthStatus, HistoryItem, SettingsUpdateRequest
from backend.presets import resolve_parameters
from backend.engine.prompt_builder import PromptBuilder
from backend.engine.diagnostics import Diagnostics
from backend.engine.output_store import OutputStore
from backend.engine.int8_fast_runtime import Int8FastRuntime
from backend.engine.official_runtime import OfficialRuntime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("BackendAPI")

app = FastAPI(
    title="Ideogram 4 Local GUI API",
    description="Backend API powering the Ideogram 4 custom web control room."
)

# CORS middleware for local frontend developers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the chosen runtime engine (defaults to custom INT8 fast adapter)
runtime_backend = "int8_fast"
engine = Int8FastRuntime()

@app.on_event("startup")
async def startup_event():
    logger.info(f"API starting up. Selected runtime: {runtime_backend}")
    engine.warmup()

@app.get("/api/health", response_model=HealthStatus)
def get_health():
    """Returns runtime diagnostics, hardware specs, and configuration checks."""
    try:
        report = Diagnostics.get_full_report(engine.name)
        return HealthStatus(
            status=report["status"],
            cuda_available=report["cuda_available"],
            gpu_name=report["gpu_name"],
            vram_total=report["vram_total"],
            vram_free=report["vram_free"],
            model_validation=report["model_validation"],
            selected_runtime=report["selected_runtime"]
        )
    except Exception as e:
        logger.error(f"Error compiling diagnostics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/progress")
def get_progress():
    """Returns the current generation progress."""
    try:
        return engine.get_progress()
    except Exception as e:
        logger.error(f"Error fetching progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings")
def get_settings():
    """Exposes all dynamic configuration settings."""
    return {
        "models_path": str(settings.models_path),
        "main_model": settings.main_model,
        "uncond_model": settings.uncond_model,
        "text_encoder": str(settings.text_encoder),
        "vae": str(settings.vae),
        "device": settings.device,
        "output_path": str(settings.output_path),
        "port": settings.port
    }

@app.post("/api/settings")
def post_settings(req: SettingsUpdateRequest):
    """Updates settings dynamically in memory and writes them to .env."""
    try:
        data = req.dict(exclude_unset=True)
        settings.update_settings(data)
        report = Diagnostics.get_full_report(engine.name)
        return {
            "success": True,
            "health": report
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/reload")
def reload_settings():
    """Triggers model reloading (warmup) with current settings."""
    try:
        logger.info("Triggering engine warmup reload...")
        engine.warmup()
        report = Diagnostics.get_full_report(engine.name)
        return {
            "success": True,
            "health": report
        }
    except Exception as e:
        logger.error(f"Error reloading engine settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_config():
    """Exposes system setup locations."""
    return {
        "models_path": str(settings.models_path),
        "main_model": settings.main_model,
        "uncond_model": settings.uncond_model,
        "text_encoder": settings.text_encoder,
        "vae": settings.vae,
        "device": settings.device,
        "output_path": str(settings.output_path),
        "active_engine": engine.name
    }

@app.post("/api/generate", response_model=GenerationResult)
def post_generate(request: GenerationRequest):
    """Triggers generation workflow."""
    try:
        # 1. Resolve steps/mu/std presets and overrides
        params = resolve_parameters(
            request.preset,
            override_steps=request.steps,
            override_mu=request.mu,
            override_std=request.std
        )
        
        # 2. Process and validate the prompt string
        clean_prompt = PromptBuilder.build(request.prompt, json_mode=request.json_mode)
        
        # 3. Create resolved request object
        resolved_req = GenerationRequest(
            prompt=clean_prompt,
            json_mode=request.json_mode,
            preset=request.preset,
            width=request.width,
            height=request.height,
            seed=request.seed,
            steps=params["steps"],
            mu=params["mu"],
            std=params["std"]
        )
        
        # 4. Invoke inference engine
        result = engine.generate(resolved_req)
        return result
    except Exception as e:
        logger.error(f"Generation job failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/api/history", response_model=List[HistoryItem])
def get_history():
    """Returns past generation records."""
    try:
        return OutputStore.get_history()
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/image/{job_id}/{file_name}")
def get_image(job_id: str, file_name: str):
    """Serves generated PNG output images."""
    target_path = Path(settings.output_path) / job_id / file_name
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Requested file not found.")
    return FileResponse(target_path)

# Serve static frontend GUI files
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")
    logger.info(f"Mounted static frontend from: {frontend_path}")
else:
    logger.warning(f"Frontend folder not found at expected path: {frontend_path}")
