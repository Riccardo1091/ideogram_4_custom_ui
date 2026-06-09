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
        """Saves image directly into the outputs directory with embedded PNG metadata."""
        from PIL import PngImagePlugin
        
        job_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
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
        
        # Create PNG metadata
        png_info = PngImagePlugin.PngInfo()
        png_info.add_text("ideogram_metadata", json.dumps(meta_dict))
        
        # Generate filename based on timestamp and seed
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        image_name = f"{timestamp_str}_{seed}.png"
        
        # Ensure unique name in output folder
        output_dir = Path(settings.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        image_path = output_dir / image_name
        counter = 1
        while image_path.exists():
            image_name = f"{timestamp_str}_{seed}_{counter}.png"
            image_path = output_dir / image_name
            counter += 1
            
        # Save image directly in outputs folder with info embedded
        image.save(image_path, "PNG", pnginfo=png_info)
        
        # Image URL to serve via API
        image_url = f"/api/image/{image_name}"
        
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
            
        # Iterate over output directory
        for item in outputs_dir.iterdir():
            if item.is_file() and item.suffix.lower() == ".png":
                # Check for metadata embedded in PNG
                try:
                    with Image.open(item) as img:
                        metadata_str = img.info.get("ideogram_metadata")
                        if metadata_str:
                            meta = json.loads(metadata_str)
                            history.append(HistoryItem(
                                job_id=meta.get("job_id"),
                                timestamp=meta.get("timestamp"),
                                prompt=meta.get("prompt"),
                                preset=meta.get("preset"),
                                width=meta.get("width"),
                                height=meta.get("height"),
                                seed=meta.get("seed"),
                                success=meta.get("success", True),
                                image_url=f"/api/image/{item.name}",
                                metadata=meta
                            ))
                        else:
                            # PNG file with no embedded metadata (e.g. user-placed file)
                            # Create a fallback HistoryItem based on file properties
                            stat = item.stat()
                            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                            history.append(HistoryItem(
                                job_id=item.stem,
                                timestamp=mtime,
                                prompt="External Image",
                                preset="default",
                                width=img.width,
                                height=img.height,
                                seed=0,
                                success=True,
                                image_url=f"/api/image/{item.name}",
                                metadata={}
                            ))
                except Exception:
                    pass
            elif item.is_dir() and item.name != "__pycache__":
                # Legacy subdirectory check
                meta_path = item / "metadata.json"
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
