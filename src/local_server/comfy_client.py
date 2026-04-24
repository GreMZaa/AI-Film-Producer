import websocket
import uuid
import json
import urllib.request
import urllib.parse
import os
import requests
import logging
from src.api.config import settings

logger = logging.getLogger(__name__)

class ComfyClient:
    def __init__(self, server_address=None):
        self.server_address = server_address or settings.COMFYUI_URL.replace("http://", "")
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def upload_image(self, image_path):
        url = f"http://{self.server_address}/upload/image"
        with open(image_path, "rb") as f:
            files = {"image": (os.path.basename(image_path), f)}
            data = {"overwrite": "true"}
            response = requests.post(url, files=files, data=data)
            return response.json()

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
            return response.read()

    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def generate_image_sync(self, prompt_text, output_path):
        # Flux.1 Schnell GGUF Workflow
        workflow = {
            "3": {
                "inputs": {
                    "seed": 42,
                    "steps": settings.IMAGE_STEPS,
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "beta",
                    "denoise": 1.0,
                    "model": ["10", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "5": {
                "inputs": {"width": 1024, "height": 768, "batch_size": 1},
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            },
            "6": {
                "inputs": {
                    "text": prompt_text,
                    "clip": ["11", 0]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Positive)"}
            },
            "7": {
                "inputs": {
                    "text": "blurry, low quality, distorted",
                    "clip": ["11", 0]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Negative)"}
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["9", 0]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "9": {
                "inputs": {"vae_name": "ae.safetensors"},
                "class_type": "VAELoader",
                "_meta": {"title": "VAE Loader"}
            },
            "10": {
                "inputs": {
                    "unet_name": settings.IMAGE_MODEL,
                    "guider": "flux"
                },
                "class_type": "UnetLoaderGGUF",
                "_meta": {"title": "Unet Loader (GGUF)"}
            },
            "11": {
                "inputs": {
                    "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                    "clip_name2": "clip_l.safetensors",
                    "type": "flux"
                },
                "class_type": "DualCLIPLoader",
                "_meta": {"title": "DualCLIPLoader"}
            },
            "12": {
                "inputs": {
                    "filename_prefix": "garage_hollywood",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        }

        return self._execute_workflow(workflow, output_path, "images")

    def generate_video_sync(self, image_path, output_path):
        # Phase 4.1: SVD Workflow in ComfyUI
        # First upload image
        upload_resp = self.upload_image(image_path)
        comfy_filename = upload_resp["name"]
        
        workflow = {
            "1": {
                "inputs": {"ckpt_name": settings.VIDEO_MODEL},
                "class_type": "ImageOnlyCheckpointLoader",
                "_meta": {"title": "Load Checkpoint (SVD)"}
            },
            "2": {
                "inputs": {
                    "width": 1024,
                    "height": 576,
                    "video_frames": 14,
                    "motion_bucket_id": 127,
                    "fps": 7,
                    "augmentation_level": 0.0,
                    "clip_vision": ["1", 1],
                    "init_image": ["3", 0],
                    "vae": ["1", 2]
                },
                "class_type": "SVD_img2vid_Conditioning",
                "_meta": {"title": "SVD_img2vid_Conditioning"}
            },
            "3": {
                "inputs": {"image": comfy_filename, "upload": "image"},
                "class_type": "LoadImage",
                "_meta": {"title": "Load Image"}
            },
            "4": {
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 2.5,
                    "sampler_name": "euler",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["2", 1],
                    "latent_image": ["2", 2]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "5": {
                "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "6": {
                "inputs": {
                    "images": ["5", 0],
                    "frame_rate": 7,
                    "loop_count": 0,
                    "filename_prefix": "garage_hollywood_vid",
                    "format": "video/h264-mp4",
                    "pingpong": False,
                    "save_output": True
                },
                "class_type": "VHS_VideoCombine",
                "_meta": {"title": "Video Combine 🎥🅥🅗🅢"}
            }
        }

        return self._execute_workflow(workflow, output_path, "gifs")
    def generate_inpainting_sync(self, image_path, mask_path, prompt_text, output_path):
        # 1. Upload both image and mask
        image_resp = self.upload_image(image_path)
        mask_resp = self.upload_image(mask_path)
        
        # 2. Inpainting Workflow (Simplified SDXL/Flux-compatible)
        # Note: Using a robust inpainting pattern
        workflow = {
            "3": {
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 0.6, # Key for inpainting
                    "model": ["10", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["13", 0]
                },
                "class_type": "KSampler"
            },
            "6": {
                "inputs": {"text": prompt_text, "clip": ["11", 0]},
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {"text": "distorted, low quality", "clip": ["11", 0]},
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {"samples": ["3", 0], "vae": ["9", 0]},
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {"vae_name": "ae.safetensors"},
                "class_type": "VAELoader"
            },
            "10": {
                "inputs": {"unet_name": settings.IMAGE_MODEL, "guider": "flux"},
                "class_type": "UnetLoaderGGUF"
            },
            "11": {
                "inputs": {
                    "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                    "clip_name2": "clip_l.safetensors",
                    "type": "flux"
                },
                "class_type": "DualCLIPLoader"
            },
            "12": {
                "inputs": {"filename_prefix": "inpainting", "images": ["8", 0]},
                "class_type": "SaveImage"
            },
            "13": {
                "inputs": {"samples": ["14", 0], "mask": ["15", 0]},
                "class_type": "SetLatentNoiseMask"
            },
            "14": {
                "inputs": {"pixels": ["16", 0], "vae": ["9", 0]},
                "class_type": "VAEEncode"
            },
            "15": {
                "inputs": {"image": mask_resp["name"], "channel": "red"},
                "class_type": "ImageToMask"
            },
            "16": {
                "inputs": {"image": image_resp["name"], "upload": "image"},
                "class_type": "LoadImage"
            }
        }

        return self._execute_workflow(workflow, output_path, "images")

    def _execute_workflow(self, workflow, output_path, output_key="images"):
        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        
        prompt_id = self.queue_prompt(workflow)['prompt_id']
        logger.info(f"Queued prompt to ComfyUI, ID: {prompt_id}")
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break # Execution finished
            else:
                continue

        history = self.get_history(prompt_id)[prompt_id]
        
        # Check both standard outputs and UI outputs (common for video nodes)
        outputs = history.get('outputs', {})
        ui_outputs = history.get('ui', {})
        
        # Look in regular outputs first
        for node_id in outputs:
            node_output = outputs[node_id]
            if output_key in node_output:
                for item in node_output[output_key]:
                    data = self.get_image(item['filename'], item['subfolder'], item['type'])
                    with open(output_path, "wb") as f:
                        f.write(data)
                    return output_path
        
        # Look in UI outputs (for VHS_VideoCombine)
        for node_id in ui_outputs:
            if 'gifs' in ui_outputs[node_id]:
                for item in ui_outputs[node_id]['gifs']:
                    data = self.get_image(item['filename'], item['subfolder'], item['type'])
                    with open(output_path, "wb") as f:
                        f.write(data)
                    return output_path

        return None

comfy_client = ComfyClient()
