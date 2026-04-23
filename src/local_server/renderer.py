import os
import torch
import uuid
import logging
from diffusers import StableVideoDiffusionPipeline
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
from src.api.config import settings
from PIL import Image

logger = logging.getLogger(__name__)

class MovieRenderer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.video_pipe = None
        # TTS and Wav2Lip would be initialized here or loaded lazily

    def load_video_model(self):
        if self.video_pipe is None:
            logger.info("Loading SVD model...")
            self.video_pipe = StableVideoDiffusionPipeline.from_pretrained(
                settings.VIDEO_MODEL, 
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                variant="fp16" if self.device == "cuda" else None
            ).to(self.device)
            # Enable memory optimizations
            if self.device == "cuda":
                self.video_pipe.enable_model_cpu_offload()
            logger.info("SVD model loaded.")

    def generate_scene_video(self, image_path: str, scene_id: int):
        """Phase 4.1: Animate the image using SVD"""
        self.load_video_model()
        
        # Ensure path is correct
        if not os.path.exists(image_path):
            # Fallback if image_path is a relative path or filename
            potential_path = os.path.join(settings.STORYBOARD_DIR, os.path.basename(image_path))
            if os.path.exists(potential_path):
                image_path = potential_path
            else:
                logger.error(f"Image not found at {image_path}")
                raise FileNotFoundError(f"Image not found: {image_path}")

        image = Image.open(image_path).convert("RGB")
        image = image.resize((1024, 576)) # SVD standard resolution
        
        logger.info(f"Animating scene {scene_id}...")
        generator = torch.manual_seed(42)
        # Low steps for faster testing, increase for quality
        with torch.no_grad():
            output = self.video_pipe(
                image, 
                decode_chunk_size=8, 
                generator=generator,
                num_frames=14, # Standard SVD short clip
                motion_bucket_id=127,
                noise_aug_strength=0.1
            )
            frames = output.frames[0]
        
        output_path = os.path.join(settings.VIDEO_DIR, f"scene_{scene_id}_{uuid.uuid4().hex[:8]}.mp4")
        
        # Save frames as video using MoviePy
        import numpy as np
        from moviepy.editor import ImageSequenceClip
        
        # Convert PIL images to numpy arrays
        video_frames = [np.array(f) for f in frames]
        clip = ImageSequenceClip(video_frames, fps=7)
        clip.write_videofile(output_path, codec="libx264", audio=False, logger=None)
        
        return output_path

    def generate_audio(self, text: str, scene_id: int):
        """Phase 4.2: Generate audio using Bark (Simplified)"""
        # Placeholder for full Bark implementation
        # To keep it lightweight for now, we return None and use subtitles in assembly
        logger.info(f"Audio requested for scene {scene_id}: {text}")
        return None 

    def assemble_final_movie(self, scenes_data: list, user_id: int):
        """Phase 4.4: Combine everything with FFmpeg/MoviePy"""
        logger.info(f"Starting final assembly for user {user_id}")
        clips = []
        
        try:
            for scene in scenes_data:
                # scene is a dict from RenderRequest
                # We need local path from image_url
                img_filename = os.path.basename(scene['image_url'])
                local_image_path = os.path.join(settings.STORYBOARD_DIR, img_filename)
                
                video_path = self.generate_scene_video(local_image_path, scene['scene_id'])
                clip = VideoFileClip(video_path)
                
                # Optional: Add dialogue as overlay
                if scene.get('dialogue') and scene['dialogue'].lower() != "silent":
                    txt_clip = (TextClip(scene['dialogue'], fontsize=24, color='white', 
                                       font='Arial', stroke_color='black', stroke_width=1)
                               .set_duration(clip.duration)
                               .set_position(('center', 'bottom'))
                               .margin(bottom=20, opacity=0))
                    clip = CompositeVideoClip([clip, txt_clip])
                    
                clips.append(clip)
            
            if not clips:
                raise ValueError("No scenes to assemble")

            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Phase 4.4: Add watermark
            watermark = (TextClip("AI PRODUCER: TRIAL", fontsize=40, color='white', 
                                 font='Arial', stroke_color='black', stroke_width=2)
                        .set_duration(final_clip.duration)
                        .set_position(('right', 'bottom'))
                        .set_opacity(0.4)
                        .margin(right=20, bottom=20, opacity=0))
            
            result = CompositeVideoClip([final_clip, watermark])
            
            output_filename = f"final_movie_{user_id}_{uuid.uuid4().hex[:8]}.mp4"
            output_path = os.path.join(settings.VIDEO_DIR, output_filename)
            
            result.write_videofile(output_path, codec="libx264", audio=False) # Audio false until TTS ready
            
            return output_path
            
        except Exception as e:
            logger.error(f"Assembly failed: {str(e)}")
            raise e

renderer = MovieRenderer()
