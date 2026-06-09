# Standalone Local Studio for Ideogram 4

An elegant, standalone local control room for Ideogram 4. This app runs a Python FastAPI backend API combined with a custom high-performance standalone runtime for loading and executing INT8 checkpoints (`ideogram4-int8-ConvRot`, `ideogram4-unconditional-int8-ConvRot`), the Qwen text encoder (`qwen3vl_8b_fp8_scaled`), and Flux VAE. It is backed by ComfyUI core, which is automatically installed, managed, and updated via the integrated Setup Wizard.

## Architecture

- **Frontend**: A highly polished single-page interface with real-time hardware status metrics, preset quick-buttons, guided JSON mode, and image generation history.
- **Backend API**: REST service routing endpoints for job scheduling, parameter rendering, status checks, and file history. Supports background download and automated updates for ComfyUI.
- **Inference Engine**: Standalone integration implementing Flow Matching schedulers and quantized INT8 ops.

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

3. **Start Application**:
   Run the batch launcher to boot the API backend and automatically open the studio:
   ```cmd
   start_all.bat
   ```
   Or manually launch the backend:
   ```cmd
   python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
   ```
   Then navigate to: `http://127.0.0.1:8000/frontend/ideogram-studio.html`

4. **Guided Setup (First Launch)**:
   At first startup, the Setup Wizard will help configure all components:
   - **Step 1: ComfyUI Core**: Simply click **Install Now** to automatically clone/download ComfyUI and its custom nodes to a local `./comfy_core` directory (ignored by git), or input a custom path if you have an existing install.
   - **Step 2: Model Weights**: Use the provided direct links to download required weights and place them inside the generated `./comfy_core/models` directories (e.g. `diffusion_models`, `text_encoders`, `vae`).
   - **Step 3: Test Run**: Click "Save & Start" to verify everything is working.

5. **Download Model Weights (Direct Links)**:
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

6. **Engine Updates**:
   You can update ComfyUI at any time from the **System Settings Control Center** (gear icon ⚙️). The app checks local commit hashes against the remote repository and displays a badge whenever an update is available. Simply click **Update Engine** to pull updates automatically.
