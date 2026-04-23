import os
import torch
import uuid
import logging
from diffusers import StableVideoDiffusionPipeline
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
from src.api.config import settings
from PIL import Image
from pydub import AudioSegment
import numpy as np
try:
    from TTS.api import TTS
except ImportError:
    TTS = None

logger = logging.getLogger(__name__)

class MovieRenderer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.video_pipe = None
        self.tts = None
        # Models for Phase 4

    def load_video_model(self):
        if self.video_pipe is None:
            logger.info("Loading SVD model...")
            self.video_pipe = StableVideoDiffusionPipeline.from_pretrained(
                settings.VIDEO_MODEL, 
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                variant="fp16" if self.device == "cuda" else None
            ).to(self.device)
            # Enable memory optimizations
            self.video_pipe.enable_model_cpu_offload() # Better for low VRAM
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
            
        output_path = os.path.join(settings.AUDIO_DIR, f"scene_{scene_id}_{uuid.uuid4().hex[:8]}.wav")
        
        logger.info(f"Generating audio for scene {scene_id}...")
        # Bark supports voice presets. For a sarcastic producer, we might want a specific one.
        # But for now, we'll use a default or let it be random.
        self.tts.tts_to_file(text=text, file_path=output_path)
        
        return output_path

    def assemble_final_movie(self, scenes_data: list, user_id: int):
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
                
                # 3. Optional Lipsync (If weights exist)
                # For now, we'll just use the raw video + audio
                
                clip = VideoFileClip(video_path)
                
                if audio_path:
                    audio_clip = AudioFileClip(audio_path)
                    if audio_clip.duration > clip.duration:
                        clip = clip.loop(duration=audio_clip.duration)
                    clip = clip.set_audio(audio_clip)
                
                # 4. Burn Subtitles (Fallback for ImageMagick)
                if scene.get('dialogue') and scene['dialogue'].lower() != "silent":
                    # We create a simple black bar with text using a custom function
                    # instead of TextClip which requires ImageMagick
                    clip = self.add_subtitles_to_clip(clip, scene['dialogue'])
                    
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
            
            result.write_videofile(output_path, codec="libx264", audio_codec="aac") 
            
            return output_path
            
        except Exception as e:
            logger.error(f"Assembly failed: {str(e)}")
            raise e

    def add_subtitles_to_clip(self, clip, text):
        """Burn subtitles using PIL/Numpy instead of ImageMagick"""
        from PIL import ImageDraw, ImageFont
        
        def make_frame(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame)
            draw = ImageDraw.Draw(img)
            
            # Simple subtitle box at bottom
            w, h = img.size
            margin = 40
            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default()
            
            # Draw text with shadow/outline
            text_w = draw.textlength(text, font=font)
            pos = ((w - text_w) // 2, h - margin - 30)
            
            # Outline
            for offset in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((pos[0]+offset[0], pos[1]+offset[1]), text, font=font, fill="black")
            # Text
            draw.text(pos, text, font=font, fill="white")
            
            return np.array(img)

        return clip.fl(lambda gf, t: make_frame(gf, t))

    def unload_all_models(self):
        """Free up GPU memory"""
        self.video_pipe = None
        self.tts = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            import gc
            gc.collect()

renderer = MovieRenderer()
