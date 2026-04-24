import uvicorn
import json
import os
import torch
import uuid
import base64
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from src.api.schemas import (
    ScriptRequest, ScriptResponse, ImageRequest, ImageResponse, 
    RenderRequest, RenderResponse, ScriptScene, InpaintingRequest, InpaintingResponse
)
from src.local_server.comfy_client import comfy_client
from src.api.config import settings
from src.api.db import get_user, create_or_update_user
import logging
from pyngrok import ngrok
import time

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

# Ollama client for LLM
llm_client = OpenAI(
    base_url=settings.OLLAMA_BASE_URL,
    api_key="ollama",
)

@app.get("/")
async def root():
    return {"status": "running", "message": "Garage Hollywood is online. Ready for action."}

@app.get("/api/user-status/{user_id}")
async def get_user_status(user_id: int):
    user = get_user(user_id)
    if not user:
        # Create user if doesn't exist
        create_or_update_user(user_id)
        user = get_user(user_id)
    
    return {
        "user_id": user["user_id"],
        "is_premium": bool(user["is_premium"]),
        "subscription_type": user["subscription_type"],
        "priority_level": user["priority_level"]
    }

@app.post("/generate-script", response_model=ScriptResponse)
async def generate_script(request: ScriptRequest):
    logger.info(f"Generating script for brief: {request.brief}")
    
    system_prompt = """
    You are a sarcastic, underground independent film director. You think mainstream cinema is dead and only raw, 
    low-budget art matters. You talk like a tired professional who has seen it all.
    
    Task: Turn the user's brief into a script with 3-5 scenes.
    
    IMPORTANT: You must output a valid JSON object. Every scene in the "scenes" array MUST have these 4 fields:
    1. "scene_id": integer
    2. "description": string (visual story beats)
    3. "dialogue": string (what characters say, or "Silent" if no speech)
    4. "image_prompt": string (highly detailed technical prompt for FLUX.1 image generation)
    
    Example Output:
    {
      "title": "Rainy Night Blues",
      "director_comment": "We'll shoot this in one take. If the actor coughs, we keep it.",
      "scenes": [
        {
          "scene_id": 1,
          "description": "A man in a trench coat stands under a flickering street lamp.",
          "dialogue": "I've been waiting for you, Marlowe.",
          "image_prompt": "Cinematic film still, 35mm, noir style, high contrast, rainy street, flickering yellow light, man in trench coat, extreme detail"
        }
      ]
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
        
        raw_content = response.choices[0].message.content
        logger.info(f"Raw LLM Response: {raw_content}")
        script_data = json.loads(raw_content)
        
        scenes = []
        for s in script_data.get("scenes", []):
            # Ensure fields exist or provide defaults to avoid Pydantic errors if model slips up
            if "description" not in s: s["description"] = "Cinematic scene"
            if "dialogue" not in s: s["dialogue"] = "Silent"
            if "image_prompt" not in s: s["image_prompt"] = s.get("description", "Cinematic shot")
            scenes.append(ScriptScene(**s))

        return ScriptResponse(
            title=script_data.get("title", "Untitled Masterpiece"),
            scenes=scenes,
            director_comment=script_data.get("director_comment", "Just shoot it. Don't ask questions.")
        )
        
    except Exception as e:
        logger.error(f"LLM Error: {str(e)}")
        if 'raw_content' in locals():
            logger.error(f"Raw content that failed: {raw_content}")
        raise HTTPException(status_code=500, detail=f"Director is having a breakdown: {str(e)}")

@app.post("/generate-image", response_model=ImageResponse)
async def generate_image(request: ImageRequest):
    logger.info(f"Generating image for scene {request.scene_id} using prompt: {request.prompt}")
    
    try:
        # Save image with unique filename
        filename = f"user_{request.user_id}_scene_{request.scene_id}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(settings.STORYBOARD_DIR, filename)
        
        # Use ComfyUI client
        result_path = comfy_client.generate_image_sync(request.prompt, filepath)
        
        if not result_path:
            raise Exception("ComfyUI failed to return an image")
        
        # Construct URL
        image_url = f"{settings.LOCAL_SERVER_URL}/static/images/{filename}"
        
        return ImageResponse(
            image_url=image_url,
            scene_id=request.scene_id
        )
        
    except Exception as e:
        logger.error(f"Image Gen Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"The camera is broken: {str(e)}")


@app.post("/api/inpainting", response_model=InpaintingResponse)
async def inpaint_image(request: InpaintingRequest):
    logger.info(f"Inpainting request for user {request.user_id}, scene {request.scene_id}")
    
    # Priority check
    user = get_user(request.user_id)
    if not user or not user["is_premium"]:
        # Allow a few free trials? No, let's keep it premium as requested for TMA
        # logger.warning(f"Free user {request.user_id} tried to inpaint.")
        # But for now, let's just prioritize. 
        # If user is not indie, maybe limit them? 
        if user and user["subscription_type"] == "bootleg":
             logger.info("Priority user (Bootleg) processing...")
        elif user and user["subscription_type"] == "indie":
             logger.info("Legendary user (Indie) processing...")
        else:
             logger.info("Free user processing with low priority...")
             time.sleep(2) # Simulate queue
    
    try:
        # 1. Prepare paths
        img_filename = os.path.basename(request.image_url)
        local_image_path = os.path.join(settings.STORYBOARD_DIR, img_filename)
        
        mask_filename = f"mask_{uuid.uuid4().hex[:8]}.png"
        mask_path = os.path.join(settings.TEMP_DIR, mask_filename)
        
        # 2. Decode mask
        mask_data = base64.b64decode(request.mask_base64.split(",")[-1])
        with open(mask_path, "wb") as f:
            f.write(mask_data)
            
        # 3. Process with ComfyUI
        output_filename = f"user_{request.user_id}_scene_{request.scene_id}_inpainted_{uuid.uuid4().hex[:4]}.png"
        output_path = os.path.join(settings.STORYBOARD_DIR, output_filename)
        
        result_path = comfy_client.generate_inpainting_sync(
            local_image_path, mask_path, request.prompt, output_path
        )
        
        if not result_path:
            raise Exception("Inpainting failed in ComfyUI")
            
        image_url = f"{settings.LOCAL_SERVER_URL}/static/images/{output_filename}"
        
        return InpaintingResponse(
            image_url=image_url,
            scene_id=request.scene_id
        )
        
    except Exception as e:
        logger.error(f"Inpainting Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"The paintbrush is broken: {str(e)}")

# Mount WebApp (after build)
webapp_dist = os.path.join(settings.BASE_DIR, "src", "webapp", "dist")
if os.path.exists(webapp_dist):
    app.mount("/webapp", StaticFiles(directory=webapp_dist, html=True), name="webapp")
    logger.info(f"Mounted Mini App at /webapp")

@app.post("/start-render", response_model=RenderResponse)
async def start_render(request: RenderRequest):
    logger.info(f"Starting render for project: {request.project_title}")
    
    try:
        from src.local_server.renderer import renderer
        
        # In a real scenario, we might want to run this in a background task
        # since it can take several minutes. For this indy-dev scale, we'll do it sync
        # or use BackgroundTasks.
        
        # Priority check
        user = get_user(request.user_id)
        is_premium = bool(user["is_premium"]) if user else False
        
        # Convert Pydantic models to dictionaries for the renderer
        scenes_data = [s.dict() for s in request.scenes]
        output_path = renderer.assemble_final_movie(scenes_data, request.user_id, is_premium=is_premium)
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
    if settings.USE_NGROK:
        port = 8000
        if settings.NGROK_AUTHTOKEN:
            ngrok.set_auth_token(settings.NGROK_AUTHTOKEN)
        
        connect_kwargs = {"addr": port}
        if settings.NGROK_DOMAIN:
            connect_kwargs["domain"] = settings.NGROK_DOMAIN
            
        public_url = ngrok.connect(**connect_kwargs).public_url
        logger.info(f"🚀 NGROK Tunnel established at: {public_url}")
        print(f"\n✨ PUBLIC URL: {public_url} ✨\n")
        # Update settings dynamically for the session
        settings.LOCAL_SERVER_URL = public_url

    uvicorn.run(app, host="0.0.0.0", port=8000)
