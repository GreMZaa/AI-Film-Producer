import os
import torch
import uuid
import logging
# from diffusers import StableVideoDiffusionPipeline # Removed to avoid transformers conflict, using ComfyUI instead

from moviepy import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, vfx
from src.api.config import settings
from PIL import Image
from pydub import AudioSegment
import numpy as np
import transformers.utils.import_utils as import_utils
if not hasattr(import_utils, "is_torchcodec_available"):
    import_utils.is_torchcodec_available = lambda: False
if not hasattr(import_utils, "is_torch_greater_or_equal"):
    import torch
    from packaging import version
    import_utils.is_torch_greater_or_equal = lambda v: version.parse(torch.__version__) >= version.parse(v)

try:
    from TTS.api import TTS
except ImportError:
    TTS = None

import subprocess
from src.local_server.comfy_client import comfy_client

logger = logging.getLogger(__name__)

class MovieRenderer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.video_pipe = None

        self.tts = None
        # Models for Phase 4

    # Removed load_video_model as we use ComfyUI for SVD


    def generate_scene_video(self, image_path: str, scene_id: int):
        """Phase 4.1: Animate the image using ComfyUI (SVD)"""
        logger.info(f"Animating scene {scene_id} using ComfyUI...")
        
        output_filename = f"scene_{scene_id}_{uuid.uuid4().hex[:8]}_svd.mp4"
        output_path = os.path.join(settings.TEMP_DIR, output_filename)
        
        try:
            # Ensure path is correct
            if not os.path.exists(image_path):
                potential_path = os.path.join(settings.STORYBOARD_DIR, os.path.basename(image_path))
                if os.path.exists(potential_path):
                    image_path = potential_path
                else:
                    logger.error(f"Image not found at {image_path}")
                    raise FileNotFoundError(f"Image not found: {image_path}")

            result = comfy_client.generate_video_sync(image_path, output_path)
            if not result:
                raise Exception("ComfyUI video generation failed")
            return output_path
        except Exception as e:
            logger.error(f"SVD Animation failed: {e}")
            raise e

    def load_tts_model(self):
        if self.tts is None and TTS is not None:
            logger.info("Loading TTS model...")
            # Using Bark for expressive voices
            self.tts = TTS("tts_models/multilingual/multi-dataset/bark").to(self.device)
            logger.info("TTS model loaded.")

    def generate_audio(self, text: str, scene_id: int):
        """Phase 4.2: Generate audio using Bark"""
        self.load_tts_model()
        if self.tts is None:
            logger.warning("TTS library not installed. Skipping audio.")
            return None
            
        output_path = os.path.join(settings.TEMP_DIR, f"scene_{scene_id}_{uuid.uuid4().hex[:8]}.wav")
        
        logger.info(f"Generating audio for scene {scene_id}...")
        # Bark supports voice presets. For a sarcastic producer, we might want a specific one.
        # But for now, we'll use a default or let it be random.
        self.tts.tts_to_file(text=text, file_path=output_path)
        
        return output_path

    def assemble_final_movie(self, scenes_data: list, user_id: int, is_premium: bool = False):
        """Phase 4.4: Combine everything with FFmpeg/MoviePy"""
        logger.info(f"Starting final assembly for user {user_id}")
        clips = []
        
        try:
            for scene in scenes_data:
                # scene is a dict from RenderRequest
                img_filename = os.path.basename(scene['image_url'])
                local_image_path = os.path.join(settings.STORYBOARD_DIR, img_filename)
                
                # 1. Generate Audio
                audio_path = None
                if scene.get('dialogue') and scene['dialogue'].lower() != "silent":
                    audio_path = self.generate_audio(scene['dialogue'], scene['scene_id'])
                
                # 2. Generate Video (Animation)
                video_path = self.generate_scene_video(local_image_path, scene['scene_id'])
                
                # 3. Lip-Sync (Wav2Lip)
                final_scene_video = video_path
                if audio_path and os.path.exists(audio_path):
                    logger.info(f"Running Lip-Sync for scene {scene['scene_id']}...")
                    synced_video_path = os.path.join(settings.TEMP_DIR, f"scene_{scene['scene_id']}_synced.mp4")
                    try:
                        final_scene_video = self.sync_lips(video_path, audio_path, synced_video_path)
                    except Exception as e:
                        logger.error(f"Lip-sync failed for scene {scene['scene_id']}: {e}. Using silent video.")
                
                clip = VideoFileClip(final_scene_video)
                
                # We need to ensure the audio is attached if sync_lips didn't already (it should have)
                # But MoviePy sometimes needs a refresh of the clip object
                if audio_path and os.path.exists(audio_path):
                    audio_clip = AudioFileClip(audio_path)
                    if audio_clip.duration > clip.duration:
                        clip = clip.with_effects([vfx.Loop(duration=audio_clip.duration)])
                    clip = clip.with_audio(audio_clip)
                
                # 4. Burn Subtitles
                if scene.get('dialogue') and scene['dialogue'].lower() != "silent":
                    clip = self.add_subtitles_to_clip(clip, scene['dialogue'])
                    
                clips.append(clip)
            
            if not clips:
                raise ValueError("No scenes to assemble")

            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Phase 5: Dynamic Watermark & Credits
            if not is_premium:
                watermark_text = "AI PRODUCER: TRIAL"
                final_clip = self.add_watermark_to_clip(final_clip, watermark_text)
            else:
                # Add a credits scene at the end for Indie Producers
                from src.api.db import get_user
                user = get_user(user_id)
                username = user["username"] if user and user["username"] else f"Producer_{user_id}"
                
                credits_text = f"DIRECTED BY\n{username.upper()}"
                credits_clip = self.create_credits_clip(final_clip.size, credits_text, duration=3)
                final_clip = concatenate_videoclips([final_clip, credits_clip], method="compose")
            
            output_filename = f"final_movie_{user_id}_{uuid.uuid4().hex[:8]}.mp4"
            output_path = os.path.join(settings.VIDEO_DIR, output_filename)
            
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac") 
            
            return output_path
            
        except Exception as e:
            logger.error(f"Assembly failed: {str(e)}")
            raise e

    def add_subtitles_to_clip(self, clip, text):
        """Burn subtitles using PIL/Numpy instead of ImageMagick"""
        from PIL import ImageDraw, ImageFont
        
        def make_frame(get_frame, t):
            frame = get_frame(t)
            # Ensure frame is in uint8 format for PIL
            if frame.dtype != np.uint8:
                frame = (frame * 255).astype(np.uint8) if frame.max() <= 1.1 else frame.astype(np.uint8)
            img = Image.fromarray(frame)
            # Create an overlay for transparency
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            w, h = img.size
            margin = 40
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default()
            
            text_w = draw.textlength(text, font=font)
            pos = ((w - text_w) // 2, h - margin - 30)
            
            # Outline (black)
            for offset in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((pos[0]+offset[0], pos[1]+offset[1]), text, font=font, fill=(0, 0, 0, 200))
            # Text (white)
            draw.text(pos, text, font=font, fill=(255, 255, 255, 255))
            
            # Composite overlay onto the original frame
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            return np.array(img)

        return clip.with_transform(make_frame)

    def add_watermark_to_clip(self, clip, text):
        """Add watermark using PIL/Numpy"""
        from PIL import ImageDraw, ImageFont
        
        def make_frame(get_frame, t):
            frame = get_frame(t)
            # Ensure frame is in uint8 format for PIL
            if frame.dtype != np.uint8:
                frame = (frame * 255).astype(np.uint8) if frame.max() <= 1.1 else frame.astype(np.uint8)
            img = Image.fromarray(frame)
            # Create an overlay for transparency
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            w, h = img.size
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            text_w = draw.textlength(text, font=font)
            # Position: bottom right
            pos = (w - text_w - 20, h - 60)
            
            # Semi-transparent black outline
            for offset in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((pos[0]+offset[0], pos[1]+offset[1]), text, font=font, fill=(0, 0, 0, 150))
            # Semi-transparent white text
            draw.text(pos, text, font=font, fill=(255, 255, 255, 150))
            
            # Composite overlay onto the original frame
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            return np.array(img)

        return clip.with_transform(make_frame)

    def sync_lips(self, video_path: str, audio_path: str, output_path: str):
        """Phase 4.3: Run Wav2Lip inference"""
        inference_script = os.path.join(settings.WAV2LIP_PATH, "inference.py")
        
        cmd = [
            "python", inference_script,
            "--checkpoint_path", settings.WAV2LIP_CHECKPOINT,
            "--face", video_path,
            "--audio", audio_path,
            "--outfile", output_path,
            "--pads", "0", "20", "0", "0", # Better for chin detection
            "--nosmooth"
        ]
        
        logger.info(f"Executing Wav2Lip: {' '.join(cmd)}")
        
        # We run this in the same environment
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=settings.WAV2LIP_PATH)
        
        if result.returncode != 0:
            logger.error(f"Wav2Lip error: {result.stderr}")
            raise Exception(f"Wav2Lip failed: {result.stderr}")
            
        return output_path

    def create_credits_clip(self, size, text, duration=3):
        """Create a black screen with centered credits text using PIL"""
        from PIL import ImageDraw, ImageFont
        import numpy as np
        
        w, h = size
        
        def make_frame(t):
            img = Image.new('RGB', (w, h), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()
            
            # Multi-line text handling
            lines = text.split("\n")
            # Calculate total height of the text block
            line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines]
            total_height = sum(line_heights) + (len(lines) - 1) * 20
            
            current_y = (h - total_height) // 2
            for i, line in enumerate(lines):
                text_w = draw.textlength(line, font=font)
                pos = ((w - text_w) // 2, current_y)
                draw.text(pos, line, font=font, fill=(255, 255, 255))
                current_y += line_heights[i] + 20
                
            return np.array(img)
            
        from moviepy import VideoClip
        return VideoClip(make_frame, duration=duration)

    def unload_all_models(self):
        """Free up GPU memory"""
        self.video_pipe = None
        self.tts = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            import gc
            gc.collect()

renderer = MovieRenderer()
