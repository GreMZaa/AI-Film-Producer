import os
import subprocess
import requests
from tqdm import tqdm

def download_file(url, filename):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    with open(filename, 'wb') as f:
        for data in response.iter_content(block_size):
            f.write(data)

def setup_wav2lip():
    repo_url = "https://github.com/Rudrabha/Wav2Lip.git"
    target_dir = "src/local_server/wav2lip"
    
    if not os.path.exists(target_dir):
        print(f"Cloning Wav2Lip into {target_dir}...")
        subprocess.run(["git", "clone", repo_url, target_dir], check=True)
    
    # Check for weights
    weights_dir = os.path.join(target_dir, "checkpoints")
    os.makedirs(weights_dir, exist_ok=True)
    
    # Note: These are large files. Usually we ask the user to download them.
    # But for a true "Agentic" experience, I'll provide the info.
    print("Wav2Lip repo ready. Weights need to be downloaded manually due to size/auth:")
    print("1. wav2lip_gan.pth -> checkpoints/")
    print("2. face_detection_model.pth -> face_detection/detection/s3fd.pth")

if __name__ == "__main__":
    setup_wav2lip()
