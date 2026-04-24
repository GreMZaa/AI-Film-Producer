from pydantic import BaseModel
from typing import List, Optional

class ScriptScene(BaseModel):
    scene_id: int
    description: str
    dialogue: str
    image_prompt: str
    image_url: Optional[str] = None

class ScriptResponse(BaseModel):
    title: str
    scenes: List[ScriptScene]
    director_comment: str

class ScriptRequest(BaseModel):
    brief: str
    user_id: int

class ImageRequest(BaseModel):
    prompt: str
    scene_id: int
    user_id: int

class ImageResponse(BaseModel):
    image_url: str
    scene_id: int

class RenderRequest(BaseModel):
    user_id: int
    project_title: str
    scenes: List[ScriptScene]

class RenderResponse(BaseModel):
    video_url: str
    status: str

class InpaintingRequest(BaseModel):
    image_url: str
    mask_base64: str
    prompt: str
    scene_id: int
    user_id: int

class InpaintingResponse(BaseModel):
    image_url: str
    scene_id: int
