"""
Manages detection, installation, updates, and Git status queries for ComfyUI and its custom nodes.
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import threading
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple
import requests

from backend.config import settings

logger = logging.getLogger("ComfyUIInstaller")

class ComfyUIInstaller:
    _lock = threading.Lock()
    _is_installing = False
    _progress = 0.0
    _step = "Idle"
    _message = "Ready"

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns the installation, git version, and update status of ComfyUI."""
        default_path = Path("comfy_core").absolute()
        
        # If COMFYUI_PATH settings is set, use it. Otherwise, use our local default path
        current_path = settings.comfyui_path if settings.comfyui_path else default_path
        
        installed = cls.is_valid_comfy_path(current_path)
        is_auto_managed = (current_path == default_path)
        
        git_installed = False
        try:
            res = subprocess.run(["git", "--version"], capture_output=True, text=True)
            git_installed = res.returncode == 0 and "git version" in res.stdout
        except Exception:
            pass

        local_commit = "N/A"
        remote_commit = "N/A"
        update_available = False
        status_msg = "ComfyUI is configured."

        if installed:
            git_dir = current_path / ".git"
            if git_dir.exists() and git_installed:
                try:
                    res_local = subprocess.run(
                        ["git", "rev-parse", "--short", "HEAD"],
                        cwd=str(current_path),
                        capture_output=True, text=True, check=True
                    )
                    local_commit = res_local.stdout.strip()
                except Exception as e:
                    logger.debug(f"Failed to get local git commit: {e}")
                    local_commit = "Error"
            else:
                local_commit = "ZIP-installed"
        else:
            status_msg = "ComfyUI is not installed or configured."

        # Return status details
        return {
            "installed": installed,
            "install_path": str(current_path).replace("\\", "/"),
            "is_auto_managed": is_auto_managed,
            "git_installed": git_installed,
            "local_commit": local_commit,
            "remote_commit": remote_commit,
            "update_available": update_available,
            "is_installing": cls._is_installing,
            "install_progress": cls._progress,
            "install_step": cls._step,
            "status_message": cls._message if cls._is_installing else status_msg
        }

    @classmethod
    def is_valid_comfy_path(cls, path: Path) -> bool:
        """Determines if a directory contains a valid ComfyUI install."""
        return path.exists() and (path / "main.py").exists() and (path / "comfy").is_dir()

    @classmethod
    def check_updates(cls) -> Tuple[bool, str]:
        """Checks if a new update is available on GitHub."""
        status = cls.get_status()
        if not status["installed"]:
            return False, "Not installed"

        current_path = Path(status["install_path"])
        git_dir = current_path / ".git"
        if not (git_dir.exists() and status["git_installed"]):
            return False, "Not a Git repository, auto-updates disabled."

        try:
            # Check ComfyUI Core (master branch)
            res_remote = subprocess.run(
                ["git", "ls-remote", "https://github.com/Comfy-Org/ComfyUI.git", "refs/heads/master"],
                capture_output=True, text=True, timeout=8
            )
            if res_remote.returncode == 0 and res_remote.stdout:
                remote_hash = res_remote.stdout.split()[0].strip()
                
                # Fetch full local head hash
                res_local = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(current_path),
                    capture_output=True, text=True
                )
                local_hash = res_local.stdout.strip()
                
                if local_hash != remote_hash:
                    return True, f"ComfyUI Core update available (remote: {remote_hash[:7]})"

            # Check ComfyUI-INT8-Fast custom node (main branch)
            node_path = current_path / "custom_nodes" / "ComfyUI-INT8-Fast"
            if node_path.exists() and (node_path / ".git").exists():
                res_node_remote = subprocess.run(
                    ["git", "ls-remote", "https://github.com/BobJohnson24/ComfyUI-INT8-Fast.git", "refs/heads/main"],
                    capture_output=True, text=True, timeout=8
                )
                if res_node_remote.returncode == 0 and res_node_remote.stdout:
                    remote_node_hash = res_node_remote.stdout.split()[0].strip()
                    res_node_local = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=str(node_path),
                        capture_output=True, text=True
                    )
                    local_node_hash = res_node_local.stdout.strip()
                    if local_node_hash != remote_node_hash:
                        return True, "Update available for ComfyUI-INT8-Fast node"

        except Exception as e:
            logger.debug(f"Update check failed: {e}")
            return False, f"Check failed: {str(e)}"

        return False, "ComfyUI is up to date."

    @classmethod
    def start_install(cls) -> Tuple[bool, str]:
        """Initiates the ComfyUI download/install background thread."""
        with cls._lock:
            if cls._is_installing:
                return False, "An installation/update is already in progress."
            cls._is_installing = True
            cls._progress = 0.0
            cls._step = "Initializing"
            cls._message = "Preparing installation..."

        thread = threading.Thread(target=cls._run_install)
        thread.daemon = True
        thread.start()
        return True, "Installation started in the background."

    @classmethod
    def start_update(cls) -> Tuple[bool, str]:
        """Initiates the ComfyUI update background thread."""
        with cls._lock:
            if cls._is_installing:
                return False, "An installation/update is already in progress."
            cls._is_installing = True
            cls._progress = 0.0
            cls._step = "Checking Updates"
            cls._message = "Connecting to GitHub..."

        thread = threading.Thread(target=cls._run_update)
        thread.daemon = True
        thread.start()
        return True, "Update started in the background."

    @classmethod
    def _run_install(cls):
        try:
            target_path = Path("comfy_core").absolute()
            
            # Check for Git
            status = cls.get_status()
            if status["git_installed"]:
                cls._run_install_git(target_path)
            else:
                cls._run_install_zip(target_path)

            # Post-install config
            cls._step = "Configuring"
            cls._message = "Setting up model pathways..."
            cls._progress = 0.9

            settings.comfyui_path = target_path
            
            # Ensure base models paths default to our new comfyui core structure
            settings.models_path = target_path / "models" / "diffusion_models"
            settings.text_encoder = target_path / "models" / "text_encoders" / "qwen3vl_8b_fp8_scaled.safetensors"
            settings.vae = target_path / "models" / "vae" / "flux2-vae.safetensors"

            # Persist back to settings & .env
            settings.update_settings({
                "models_path": str(settings.models_path),
                "text_encoder": str(settings.text_encoder),
                "vae": str(settings.vae)
            })

            cls._progress = 1.0
            cls._step = "Done"
            cls._message = "Installation completed successfully! ComfyUI core is active."
        except Exception as e:
            logger.error(f"Installation failed: {e}", exc_info=True)
            cls._step = "Error"
            cls._message = f"Installation failed: {str(e)}"
        finally:
            with cls._lock:
                cls._is_installing = False

    @classmethod
    def _run_install_git(cls, target_path: Path):
        cls._step = "Cloning ComfyUI"
        cls._message = "Downloading ComfyUI core via Git..."
        cls._progress = 0.1
        
        # Clone ComfyUI Core
        if target_path.exists():
            shutil.rmtree(target_path, ignore_errors=True)
            
        cmd_core = ["git", "clone", "--depth", "1", "https://github.com/Comfy-Org/ComfyUI.git", str(target_path)]
        res = subprocess.run(cmd_core, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to clone ComfyUI repository: {res.stderr}")

        cls._step = "Cloning Custom Nodes"
        cls._message = "Downloading ComfyUI-INT8-Fast custom nodes..."
        cls._progress = 0.5

        node_path = target_path / "custom_nodes" / "ComfyUI-INT8-Fast"
        cmd_node = ["git", "clone", "--depth", "1", "https://github.com/BobJohnson24/ComfyUI-INT8-Fast.git", str(node_path)]
        res_node = subprocess.run(cmd_node, capture_output=True, text=True)
        if res_node.returncode != 0:
            raise RuntimeError(f"Failed to clone ComfyUI-INT8-Fast repository: {res_node.stderr}")

    @classmethod
    def _run_install_zip(cls, target_path: Path):
        temp_dir = Path("temp_install")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # 1. Download ComfyUI ZIP
            cls._step = "Downloading ComfyUI"
            cls._message = "Fetching ComfyUI core zip..."
            cls._progress = 0.1
            
            comfy_zip = temp_dir / "comfyui.zip"
            cls._download_file_with_progress(
                "https://github.com/Comfy-Org/ComfyUI/archive/refs/heads/master.zip",
                comfy_zip,
                start_pct=0.1, end_pct=0.4
            )
            
            # Extract ComfyUI ZIP
            cls._step = "Extracting ComfyUI"
            cls._message = "Extracting ComfyUI files..."
            cls._progress = 0.45
            
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            cls._extract_zip(comfy_zip, target_path)

            # 2. Download Custom Nodes ZIP
            cls._step = "Downloading Custom Nodes"
            cls._message = "Fetching ComfyUI-INT8-Fast zip..."
            cls._progress = 0.55
            
            node_zip = temp_dir / "node.zip"
            node_path = target_path / "custom_nodes" / "ComfyUI-INT8-Fast"
            cls._download_file_with_progress(
                "https://github.com/BobJohnson24/ComfyUI-INT8-Fast/archive/refs/heads/main.zip",
                node_zip,
                start_pct=0.55, end_pct=0.75
            )

            # Extract Custom Nodes ZIP
            cls._step = "Extracting Custom Nodes"
            cls._message = "Extracting custom nodes..."
            cls._progress = 0.8
            cls._extract_zip(node_zip, node_path)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _run_update(cls):
        try:
            status = cls.get_status()
            current_path = Path(status["install_path"])
            
            git_dir = current_path / ".git"
            if git_dir.exists() and status["git_installed"]:
                cls._step = "Updating ComfyUI"
                cls._message = "Pulling updates for ComfyUI Core..."
                cls._progress = 0.2
                
                res_core = subprocess.run(["git", "pull"], cwd=str(current_path), capture_output=True, text=True)
                if res_core.returncode != 0:
                    raise RuntimeError(f"Git pull core failed: {res_core.stderr}")
                
                cls._progress = 0.5
                cls._step = "Updating Custom Nodes"
                cls._message = "Pulling updates for ComfyUI-INT8-Fast..."
                
                node_path = current_path / "custom_nodes" / "ComfyUI-INT8-Fast"
                if node_path.exists() and (node_path / ".git").exists():
                    res_node = subprocess.run(["git", "pull"], cwd=str(node_path), capture_output=True, text=True)
                    if res_node.returncode != 0:
                        raise RuntimeError(f"Git pull custom node failed: {res_node.stderr}")

                cls._progress = 1.0
                cls._step = "Done"
                cls._message = "ComfyUI and custom nodes updated successfully!"
            else:
                # No git: download ZIP update, overlaying it on top while preserving models/
                cls._step = "Downloading Zip Update"
                cls._message = "Downloading latest ComfyUI core source..."
                cls._progress = 0.1
                
                temp_dir = Path("temp_update")
                temp_dir.mkdir(exist_ok=True)
                
                try:
                    comfy_zip = temp_dir / "comfyui.zip"
                    cls._download_file_with_progress(
                        "https://github.com/Comfy-Org/ComfyUI/archive/refs/heads/master.zip",
                        comfy_zip,
                        start_pct=0.1, end_pct=0.5
                    )
                    
                    cls._step = "Applying Core Update"
                    cls._message = "Extracting source files (preserving local models)..."
                    cls._progress = 0.6
                    
                    # Instead of deleting comfyui_path, we extract to temp directory first,
                    # then copy files over, carefully skipping `models` directory or merging it.
                    temp_extract = temp_dir / "extract"
                    cls._extract_zip(comfy_zip, temp_extract)
                    
                    # Copy everything except 'models'
                    for item in temp_extract.iterdir():
                        if item.name == "models":
                            continue
                        dest_item = current_path / item.name
                        if item.is_dir():
                            shutil.copytree(item, dest_item, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, dest_item)
                    
                    cls._progress = 0.8
                    cls._step = "Applying Custom Nodes"
                    cls._message = "Updating custom nodes..."
                    
                    node_zip = temp_dir / "node.zip"
                    cls._download_file_with_progress(
                        "https://github.com/BobJohnson24/ComfyUI-INT8-Fast/archive/refs/heads/main.zip",
                        node_zip,
                        start_pct=0.8, end_pct=0.95
                    )
                    
                    node_path = current_path / "custom_nodes" / "ComfyUI-INT8-Fast"
                    if node_path.exists():
                        shutil.rmtree(node_path, ignore_errors=True)
                    cls._extract_zip(node_zip, node_path)
                    
                    cls._progress = 1.0
                    cls._step = "Done"
                    cls._message = "ComfyUI update applied successfully (ZIP mode)!"
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            cls._step = "Error"
            cls._message = f"Update failed: {str(e)}"
        finally:
            with cls._lock:
                cls._is_installing = False

    @classmethod
    def _download_file_with_progress(cls, url: str, dest_path: Path, start_pct: float, end_pct: float):
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        total_length = response.headers.get('content-length')
        
        if total_length is None:
            with open(dest_path, 'wb') as f:
                f.write(response.content)
        else:
            total_length = int(total_length)
            dl = 0
            with open(dest_path, 'wb') as f:
                for data in response.iter_content(chunk_size=65536):
                    dl += len(data)
                    f.write(data)
                    fraction = dl / total_length
                    cls._progress = start_pct + fraction * (end_pct - start_pct)

    @classmethod
    def _extract_zip(cls, zip_path: Path, target_dir: Path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            temp_extract = Path(zip_path).parent / "temp_extract"
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            temp_extract.mkdir(parents=True, exist_ok=True)
            zip_ref.extractall(temp_extract)
            
            top_dirs = [p for p in temp_extract.iterdir() if p.is_dir()]
            if len(top_dirs) == 1:
                target_dir.mkdir(parents=True, exist_ok=True)
                for item in top_dirs[0].iterdir():
                    dest_item = target_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest_item)
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                for item in temp_extract.iterdir():
                    dest_item = target_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest_item)
            shutil.rmtree(temp_extract, ignore_errors=True)
