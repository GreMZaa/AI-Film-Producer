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
    
    # Models Configuration
    LLM_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    IMAGE_MODEL: str = "black-forest-labs/FLUX.1-schnell"
    VIDEO_MODEL: str = "stabilityai/stable-video-diffusion-img2vid-xt"
    TTS_MODEL: str = "suno/bark"
    IMAGE_STEPS: int = 4
    
    class Config:
        env_file = ".env"

settings = Settings()

# Ensure directories exist (only if not on Vercel)
if not os.environ.get("VERCEL"):
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.STORYBOARD_DIR, exist_ok=True)
    os.makedirs(settings.VIDEO_DIR, exist_ok=True)
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)
