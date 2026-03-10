# backend/models/voice.py - COMPLETE PROFESSIONAL VOICE PROCESSING
# Supports multiple providers: AssemblyAI, ElevenLabs, OpenAI, Google, Azure

import aiohttp
import asyncio
import os
import base64
import uuid
import json
import re
from typing import Optional, Dict, Any, List, Union, AsyncGenerator
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib
from dotenv import load_dotenv

# WebSocket for real-time
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️ WebSockets not installed - real-time features disabled")

load_dotenv()

class VoiceProvider(str, Enum):
    """Available voice providers"""
    ASSEMBLYAI = "assemblyai"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    DEEPGRAM = "deepgram"

class VoiceGender(str, Enum):
    """Voice genders"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class AudioFormat(str, Enum):
    """Audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    AAC = "aac"
    FLAC = "flac"
    PCM = "pcm"

class VoiceProcessor:
    # 👈 FIXED: __init__ with assemblyai_key and elevenlabs_key parameters
    def __init__(self, assemblyai_key: str = None, elevenlabs_key: str = None):
        # API Keys - Use passed parameters first, then fallback to env
        self.assembly_key = assemblyai_key or os.getenv("ASSEMBLYAI_API_KEY")
        self.elevenlabs_key = elevenlabs_key or os.getenv("ELEVENLABS_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.azure_key = os.getenv("AZURE_SPEECH_KEY")
        self.azure_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.deepgram_key = os.getenv("DEEPGRAM_API_KEY")
        
        # Voice configurations
        self.voices = {
            # Urdu voices
            "urdu-female": {
                "provider": VoiceProvider.ELEVENLABS,
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Urdu Female",
                "gender": VoiceGender.FEMALE,
                "language": "ur",
                "description": "Natural Urdu female voice"
            },
            "urdu-male": {
                "provider": VoiceProvider.ELEVENLABS,
                "voice_id": "AZnzlk1XvdvUeBnXmlld",
                "name": "Urdu Male",
                "gender": VoiceGender.MALE,
                "language": "ur",
                "description": "Professional Urdu male voice"
            },
            "urdu-google-female": {
                "provider": VoiceProvider.GOOGLE,
                "voice_id": "ur-IN-Standard-A",
                "name": "Google Urdu Female",
                "gender": VoiceGender.FEMALE,
                "language": "ur",
                "description": "Google's Urdu female voice"
            },
            "urdu-google-male": {
                "provider": VoiceProvider.GOOGLE,
                "voice_id": "ur-IN-Standard-B",
                "name": "Google Urdu Male",
                "gender": VoiceGender.MALE,
                "language": "ur",
                "description": "Google's Urdu male voice"
            },
            "urdu-azure-female": {
                "provider": VoiceProvider.AZURE,
                "voice_id": "ur-PK-Asad",
                "name": "Azure Urdu Female",
                "gender": VoiceGender.FEMALE,
                "language": "ur",
                "description": "Microsoft Azure Urdu female voice"
            },
            
            # English voices
            "english-female": {
                "provider": VoiceProvider.ELEVENLABS,
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "name": "English Female",
                "gender": VoiceGender.FEMALE,
                "language": "en",
                "description": "Natural English female voice"
            },
            "english-male": {
                "provider": VoiceProvider.ELEVENLABS,
                "voice_id": "ErXwobaYiN019PkySvjV",
                "name": "English Male",
                "gender": VoiceGender.MALE,
                "language": "en",
                "description": "Professional English male voice"
            },
            "english-openai-female": {
                "provider": VoiceProvider.OPENAI,
                "voice_id": "nova",
                "name": "OpenAI Nova",
                "gender": VoiceGender.FEMALE,
                "language": "en",
                "description": "OpenAI's Nova voice"
            },
            "english-openai-male": {
                "provider": VoiceProvider.OPENAI,
                "voice_id": "onyx",
                "name": "OpenAI Onyx",
                "gender": VoiceGender.MALE,
                "language": "en",
                "description": "OpenAI's Onyx voice"
            },
            "english-google-female": {
                "provider": VoiceProvider.GOOGLE,
                "voice_id": "en-US-Standard-C",
                "name": "Google English Female",
                "gender": VoiceGender.FEMALE,
                "language": "en",
                "description": "Google's English female voice"
            },
            "english-google-male": {
                "provider": VoiceProvider.GOOGLE,
                "voice_id": "en-US-Standard-D",
                "name": "Google English Male",
                "gender": VoiceGender.MALE,
                "language": "en",
                "description": "Google's English male voice"
            },
            "english-azure-female": {
                "provider": VoiceProvider.AZURE,
                "voice_id": "en-US-JennyNeural",
                "name": "Azure Jenny",
                "gender": VoiceGender.FEMALE,
                "language": "en",
                "description": "Microsoft Azure Jenny voice"
            },
            "english-azure-male": {
                "provider": VoiceProvider.AZURE,
                "voice_id": "en-US-GuyNeural",
                "name": "Azure Guy",
                "gender": VoiceGender.MALE,
                "language": "en",
                "description": "Microsoft Azure Guy voice"
            },
            
            # Hindi voices
            "hindi-female": {
                "provider": VoiceProvider.ELEVENLABS,
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Hindi Female",
                "gender": VoiceGender.FEMALE,
                "language": "hi",
                "description": "Hindi female voice"
            },
            "hindi-google-female": {
                "provider": VoiceProvider.GOOGLE,
                "voice_id": "hi-IN-Standard-A",
                "name": "Google Hindi Female",
                "gender": VoiceGender.FEMALE,
                "language": "hi",
                "description": "Google's Hindi female voice"
            },
            "hindi-azure-female": {
                "provider": VoiceProvider.AZURE,
                "voice_id": "hi-IN-SwaraNeural",
                "name": "Azure Hindi Female",
                "gender": VoiceGender.FEMALE,
                "language": "hi",
                "description": "Microsoft Azure Hindi female voice"
            },
            
            # Arabic voices
            "arabic-female": {
                "provider": VoiceProvider.ELEVENLABS,
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Arabic Female",
                "gender": VoiceGender.FEMALE,
                "language": "ar",
                "description": "Arabic female voice"
            },
            "arabic-google-female": {
                "provider": VoiceProvider.GOOGLE,
                "voice_id": "ar-XA-Standard-A",
                "name": "Google Arabic Female",
                "gender": VoiceGender.FEMALE,
                "language": "ar",
                "description": "Google's Arabic female voice"
            }
        }
        
        # Transcription models
        self.transcription_models = {
            "assemblyai": {
                "provider": VoiceProvider.ASSEMBLYAI,
                "languages": ["ur", "en", "hi", "ar", "es", "fr", "de", "zh", "ru"],
                "features": ["language_detection", "punctuation", "sentiment", "entities"]
            },
            "openai": {
                "provider": VoiceProvider.OPENAI,
                "model": "whisper-1",
                "languages": ["ur", "en", "hi", "ar", "es", "fr", "de", "zh", "ru"],
                "features": ["translation"]
            },
            "google": {
                "provider": VoiceProvider.GOOGLE,
                "languages": ["ur", "en", "hi", "ar", "es", "fr", "de", "zh", "ru"],
                "features": ["real_time", "speaker_diarization"]
            },
            "deepgram": {
                "provider": VoiceProvider.DEEPGRAM,
                "languages": ["en", "es", "fr", "de"],
                "features": ["real_time", "punctuation", "numbers"]
            }
        }
        
        # Audio settings
        self.audio_settings = {
            "sample_rates": [8000, 16000, 22050, 44100, 48000],
            "channels": [1, 2],
            "bitrates": [64, 128, 192, 256, 320]
        }
        
        # Cache for generated audio
        self.audio_cache = {}
        self.cache_ttl = 604800  # 7 days
        
        # Storage path
        self.output_dir = Path("outputs/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # ========== TRANSCRIPTION METHODS ==========
    
    async def transcribe(self, 
                        audio_path: str, 
                        language: str = "ur",
                        provider: str = "auto",
                        options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Transcribe audio to text with multiple provider support
        """
        try:
            # Auto-select provider
            if provider == "auto":
                provider = await self._select_best_transcription_provider(language)
            
            # Read audio file
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            # Get audio info
            audio_info = await self._get_audio_info(audio_path)
            
            # Call appropriate provider
            if provider == VoiceProvider.ASSEMBLYAI:
                result = await self._transcribe_assemblyai(audio_data, language, options)
            elif provider == VoiceProvider.OPENAI:
                result = await self._transcribe_openai(audio_path, language, options)
            elif provider == VoiceProvider.GOOGLE:
                result = await self._transcribe_google(audio_data, language, options)
            elif provider == VoiceProvider.DEEPGRAM:
                result = await self._transcribe_deepgram(audio_data, language, options)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Add metadata
            result["provider"] = provider.value if hasattr(provider, 'value') else str(provider)
            result["language"] = language
            result["audio_info"] = audio_info
            
            return result
            
        except Exception as e:
            return {
                "error": True,
                "message": f"Transcription failed: {str(e)}",
                "text": None
            }
    
    async def _transcribe_assemblyai(self, audio_data: bytes, language: str, options: Optional[Dict]) -> Dict:
        """Transcribe using AssemblyAI"""
        if not self.assembly_key:
            raise Exception("AssemblyAI API key not configured")
        
        async with aiohttp.ClientSession() as session:
            # Upload audio
            async with session.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": self.assembly_key},
                data=audio_data
            ) as response:
                upload_result = await response.json()
                audio_url = upload_result["upload_url"]
            
            # Configure transcription
            config = {
                "audio_url": audio_url,
                "language_detection": language == "auto",
                "punctuate": options.get("punctuate", True) if options else True,
                "format_text": options.get("format_text", True) if options else True,
                "sentiment_analysis": options.get("sentiment", False) if options else False,
                "entity_detection": options.get("entities", False) if options else False,
                "auto_chapters": options.get("chapters", False) if options else False
            }
            
            if language != "auto":
                config["language_code"] = language
            
            # Submit transcription
            async with session.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={
                    "authorization": self.assembly_key,
                    "content-type": "application/json"
                },
                json=config
            ) as response:
                transcript_result = await response.json()
                transcript_id = transcript_result["id"]
            
            # Poll for result
            max_attempts = 60
            for attempt in range(max_attempts):
                await asyncio.sleep(2)
                
                async with session.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"authorization": self.assembly_key}
                ) as response:
                    result = await response.json()
                
                if result["status"] == "completed":
                    return {
                        "text": result["text"],
                        "confidence": result.get("confidence", 0.95),
                        "words": result.get("words", []),
                        "sentences": result.get("sentences", []),
                        "sentiment": result.get("sentiment_analysis_results", []),
                        "entities": result.get("entities", []),
                        "chapters": result.get("chapters", []),
                        "audio_duration": result.get("audio_duration"),
                        "processing_time": attempt * 2
                    }
                elif result["status"] == "error":
                    raise Exception(f"AssemblyAI error: {result['error']}")
            
            raise Exception("Transcription timeout")
    
    async def _transcribe_openai(self, audio_path: str, language: str, options: Optional[Dict]) -> Dict:
        """Transcribe using OpenAI Whisper"""
        if not self.openai_key:
            raise Exception("OpenAI API key not configured")
        
        # Import openai
        try:
            import openai
        except ImportError:
            raise Exception("OpenAI package not installed. Run: pip install openai")
        
        openai.api_key = self.openai_key
        
        try:
            with open(audio_path, "rb") as audio_file:
                # Choose between transcription and translation
                if options and options.get("translate", False):
                    # Translate to English
                    response = await openai.Translation.acreate(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json"
                    )
                else:
                    # Transcribe in original language
                    response = await openai.Transcription.acreate(
                        model="whisper-1",
                        file=audio_file,
                        language=language if language != "auto" else None,
                        response_format="verbose_json",
                        prompt=options.get("prompt") if options else None
                    )
            
            return {
                "text": response["text"],
                "language": response.get("language", language),
                "duration": response.get("duration"),
                "segments": response.get("segments", []),
                "confidence": 0.95,  # Whisper doesn't provide confidence
                "provider": "openai"
            }
            
        except Exception as e:
            raise Exception(f"OpenAI Whisper error: {str(e)}")
    
    async def _transcribe_google(self, audio_data: bytes, language: str, options: Optional[Dict]) -> Dict:
        """Transcribe using Google Speech-to-Text"""
        if not self.google_key:
            raise Exception("Google API key not configured")
        
        # Encode audio as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Prepare config
        config = {
            "encoding": "LINEAR16",
            "sample_rate_hertz": 16000,
            "audio_channel_count": 1,
            "enable_automatic_punctuation": options.get("punctuate", True) if options else True,
            "enable_word_confidence": True,
            "enable_word_time_offsets": True,
            "model": "latest_long" if options and options.get("long") else "latest_short"
        }
        
        if language != "auto":
            config["language_code"] = language
        else:
            config["language_code"] = "ur-PK"  # Default to Urdu
        
        # Add alternative languages
        if options and options.get("alternative_languages"):
            config["alternative_language_codes"] = options["alternative_languages"]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://speech.googleapis.com/v1/speech:recognize?key={self.google_key}",
                json={
                    "config": config,
                    "audio": {
                        "content": audio_base64
                    }
                }
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    results = data.get("results", [])
                    if results:
                        alternative = results[0].get("alternatives", [{}])[0]
                        
                        # Process words with timings
                        words = []
                        if "words" in alternative:
                            for word_info in alternative["words"]:
                                words.append({
                                    "word": word_info["word"],
                                    "start": float(word_info.get("startTime", "0s").replace("s", "")),
                                    "end": float(word_info.get("endTime", "0s").replace("s", "")),
                                    "confidence": word_info.get("confidence", 1.0)
                                })
                        
                        return {
                            "text": alternative.get("transcript", ""),
                            "confidence": alternative.get("confidence", 0.95),
                            "words": words,
                            "language": results[0].get("languageCode", language),
                            "provider": "google"
                        }
                    else:
                        return {"text": "", "confidence": 0}
                else:
                    raise Exception(f"Google Speech error: {data}")
    
    async def _transcribe_deepgram(self, audio_data: bytes, language: str, options: Optional[Dict]) -> Dict:
        """Transcribe using Deepgram"""
        if not self.deepgram_key:
            raise Exception("Deepgram API key not configured")
        
        # Prepare query parameters
        params = {
            "punctuate": "true" if options and options.get("punctuate", True) else "false",
            "diarize": "true" if options and options.get("diarize", False) else "false",
            "numerals": "true" if options and options.get("numerals", False) else "false",
            "utterances": "true" if options and options.get("utterances", False) else "false"
        }
        
        if language != "auto":
            params["language"] = language
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {self.deepgram_key}",
                    "Content-Type": "audio/wav"
                },
                params=params,
                data=audio_data
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    results = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0]
                    
                    return {
                        "text": results.get("transcript", ""),
                        "confidence": results.get("confidence", 0.95),
                        "words": results.get("words", []),
                        "paragraphs": results.get("paragraphs", {}),
                        "provider": "deepgram"
                    }
                else:
                    raise Exception(f"Deepgram error: {data}")
    
    # ========== SPEECH SYNTHESIS METHODS ==========
    
    async def synthesize(self, 
                        text: str, 
                        voice: str = "urdu-female",
                        options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Convert text to speech with multiple voice options
        """
        try:
            # Get voice configuration
            voice_config = self.voices.get(voice)
            if not voice_config:
                # Try to find by language
                voice_config = await self._find_voice_by_language(text, voice)
            
            if not voice_config:
                raise ValueError(f"Voice '{voice}' not found")
            
            provider = voice_config["provider"]
            voice_id = voice_config["voice_id"]
            
            # Synthesis options
            speed = options.get("speed", 1.0) if options else 1.0
            pitch = options.get("pitch", 0) if options else 0
            format_type = options.get("format", AudioFormat.MP3)
            
            # Generate cache key
            cache_key = hashlib.md5(
                f"{text}_{voice}_{speed}_{pitch}_{format_type}".encode()
            ).hexdigest()
            
            # Check cache
            if cache_key in self.audio_cache:
                cached = self.audio_cache[cache_key]
                if datetime.now().timestamp() - cached["timestamp"] < self.cache_ttl:
                    return cached["result"]
            
            # Call appropriate provider
            if provider == VoiceProvider.ELEVENLABS:
                result = await self._synthesize_elevenlabs(text, voice_id, voice_config, options)
            elif provider == VoiceProvider.OPENAI:
                result = await self._synthesize_openai(text, voice_id, options)
            elif provider == VoiceProvider.GOOGLE:
                result = await self._synthesize_google(text, voice_id, options)
            elif provider == VoiceProvider.AZURE:
                result = await self._synthesize_azure(text, voice_id, options)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Save to cache
            self.audio_cache[cache_key] = {
                "result": result,
                "timestamp": datetime.now().timestamp()
            }
            
            return result
            
        except Exception as e:
            return {
                "error": True,
                "message": f"Synthesis failed: {str(e)}",
                "url": None
            }
    
    async def _synthesize_elevenlabs(self, text: str, voice_id: str, voice_config: Dict, options: Optional[Dict]) -> Dict:
        """Synthesize using ElevenLabs"""
        if not self.elevenlabs_key:
            raise Exception("ElevenLabs API key not configured")
        
        # Synthesis options
        stability = options.get("stability", 0.5) if options else 0.5
        similarity_boost = options.get("similarity_boost", 0.5) if options else 0.5
        speed = options.get("speed", 1.0) if options else 1.0
        model = options.get("model", "eleven_monolingual_v1") if options else "eleven_monolingual_v1"
        
        # Use multilingual model for Urdu
        if voice_config.get("language") == "ur":
            model = "eleven_multilingual_v1"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.elevenlabs_key
                },
                json={
                    "text": text,
                    "model_id": model,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "speed": speed
                    }
                }
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # Save audio file
                    filename = f"speech_{uuid.uuid4()}.mp3"
                    file_path = self.output_dir / filename
                    
                    with open(file_path, "wb") as f:
                        f.write(audio_data)
                    
                    return {
                        "url": f"/static/audio/{filename}",
                        "provider": "elevenlabs",
                        "voice": voice_id,
                        "duration": len(audio_data) / 16000,  # Approximate
                        "size": len(audio_data),
                        "format": "mp3"
                    }
                else:
                    error_data = await response.text()
                    raise Exception(f"ElevenLabs error: {error_data}")
    
    async def _synthesize_openai(self, text: str, voice_id: str, options: Optional[Dict]) -> Dict:
        """Synthesize using OpenAI TTS"""
        if not self.openai_key:
            raise Exception("OpenAI API key not configured")
        
        try:
            import openai
        except ImportError:
            raise Exception("OpenAI package not installed. Run: pip install openai")
        
        openai.api_key = self.openai_key
        
        try:
            response = await openai.audio.speech.create(
                model="tts-1",
                voice=voice_id,
                input=text,
                speed=options.get("speed", 1.0) if options else 1.0,
                response_format=options.get("format", "mp3") if options else "mp3"
            )
            
            # Get audio data
            audio_data = response.content
            
            # Save audio file
            format_ext = options.get("format", "mp3") if options else "mp3"
            filename = f"speech_{uuid.uuid4()}.{format_ext}"
            file_path = self.output_dir / filename
            
            with open(file_path, "wb") as f:
                f.write(audio_data)
            
            return {
                "url": f"/static/audio/{filename}",
                "provider": "openai",
                "voice": voice_id,
                "duration": len(audio_data) / 16000,  # Approximate
                "size": len(audio_data),
                "format": format_ext
            }
            
        except Exception as e:
            raise Exception(f"OpenAI TTS error: {str(e)}")
    
    async def _synthesize_google(self, text: str, voice_id: str, options: Optional[Dict]) -> Dict:
        """Synthesize using Google Text-to-Speech"""
        if not self.google_key:
            raise Exception("Google API key not configured")
        
        # Synthesis options
        speed = options.get("speed", 1.0) if options else 1.0
        pitch = options.get("pitch", 0) if options else 0
        format_type = options.get("format", "mp3") if options else "mp3"
        
        # Audio config
        audio_config = {
            "audio_encoding": "MP3" if format_type == "mp3" else "LINEAR16",
            "speaking_rate": speed,
            "pitch": pitch
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.google_key}",
                json={
                    "input": {"text": text},
                    "voice": {
                        "languageCode": voice_id.split("-")[0] + "-" + voice_id.split("-")[1],
                        "name": voice_id
                    },
                    "audioConfig": audio_config
                }
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Decode base64 audio
                    audio_content = data.get("audioContent", "")
                    if audio_content:
                        audio_data = base64.b64decode(audio_content)
                        
                        # Save audio file
                        filename = f"speech_{uuid.uuid4()}.{format_type}"
                        file_path = self.output_dir / filename
                        
                        with open(file_path, "wb") as f:
                            f.write(audio_data)
                        
                        return {
                            "url": f"/static/audio/{filename}",
                            "provider": "google",
                            "voice": voice_id,
                            "duration": len(audio_data) / 16000,  # Approximate
                            "size": len(audio_data),
                            "format": format_type
                        }
                    else:
                        raise Exception("No audio content in response")
                else:
                    raise Exception(f"Google TTS error: {data}")
    
    async def _synthesize_azure(self, text: str, voice_id: str, options: Optional[Dict]) -> Dict:
        """Synthesize using Azure Speech Services"""
        if not self.azure_key or not self.azure_region:
            raise Exception("Azure Speech Services not configured")
        
        # Synthesis options
        speed = options.get("speed", 1.0) if options else 1.0
        pitch = options.get("pitch", 0) if options else 0
        format_type = options.get("format", "mp3") if options else "mp3"
        
        # Build SSML
        ssml = f"""
        <speak version='1.0' xml:lang='{voice_id[:5]}'>
            <voice name='{voice_id}'>
                <prosody rate='{speed}' pitch='{pitch}%'>
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        
        # Map format
        output_format = "audio-24khz-160kbitrate-mono-mp3" if format_type == "mp3" else "riff-16khz-16bit-mono-pcm"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://{self.azure_region}.tts.speech.microsoft.com/cognitiveservices/v1",
                headers={
                    "Ocp-Apim-Subscription-Key": self.azure_key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": output_format,
                    "User-Agent": "PakChat"
                },
                data=ssml.encode('utf-8')
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # Save audio file
                    filename = f"speech_{uuid.uuid4()}.{format_type}"
                    file_path = self.output_dir / filename
                    
                    with open(file_path, "wb") as f:
                        f.write(audio_data)
                    
                    return {
                        "url": f"/static/audio/{filename}",
                        "provider": "azure",
                        "voice": voice_id,
                        "duration": len(audio_data) / 16000,  # Approximate
                        "size": len(audio_data),
                        "format": format_type
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Azure TTS error: {error_text}")
    
    # ========== REAL-TIME TRANSCRIPTION ==========
    
    async def real_time_transcribe(self, 
                                   audio_stream,
                                   language: str = "ur",
                                   on_result: Optional[callable] = None) -> AsyncGenerator[str, None]:
        """
        Real-time transcription using WebSockets
        """
        if not WEBSOCKETS_AVAILABLE:
            yield "WebSockets not available. Install with: pip install websockets"
            return
        
        # Use Deepgram for real-time (best latency)
        if self.deepgram_key:
            async for text in self._realtime_deepgram(audio_stream, language, on_result):
                yield text
        # Fallback to Google
        elif self.google_key:
            async for text in self._realtime_google(audio_stream, language, on_result):
                yield text
        else:
            yield "Real-time transcription requires Deepgram or Google API key"
    
    async def _realtime_deepgram(self, audio_stream, language: str, on_result: Optional[callable]):
        """Real-time transcription with Deepgram"""
        if not WEBSOCKETS_AVAILABLE:
            return
        
        deepgram_url = "wss://api.deepgram.com/v1/listen"
        
        params = {
            "punctuate": "true",
            "language": language,
            "encoding": "linear16",
            "sample_rate": "16000",
            "channels": "1"
        }
        
        async with websockets.connect(
            f"{deepgram_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}",
            extra_headers={"Authorization": f"Token {self.deepgram_key}"}
        ) as ws:
            # Send audio in chunks
            async for chunk in audio_stream:
                await ws.send(chunk)
                
                # Receive transcription
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    data = json.loads(response)
                    
                    transcript = data.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                    if transcript and on_result:
                        await on_result(transcript)
                    
                    yield transcript
                except asyncio.TimeoutError:
                    continue
    
    async def _realtime_google(self, audio_stream, language: str, on_result: Optional[callable]):
        """Real-time transcription with Google (placeholder)"""
        # Google doesn't have simple WebSocket API
        # Would need to use bidirectional streaming gRPC
        yield "Google real-time transcription requires gRPC setup"
    
    # ========== AUDIO UTILITIES ==========
    
    async def _get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get audio file information"""
        try:
            import wave
            with wave.open(audio_path, 'rb') as wav:
                return {
                    "channels": wav.getnchannels(),
                    "sample_width": wav.getsampwidth(),
                    "frame_rate": wav.getframerate(),
                    "frames": wav.getnframes(),
                    "duration": wav.getnframes() / wav.getframerate()
                }
        except:
            # Fallback to file size
            size = os.path.getsize(audio_path)
            return {
                "size": size,
                "duration": size / 16000 / 2  # Rough estimate
            }
    
    async def _select_best_transcription_provider(self, language: str) -> VoiceProvider:
        """Select best transcription provider for language"""
        
        if language == "ur" and self.assembly_key:
            return VoiceProvider.ASSEMBLYAI
        elif language in ["en", "es", "fr"] and self.deepgram_key:
            return VoiceProvider.DEEPGRAM
        elif self.openai_key:
            return VoiceProvider.OPENAI
        elif self.google_key:
            return VoiceProvider.GOOGLE
        elif self.assembly_key:
            return VoiceProvider.ASSEMBLYAI
        else:
            raise Exception("No transcription provider available")
    
    async def _find_voice_by_language(self, text: str, preferred_voice: str) -> Optional[Dict]:
        """Find appropriate voice by language"""
        # Detect language from text (simple detection)
        urdu_chars = re.search(r'[۔،؟آابپتٹثجچحخدڈذرڑزژسشصضطظعغفقکگلمنوہھئی]', text)
        
        if urdu_chars:
            # Urdu text - find Urdu voice
            for voice_name, config in self.voices.items():
                if config.get("language") == "ur" and preferred_voice in voice_name:
                    return config
            # Default Urdu voice
            return self.voices.get("urdu-female")
        else:
            # English text
            return self.voices.get("english-female")
    
    async def convert_format(self, audio_path: str, target_format: str) -> str:
        """Convert audio to different format"""
        # This would use ffmpeg
        # For now, return original path
        return audio_path
    
    async def get_available_voices(self, language: Optional[str] = None) -> List[Dict]:
        """Get list of available voices"""
        voices = []
        
        for name, config in self.voices.items():
            if not language or config.get("language") == language:
                voices.append({
                    "name": name,
                    "display_name": config["name"],
                    "provider": config["provider"].value if hasattr(config["provider"], 'value') else str(config["provider"]),
                    "gender": config["gender"].value if hasattr(config["gender"], 'value') else str(config["gender"]),
                    "language": config["language"],
                    "description": config["description"]
                })
        
        return voices
    
    async def get_available_providers(self) -> Dict[str, bool]:
        """Get available providers"""
        return {
            "assemblyai": bool(self.assembly_key),
            "elevenlabs": bool(self.elevenlabs_key),
            "openai": bool(self.openai_key),
            "google": bool(self.google_key),
            "azure": bool(self.azure_key),
            "deepgram": bool(self.deepgram_key)
        }
    
    async def estimate_cost(self, text: str, provider: str = "elevenlabs") -> Dict[str, Any]:
        """Estimate cost for TTS"""
        char_count = len(text)
        
        costs = {
            "elevenlabs": 0.0003,  # per character
            "openai": 0.015,  # per 1000 characters
            "google": 0.000016,  # per character
            "azure": 0.000015  # per character
        }
        
        cost_per_char = costs.get(provider, 0.0003)
        estimated_cost = char_count * cost_per_char
        
        return {
            "provider": provider,
            "characters": char_count,
            "cost_per_char": cost_per_char,
            "estimated_cost": round(estimated_cost, 4),
            "currency": "USD"
        }