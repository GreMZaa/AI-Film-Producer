import os
from huggingface_hub import hf_hub_download
import requests
from tqdm import tqdm

def download_file(url, target_path):
    if os.path.exists(target_path):
        print(f"✅ {os.path.basename(target_path)} already exists.")
        return
    
    print(f"🚀 Downloading {os.path.basename(target_path)} from direct link...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code != 200:
            print(f"❌ Failed to download from {url}: {response.status_code}")
            return
            
        total_size = int(response.headers.get('content-length', 0))
        
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        with open(target_path, "wb") as f, tqdm(
            total=total_size, unit='iB', unit_scale=True, desc=os.path.basename(target_path)
        ) as pbar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                pbar.update(size)
    except Exception as e:
        print(f"❌ Download error: {e}")

def smart_download(repo_list, filename, local_dir):
    """Tries to download a file from a list of repositories."""
    os.makedirs(local_dir, exist_ok=True)
    target_path = os.path.join(local_dir, filename)
    
    if os.path.exists(target_path):
        print(f"✅ {filename} already exists in {local_dir}.")
        return True

    for repo_id in repo_list:
        print(f"🔍 Attempting to download {filename} from {repo_id}...")
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=local_dir,
                local_dir_use_symlinks=False
            )
            print(f"✅ Successfully downloaded {filename} from {repo_id}")
            return True
        except Exception as e:
            # Check for gated access error
            if "gated" in str(e).lower() or "401" in str(e) or "403" in str(e):
                print(f"⚠️ Access denied for {repo_id} (Gated or private).")
            else:
                print(f"⚠️ Failed from {repo_id}: {e}")
            continue
    
    return False

def setup_phase4_models():
    # 1. SVD for ComfyUI
    comfy_path = "D:\\ComfyUI"
    svd_dir = os.path.join(comfy_path, "models", "checkpoints")
    svd_filename = "svd_xt_1_1.safetensors"
    
    # List of repos to try for SVD
    svd_repos = [
        "frizylabs/stable-video-diffusion-img2vid-xt-1-1", # Often public
        "vdo/stable-video-diffusion-img2vid-xt-1-1",
        "stabilityai/stable-video-diffusion-img2vid-xt-1-1" # Gated, try last
    ]
    
    print("\n--- 1. SETTING UP SVD XT 1.1 ---")
    if not smart_download(svd_repos, svd_filename, svd_dir):
        print("❌ All SVD download attempts failed. You may need to manualy download it to D:\\ComfyUI\\models\\checkpoints\\svd_xt_1_1.safetensors")

    # 2. Wav2Lip GAN
    wav2lip_dir = r"c:\Users\Admin\Desktop\Video\src\local_server\wav2lip\checkpoints"
    wav2lip_repos = [
        "Nekochu/Wav2Lip",
        "numz/wav2lip_studio",
        "camenduru/Wav2Lip"
    ]
    
    print("\n--- 2. SETTING UP Wav2Lip GAN ---")
    if not smart_download(wav2lip_repos, "wav2lip_gan.pth", wav2lip_dir):
        print("❌ Wav2Lip GAN download failed.")

    # 3. S3FD Face Detection
    s3fd_repos = [
        "rippertnt/wav2lip",
        "Cong-HGMedia/facedetection",
        "camenduru/facexlib"
    ]
    
    print("\n--- 3. SETTING UP S3FD ---")
    if not smart_download(s3fd_repos, "s3fd.pth", wav2lip_dir):
        print("❌ S3FD download failed.")

if __name__ == "__main__":
    setup_phase4_models()
