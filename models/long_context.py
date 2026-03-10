# backend/models/long_context.py - ENHANCED VERSION
# Supports multiple models with 1M+ context window

import aiohttp
import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class LongContextProcessor:
    def __init__(self):
        # API Keys
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Available models with large context
        self.models = {
            # FREE models (OpenRouter)
            "nemotron-3-nano": {
                "provider": "openrouter",
                "model": "nvidia/nemotron-3-nano-30b-a3b:free",
                "context": 1000000,  # 1M tokens
                "free": True,
                "description": "Best free model with 1M context"
            },
            "gemma-2-9b-it": {
                "provider": "openrouter",
                "model": "google/gemma-2-9b-it:free",
                "context": 8192,
                "free": True,
                "description": "Google's Gemma 2 (free)"
            },
            "llama-3-8b-instruct": {
                "provider": "openrouter",
                "model": "meta-llama/llama-3-8b-instruct:free",
                "context": 8192,
                "free": True,
                "description": "Meta's Llama 3 (free)"
            },
            
            # Paid models (better quality)
            "claude-3-opus": {
                "provider": "anthropic",
                "model": "claude-3-opus-20240229",
                "context": 200000,  # 200K tokens
                "free": False,
                "description": "Best quality, 200K context"
            },
            "claude-3-sonnet": {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "context": 200000,
                "free": False,
                "description": "Good balance, 200K context"
            },
            "gpt-4-turbo": {
                "provider": "openai",
                "model": "gpt-4-turbo-preview",
                "context": 128000,  # 128K tokens
                "free": False,
                "description": "OpenAI's best, 128K context"
            },
            "gpt-3.5-turbo": {
                "provider": "openai",
                "model": "gpt-3.5-turbo-16k",
                "context": 16384,
                "free": False,
                "description": "Cheaper option, 16K context"
            }
        }
        
        # Default model (free)
        self.default_model = "nemotron-3-nano"
        
    async def process(
        self,
        text: str,
        task: str = "summarize",
        questions: Optional[List[str]] = None,
        model: str = "auto",
        language: str = "urdu"
    ) -> Dict[str, Any]:
        """
        Process long documents (up to 1M tokens)
        
        Args:
            text: Document text
            task: summarize, analyze, qa, extract, translate
            questions: For QA task
            model: Model to use (auto = best available)
            language: Response language (urdu, english, roman-urdu)
        """
        try:
            # Select model
            if model == "auto":
                model_key = self._select_best_model(len(text))
            else:
                model_key = model
                if model_key not in self.models:
                    model_key = self.default_model
            
            model_config = self.models[model_key]
            
            # Estimate tokens
            estimated_tokens = len(text) // 4
            print(f"📊 Processing {estimated_tokens} tokens using {model_key}...")
            
            # Check if text is too long for model
            if estimated_tokens > model_config["context"]:
                print(f"⚠️ Text too long ({estimated_tokens} > {model_config['context']}). Using chunking...")
                return await self.process_chunked(text, task, questions, model_key, language)
            
            # Prepare prompt based on task and language
            prompt = self._prepare_prompt(text, task, questions, language, estimated_tokens)
            
            # Call appropriate provider
            if model_config["provider"] == "openrouter":
                result = await self._call_openrouter(model_config["model"], prompt, language)
            elif model_config["provider"] == "openai":
                result = await self._call_openai(model_config["model"], prompt)
            elif model_config["provider"] == "anthropic":
                result = await self._call_anthropic(model_config["model"], prompt)
            else:
                raise ValueError(f"Unknown provider: {model_config['provider']}")
            
            return {
                "success": True,
                "result": result,
                "tokens_used": estimated_tokens,
                "task": task,
                "model": model_key,
                "document_length": len(text),
                "estimated_tokens": estimated_tokens,
                "provider": model_config["provider"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": f"Processing failed: {str(e)}"
            }
    
    def _select_best_model(self, text_length: str) -> str:
        """Select best model based on text length"""
        estimated_tokens = len(text_length) // 4
        
        if estimated_tokens > 100000:
            return "nemotron-3-nano"  # Free 1M context
        elif estimated_tokens > 50000:
            return "claude-3-sonnet"  # 200K context
        elif estimated_tokens > 10000:
            return "gpt-4-turbo"  # 128K context
        else:
            return "gemma-2-9b-it"  # Free small model
    
    def _prepare_prompt(self, text: str, task: str, questions: Optional[List[str]], language: str, estimated_tokens: int) -> str:
        """Prepare prompt based on task and language"""
        
        # Language instructions
        lang_instructions = {
            "urdu": "براہ کرم اردو میں جواب دیں۔",
            "roman-urdu": "Roman Urdu mein jawab dein.",
            "english": "Please respond in English."
        }
        
        lang_instruction = lang_instructions.get(language, "Please respond in Urdu.")
        
        # Task-specific prompts
        prompts = {
            "summarize": f"""Task: Summarize this document
Language: {lang_instruction}
Document length: ~{estimated_tokens} tokens
Document: {text[:500000]}

Please provide:
1. Executive summary (2-3 paragraphs)
2. Key points (bullet points)
3. Main conclusions""",
            
            "analyze": f"""Task: Analyze this document in depth
Language: {lang_instruction}
Document length: ~{estimated_tokens} tokens
Document: {text[:500000]}

Please provide:
1. Main themes and topics
2. Key insights and findings  
3. Strengths and weaknesses
4. Implications and recommendations
5. Critical analysis""",
            
            "qa": f"""Task: Answer questions based on document
Language: {lang_instruction}
Questions: {json.dumps(questions, ensure_ascii=False)}

Document: {text[:500000]}

Please answer each question thoroughly based only on the document.""",
            
            "extract": f"""Task: Extract all key information
Language: {lang_instruction}
Document: {text[:500000]}

Please extract and organize:
1. Key facts and data points
2. Names, dates, locations
3. Statistics and numbers
4. Important quotes
5. Technical terms and definitions

Format as structured JSON.""",
            
            "translate": f"""Task: Translate this document
Target Language: {language}
Document: {text[:500000]}

Please provide a complete translation while preserving meaning and context.""",
            
            "sentiment": f"""Task: Analyze sentiment throughout document
Language: {lang_instruction}
Document: {text[:500000]}

Please provide:
1. Overall sentiment (positive/negative/neutral)
2. Sentiment trends throughout document
3. Key emotional triggers
4. Language analysis""",
            
            "topics": f"""Task: Extract main topics and themes
Language: {lang_instruction}
Document: {text[:500000]}

Please identify:
1. Primary topics (with relevance %)
2. Secondary topics
3. Topic relationships
4. Topic evolution throughout document"""
        }
        
        return prompts.get(task, prompts["summarize"])
    
    async def _call_openrouter(self, model: str, prompt: str, language: str) -> str:
        """Call OpenRouter API"""
        if not self.openrouter_key:
            raise Exception("OpenRouter API key not configured")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://pakchat.ai",
                    "X-Title": "PakChat"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": f"You are PakChat with large context memory. Respond in {language}."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4000
                },
                timeout=120
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter error {response.status}: {error_text}")
    
    async def _call_openai(self, model: str, prompt: str) -> str:
        """Call OpenAI API"""
        if not self.openai_key:
            raise Exception("OpenAI API key not configured")
        
        import openai
        openai.api_key = self.openai_key
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=[
                    {"role": "system", "content": "You are PakChat with large context memory."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"OpenAI error: {str(e)}")
    
    async def _call_anthropic(self, model: str, prompt: str) -> str:
        """Call Anthropic API"""
        if not self.anthropic_key:
            raise Exception("Anthropic API key not configured")
        
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)
        
        try:
            response = await client.messages.create(
                model=model,
                system="You are PakChat with large context memory.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic error: {str(e)}")
    
    async def process_chunked(
        self, 
        text: str, 
        task: str = "summarize",
        questions: Optional[List[str]] = None,
        model: str = "auto",
        language: str = "urdu",
        chunk_size: int = 100000
    ) -> Dict[str, Any]:
        """
        Process extremely long documents by chunking
        """
        # Split into chunks
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        total_chunks = len(chunks)
        
        print(f"📦 Splitting into {total_chunks} chunks...")
        
        # Process each chunk
        chunk_results = []
        for i, chunk in enumerate(chunks):
            print(f"🔄 Processing chunk {i+1}/{total_chunks}...")
            result = await self.process(
                chunk, 
                task="summarize" if task != "qa" else task,
                questions=questions,
                model=model,
                language=language
            )
            if result.get("success"):
                chunk_results.append(result["result"])
        
        # Combine results based on task
        if task == "qa":
            # For QA, combine all answers
            combined = "\n\n".join(chunk_results)
            return {
                "success": True,
                "result": combined,
                "tokens_used": sum(len(r) for r in chunk_results) // 4,
                "task": task,
                "model": model,
                "document_length": len(text),
                "chunks_processed": total_chunks,
                "chunk_results": chunk_results
            }
        else:
            # For other tasks, summarize the summaries
            combined_text = "\n\n".join([
                f"Chunk {i+1} Summary:\n{res}" 
                for i, res in enumerate(chunk_results)
            ])
            
            final_result = await self.process(
                combined_text,
                task=task,
                questions=questions,
                model=model,
                language=language
            )
            
            if final_result.get("success"):
                final_result["chunks_processed"] = total_chunks
                final_result["chunk_results"] = chunk_results
            
            return final_result
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models"""
        return {
            "models": self.models,
            "default": self.default_model,
            "total_models": len(self.models),
            "free_models": sum(1 for m in self.models.values() if m["free"])
        }
    
    async def estimate_cost(self, text: str, model: str = "auto") -> Dict[str, Any]:
        """Estimate processing cost"""
        estimated_tokens = len(text) // 4
        
        if model == "auto":
            model = self._select_best_model(text)
        
        model_config = self.models.get(model, self.models[self.default_model])
        
        # Approximate costs (per 1K tokens)
        costs = {
            "openrouter": 0.0,  # Free models
            "openai": 0.01,      # GPT-4 approx
            "anthropic": 0.015   # Claude approx
        }
        
        provider = model_config["provider"]
        cost_per_1k = costs.get(provider, 0)
        estimated_cost = (estimated_tokens / 1000) * cost_per_1k
        
        return {
            "model": model,
            "provider": provider,
            "estimated_tokens": estimated_tokens,
            "cost_per_1k": cost_per_1k,
            "estimated_cost": estimated_cost,
            "free": model_config["free"]
        }