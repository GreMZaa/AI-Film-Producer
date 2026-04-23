import uvicorn
import json
import os
import torch
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from diffusers import FluxPipeline
from src.api.schemas import ScriptRequest, ScriptResponse, ImageRequest, ImageResponse, RenderRequest, RenderResponse, ScriptScene
from src.api.config import settings
import logging
from pyngrok import ngrok

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Producer Local Server")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets
app.mount("/static/images", StaticFiles(directory=settings.STORYBOARD_DIR), name="images")
app.mount("/static/videos", StaticFiles(directory=settings.VIDEO_DIR), name="videos")

# Initialize LLM Client
llm_client = OpenAI(
    base_url=settings.OLLAMA_BASE_URL,
    api_key="ollama",
)

# Global pipeline variable for lazy loading
image_pipe = None

def get_image_pipe():
    global image_pipe
    if image_pipe is None:
        logger.info(f"Loading image model: {settings.IMAGE_MODEL}...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if device == "cuda" else torch.float32
        
        try:
            image_pipe = FluxPipeline.from_pretrained(
                settings.IMAGE_MODEL, 
                torch_dtype=dtype
            ).to(device)
            logger.info("Image model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load image model: {e}")
            raise e
    return image_pipe

@app.get("/")
async def root():
    return {"status": "running", "message": "Garage Hollywood is online. Ready for action."}

@app.post("/generate-script", response_model=ScriptResponse)
async def generate_script(request: ScriptRequest):
    logger.info(f"Generating script for brief: {request.brief}")
    
    system_prompt = """
    You are a sarcastic, underground independent film director. You think mainstream cinema is dead and only raw, 
    low-budget art matters. You talk like a tired professional who has seen it all.
    
    Task: Turn the user's brief into a script with 3-5 scenes.
    Each scene must have:
    - scene_id (int)
    - description (visual description of the action)
    - dialogue (the lines spoken, or 'Silent' if no speech)
    - image_prompt (a technical prompt for FLUX/Stable Diffusion to generate a cinematic storyboard frame. 
      Include lighting, angle, and style like 'gritty indie film', 'handheld camera', 'natural lighting').
    
    Output ONLY a valid JSON in the following format:
    {
      "title": "Movie Title",
      "scenes": [
        {"scene_id": 1, "description": "...", "dialogue": "...", "image_prompt": "..."},
        ...
      ],
      "director_comment": "Your sarcastic take on why this is 'real art'."
    }
    """
    
    try:
        response = llm_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Brief: {request.brief}"}
            ],
            response_format={"type": "json_object"}
        )
        
        script_data = json.loads(response.choices[0].message.content)
        
        return ScriptResponse(
            title=script_data.get("title", "Untitled Masterpiece"),
            scenes=[ScriptScene(**s) for s in script_data.get("scenes", [])],
            director_comment=script_data.get("director_comment", "Just shoot it. Don't ask questions.")
        )
        
    except Exception as e:
        logger.error(f"LLM Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Director is having a breakdown: {str(e)}")

@app.post("/generate-image", response_model=ImageResponse)
async def generate_image(request: ImageRequest):
    logger.info(f"Generating image for scene {request.scene_id} using prompt: {request.prompt}")
    
    try:
        pipe = get_image_pipe()
        
        # Generate image
        image = pipe(
            request.prompt,
            num_inference_steps=settings.IMAGE_STEPS,
            guidance_scale=3.5,
            height=768,
            width=1024
        ).images[0]
        
        # Save image
        filename = f"user_{request.user_id}_scene_{request.scene_id}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(settings.STORYBOARD_DIR, filename)
        image.save(filepath)
        
        # Construct URL (assuming local server is accessible)
        # Note: In production, settings.LOCAL_SERVER_URL should be the public URL
        image_url = f"{settings.LOCAL_SERVER_URL}/static/images/{filename}"
        
        return ImageResponse(
            image_url=image_url,
            scene_id=request.scene_id
        )
        
    except Exception as e:
        logger.error(f"Image Gen Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"The camera is broken: {str(e)}")

@app.post("/start-render", response_model=RenderResponse)
async def start_render(request: RenderRequest):
    logger.info(f"Starting render for project: {request.project_title}")
    
    try:
        from src.local_server.renderer import renderer
        
        # Unload image pipe to free memory for video/audio
        global image_pipe
        if image_pipe is not None:
            logger.info("Unloading image model for rendering...")
            image_pipe = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        # In a real scenario, we might want to run this in a background task
        # since it can take several minutes. For this indy-dev scale, we'll do it sync
        # or use BackgroundTasks.
        
        # Prepare scenes data for renderer
        scenes_data = [scene.dict() for scene in request.scenes]
        
        output_path = renderer.assemble_final_movie(scenes_data, request.user_id)
        filename = os.path.basename(output_path)
        
        video_url = f"{settings.LOCAL_SERVER_URL}/static/videos/{filename}"
        
        return RenderResponse(
            video_url=video_url,
            status="completed"
        )
        
    except Exception as e:
        logger.error(f"Render Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"The editing room is on fire: {str(e)}")

if __name__ == "__main__":
    # Start ngrok tunnel if enabled
    use_ngrok = os.getenv("USE_NGROK", "False").lower() == "true"
    if use_ngrok:
        port = 8000
        authtoken = os.getenv("NGROK_AUTHTOKEN")
        if authtoken:
            ngrok.set_auth_token(authtoken)
        
        public_url = ngrok.connect(port).public_url
        logger.info(f"🚀 NGROK Tunnel established at: {public_url}")
        print(f"\n✨ PUBLIC URL: {public_url} ✨\n")
        # Update settings dynamically for the session
        settings.LOCAL_SERVER_URL = public_url

    uvicorn.run(app, host="0.0.0.0", port=8000)
