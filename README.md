# Ideogram 4 Local Studio

An elegant, standalone local control room for Ideogram 4, completely decoupled from ComfyUI. This app runs a Python FastAPI backend API combined with a custom high-performance runtime for loading and executing INT8 checkpoints (`ideogram4-int8-ConvRot`, `ideogram4-unconditional-int8-ConvRot`), the Qwen text encoder (`qwen3vl_8b_fp8_scaled`), and Flux VAE.

## Architecture

- **Frontend**: A highly polished single-page interface with real-time hardware status metrics, preset quick-buttons, guided JSON mode, and image generation history.
- **Backend API**: REST service routing endpoints for job scheduling, parameter rendering, status checks, and file history.
- **Inference Engine**: Custom standalone integration implementing Flow Matching schedulers and quantized INT8 ops.

---

## Setup Instructions

1. **Prerequisites**:
   Ensure you have Python 3.10+ and an NVIDIA GPU with CUDA installed.

2. **Installation**:
   Create a virtual environment and install the required Python packages:

   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Download Model Weights**:
   The custom INT8 inference engine requires the following models, text encoder, and VAE. Download them from Hugging Face and place them in your preferred directories:

   *   **Text Encoder (Qwen-3VL 8B FP8 Scaled)**
       *   File: `qwen3vl_8b_fp8_scaled.safetensors`
       *   Download Link: [Download Text Encoder](https://huggingface.co/Comfy-Org/Ideogram-4/resolve/main/text_encoders/qwen3vl_8b_fp8_scaled.safetensors?download=true)
   *   **Conditional UNet Model (Ideogram 4 INT8)**
       *   File: `ideogram4-int8-ConvRot.safetensors`
       *   Download Link: [Download Conditional UNet](https://huggingface.co/bertbobson/Ideogram-4-INT8-ConvRot/resolve/main/ideogram4-int8-ConvRot.safetensors?download=true)
   *   **Unconditional UNet Model (Ideogram 4 INT8 Unconditional)**
       *   File: `ideogram4-unconditional-int8-ConvRot.safetensors`
       *   Download Link: [Download Unconditional UNet](https://huggingface.co/bertbobson/Ideogram-4-INT8-ConvRot/resolve/main/ideogram4-unconditional-int8-ConvRot.safetensors?download=true)
   *   **Flux VAE**
       *   File: `flux2-vae.safetensors`
       *   Download Link: [Download Flux VAE](https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors?download=true)

4. **Configure Environment Paths**:
   Copy the `.env.example` file to `.env` and configure the absolute paths to your directories and files:

   ```env
   IDEOGRAM_MODELS_PATH=C:/path/to/your/models/diffusion_models
   IDEOGRAM_MAIN_MODEL=ideogram4-int8-ConvRot.safetensors
   IDEOGRAM_UNCOND_MODEL=ideogram4-unconditional-int8-ConvRot.safetensors
   IDEOGRAM_TEXT_ENCODER=C:/path/to/your/models/text_encoders/qwen3vl_8b_fp8_scaled.safetensors
   IDEOGRAM_VAE=C:/path/to/your/models/vae/flux2-vae.safetensors
   IDEOGRAM_OUTPUT_PATH=C:/path/to/your/outputs
   ```

5. **Verify Environment**:
   Run the CLI smoke test to make sure configuration and PyTorch environment are set up correctly:

   ```cmd
   python backend/smoke_test.py
   ```

6. **Start Application**:
   Run the batch launcher to boot the API backend and automatically open the studio:
   ```cmd
   start_all.bat
   ```
   Or manually launch the backend:
   ```cmd
   python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
   ```
   Then navigate to: `http://127.0.0.1:8000/frontend/ideogram-studio.html`
