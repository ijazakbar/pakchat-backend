# backend/models/chat.py - COMPLETE VERSION WITH ALL PROVIDERS

import openai
import groq
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
import os
import json
from dotenv import load_dotenv

# Third-party providers
try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("⚠️ Google GenerativeAI not installed")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ Anthropic not installed")

try:
    from openai import AsyncOpenAI
    OPENAI_NEW = True
except ImportError:
    OPENAI_NEW = False
    print("⚠️ New OpenAI client not installed")

try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    print("⚠️ Replicate not installed")

try:
    import aiohttp
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    print("⚠️ aiohttp not installed")

try:
    from huggingface_hub import InferenceClient
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    print("⚠️ huggingface_hub not installed")

load_dotenv()

class ChatModel:
    def __init__(self):
        # === ALL API KEYS ===
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.replicate_key = os.getenv("REPLICATE_API_KEY")
        self.fal_key = os.getenv("FAL_AI_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.cohere_key = os.getenv("COHERE_API_KEY")
        self.mistral_key = os.getenv("MISTRAL_API_KEY")
        
        # === ALL CLIENTS INITIALIZATION ===
        
        # 1. OpenAI Client
        if self.openai_key:
            if OPENAI_NEW:
                self.openai_client = AsyncOpenAI(api_key=self.openai_key)
            else:
                openai.api_key = self.openai_key
                self.openai_client = openai
        else:
            self.openai_client = None
        
        # 2. Groq Client
        if self.groq_key:
            self.groq_client = groq.AsyncGroq(api_key=self.groq_key)
        else:
            self.groq_client = None
        
        # 3. DeepSeek Client (OpenAI-compatible)
        if self.deepseek_key:
            self.deepseek_client = AsyncOpenAI(
                api_key=self.deepseek_key,
                base_url="https://api.deepseek.com/v1"
            )
        else:
            self.deepseek_client = None
        
        # 4. OpenRouter Client
        if self.openrouter_key:
            self.openrouter_client = AsyncOpenAI(
                api_key=self.openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
        else:
            self.openrouter_client = None
        
        # 5. Google Gemini Client
        if self.google_key and GOOGLE_AVAILABLE:
            genai.configure(api_key=self.google_key)
            self.google_client = genai
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        else:
            self.google_client = None
            self.gemini_model = None
        
        # 6. Anthropic Claude Client
        if self.anthropic_key and ANTHROPIC_AVAILABLE:
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)
        else:
            self.anthropic_client = None
        
        # 7. HuggingFace Client
        if self.huggingface_key and HUGGINGFACE_AVAILABLE:
            self.hf_client = InferenceClient(token=self.huggingface_key)
        else:
            self.hf_client = None
        
        # 8. Replicate Client
        if self.replicate_key and REPLICATE_AVAILABLE:
            replicate.Client(api_token=self.replicate_key)
            self.replicate_client = replicate
        else:
            self.replicate_client = None
        
        # 9. FAL.ai Client
        self.fal_client = None  # Will initialize on demand
        
        # 10. Cohere Client
        self.cohere_client = None  # Add if needed
        
        # 11. Mistral Client
        self.mistral_client = None  # Add if needed
        
        # === SYSTEM PROMPTS ===
        self.system_prompts = {
            "urdu": """آپ پاک چيٹ ہيں - ایک دیسی AI اسسٹنٹ۔
آپ کا کام صارفين کی اردو، رومن اردو اور انگريزی میں مدد کرنا ہے۔
پاکستانی ثقافت، کھانے، کرکٹ اور مقامی مسائل کی گہری سمجھ رکھتے ہيں۔
ہميشہ مددگار، دوستانہ اور احترام سے پيش آيں۔
مختصر اور جامع جواب ديں۔""",
            
            "roman-urdu": """Ap PakChat hain - ek desi AI assistant.
Ap ka kaam users ki Roman Urdu, Urdu aur English mein madad karna hai.
Pakistani culture, khanay, cricket aur local issues ki gehri samaj rakhtay hain.
Hamesha madadgar, dostana aur izzat say pesh aayein.
Mukhtasar aur jamey jawab dein.""",
            
            "english": """You are PakChat - a desi AI assistant.
Your job is to help users in Urdu, Roman Urdu, and English.
You have deep understanding of Pakistani culture, food, cricket, and local issues.
Always be helpful, friendly, and respectful.
Keep responses concise and to the point."""
        }
    
    # === MAIN CHAT METHOD - ALL PROVIDERS ===
    async def chat(self, 
                   messages: list, 
                   provider: str = "auto",
                   temperature: float = 0.7,
                   max_tokens: Optional[int] = None,
                   language: str = "urdu") -> Dict[str, Any]:
        """
        Main chat method - supports ALL providers:
        - "auto" - tries all in order
        - "deepseek" - DeepSeek API
        - "groq" - Groq (fastest)
        - "openai" - OpenAI GPT-4
        - "openrouter" - 50+ models
        - "google" - Gemini Pro
        - "anthropic" - Claude
        - "huggingface" - HuggingFace models
        - "cohere" - Cohere
        - "mistral" - Mistral AI
        """
        try:
            # Add system prompt if not present
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {
                    "role": "system", 
                    "content": self.system_prompts.get(language, self.system_prompts["urdu"])
                })
            
            # Auto-select provider (try in order)
            if provider == "auto":
                # Priority order: fastest/cheapest first
                providers_order = [
                    "groq",      # Fastest
                    "deepseek",  # Cheap & good
                    "openrouter", # 50+ models
                    "openai",    # GPT-4
                    "google",    # Gemini (free)
                    "anthropic", # Claude
                    "huggingface", # Open source
                    "cohere",    # Enterprise
                    "mistral"    # European
                ]
                last_error = None
                
                for p in providers_order:
                    try:
                        result = await self._chat_with_provider(
                            provider=p,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        result["provider"] = p
                        return result
                    except Exception as e:
                        last_error = e
                        continue
                
                raise Exception(f"All providers failed. Last error: {last_error}")
            
            # Specific provider
            else:
                result = await self._chat_with_provider(
                    provider=provider,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                result["provider"] = provider
                return result
                
        except Exception as e:
            return {
                "error": True,
                "message": f"Chat error: {str(e)}",
                "choices": [{
                    "message": {
                        "content": f"Maafi chahta hoon, koi masla aa gaya: {str(e)}"
                    }
                }]
            }
    
    # === INTERNAL PROVIDER METHODS ===
    async def _chat_with_provider(self, 
                                  provider: str,
                                  messages: list,
                                  temperature: float,
                                  max_tokens: Optional[int]) -> Dict[str, Any]:
        """Route to specific provider"""
        
        if provider == "deepseek":
            return await self._deepseek_chat(messages, temperature, max_tokens)
        elif provider == "groq":
            return await self._groq_chat(messages, temperature, max_tokens)
        elif provider == "openai":
            return await self._openai_chat(messages, temperature, max_tokens)
        elif provider == "openrouter":
            return await self._openrouter_chat(messages, temperature, max_tokens)
        elif provider == "google":
            return await self._google_chat(messages, temperature, max_tokens)
        elif provider == "anthropic":
            return await self._anthropic_chat(messages, temperature, max_tokens)
        elif provider == "huggingface":
            return await self._huggingface_chat(messages, temperature, max_tokens)
        elif provider == "cohere":
            return await self._cohere_chat(messages, temperature, max_tokens)
        elif provider == "mistral":
            return await self._mistral_chat(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    # === 1. DEEPSEEK ===
    async def _deepseek_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.deepseek_client:
            raise Exception("DeepSeek API key not configured")
        
        try:
            response = await self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 4096
            )
            
            return {
                "choices": [{
                    "message": {
                        "content": response.choices[0].message.content
                    }
                }],
                "usage": {
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "model": "deepseek-chat"
            }
        except Exception as e:
            raise Exception(f"DeepSeek error: {str(e)}")
    
    # === 2. GROQ (FASTEST) ===
    async def _groq_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.groq_client:
            raise Exception("Groq API key not configured")
        
        try:
            response = await self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 4096
            )
            
            return {
                "choices": [{
                    "message": {
                        "content": response.choices[0].message.content
                    }
                }],
                "usage": {
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "model": "mixtral-8x7b-32768"
            }
        except Exception as e:
            raise Exception(f"Groq error: {str(e)}")
    
    # === 3. OPENAI ===
    async def _openai_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.openai_key:
            raise Exception("OpenAI API key not configured")
        
        try:
            if hasattr(self, 'openai_client') and hasattr(self.openai_client, 'chat'):
                # New OpenAI client
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or 4096
                )
                return {
                    "choices": [{
                        "message": {
                            "content": response.choices[0].message.content
                        }
                    }],
                    "usage": {
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    "model": "gpt-4-turbo-preview"
                }
            else:
                # Old OpenAI client
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or 4096
                )
                return {
                    "choices": [{
                        "message": {
                            "content": response.choices[0].message.content
                        }
                    }],
                    "usage": {
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    "model": "gpt-4-turbo-preview"
                }
        except Exception as e:
            raise Exception(f"OpenAI error: {str(e)}")
    
    # === 4. OPENROUTER (50+ MODELS) ===
    async def _openrouter_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.openrouter_client:
            raise Exception("OpenRouter API key not configured")
        
        try:
            response = await self.openrouter_client.chat.completions.create(
                model="openai/gpt-3.5-turbo",  # OpenRouter will use best available
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 4096,
                headers={
                    "HTTP-Referer": "https://pakchat.ai",
                    "X-Title": "PakChat"
                }
            )
            
            return {
                "choices": [{
                    "message": {
                        "content": response.choices[0].message.content
                    }
                }],
                "usage": {
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "model": response.model,
                "provider": "openrouter"
            }
        except Exception as e:
            raise Exception(f"OpenRouter error: {str(e)}")
    
    # === 5. GOOGLE GEMINI ===
    async def _google_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.google_client or not self.gemini_model:
            raise Exception("Google API key not configured")
        
        try:
            # Convert messages to Google format
            prompt = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    prompt += f"System: {content}\n\n"
                elif role == "user":
                    prompt += f"User: {content}\n"
                elif role == "assistant":
                    prompt += f"Assistant: {content}\n"
            
            prompt += "Assistant: "
            
            # Generate response
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens or 4096,
                }
            )
            
            return {
                "choices": [{
                    "message": {
                        "content": response.text
                    }
                }],
                "usage": {
                    "total_tokens": len(prompt.split()) + len(response.text.split())
                },
                "model": "gemini-pro"
            }
        except Exception as e:
            raise Exception(f"Google Gemini error: {str(e)}")
    
    # === 6. ANTHROPIC CLAUDE ===
    async def _anthropic_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.anthropic_client:
            raise Exception("Anthropic API key not configured")
        
        try:
            # Convert messages to Anthropic format
            system_prompt = ""
            user_messages = []
            
            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", "")
                else:
                    user_messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Create message
            response = await self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                system=system_prompt if system_prompt else None,
                messages=user_messages,
                temperature=temperature,
                max_tokens=max_tokens or 4096
            )
            
            return {
                "choices": [{
                    "message": {
                        "content": response.content[0].text
                    }
                }],
                "usage": {
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                "model": "claude-3-opus"
            }
        except Exception as e:
            raise Exception(f"Anthropic Claude error: {str(e)}")
    
    # === 7. HUGGINGFACE ===
    async def _huggingface_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.hf_client:
            raise Exception("HuggingFace API key not configured")
        
        try:
            # Get last user message
            last_user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            
            if not last_user_msg:
                raise Exception("No user message found")
            
            # Use HuggingFace chat model
            response = self.hf_client.text_generation(
                last_user_msg,
                model="mistralai/Mistral-7B-Instruct-v0.2",
                max_new_tokens=max_tokens or 512,
                temperature=temperature
            )
            
            return {
                "choices": [{
                    "message": {
                        "content": response
                    }
                }],
                "usage": {
                    "total_tokens": len(last_user_msg.split()) + len(response.split())
                },
                "model": "Mistral-7B-Instruct"
            }
        except Exception as e:
            raise Exception(f"HuggingFace error: {str(e)}")
    
    # === 8. COHERE ===
    async def _cohere_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.cohere_key:
            raise Exception("Cohere API key not configured")
        
        try:
            # Get last user message
            last_user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            
            # Call Cohere API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.cohere.ai/v1/generate",
                    headers={
                        "Authorization": f"Bearer {self.cohere_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": last_user_msg,
                        "max_tokens": max_tokens or 300,
                        "temperature": temperature,
                        "model": "command"
                    }
                ) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        text = data.get("generations", [{}])[0].get("text", "")
                        return {
                            "choices": [{
                                "message": {
                                    "content": text
                                }
                            }],
                            "usage": {
                                "total_tokens": data.get("meta", {}).get("tokens", {}).get("total", 0)
                            },
                            "model": "cohere-command"
                        }
                    else:
                        raise Exception(f"Cohere API error: {data}")
        except Exception as e:
            raise Exception(f"Cohere error: {str(e)}")
    
    # === 9. MISTRAL ===
    async def _mistral_chat(self, messages: list, temperature: float, max_tokens: Optional[int]):
        if not self.mistral_key:
            raise Exception("Mistral API key not configured")
        
        try:
            # Call Mistral API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.mistral_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mistral-small-latest",
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens or 2048
                    }
                ) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        return {
                            "choices": data.get("choices", []),
                            "usage": data.get("usage", {}),
                            "model": "mistral-small"
                        }
                    else:
                        raise Exception(f"Mistral API error: {data}")
        except Exception as e:
            raise Exception(f"Mistral error: {str(e)}")
    
    # === STREAMING METHODS ===
    async def stream_chat(self, 
                          messages: list,
                          provider: str = "groq",
                          temperature: float = 0.7,
                          language: str = "urdu") -> AsyncGenerator[str, None]:
        """Streaming response - supports Groq, DeepSeek, OpenRouter"""
        try:
            # Add system prompt if not present
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {
                    "role": "system", 
                    "content": self.system_prompts.get(language, self.system_prompts["urdu"])
                })
            
            if provider == "groq" and self.groq_client:
                # Groq streaming
                stream = await self.groq_client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            
            elif provider == "deepseek" and self.deepseek_client:
                # DeepSeek streaming
                stream = await self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            
            elif provider == "openrouter" and self.openrouter_client:
                # OpenRouter streaming
                stream = await self.openrouter_client.chat.completions.create(
                    model="openai/gpt-3.5-turbo",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4096,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            
            else:
                # Fallback to non-streaming
                response = await self.chat(messages, provider, temperature, language=language)
                content = response["choices"][0]["message"]["content"]
                for word in content.split():
                    yield word + " "
                    await asyncio.sleep(0.05)
                    
        except Exception as e:
            yield f"Stream error: {str(e)}"
    
    # === BACKWARD COMPATIBILITY METHODS ===
    async def quick_response(self, message: str, language: str = "urdu") -> str:
        """Quick response using Groq (for backward compatibility)"""
        messages = [{"role": "user", "content": message}]
        result = await self.chat(messages, provider="groq", language=language)
        return result["choices"][0]["message"]["content"]
    
    async def deep_response(self, message: str, language: str = "urdu") -> str:
        """Deep response using best model"""
        messages = [{"role": "user", "content": message}]
        result = await self.chat(messages, provider="auto", language=language)
        return result["choices"][0]["message"]["content"]
    
    async def reasoning_response(self, message: str, language: str = "urdu") -> str:
        """Reasoning response"""
        messages = [
            {"role": "system", "content": "Think step by step. Show your reasoning."},
            {"role": "user", "content": message}
        ]
        result = await self.chat(messages, provider="deepseek", language=language)
        return result["choices"][0]["message"]["content"]
    
    async def stream_response(self, message: str, language: str = "urdu") -> AsyncGenerator[str, None]:
        """Stream response (backward compatibility)"""
        messages = [{"role": "user", "content": message}]
        async for chunk in self.stream_chat(messages, provider="groq", language=language):
            yield chunk