# backend/models/video.py - COMPLETE PROFESSIONAL VIDEO GENERATION
# Supports multiple providers: RunPod, Replicate, FAL.ai, and more

import aiohttp
import asyncio
import json
import os
import time
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

class VideoProvider(str, Enum):
    """Available video generation providers"""
    RUNPOD = "runpod"
    REPLICATE = "replicate"
    FAL = "fal"
    COLAB = "colab"
    STABILITY = "stability"
    KLING = "kling"
    PIKA = "pika"
    LUMA = "luma"

class VideoStyle(str, Enum):
    """Video styles"""
    REALISTIC = "realistic"
    ANIMATION = "animation"
    CINEMATIC = "cinematic"
    CARTOON = "cartoon"
    ANIME = "anime"
    THREE_D = "3d"
    PIXAR = "pixar"
    CLAY = "clay"
    SKETCH = "sketch"
    WATERCOLOR = "watercolor"

class VideoResolution(str, Enum):
    """Video resolutions"""
    SD = "480p"    # 854x480
    HD = "720p"    # 1280x720
    FULL_HD = "1080p"  # 1920x1080
    QHD = "1440p"  # 2560x1440
    UHD = "2160p"  # 3840x2160 (4K)

class VideoGenerator:
    def __init__(self):
        # API Keys
        self.runpod_key = os.getenv("RUNPOD_API_KEY")
        self.replicate_key = os.getenv("REPLICATE_API_KEY")
        self.fal_key = os.getenv("FAL_AI_API_KEY")
        self.stability_key = os.getenv("STABILITY_API_KEY")
        self.kling_key = os.getenv("KLING_API_KEY")
        self.pika_key = os.getenv("PIKA_API_KEY")
        self.luma_key = os.getenv("LUMA_API_KEY")
        self.colab_url = os.getenv("COLAB_VIDEO_API_URL")
        
        # Provider configurations
        self.providers = {
            VideoProvider.RUNPOD: {
                "name": "RunPod",
                "models": {
                    "stable-video-diffusion": "stability-ai/stable-video-diffusion",
                    "zeroscope": "another-ai/zeroscope",
                    "modelscope": "damo-vilab/modelscope"
                },
                "cost_per_second": 0.066 / 60,  # $0.066 per 5 seconds
                "speed": "medium",
                "quality": "good"
            },
            VideoProvider.REPLICATE: {
                "name": "Replicate",
                "models": {
                    "stable-video-diffusion": "stability-ai/stable-video-diffusion",
                    "zeroscope": "another-ai/zeroscope",
                    "modelscope": "damo-vilab/modelscope"
                },
                "cost_per_second": 0.20 / 5,  # $0.20 per 5 seconds
                "speed": "medium",
                "quality": "good"
            },
            VideoProvider.FAL: {
                "name": "FAL.ai",
                "models": {
                    "ltx-video": "fal-ai/ltx-video",
                    "kling": "fal-ai/kling-video",
                    "pika": "fal-ai/pika",
                    "stable-video": "fal-ai/stable-video"
                },
                "cost_per_second": 0.20 / 5,
                "speed": "fast",
                "quality": "excellent"
            },
            VideoProvider.STABILITY: {
                "name": "Stability AI",
                "models": {
                    "stable-video-diffusion": "stable-video-diffusion"
                },
                "cost_per_second": 0.15 / 5,
                "speed": "slow",
                "quality": "excellent"
            },
            VideoProvider.KLING: {
                "name": "Kling AI",
                "models": {
                    "kling-1.0": "kling-v1"
                },
                "cost_per_second": 0.10 / 5,
                "speed": "fast",
                "quality": "excellent"
            },
            VideoProvider.COLAB: {
                "name": "Google Colab",
                "models": {
                    "colab-video": "colab-video"
                },
                "cost_per_second": 0,  # Free
                "speed": "slow",
                "quality": "good"
            }
        }
        
        # Resolution configurations
        self.resolutions = {
            VideoResolution.SD: {"width": 854, "height": 480, "frames": 24},
            VideoResolution.HD: {"width": 1280, "height": 720, "frames": 30},
            VideoResolution.FULL_HD: {"width": 1920, "height": 1080, "frames": 30},
            VideoResolution.QHD: {"width": 2560, "height": 1440, "frames": 30},
            VideoResolution.UHD: {"width": 3840, "height": 2160, "frames": 30}
        }
        
        # Style presets
        self.style_presets = {
            VideoStyle.REALISTIC: "photorealistic, high quality, detailed",
            VideoStyle.ANIMATION: "animated, cartoon style, vibrant colors",
            VideoStyle.CINEMATIC: "cinematic, movie-like, dramatic lighting",
            VideoStyle.CARTOON: "cartoon style, colorful, fun",
            VideoStyle.ANIME: "anime style, Japanese animation",
            VideoStyle.THREE_D: "3D rendered, computer graphics",  # ✅ Yahan bhi change karo
            VideoStyle.PIXAR: "Pixar style, 3D animation",
            VideoStyle.CLAY: "clay animation style, stop motion",
            VideoStyle.SKETCH: "sketch style, hand-drawn",
            VideoStyle.WATERCOLOR: "watercolor painting style"
        }
        
        # Job storage
        self.jobs = {}
        self.max_jobs_per_user = 10
        self.job_ttl = 86400  # 24 hours
        
        # Cache for generated videos
        self.cache = {}
        self.cache_ttl = 604800  # 7 days
    
    # ========== MAIN METHODS ==========
    
    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: Union[str, VideoResolution] = VideoResolution.HD,
        style: Union[str, VideoStyle] = VideoStyle.REALISTIC,
        provider: Union[str, VideoProvider] = "auto",
        model: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        fps: int = 30,
        seed: Optional[int] = None,
        user_id: str = "anonymous",
        webhook_url: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Generate video with automatic provider selection
        """
        # Validate inputs
        if not prompt:
            return {"error": "Prompt is required", "status": "failed"}
        
        if duration < 2 or duration > 30:
            return {"error": "Duration must be between 2 and 30 seconds", "status": "failed"}
        
        # Convert string enums
        if isinstance(resolution, str):
            resolution = VideoResolution(resolution)
        if isinstance(style, str):
            style = VideoStyle(style)
        if isinstance(provider, str) and provider != "auto":
            provider = VideoProvider(provider)
        
        # Check user job limit
        user_jobs = [j for j in self.jobs.values() if j.get("user_id") == user_id]
        if len(user_jobs) >= self.max_jobs_per_user:
            # Clean old jobs
            await self._cleanup_old_jobs(user_id)
            user_jobs = [j for j in self.jobs.values() if j.get("user_id") == user_id]
            if len(user_jobs) >= self.max_jobs_per_user:
                return {"error": "Too many pending jobs. Please wait for some to complete.", "status": "failed"}
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Get resolution config
        res_config = self.resolutions.get(resolution, self.resolutions[VideoResolution.HD])
        
        # Get style prompt
        style_prompt = self.style_presets.get(style, "")
        
        # Enhance prompt with style
        enhanced_prompt = f"{prompt}, {style_prompt}, high quality, {resolution.value} video"
        
        # Select provider if auto
        if provider == "auto" or provider == "auto":
            provider = await self._select_best_provider(duration, priority)
        
        # Get provider config
        provider_config = self.providers.get(provider)
        if not provider_config:
            return {"error": f"Provider {provider} not available", "status": "failed"}
        
        # Select model
        if not model:
            model = list(provider_config["models"].keys())[0]
        
        # Create job
        job = {
            "id": job_id,
            "user_id": user_id,
            "status": "submitted",
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "negative_prompt": negative_prompt,
            "duration": duration,
            "resolution": resolution.value,
            "style": style.value,
            "provider": provider.value,
            "model": model,
            "fps": fps,
            "seed": seed or int(time.time()),
            "webhook_url": webhook_url,
            "priority": priority,
            "submitted_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
            "progress": 0,
            "cost_estimate": provider_config["cost_per_second"] * duration
        }
        
        self.jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._process_job(job_id))
        
        return {
            "job_id": job_id,
            "status": "submitted",
            "estimated_time": self._get_estimated_time(provider, duration),
            "cost_estimate": job["cost_estimate"],
            "provider": provider.value,
            "webhook_url": webhook_url
        }
    
    async def _process_job(self, job_id: str):
        """Process video generation job"""
        job = self.jobs[job_id]
        
        try:
            job["status"] = "processing"
            job["updated_at"] = datetime.now().isoformat()
            
            provider = VideoProvider(job["provider"])
            
            # Update progress
            job["progress"] = 10
            
            # Call appropriate provider
            if provider == VideoProvider.RUNPOD:
                result = await self._runpod_generate(job)
            elif provider == VideoProvider.REPLICATE:
                result = await self._replicate_generate(job)
            elif provider == VideoProvider.FAL:
                result = await self._fal_generate(job)
            elif provider == VideoProvider.STABILITY:
                result = await self._stability_generate(job)
            elif provider == VideoProvider.KLING:
                result = await self._kling_generate(job)
            elif provider == VideoProvider.COLAB:
                result = await self._colab_generate(job)
            else:
                raise Exception(f"Unsupported provider: {provider}")
            
            job["progress"] = 100
            
            if result:
                job["status"] = "completed"
                job["result"] = result
                job["completed_at"] = datetime.now().isoformat()
                
                # Add to cache
                await self._cache_video(job, result)
                
                # Call webhook if provided
                if job.get("webhook_url"):
                    await self._call_webhook(job)
            else:
                job["status"] = "failed"
                job["error"] = "Generation failed - no result returned"
                
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = datetime.now().isoformat()
            print(f"Video generation failed for {job_id}: {e}")
        
        job["updated_at"] = datetime.now().isoformat()
    
    # ========== PROVIDER METHODS ==========
    
    async def _runpod_generate(self, job: Dict) -> Optional[Dict]:
        """Generate video using RunPod"""
        if not self.runpod_key:
            raise Exception("RunPod API key not configured")
        
        try:
            # Update progress
            job["progress"] = 20
            
            # Submit to RunPod
            async with aiohttp.ClientSession() as session:
                # Create endpoint
                async with session.post(
                    "https://api.runpod.ai/v2/stable-video-diffusion/runsync",
                    headers={
                        "Authorization": f"Bearer {self.runpod_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": {
                            "prompt": job["enhanced_prompt"],
                            "negative_prompt": job.get("negative_prompt", ""),
                            "num_frames": job["duration"] * job["fps"],
                            "width": self.resolutions[VideoResolution(job["resolution"])]["width"],
                            "height": self.resolutions[VideoResolution(job["resolution"])]["height"],
                            "seed": job["seed"]
                        }
                    },
                    timeout=300
                ) as response:
                    data = await response.json()
                    
                    job["progress"] = 80
                    
                    if response.status == 200:
                        return {
                            "url": data.get("output", {}).get("video_url"),
                            "provider": "runpod",
                            "model": job["model"],
                            "duration": job["duration"],
                            "resolution": job["resolution"],
                            "size": data.get("output", {}).get("size"),
                            "seed": job["seed"]
                        }
                    else:
                        raise Exception(f"RunPod error: {data}")
                        
        except Exception as e:
            print(f"RunPod generation error: {e}")
            return None
    
    async def _replicate_generate(self, job: Dict) -> Optional[Dict]:
        """Generate video using Replicate"""
        if not self.replicate_key:
            raise Exception("Replicate API key not configured")
        
        try:
            job["progress"] = 20
            
            async with aiohttp.ClientSession() as session:
                # Create prediction
                async with session.post(
                    "https://api.replicate.com/v1/predictions",
                    headers={
                        "Authorization": f"Token {self.replicate_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "version": "stability-ai/stable-video-diffusion",
                        "input": {
                            "prompt": job["enhanced_prompt"],
                            "negative_prompt": job.get("negative_prompt", ""),
                            "num_frames": job["duration"] * job["fps"],
                            "width": self.resolutions[VideoResolution(job["resolution"])]["width"],
                            "height": self.resolutions[VideoResolution(job["resolution"])]["height"],
                            "seed": job["seed"]
                        }
                    }
                ) as response:
                    data = await response.json()
                    
                job["progress"] = 40
                
                # Poll for results
                prediction_id = data["id"]
                max_attempts = 60
                attempt = 0
                
                while attempt < max_attempts:
                    attempt += 1
                    await asyncio.sleep(2)
                    
                    job["progress"] = 40 + (attempt * 2)
                    
                    async with session.get(
                        f"https://api.replicate.com/v1/predictions/{prediction_id}",
                        headers={"Authorization": f"Token {self.replicate_key}"}
                    ) as response:
                        status = await response.json()
                        
                    if status["status"] == "succeeded":
                        job["progress"] = 100
                        return {
                            "url": status["output"],
                            "provider": "replicate",
                            "model": job["model"],
                            "duration": job["duration"],
                            "resolution": job["resolution"],
                            "seed": job["seed"]
                        }
                    elif status["status"] == "failed":
                        raise Exception("Replicate generation failed")
                    
                    # Update progress
                    job["updated_at"] = datetime.now().isoformat()
            
            return None
            
        except Exception as e:
            print(f"Replicate generation error: {e}")
            return None
    
    async def _fal_generate(self, job: Dict) -> Optional[Dict]:
        """Generate video using FAL.ai"""
        if not self.fal_key:
            raise Exception("FAL.ai API key not configured")
        
        try:
            job["progress"] = 30
            
            async with aiohttp.ClientSession() as session:
                # Map model
                model_map = {
                    "ltx-video": "fal-ai/ltx-video",
                    "kling": "fal-ai/kling-video",
                    "pika": "fal-ai/pika",
                    "stable-video": "fal-ai/stable-video"
                }
                
                fal_model = model_map.get(job["model"], "fal-ai/ltx-video")
                
                async with session.post(
                    f"https://fal.run/{fal_model}",
                    headers={
                        "Authorization": f"Key {self.fal_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": job["enhanced_prompt"],
                        "negative_prompt": job.get("negative_prompt", ""),
                        "num_frames": job["duration"] * job["fps"],
                        "video_size": job["resolution"],
                        "seed": job["seed"]
                    }
                ) as response:
                    data = await response.json()
                    
                    job["progress"] = 90
                    
                    if response.status == 200:
                        return {
                            "url": data["video"]["url"],
                            "provider": "fal",
                            "model": job["model"],
                            "duration": job["duration"],
                            "resolution": job["resolution"],
                            "seed": job["seed"]
                        }
                    else:
                        raise Exception(f"FAL.ai error: {data}")
                        
        except Exception as e:
            print(f"FAL.ai generation error: {e}")
            return None
    
    async def _stability_generate(self, job: Dict) -> Optional[Dict]:
        """Generate video using Stability AI"""
        if not self.stability_key:
            raise Exception("Stability AI API key not configured")
        
        try:
            job["progress"] = 25
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.stability.ai/v2beta/image-to-video",
                    headers={
                        "authorization": f"Bearer {self.stability_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": job["enhanced_prompt"],
                        "seed": job["seed"],
                        "cfg_scale": 7,
                        "motion_bucket_id": 127
                    }
                ) as response:
                    data = await response.json()
                    
                    job["progress"] = 50
                    
                    if response.status == 200:
                        generation_id = data.get("id")
                        
                        # Poll for completion
                        for _ in range(60):
                            await asyncio.sleep(2)
                            job["progress"] += 1
                            
                            async with session.get(
                                f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                                headers={"authorization": f"Bearer {self.stability_key}"}
                            ) as result_response:
                                if result_response.status == 200:
                                    result = await result_response.json()
                                    job["progress"] = 100
                                    return {
                                        "url": result.get("video"),
                                        "provider": "stability",
                                        "model": "stable-video-diffusion",
                                        "duration": job["duration"],
                                        "resolution": job["resolution"],
                                        "seed": job["seed"]
                                    }
                                elif result_response.status == 202:
                                    continue
                                else:
                                    break
                    
                    raise Exception(f"Stability AI error: {data}")
                    
        except Exception as e:
            print(f"Stability AI generation error: {e}")
            return None
    
    async def _kling_generate(self, job: Dict) -> Optional[Dict]:
        """Generate video using Kling AI"""
        if not self.kling_key:
            raise Exception("Kling AI API key not configured")
        
        try:
            job["progress"] = 20
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.kling.ai/v1/videos",
                    headers={
                        "Authorization": f"Bearer {self.kling_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": job["enhanced_prompt"],
                        "negative_prompt": job.get("negative_prompt", ""),
                        "duration": job["duration"],
                        "resolution": job["resolution"],
                        "fps": job["fps"],
                        "seed": job["seed"]
                    }
                ) as response:
                    data = await response.json()
                    
                    job["progress"] = 40
                    
                    if response.status == 200:
                        task_id = data.get("task_id")
                        
                        # Poll for completion
                        for _ in range(60):
                            await asyncio.sleep(2)
                            job["progress"] += 1
                            
                            async with session.get(
                                f"https://api.kling.ai/v1/videos/{task_id}",
                                headers={"Authorization": f"Bearer {self.kling_key}"}
                            ) as status_response:
                                status_data = await status_response.json()
                                
                                if status_data.get("status") == "completed":
                                    job["progress"] = 100
                                    return {
                                        "url": status_data.get("result", {}).get("url"),
                                        "provider": "kling",
                                        "model": "kling-1.0",
                                        "duration": job["duration"],
                                        "resolution": job["resolution"],
                                        "seed": job["seed"]
                                    }
                                elif status_data.get("status") == "failed":
                                    break
                    
                    raise Exception(f"Kling AI error: {data}")
                    
        except Exception as e:
            print(f"Kling AI generation error: {e}")
            return None
    
    async def _colab_generate(self, job: Dict) -> Optional[Dict]:
        """Generate video using Google Colab"""
        if not self.colab_url:
            raise Exception("Colab URL not configured")
        
        try:
            job["progress"] = 30
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.colab_url}/generate",
                    json={
                        "prompt": job["enhanced_prompt"],
                        "duration": job["duration"],
                        "resolution": job["resolution"]
                    },
                    timeout=300
                ) as response:
                    data = await response.json()
                    
                    job["progress"] = 90
                    
                    if response.status == 200:
                        return {
                            "url": data.get("video_url"),
                            "provider": "colab",
                            "model": "colab-video",
                            "duration": job["duration"],
                            "resolution": job["resolution"],
                            "seed": job["seed"]
                        }
                    else:
                        raise Exception(f"Colab error: {data}")
                        
        except Exception as e:
            print(f"Colab generation error: {e}")
            return None
    
    # ========== UTILITY METHODS ==========
    
    async def _select_best_provider(self, duration: int, priority: str) -> VideoProvider:
        """Select best provider based on duration and priority"""
        
        if priority == "fast":
            # Fastest providers
            available = [VideoProvider.FAL, VideoProvider.KLING]
        elif priority == "cheap":
            # Cheapest providers
            available = [VideoProvider.COLAB, VideoProvider.RUNPOD]
        else:
            # Balanced
            available = [VideoProvider.FAL, VideoProvider.REPLICATE, VideoProvider.RUNPOD]
        
        # Check which providers have keys
        providers_with_keys = []
        for provider in available:
            if provider == VideoProvider.FAL and self.fal_key:
                providers_with_keys.append(provider)
            elif provider == VideoProvider.REPLICATE and self.replicate_key:
                providers_with_keys.append(provider)
            elif provider == VideoProvider.RUNPOD and self.runpod_key:
                providers_with_keys.append(provider)
            elif provider == VideoProvider.KLING and self.kling_key:
                providers_with_keys.append(provider)
            elif provider == VideoProvider.COLAB and self.colab_url:
                providers_with_keys.append(provider)
        
        if providers_with_keys:
            return providers_with_keys[0]
        
        # Default to FAL if available
        if self.fal_key:
            return VideoProvider.FAL
        
        return VideoProvider.RUNPOD
    
    def _get_estimated_time(self, provider: VideoProvider, duration: int) -> int:
        """Get estimated processing time in seconds"""
        
        times = {
            VideoProvider.FAL: 30,
            VideoProvider.KLING: 45,
            VideoProvider.REPLICATE: 60,
            VideoProvider.RUNPOD: 90,
            VideoProvider.STABILITY: 120,
            VideoProvider.COLAB: 180
        }
        
        base_time = times.get(provider, 60)
        return base_time + (duration * 2)
    
    async def _cleanup_old_jobs(self, user_id: str):
        """Clean up old jobs for user"""
        now = datetime.now()
        to_delete = []
        
        for job_id, job in self.jobs.items():
            if job.get("user_id") == user_id:
                completed_at = job.get("completed_at")
                if completed_at:
                    completed_time = datetime.fromisoformat(completed_at)
                    if (now - completed_time).seconds > self.job_ttl:
                        to_delete.append(job_id)
        
        for job_id in to_delete:
            del self.jobs[job_id]
    
    async def _cache_video(self, job: Dict, result: Dict):
        """Cache generated video"""
        cache_key = hashlib.md5(
            f"{job['prompt']}_{job['duration']}_{job['resolution']}_{job['style']}".encode()
        ).hexdigest()
        
        self.cache[cache_key] = {
            "job": job,
            "result": result,
            "cached_at": datetime.now().isoformat()
        }
    
    async def _call_webhook(self, job: Dict):
        """Call webhook with result"""
        if not job.get("webhook_url"):
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    job["webhook_url"],
                    json={
                        "job_id": job["id"],
                        "status": job["status"],
                        "result": job["result"],
                        "error": job["error"],
                        "completed_at": job.get("completed_at")
                    }
                )
        except Exception as e:
            print(f"Webhook call failed: {e}")
    
    # ========== JOB MANAGEMENT ==========
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        job = self.jobs.get(job_id)
        
        if not job:
            return {
                "job_id": job_id,
                "status": "not_found"
            }
        
        return {
            "job_id": job["id"],
            "status": job["status"],
            "progress": job.get("progress", 0),
            "prompt": job["prompt"],
            "duration": job["duration"],
            "resolution": job["resolution"],
            "style": job["style"],
            "provider": job["provider"],
            "submitted_at": job["submitted_at"],
            "updated_at": job["updated_at"],
            "completed_at": job.get("completed_at"),
            "result": job.get("result"),
            "error": job.get("error")
        }
    
    async def get_user_jobs(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get all jobs for user"""
        user_jobs = []
        
        for job in self.jobs.values():
            if job.get("user_id") == user_id:
                user_jobs.append({
                    "job_id": job["id"],
                    "status": job["status"],
                    "prompt": job["prompt"][:50],
                    "duration": job["duration"],
                    "submitted_at": job["submitted_at"],
                    "completed_at": job.get("completed_at")
                })
        
        # Sort by submitted_at descending
        user_jobs.sort(key=lambda x: x["submitted_at"], reverse=True)
        
        return user_jobs[:limit]
    
    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a pending job"""
        job = self.jobs.get(job_id)
        
        if not job or job.get("user_id") != user_id:
            return False
        
        if job["status"] in ["submitted", "processing"]:
            job["status"] = "cancelled"
            job["completed_at"] = datetime.now().isoformat()
            return True
        
        return False
    
    async def get_providers(self) -> Dict[str, Any]:
        """Get available providers and their status"""
        providers = {}
        
        for provider, config in self.providers.items():
            has_key = False
            if provider == VideoProvider.RUNPOD:
                has_key = bool(self.runpod_key)
            elif provider == VideoProvider.REPLICATE:
                has_key = bool(self.replicate_key)
            elif provider == VideoProvider.FAL:
                has_key = bool(self.fal_key)
            elif provider == VideoProvider.STABILITY:
                has_key = bool(self.stability_key)
            elif provider == VideoProvider.KLING:
                has_key = bool(self.kling_key)
            elif provider == VideoProvider.COLAB:
                has_key = bool(self.colab_url)
            
            providers[provider.value] = {
                "name": config["name"],
                "available": has_key,
                "models": list(config["models"].keys()),
                "cost_per_second": config["cost_per_second"],
                "speed": config["speed"],
                "quality": config["quality"]
            }
        
        return providers
    
    async def get_styles(self) -> Dict[str, str]:
        """Get available styles"""
        return {style.value: self.style_presets[style] for style in VideoStyle}
    
    async def get_resolutions(self) -> Dict[str, Dict]:
        """Get available resolutions"""
        return {
            res.value: {
                "width": config["width"],
                "height": config["height"],
                "frames": config["frames"]
            }
            for res, config in self.resolutions.items()
        }
    
    async def estimate_cost(self, 
                           prompt: str, 
                           duration: int = 5, 
                           resolution: str = "720p",
                           provider: str = "auto") -> Dict[str, Any]:
        """Estimate cost for video generation"""
        
        if provider == "auto":
            provider = (await self._select_best_provider(duration, "normal")).value
        
        provider_config = self.providers.get(VideoProvider(provider))
        if not provider_config:
            return {"error": "Provider not available"}
        
        cost_per_second = provider_config["cost_per_second"]
        total_cost = cost_per_second * duration
        
        # Resolution multiplier
        res_multipliers = {
            "480p": 0.5,
            "720p": 1.0,
            "1080p": 2.0,
            "1440p": 3.0,
            "2160p": 5.0
        }
        
        multiplier = res_multipliers.get(resolution, 1.0)
        total_cost *= multiplier
        
        return {
            "provider": provider,
            "duration_seconds": duration,
            "resolution": resolution,
            "cost_per_second": cost_per_second,
            "estimated_cost": round(total_cost, 4),
            "currency": "USD"
        }