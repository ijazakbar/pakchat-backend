# backend/models/image.py - COMPLETE FIXED VERSION
# Supports: OpenAI DALL-E, Replicate, FAL.ai, Stability AI

import openai
import aiohttp
import asyncio
import base64
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

# Try importing optional providers
try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    print("⚠️ Replicate not installed")

try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    FAL_AVAILABLE = False
    print("⚠️ FAL.ai client not installed")

load_dotenv()

class ImageProcessor:
    def __init__(self):
        # API Keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.replicate_key = os.getenv("REPLICATE_API_KEY")
        self.fal_key = os.getenv("FAL_AI_API_KEY")
        self.stability_key = os.getenv("STABILITY_API_KEY")
        self.huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
        
        # Initialize OpenAI client
        if self.openai_key:
            if hasattr(openai, 'OpenAI'):
                # New OpenAI client (v1+)
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
                self.use_new_openai = True
            else:
                # Old OpenAI client
                openai.api_key = self.openai_key
                self.openai_client = openai
                self.use_new_openai = False
        else:
            self.openai_client = None
            self.use_new_openai = False
        
        # Initialize Replicate client
        if self.replicate_key and REPLICATE_AVAILABLE:
            self.replicate_client = replicate.Client(api_token=self.replicate_key)
        else:
            self.replicate_client = None
        
        # Models configuration
        self.models = {
            "dalle-3": {
                "provider": "openai",
                "model": "dall-e-3",
                "sizes": ["1024x1024", "1792x1024", "1024x1792"],
                "quality": ["standard", "hd"]
            },
            "dalle-2": {
                "provider": "openai",
                "model": "dall-e-2",
                "sizes": ["256x256", "512x512", "1024x1024"]
            },
            "stable-diffusion-xl": {
                "provider": "replicate",
                "model": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                "sizes": ["1024x1024", "1152x896", "1216x832", "1344x768", "1536x640"]
            },
            "flux": {
                "provider": "replicate",
                "model": "black-forest-labs/flux-dev",
                "sizes": ["1024x1024"]
            },
            "playground-v2": {
                "provider": "replicate",
                "model": "playgroundai/playground-v2.5-1024px-aesthetic",
                "sizes": ["1024x1024"]
            },
            "fal-ai/flux": {
                "provider": "fal",
                "model": "fal-ai/flux",
                "sizes": ["1024x1024"]
            },
            "fal-ai/stable-diffusion": {
                "provider": "fal",
                "model": "fal-ai/stable-diffusion-v3",
                "sizes": ["1024x1024"]
            }
        }
    
    # ========== IMAGE GENERATION ==========
    
    async def generate(self, 
                       prompt: str, 
                       model: str = "dalle-3",
                       size: str = "1024x1024",
                       quality: str = "standard",
                       num_images: int = 1) -> Dict[str, Any]:
        """
        Generate image using specified model
        Models available:
        - "dalle-3" - OpenAI DALL-E 3 (best quality)
        - "dalle-2" - OpenAI DALL-E 2 (cheaper)
        - "stable-diffusion-xl" - SDXL on Replicate
        - "flux" - Flux model on Replicate
        - "playground-v2" - Playground v2.5
        - "fal-ai/flux" - Flux on FAL.ai
        - "fal-ai/stable-diffusion" - SD3 on FAL.ai
        """
        try:
            model_config = self.models.get(model)
            if not model_config:
                # Try to find by provider
                if model.startswith("fal-ai/"):
                    model_config = {
                        "provider": "fal",
                        "model": model
                    }
                else:
                    # Default to DALL-E 3
                    model_config = self.models["dalle-3"]
            
            provider = model_config["provider"]
            
            if provider == "openai":
                return await self._generate_openai(prompt, model_config, size, quality, num_images)
            elif provider == "replicate":
                return await self._generate_replicate(prompt, model_config, size, num_images)
            elif provider == "fal":
                return await self._generate_fal(prompt, model_config, size, num_images)
            elif provider == "stability":
                return await self._generate_stability(prompt, model_config, size, num_images)
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
        except Exception as e:
            return {
                "error": True,
                "message": f"Image generation failed: {str(e)}",
                "prompt": prompt
            }
    
    # ========== OPENAI DALL-E ==========
    
    async def _generate_openai(self, prompt: str, model_config: Dict, size: str, quality: str, num_images: int) -> Dict[str, Any]:
        """Generate using OpenAI DALL-E"""
        if not self.openai_client:
            raise Exception("OpenAI API key not configured")
        
        try:
            model = model_config["model"]
            
            if self.use_new_openai:
                # New OpenAI client (v1+)
                if model == "dall-e-3":
                    response = self.openai_client.images.generate(
                        model=model,
                        prompt=prompt,
                        size=size,
                        quality=quality,
                        n=num_images
                    )
                else:
                    response = self.openai_client.images.generate(
                        model=model,
                        prompt=prompt,
                        size=size,
                        n=num_images
                    )
                
                images = []
                for img in response.data:
                    images.append({
                        "url": img.url,
                        "revised_prompt": getattr(img, 'revised_prompt', prompt)
                    })
                
                return {
                    "success": True,
                    "provider": "openai",
                    "model": model,
                    "images": images,
                    "prompt": prompt
                }
            else:
                # Old OpenAI client
                if model == "dall-e-3":
                    response = await openai.Image.acreate(
                        model=model,
                        prompt=prompt,
                        size=size,
                        quality=quality,
                        n=num_images
                    )
                else:
                    response = await openai.Image.acreate(
                        model=model,
                        prompt=prompt,
                        size=size,
                        n=num_images
                    )
                
                images = [{"url": img.url, "revised_prompt": prompt} for img in response.data]
                
                return {
                    "success": True,
                    "provider": "openai",
                    "model": model,
                    "images": images,
                    "prompt": prompt
                }
                
        except Exception as e:
            raise Exception(f"OpenAI generation error: {str(e)}")
    
    # ========== REPLICATE ==========
    
    async def _generate_replicate(self, prompt: str, model_config: Dict, size: str, num_images: int) -> Dict[str, Any]:
        """Generate using Replicate"""
        if not self.replicate_client:
            raise Exception("Replicate API key not configured")
        
        try:
            model = model_config["model"]
            
            # Parse size
            width, height = map(int, size.split('x'))
            
            # Run prediction
            output = await asyncio.to_thread(
                self.replicate_client.run,
                model,
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": num_images,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 50
                }
            )
            
            # Process output
            images = []
            if isinstance(output, list):
                for img_url in output:
                    images.append({"url": img_url})
            elif isinstance(output, str):
                images.append({"url": output})
            else:
                images.append({"url": str(output)})
            
            return {
                "success": True,
                "provider": "replicate",
                "model": model,
                "images": images,
                "prompt": prompt
            }
            
        except Exception as e:
            raise Exception(f"Replicate generation error: {str(e)}")
    
    # ========== FAL.AI ==========
    
    async def _generate_fal(self, prompt: str, model_config: Dict, size: str, num_images: int) -> Dict[str, Any]:
        """Generate using FAL.ai"""
        if not self.fal_key:
            raise Exception("FAL.ai API key not configured")
        
        try:
            model = model_config["model"]
            
            # Parse size
            width, height = map(int, size.split('x'))
            
            # Call FAL.ai API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://fal.run/{model}",
                    headers={
                        "Authorization": f"Key {self.fal_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": prompt,
                        "image_size": size,
                        "num_images": num_images,
                        "guidance_scale": 7.5,
                        "num_inference_steps": 30
                    }
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        images = []
                        if "images" in result:
                            for img in result["images"]:
                                images.append({"url": img["url"]})
                        elif "image" in result:
                            images.append({"url": result["image"]["url"]})
                        
                        return {
                            "success": True,
                            "provider": "fal",
                            "model": model,
                            "images": images,
                            "prompt": prompt
                        }
                    else:
                        raise Exception(f"FAL.ai error: {result}")
                        
        except Exception as e:
            raise Exception(f"FAL.ai generation error: {str(e)}")
    
    # ========== STABILITY AI ==========
    
    async def _generate_stability(self, prompt: str, model_config: Dict, size: str, num_images: int) -> Dict[str, Any]:
        """Generate using Stability AI"""
        if not self.stability_key:
            raise Exception("Stability AI API key not configured")
        
        try:
            # Parse size
            width, height = map(int, size.split('x'))
            
            # Call Stability AI API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.stability_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text_prompts": [{"text": prompt, "weight": 1}],
                        "cfg_scale": 7,
                        "height": height,
                        "width": width,
                        "samples": num_images,
                        "steps": 30
                    }
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        images = []
                        for artifact in result.get("artifacts", []):
                            if artifact["finishReason"] == "SUCCESS":
                                img_data = artifact["base64"]
                                images.append({"base64": img_data})
                        
                        return {
                            "success": True,
                            "provider": "stability",
                            "model": "stable-diffusion-xl",
                            "images": images,
                            "prompt": prompt
                        }
                    else:
                        raise Exception(f"Stability AI error: {result}")
                        
        except Exception as e:
            raise Exception(f"Stability AI generation error: {str(e)}")
    
    # ========== IMAGE ANALYSIS ==========
    
    async def analyze(self, 
                      image_path: str, 
                      prompt: Optional[str] = None,
                      model: str = "gpt-4-vision") -> Dict[str, Any]:
        """
        Analyze image using GPT-4 Vision
        """
        if not self.openai_client:
            raise Exception("OpenAI API key not configured for vision analysis")
        
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            
            # Default prompt
            if not prompt:
                prompt = "What's in this image? Describe in detail in Urdu and English."
            
            # Determine image type
            if image_path.lower().endswith('.png'):
                media_type = "image/png"
            else:
                media_type = "image/jpeg"
            
            if self.use_new_openai:
                # New OpenAI client
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                
                analysis = response.choices[0].message.content
            else:
                # Old OpenAI client
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": f"data:{media_type};base64,{base64_image}"
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                
                analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "analysis": analysis,
                "prompt": prompt,
                "model": "gpt-4-vision"
            }
            
        except Exception as e:
            return {
                "error": True,
                "message": f"Image analysis failed: {str(e)}"
            }
    
    # ========== IMAGE EDITING ==========
    
    async def edit(self, 
                   image_path: str, 
                   mask_path: Optional[str] = None, 
                   prompt: str = "",
                   model: str = "dalle-2") -> Dict[str, Any]:
        """
        Edit image using DALL-E 2 (edits) or inpainting
        """
        if not self.openai_client:
            raise Exception("OpenAI API key not configured")
        
        try:
            with open(image_path, "rb") as img:
                if mask_path and os.path.exists(mask_path):
                    with open(mask_path, "rb") as mask:
                        if self.use_new_openai:
                            response = self.openai_client.images.edit(
                                image=img,
                                mask=mask,
                                prompt=prompt,
                                n=1,
                                size="1024x1024"
                            )
                        else:
                            response = await openai.Image.acreate_edit(
                                image=img,
                                mask=mask,
                                prompt=prompt,
                                n=1,
                                size="1024x1024"
                            )
                else:
                    # Create variation
                    if self.use_new_openai:
                        response = self.openai_client.images.create_variation(
                            image=img,
                            n=1,
                            size="1024x1024"
                        )
                    else:
                        response = await openai.Image.acreate_variation(
                            image=img,
                            n=1,
                            size="1024x1024"
                        )
            
            images = [{"url": img.url} for img in response.data]
            
            return {
                "success": True,
                "provider": "openai",
                "model": model,
                "images": images,
                "prompt": prompt if prompt else "variation"
            }
            
        except Exception as e:
            return {
                "error": True,
                "message": f"Image edit failed: {str(e)}"
            }
    
    # ========== IMAGE UPSCALING ==========
    
    async def upscale(self, 
                      image_path: str, 
                      scale: int = 2,
                      provider: str = "replicate") -> Dict[str, Any]:
        """
        Upscale image using Replicate or other providers
        """
        if provider == "replicate" and self.replicate_client:
            return await self._upscale_replicate(image_path, scale)
        elif provider == "fal" and self.fal_key:
            return await self._upscale_fal(image_path, scale)
        else:
            raise Exception(f"Upscaling provider {provider} not available")
    
    async def _upscale_replicate(self, image_path: str, scale: int) -> Dict[str, Any]:
        """Upscale using Replicate"""
        try:
            # Upload image first
            async with aiohttp.ClientSession() as session:
                with open(image_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename='image.png')
                    
                    async with session.post(
                        "https://api.replicate.com/v1/files",
                        headers={"Authorization": f"Token {self.replicate_key}"},
                        data=form
                    ) as response:
                        file_data = await response.json()
                
                # Run upscaling
                async with session.post(
                    "https://api.replicate.com/v1/predictions",
                    headers={"Authorization": f"Token {self.replicate_key}"},
                    json={
                        "version": "stability-ai/sd-x2-latent-upscaler",
                        "input": {
                            "image": file_data["urls"]["get"],
                            "scale": scale
                        }
                    }
                ) as response:
                    prediction = await response.json()
                
                # Poll for result
                for _ in range(30):
                    await asyncio.sleep(1)
                    async with session.get(
                        f"https://api.replicate.com/v1/predictions/{prediction['id']}",
                        headers={"Authorization": f"Token {self.replicate_key}"}
                    ) as response:
                        status = await response.json()
                    
                    if status["status"] == "succeeded":
                        return {
                            "success": True,
                            "provider": "replicate",
                            "url": status["output"],
                            "scale": scale
                        }
                    elif status["status"] == "failed":
                        raise Exception("Upscaling failed")
            
            raise Exception("Upscaling timeout")
            
        except Exception as e:
            return {
                "error": True,
                "message": f"Upscaling failed: {str(e)}"
            }
    
    async def _upscale_fal(self, image_path: str, scale: int) -> Dict[str, Any]:
        """Upscale using FAL.ai"""
        try:
            # Upload image to FAL
            async with aiohttp.ClientSession() as session:
                with open(image_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename='image.png')
                    
                    async with session.post(
                        "https://fal.ai/storage/upload",
                        headers={"Authorization": f"Key {self.fal_key}"},
                        data=form
                    ) as response:
                        upload_data = await response.json()
                
                # Run upscaling
                async with session.post(
                    "https://fal.run/fal-ai/esrgan",
                    headers={
                        "Authorization": f"Key {self.fal_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "image_url": upload_data["url"],
                        "scale": scale
                    }
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        return {
                            "success": True,
                            "provider": "fal",
                            "url": result["image"]["url"],
                            "scale": scale
                        }
                    else:
                        raise Exception(f"FAL upscaling error: {result}")
                        
        except Exception as e:
            return {
                "error": True,
                "message": f"FAL upscaling failed: {str(e)}"
            }
    
    # ========== IMAGE TO IMAGE ==========
    
    async def image_to_image(self,
                            image_path: str,
                            prompt: str,
                            model: str = "stable-diffusion-xl") -> Dict[str, Any]:
        """
        Transform image using image-to-image models
        """
        if model.startswith("fal-ai/"):
            return await self._img2img_fal(image_path, prompt, model)
        else:
            return await self._img2img_replicate(image_path, prompt)
    
    async def _img2img_replicate(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Image-to-image using Replicate"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename='image.png')
                    
                    async with session.post(
                        "https://api.replicate.com/v1/files",
                        headers={"Authorization": f"Token {self.replicate_key}"},
                        data=form
                    ) as response:
                        file_data = await response.json()
                
                # Run img2img
                async with session.post(
                    "https://api.replicate.com/v1/predictions",
                    headers={"Authorization": f"Token {self.replicate_key}"},
                    json={
                        "version": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                        "input": {
                            "image": file_data["urls"]["get"],
                            "prompt": prompt,
                            "strength": 0.8
                        }
                    }
                ) as response:
                    prediction = await response.json()
                
                # Poll for result
                for _ in range(30):
                    await asyncio.sleep(1)
                    async with session.get(
                        f"https://api.replicate.com/v1/predictions/{prediction['id']}",
                        headers={"Authorization": f"Token {self.replicate_key}"}
                    ) as response:
                        status = await response.json()
                    
                    if status["status"] == "succeeded":
                        return {
                            "success": True,
                            "provider": "replicate",
                            "url": status["output"],
                            "prompt": prompt
                        }
            
            raise Exception("Image-to-image timeout")
            
        except Exception as e:
            return {
                "error": True,
                "message": f"Image-to-image failed: {str(e)}"
            }
    
    async def _img2img_fal(self, image_path: str, prompt: str, model: str) -> Dict[str, Any]:
        """Image-to-image using FAL.ai"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename='image.png')
                    
                    async with session.post(
                        "https://fal.ai/storage/upload",
                        headers={"Authorization": f"Key {self.fal_key}"},
                        data=form
                    ) as response:
                        upload_data = await response.json()
                
                # Run img2img
                async with session.post(
                    f"https://fal.run/{model}",
                    headers={
                        "Authorization": f"Key {self.fal_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "image_url": upload_data["url"],
                        "prompt": prompt,
                        "strength": 0.8
                    }
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        return {
                            "success": True,
                            "provider": "fal",
                            "url": result["image"]["url"],
                            "prompt": prompt
                        }
                    else:
                        raise Exception(f"FAL img2img error: {result}")
                        
        except Exception as e:
            return {
                "error": True,
                "message": f"FAL img2img failed: {str(e)}"
            }