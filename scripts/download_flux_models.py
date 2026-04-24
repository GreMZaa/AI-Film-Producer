import os
from huggingface_hub import hf_hub_download

def download_models(comfy_path):
    print(f"🚀 Starting model download for ComfyUI at: {comfy_path}")
    
    models = [
        {
            "repo_id": "city96/FLUX.1-schnell-gguf",
            "filename": "flux1-schnell-Q4_K_S.gguf",
            "subfolder": "models/unet"
        },
        {
            "repo_id": "comfyanonymous/flux_vae",
            "filename": "ae.safetensors",
            "subfolder": "models/vae"
        },
        {
            "repo_id": "comfyanonymous/flux_text_encoders",
            "filename": "clip_l.safetensors",
            "subfolder": "models/clip"
        },
        {
            "repo_id": "comfyanonymous/flux_text_encoders",
            "filename": "t5xxl_fp8_e4m3fn.safetensors",
            "subfolder": "models/clip"
        }
    ]

    for m in models:
        target_dir = os.path.join(comfy_path, m["subfolder"])
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, m["filename"])
        
        if os.path.exists(target_path):
            print(f"✅ {m['filename']} already exists.")
            continue
            
        print(f"📥 Downloading {m['filename']}...")
        hf_hub_download(
            repo_id=m["repo_id"],
            filename=m["filename"],
            local_dir=target_dir,
            local_dir_use_symlinks=False
        )

if __name__ == "__main__":
    path = input("Enter your ComfyUI absolute path (e.g., D:\\ComfyUI): ")
    if os.path.exists(path):
        download_models(path)
    else:
        print("❌ Invalid path.")
