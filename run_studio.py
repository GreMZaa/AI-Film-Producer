import subprocess
import time
import sys
import os
import psutil
from pathlib import Path

def is_process_running(process_name):
    """Check if there is any running process that contains the given name."""
    for proc in psutil.process_iter(['name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def start_service(name, path, args=None):
    """Start a background service if not already running."""
    if is_process_running(name):
        print(f"✅ {name} is already running.")
        return None
    
    if not os.path.exists(path):
        print(f"❌ Could not find {name} at {path}")
        return None
    
    print(f"🚀 Starting {name}...")
    try:
        cmd = [path] + (args or [])
        return subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    except Exception as e:
        print(f"⚠️ Failed to start {name}: {e}")
        return None

def start_studio():
    print("\n--- 🎬 Garage Hollywood Studio Control Center ---")
    
    # 🔍 1. Start Ollama
    ollama_path = os.path.expandvars(r"%LOCALAPPDATA%\Ollama\ollama app.exe")
    start_service("Ollama", ollama_path)
    
    # 🔍 2. Start ComfyUI (Looking for portable or local install)
    comfy_path = None
    possible_comfy_paths = [
        Path.cwd().parent / "ComfyUI_windows_portable" / "run_nvidia_gpu.bat",
        Path.cwd() / "ComfyUI" / "main.py",
        Path.home() / "Desktop" / "ComfyUI_windows_portable" / "run_nvidia_gpu.bat"
    ]
    
    for p in possible_comfy_paths:
        if p.exists():
            comfy_path = str(p)
            break
            
    if comfy_path:
        if comfy_path.endswith(".py"):
            start_service("ComfyUI", sys.executable, [comfy_path])
        else:
            start_service("ComfyUI", comfy_path)
    else:
        print("⚠️ ComfyUI not found automatically. Please start it manually.")

    executable = sys.executable
    is_frozen = getattr(sys, 'frozen', False)
    
    # 🧹 Automated Cleanup
    print("🧹 Running maintenance cleanup...")
    try:
        if is_frozen:
            subprocess.run([executable, "--cleanup"], check=False)
        else:
            subprocess.run([sys.executable, "scripts/cleanup.py", "--dir", "outputs/temp", "--days", "7"], check=False)
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")

    # 🚀 3. Start Local API Server (GPU Support)
    print("🚀 Starting Local API Server...")
    if is_frozen:
        backend_proc = subprocess.Popen([executable, "--backend"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        backend_proc = subprocess.Popen([sys.executable, "-m", "src.local_server.main"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    # 🌐 Optional: Start Ngrok Tunnel
    from src.api.config import settings
    if settings.USE_NGROK and settings.NGROK_AUTHTOKEN:
        print("🌐 Starting Ngrok Tunnel...")
        try:
            from pyngrok import ngrok
            ngrok.set_auth_token(settings.NGROK_AUTHTOKEN)
            public_url = ngrok.connect(8000).public_url
            print(f"🌍 Public URL: {public_url}")
            print("📢 IMPORTANT: Set this URL as LOCAL_SERVER_URL in Vercel settings!")
        except Exception as e:
            print(f"⚠️ Ngrok failed to start: {e}")

    try:
        print("✅ Local Server is running. Keep this window open.")
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("❌ Backend crashed. Shutting down.")
                break
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    finally:
        backend_proc.terminate()
        if settings.USE_NGROK:
            from pyngrok import ngrok
            ngrok.disconnect()
            ngrok.kill()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--cleanup":
            try:
                from scripts.cleanup import cleanup_old_files
                from pathlib import Path
                project_root = Path(__file__).parent
                temp_dir = project_root / "outputs" / "temp"
                cleanup_old_files(str(temp_dir), days=7)
            except ImportError:
                print("⚠️ Cleanup script not found, skipping...")
        elif arg == "--backend":
            import uvicorn
            from src.local_server.main import app
            uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        start_studio()
