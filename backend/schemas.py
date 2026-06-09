"""
Defines input/output schemas for the local REST API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="Prompt text or structured JSON prompt as string")
    json_mode: bool = Field(False, description="Whether the prompt is a structured JSON prompt")
    preset: str = Field("default", description="Generation preset: turbo, default, quality")
    width: int = Field(1024, description="Output image width")
    height: int = Field(1024, description="Output image height")
    seed: Optional[int] = Field(None, description="Generation seed (random if null)")
    steps: Optional[int] = Field(None, description="Override steps if specified")
    mu: Optional[float] = Field(None, description="Override mu if specified")
    std: Optional[float] = Field(None, description="Override std if specified")

class GenerationResolvedRequest(BaseModel):
    prompt: str
    json_mode: bool
    preset: str
    width: int
    height: int
    seed: int
    steps: int
    mu: float
    std: float

class GenerationResult(BaseModel):
    job_id: str
    image_url: str
    seed: int
    time_taken: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any]

class HealthStatus(BaseModel):
    status: str
    cuda_available: bool
    gpu_name: Optional[str]
    vram_total: Optional[float]
    vram_free: Optional[float]
    model_validation: Dict[str, bool]
    selected_runtime: str

class HistoryItem(BaseModel):
    job_id: str
    timestamp: str
    prompt: str
    preset: str
    width: int
    height: int
    seed: int
    success: bool
    image_url: str
    metadata: Dict[str, Any]

class SettingsUpdateRequest(BaseModel):
    main_model: Optional[str] = None
    uncond_model: Optional[str] = None
    text_encoder: Optional[str] = None
    vae: Optional[str] = None
    output_path: Optional[str] = None
    device: Optional[str] = None
    port: Optional[int] = None
    comfyui_path: Optional[str] = None

class BrowsePathRequest(BaseModel):
    kind: str = Field("file", description="Path selector type: file or directory")
    title: Optional[str] = None
    initial_path: Optional[str] = None
    filetypes: Optional[List[List[str]]] = None
