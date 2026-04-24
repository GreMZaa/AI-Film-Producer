import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str = "your_token_here"
    LOCAL_SERVER_URL: str = "http://localhost:8000"
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    STORYBOARD_DIR: str = os.path.join(BASE_DIR, "outputs", "images")
    VIDEO_DIR: str = os.path.join(BASE_DIR, "outputs", "videos")
    AUDIO_DIR: str = os.path.join(BASE_DIR, "outputs", "audio")
    TEMP_DIR: str = os.path.join(BASE_DIR, "outputs", "temp")
    
    # Models Configuration
    LLM_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    COMFYUI_URL: str = "http://localhost:8188"
    IMAGE_MODEL: str = "flux1-schnell-Q4_K_S.gguf"
    IMAGE_STEPS: int = 4
    VIDEO_MODEL: str = "svd_xt_1_1.safetensors"
    VIDEO_FPS: int = 24
    
    # Paths for Phase 4
    WAV2LIP_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "local_server", "wav2lip")
    WAV2LIP_CHECKPOINT: str = os.path.join(WAV2LIP_PATH, "checkpoints", "wav2lip_gan.pth")
    FACE_DETECTION_CHECKPOINT: str = os.path.join(WAV2LIP_PATH, "checkpoints", "s3fd.pth")

    # Ngrok Configuration
    USE_NGROK: bool = False
    NGROK_AUTHTOKEN: str = ""
    NGROK_DOMAIN: str = ""
    
    # Phase 5: Economy & WebApp
    PAYMENT_PROVIDER_TOKEN: str = "" # To be filled in .env
    DATABASE_URL: str = "sqlite:///./data/ai_producer.db"
    
    @property
    def database_url_resolved(self) -> str:
        if os.environ.get("VERCEL"):
            return "sqlite:////tmp/ai_producer.db"
        return self.DATABASE_URL

    WEBAPP_URL: str = "" # Will be set to LOCAL_SERVER_URL + /webapp in main.py
    
    class Config:
        env_file = ".env"

settings = Settings()

# Ensure directories exist (only if not on Vercel)
if not os.environ.get("VERCEL"):
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.STORYBOARD_DIR, exist_ok=True)
    os.makedirs(settings.VIDEO_DIR, exist_ok=True)
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
