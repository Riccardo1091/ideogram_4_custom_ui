"""
Standalone INT8 High-Performance Runtime for Ideogram 4.
Integrates with the ComfyUI core components and the ComfyUI-INT8-Fast custom nodes
to execute local inference using PyTorch and quantized models.
"""

import sys
import os
import time
import logging
import types
import importlib.util
from pathlib import Path
import numpy as np
import torch
from PIL import Image, ImageDraw
from backend.config import settings
from backend.engine.base import BaseRuntime
from backend.schemas import GenerationRequest, GenerationResult
from backend.engine.model_registry import ModelRegistry
from backend.engine.output_store import OutputStore

logger = logging.getLogger("Int8FastRuntime")


class ProgressTracker:
    def __init__(self):
        self.active = False
        self.current_step = 0
        self.total_steps = 0
        self.start_time = None
        self.elapsed_time = 0.0
        self.estimated_time_remaining = 0.0

    def reset(self):
        self.active = False
        self.current_step = 0
        self.total_steps = 0
        self.start_time = None
        self.elapsed_time = 0.0
        self.estimated_time_remaining = 0.0

    def start(self, total_steps):
        self.active = True
        self.current_step = 0
        self.total_steps = total_steps
        self.start_time = time.time()
        self.elapsed_time = 0.0
        self.estimated_time_remaining = 0.0

    def update(self, current, total):
        self.current_step = current
        self.total_steps = total
        if not self.active:
            self.active = True
            self.start_time = time.time()
            
        if self.start_time is None:
            self.start_time = time.time()
            
        now = time.time()
        self.elapsed_time = now - self.start_time
        
        if current > 0:
            avg_time_per_step = self.elapsed_time / current
            remaining_steps = total - current
            self.estimated_time_remaining = avg_time_per_step * remaining_steps
        else:
            self.estimated_time_remaining = 0.0

    def to_dict(self):
        percentage = 0.0
        if self.total_steps > 0:
            percentage = (self.current_step / self.total_steps) * 100
        return {
            "active": self.active,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "percentage": round(percentage, 1),
            "elapsed_time": round(self.elapsed_time, 1),
            "estimated_time_remaining": round(self.estimated_time_remaining, 1)
        }


class Int8FastRuntime(BaseRuntime):
    def __init__(self):
        self._warmed_up = False
        self._vae = None
        self._clip = None
        self._unet_cond = None
        self._unet_uncond = None
        self.progress_tracker = ProgressTracker()

    @property
    def name(self) -> str:
        return "int8_fast"

    def health(self) -> dict:
        return {
            "warmed_up": self._warmed_up,
            "backend": "int8_fast_w8a8_comfyui",
            "ready": self._warmed_up and (self._vae is not None)
        }

    def get_progress(self) -> dict:
        return self.progress_tracker.to_dict()

    def warmup(self) -> None:
        logger.info("Initializing Custom INT8 Fast Runtime (ComfyUI Core / OTUNetLoaderW8A8 mode)...")
        
        # Dynamically locate ComfyUI directory
        comfyui_path = os.getenv("COMFYUI_PATH")
        if not comfyui_path:
            models_path = Path(settings.models_path).absolute()
            # Search upwards for 'ComfyUI' or 'models' directory to find the base ComfyUI directory
            found = False
            for parent in [models_path] + list(models_path.parents):
                if parent.name.lower() == "comfyui":
                    comfyui_path = str(parent)
                    found = True
                    break
            if not found:
                for parent in [models_path] + list(models_path.parents):
                    if parent.name.lower() == "models":
                        comfyui_path = str(parent.parent)
                        found = True
                        break
            if not found:
                comfyui_path = r"C:\Users\Riccardo\Desktop\ComfyUI"

        logger.info(f"Resolved ComfyUI path: {comfyui_path}")
        
        if os.path.exists(comfyui_path):
            if comfyui_path not in sys.path:
                sys.path.append(comfyui_path)

            # Register the hyphenated custom nodes directory as a pseudo package
            pkg_dir = os.path.join(comfyui_path, "custom_nodes", "ComfyUI-INT8-Fast")
            if os.path.exists(pkg_dir) and "ComfyUI_INT8_Fast" not in sys.modules:
                pkg = types.ModuleType("ComfyUI_INT8_Fast")
                pkg.__path__ = [pkg_dir]
                pkg.__file__ = os.path.join(pkg_dir, "__init__.py")
                sys.modules["ComfyUI_INT8_Fast"] = pkg
                try:
                    spec = importlib.util.spec_from_file_location("ComfyUI_INT8_Fast", os.path.join(pkg_dir, "__init__.py"))
                    if spec and spec.loader:
                        spec.loader.exec_module(pkg)
                        logger.info("ComfyUI_INT8_Fast package registered successfully.")
                except Exception as e:
                    logger.error(f"Failed to load ComfyUI_INT8_Fast package: {e}")
        else:
            logger.warning(f"ComfyUI path does not exist: {comfyui_path}")

        missing = ModelRegistry.get_missing_files()
        if missing:
            logger.warning(f"Required INT8 models not found: {list(missing.keys())}. Launching backend in Simulation Mode.")
            self._warmed_up = True
            return

        try:
            import comfy.model_management
            import comfy.utils
            import nodes
            import folder_paths
            from ComfyUI_INT8_Fast import int8_unet_loader

            paths = ModelRegistry.get_paths()
            
            # Register directories in ComfyUI folder paths registry
            folder_paths.add_model_folder_path("vae", str(paths["vae"].parent))
            folder_paths.add_model_folder_path("text_encoders", str(paths["text_encoder"].parent))
            folder_paths.add_model_folder_path("diffusion_models", str(paths["main_model"].parent))

            logger.info(f"Loading VAE from: {paths['vae'].name} ...")
            vae_loader = nodes.VAELoader()
            self._vae = vae_loader.load_vae(paths["vae"].name)[0]
            logger.info("VAE model loaded successfully.")

            logger.info(f"Loading CLIP text encoder: {paths['text_encoder'].name} ...")
            clip_loader = nodes.CLIPLoader()
            self._clip = clip_loader.load_clip(paths["text_encoder"].name, "ideogram4")[0]
            logger.info("CLIP loaded successfully.")

            logger.info(f"Loading INT8 UNet Conditional: {paths['main_model'].name} ...")
            unet_loader = int8_unet_loader.UNetLoaderINTW8A8()
            self._unet_cond = unet_loader.load_unet(
                unet_name=paths["main_model"].name,
                weight_dtype="default",
                model_type="ideogram4",
                on_the_fly_quantization=False,
                enable_convrot=True,
                lora_mode="None"
            )[0]
            logger.info("Conditional UNet loaded successfully.")

            logger.info(f"Loading INT8 UNet Unconditional: {paths['uncond_model'].name} ...")
            self._unet_uncond = unet_loader.load_unet(
                unet_name=paths["uncond_model"].name,
                weight_dtype="default",
                model_type="ideogram4",
                on_the_fly_quantization=False,
                enable_convrot=True,
                lora_mode="None"
            )[0]
            logger.info("Unconditional UNet loaded successfully.")

            # Force comfy_cast_weights = True on the UNets for offloading support
            logger.info("Applying cast weights flag for RTX 3060/12GB offloading compatibility...")
            for model in [self._unet_cond, self._unet_uncond]:
                for name, module in model.model.named_modules():
                    if hasattr(module, "comfy_cast_weights"):
                        module.comfy_cast_weights = True

            # Register progress hook
            def comfy_progress_hook(current, total, preview, node_id=None):
                self.progress_tracker.update(current, total)
            comfy.utils.set_progress_bar_global_hook(comfy_progress_hook)
            logger.info("Progress bar hook configured successfully.")

            self._warmed_up = True
            logger.info("Custom INT8 Fast Runtime successfully loaded and ready.")
        except Exception as e:
            logger.error(f"Error loading INT8 models: {e}. Falling back to simulation.", exc_info=True)
            self._warmed_up = True

    def generate(self, request: GenerationRequest) -> GenerationResult:
        start_time = time.time()
        logger.info(f"Running generation on custom INT8 runtime. Prompt: {request.prompt[:50]}")

        # Fall back to simulation if models are not loaded
        if self._vae is None:
            logger.warning("No models loaded. Running in Simulation Mode.")
            return self._generate_simulation(request, start_time)

        # Initialize progress tracker
        self.progress_tracker.reset()
        self.progress_tracker.start(request.steps + 1)

        try:
            import comfy.model_management
            import nodes
            import comfy_extras.nodes_model_advanced
            import comfy_extras.nodes_custom_sampler
            import comfy_extras.nodes_flux
            import comfy_extras.nodes_ideogram4

            with torch.no_grad():
                # Step 1: Shifting Model Sampling
                logger.info("Step 1: Shifting Model Sampling...")
                unet_cond_shifted = comfy_extras.nodes_model_advanced.ModelSamplingAuraFlow().patch_aura(self._unet_cond, shift=5.0)[0]

                # Step 2: Applying CFG Override
                logger.info("Step 2: Applying CFG Override...")
                unet_cond_override = comfy_extras.nodes_custom_sampler.CFGOverride().execute(
                    unet_cond_shifted, 
                    cfg=3.0, 
                    start_percent=0.7, 
                    end_percent=1.0
                )[0]

                # Step 3: Text Encoding prompt
                logger.info("Step 3: Text Encoding prompt...")
                cond_positive = nodes.CLIPTextEncode().encode(self._clip, request.prompt)[0]
                cond_negative = nodes.ConditioningZeroOut().zero_out(cond_positive)[0]

                # Step 4: Creating Dual Model Guider
                logger.info("Step 4: Creating Dual Model Guider...")
                guider = comfy_extras.nodes_custom_sampler.DualModelGuider().execute(
                    model=unet_cond_override,
                    positive=cond_positive,
                    cfg=7.0,
                    model_negative=self._unet_uncond,
                    negative=cond_negative
                )[0]

                # Step 5: Setup Noise & Empty Latent
                logger.info("Step 5: Setup Noise & Empty Latent...")
                seed = request.seed if request.seed is not None else int(time.time() * 1000) % 2**31
                noise = comfy_extras.nodes_custom_sampler.RandomNoise().execute(noise_seed=seed)[0]
                latent_image = comfy_extras.nodes_flux.EmptyFlux2LatentImage().execute(
                    width=request.width, 
                    height=request.height, 
                    batch_size=1
                )[0]

                # Step 6: Getting Scheduler Sigmas
                logger.info("Step 6: Getting Scheduler Sigmas...")
                sigmas = comfy_extras.nodes_ideogram4.ideogram4_sigmas(
                    num_steps=request.steps, 
                    width=request.width, 
                    height=request.height, 
                    mu=request.mu, 
                    std=request.std
                )

                # Step 7: Extending Intermediate Sigmas
                logger.info("Step 7: Extending Intermediate Sigmas...")
                sigmas_extended = comfy_extras.nodes_custom_sampler.ExtendIntermediateSigmas().execute(
                    sigmas=sigmas,
                    steps=2,
                    start_at_sigma=1.0,
                    end_at_sigma=0.98,
                    spacing="linear"
                )[0]

                # Step 8: KSampler Select
                logger.info("Step 8: KSampler Select...")
                sampler = comfy_extras.nodes_custom_sampler.KSamplerSelect().execute(sampler_name="euler")[0]

                # Step 8.3: Ensure comfy_cast_weights = True is applied to all modules
                logger.info("Step 8.3: Setting comfy_cast_weights = True for offloading support...")
                for model in [unet_cond_override, self._unet_uncond]:
                    for name, module in model.model.named_modules():
                        if hasattr(module, "comfy_cast_weights"):
                            module.comfy_cast_weights = True

                # Step 8.5: Move models to GPU
                logger.info("Step 8.5: Loading models onto GPU...")
                comfy.model_management.load_models_gpu([unet_cond_override, self._unet_uncond])

                # Step 9: Running Denoising Loop
                logger.info("Step 9: Running Denoising Loop...")
                out_latent, out_denoised = comfy_extras.nodes_custom_sampler.SamplerCustomAdvanced().execute(
                    noise=noise,
                    guider=guider,
                    sampler=sampler,
                    sigmas=sigmas_extended,
                    latent_image=latent_image
                )

                # Step 10: Decoding Latent with VAE
                logger.info("Step 10: Decoding Latent with VAE...")
                decoded = nodes.VAEDecode().decode(self._vae, out_latent)[0]

                # Step 11: Converting output tensor to PIL Image
                logger.info("Step 11: Saving Image...")
                i = 255. * decoded[0].cpu().numpy()
                img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

                time_taken = time.time() - start_time
                
                # Save using OutputStore
                history_item = OutputStore.save_generation(
                    image=img,
                    prompt=request.prompt,
                    preset=request.preset,
                    width=request.width,
                    height=request.height,
                    seed=seed,
                    metadata={
                        "runtime": self.name,
                        "time_taken": time_taken,
                        "quantization": "W8A8_tensorwise",
                        "scheduler": {"steps": request.steps, "mu": request.mu, "std": request.std}
                    }
                )

                logger.info(f"Generation successful. Job ID: {history_item.job_id}")
                return GenerationResult(
                    job_id=history_item.job_id,
                    image_url=history_item.image_url,
                    seed=seed,
                    time_taken=time_taken,
                    success=True,
                    metadata=history_item.metadata
                )

        except Exception as e:
            logger.error(f"Inference execution failed: {e}", exc_info=True)
            return GenerationResult(
                job_id="",
                image_url="",
                seed=0,
                time_taken=time.time() - start_time,
                success=False,
                error=str(e),
                metadata={}
            )
        finally:
            self.progress_tracker.active = False

    def _generate_simulation(self, request: GenerationRequest, start_time: float) -> GenerationResult:
        # Initialize progress tracker
        self.progress_tracker.reset()
        self.progress_tracker.start(request.steps)
        
        # Simulate steps
        for step in range(1, request.steps + 1):
            time.sleep(1.8 / request.steps)
            self.progress_tracker.update(step, request.steps)
        
        # Draw elegant layout representation
        img = Image.new("RGB", (request.width, request.height), color=(10, 10, 14))
        draw = ImageDraw.Draw(img)
        
        # Styled modern grid preview background
        draw.rectangle([10, 10, request.width - 10, request.height - 10], outline=(40, 42, 60), width=1)
        
        # Generate custom layout aesthetics
        for y in range(request.height):
            # elegant linear vertical gradient
            r = int(12 + (y / request.height) * 12)
            g = int(12 + (y / request.height) * 14)
            b = int(18 + (y / request.height) * 25)
            for x in range(request.width):
                if 10 < x < request.width - 10 and 10 < y < request.height - 10:
                    img.putpixel((x, y), (r, g, b))
                    
        # Aesthetic circular glow element
        draw.ellipse([request.width//4, request.height//4, 3*request.width//4, 3*request.height//4], outline=(35, 45, 75), width=2)
        
        # Metadata drawing
        draw.text((30, 40), "IDEOGRAM 4 (Simulation Mode)", fill=(200, 220, 255))
        draw.text((30, 70), f"Prompt: {request.prompt[:60]}...", fill=(120, 130, 150))
        draw.text((30, 100), f"Resolution: {request.width} x {request.height}", fill=(90, 100, 120))
        draw.text((30, 130), f"Preset: {request.preset.upper()} (steps={request.steps}, mu={request.mu}, std={request.std})", fill=(90, 100, 120))
        
        seed = request.seed if request.seed is not None else 777
        time_taken = time.time() - start_time
        
        history_item = OutputStore.save_generation(
            image=img,
            prompt=request.prompt,
            preset=request.preset,
            width=request.width,
            height=request.height,
            seed=seed,
            metadata={
                "runtime": self.name,
                "time_taken": time_taken,
                "quantization": "Simulation",
                "scheduler": {"steps": request.steps, "mu": request.mu, "std": request.std}
            }
        )
        
        self.progress_tracker.active = False
        
        return GenerationResult(
            job_id=history_item.job_id,
            image_url=history_item.image_url,
            seed=seed,
            time_taken=time_taken,
            success=True,
            metadata=history_item.metadata
        )
