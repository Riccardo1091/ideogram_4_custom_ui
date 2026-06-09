"""
Handles storage of output images and metadata files inside unique job folders.
"""

import os
import json
import uuid
import datetime
from pathlib import Path
from PIL import Image
from backend.config import settings
from backend.schemas import HistoryItem

class OutputStore:
    @staticmethod
    def save_generation(
        image: Image.Image,
        prompt: str,
        preset: str,
        width: int,
        height: int,
        seed: int,
        metadata: dict,
        success: bool = True
    ) -> HistoryItem:
        """Saves image and metadata into a job directory and returns a HistoryItem."""
        job_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        job_dir = Path(settings.output_path) / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save image
        image_name = "output.png"
        image_path = job_dir / image_name
        image.save(image_path, "PNG")
        
        # Build metadata dictionary
        meta_dict = {
            "job_id": job_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "preset": preset,
            "width": width,
            "height": height,
            "seed": seed,
            "success": success,
            "details": metadata
        }
        
        # Save JSON metadata
        meta_path = job_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, indent=2, ensure_ascii=False)
            
        # Image URL to serve via API
        image_url = f"/api/image/{job_id}/{image_name}"
        
        return HistoryItem(
            job_id=job_id,
            timestamp=timestamp,
            prompt=prompt,
            preset=preset,
            width=width,
            height=height,
            seed=seed,
            success=success,
            image_url=image_url,
            metadata=meta_dict
        )

    @staticmethod
    def get_history() -> list[HistoryItem]:
        """Scans the outputs directory and returns all history items sorted by timestamp."""
        history = []
        outputs_dir = Path(settings.output_path)
        if not outputs_dir.exists():
            return history
            
        for job_dir in outputs_dir.iterdir():
            if job_dir.is_dir():
                meta_path = job_dir / "metadata.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        
                        image_name = "output.png"
                        history.append(HistoryItem(
                            job_id=meta.get("job_id"),
                            timestamp=meta.get("timestamp"),
                            prompt=meta.get("prompt"),
                            preset=meta.get("preset"),
                            width=meta.get("width"),
                            height=meta.get("height"),
                            seed=meta.get("seed"),
                            success=meta.get("success", True),
                            image_url=f"/api/image/{meta.get('job_id')}/{image_name}",
                            metadata=meta
                        ))
                    except Exception:
                        pass # Ignore corrupted directories/JSONs
                        
        # Sort by timestamp descending
        history.sort(key=lambda x: x.timestamp, reverse=True)
        return history
