"""
Responsible for parsing and centralizing configuration settings from environment variables.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

@dataclass
class Settings:
    port: int = field(default_factory=lambda: int(os.getenv("IDEOGRAM_PORT", 8000)))
    main_model: str = field(default_factory=lambda: os.getenv("IDEOGRAM_MAIN_MODEL", str(Path("./models/diffusion_models/ideogram4-int8-ConvRot.safetensors").absolute())))
    uncond_model: str = field(default_factory=lambda: os.getenv("IDEOGRAM_UNCOND_MODEL", str(Path("./models/diffusion_models/ideogram4-unconditional-int8-ConvRot.safetensors").absolute())))
    text_encoder: str = field(default_factory=lambda: os.getenv("IDEOGRAM_TEXT_ENCODER", str(Path("./models/text_encoders/qwen3vl_8b_fp8_scaled.safetensors").absolute())))
    vae: str = field(default_factory=lambda: os.getenv("IDEOGRAM_VAE", str(Path("./models/vae/flux2-vae.safetensors").absolute())))
    device: str = field(default_factory=lambda: os.getenv("IDEOGRAM_DEVICE", "cuda"))
    output_path: Path = field(default_factory=lambda: Path(os.getenv("IDEOGRAM_OUTPUT_PATH", "./outputs")).absolute())
    comfyui_path: Optional[Path] = field(default_factory=lambda: Path(os.getenv("COMFYUI_PATH")).absolute() if os.getenv("COMFYUI_PATH") else None)

    def __post_init__(self):
        # Auto-create output directory
        self.output_path.mkdir(parents=True, exist_ok=True)

    def validate(self) -> dict:
        """Validates existence of paths and models, returning a report."""
        from backend.engine.model_registry import ModelRegistry
        model_checks = ModelRegistry.check_files()
        report = {
            "main_model_exists": model_checks.get("main_model", False),
            "uncond_model_exists": model_checks.get("uncond_model", False),
            "text_encoder_exists": model_checks.get("text_encoder", False),
            "vae_exists": model_checks.get("vae", False),
            "output_path_exists": self.output_path.exists()
        }
        return report

    def update_settings(self, data: dict):
        """Updates in-memory settings and writes them to the .env file."""
        if "main_model" in data and data["main_model"]:
            self.main_model = str(Path(data["main_model"]).absolute())
        if "uncond_model" in data and data["uncond_model"]:
            self.uncond_model = str(Path(data["uncond_model"]).absolute())
        if "text_encoder" in data and data["text_encoder"]:
            self.text_encoder = str(Path(data["text_encoder"]).absolute())
        if "vae" in data and data["vae"]:
            self.vae = str(Path(data["vae"]).absolute())
        if "output_path" in data and data["output_path"]:
            self.output_path = Path(data["output_path"]).absolute()
            self.output_path.mkdir(parents=True, exist_ok=True)
        if "port" in data and data["port"]:
            try:
                self.port = int(data["port"])
            except ValueError:
                pass
        if "device" in data and data["device"]:
            self.device = data["device"]
        if "comfyui_path" in data:
            self.comfyui_path = Path(data["comfyui_path"]).absolute() if data["comfyui_path"] else None

        # Write out to .env file
        env_path = Path(".env")
        mapping = {
            "IDEOGRAM_PORT": str(self.port),
            "IDEOGRAM_MAIN_MODEL": str(self.main_model).replace("\\", "/"),
            "IDEOGRAM_UNCOND_MODEL": str(self.uncond_model).replace("\\", "/"),
            "IDEOGRAM_TEXT_ENCODER": str(self.text_encoder).replace("\\", "/"),
            "IDEOGRAM_VAE": str(self.vae).replace("\\", "/"),
            "IDEOGRAM_DEVICE": self.device,
            "IDEOGRAM_OUTPUT_PATH": str(self.output_path).replace("\\", "/"),
        }
        if self.comfyui_path:
            mapping["COMFYUI_PATH"] = str(self.comfyui_path).replace("\\", "/")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# Ideogram 4 Local App Configurations\n")
            for key, val in mapping.items():
                f.write(f"{key}={val}\n")

# Global settings instance
settings = Settings()
