# utils/database.py - Complete with all APIs from main.py
from supabase import create_client, Client
import os
import logging
from dotenv import load_dotenv
import redis
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiohttp
import asyncio

logger = logging.getLogger(__name__)
load_dotenv()

class Database:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # ========== SUPABASE CONFIG ==========
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase: Optional[Client] = None
        
        # ========== REDIS CONFIG ==========
        self.upstash_redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.upstash_redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis_client = None
        
        # ========== LLMs & AI APIs ==========
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.replicate_api_key = os.getenv("REPLICATE_API_KEY")
        self.fal_ai_api_key = os.getenv("FAL_AI_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        
        # ========== NEWS APIs ==========
        self.thenews_api_key = os.getenv("THE_NEWS_API_KEY")
        self.thenews_api_url = os.getenv("THE_NEWS_API_URL", "https://api.thenewsapi.com/v1")
        self.newsdata_io_key = os.getenv("NEWSDATA_IO_KEY")
        self.newsdata_io_url = os.getenv("NEWSDATA_IO_URL", "https://newsdata.io/api/1")
        self.newsapi_org_key = os.getenv("NEWSAPI_ORG_KEY")
        self.newsapi_org_url = os.getenv("NEWSAPI_ORG_URL", "https://newsapi.org/v2")
        
        # ========== WIKIPEDIA APIs ==========
        self.wikipedia_urls = {
            'en': os.getenv("WIKIPEDIA_EN_URL", "https://en.wikipedia.org/api/rest_v1"),
            'ur': os.getenv("WIKIPEDIA_UR_URL", "https://ur.wikipedia.org/api/rest_v1"),
            'hi': os.getenv("WIKIPEDIA_HI_URL", "https://hi.wikipedia.org/api/rest_v1"),
            'ar': os.getenv("WIKIPEDIA_AR_URL", "https://ar.wikipedia.org/api/rest_v1"),
            'bn': os.getenv("WIKIPEDIA_BN_URL", "https://bn.wikipedia.org/api/rest_v1"),
            'es': os.getenv("WIKIPEDIA_ES_URL", "https://es.wikipedia.org/api/rest_v1"),
            'fr': os.getenv("WIKIPEDIA_FR_URL", "https://fr.wikipedia.org/api/rest_v1"),
            'zh': os.getenv("WIKIPEDIA_ZH_URL", "https://zh.wikipedia.org/api/rest_v1"),
            'ru': os.getenv("WIKIPEDIA_RU_URL", "https://ru.wikipedia.org/api/rest_v1"),
        }
        self.wiki_user_agent = os.getenv("WIKI_USER_AGENT", "PakChatAI/1.0 (contact@pakchat.ai)")
        
        # ========== OTHER SERVICES ==========
        self.kaggle_api_token = os.getenv("KAGGLE_API_TOKEN")
        self.assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.open_library_url = os.getenv("REACT_APP_OPEN_LIBRARY_URL", "https://openlibrary.org")
        self.colab_video_api_url = os.getenv("REACT_APP_COLAB_VIDEO_API_URL")
        
        # ========== JWT ==========
        self.jwt_secret = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
        
        # ========== DATABASE URL ==========
        self.database_url = os.getenv("DATABASE_URL", "postgresql://localhost/pakchat")
        
        # Initialize connections
        self._init_db()
        self._initialized = True
    
    def _init_db(self):
        """Initialize all database connections"""
        try:
            logger.info("📦 Initializing database connections...")
            
            # 1. Initialize Supabase
            if self.supabase_url and self.supabase_key:
                self.supabase = create_client(
                    self.supabase_url, 
                    self.supabase_key,
                    options={
                        "schema": "public",
                        "headers": {
                            "X-Client-Info": "pakchat-backend"
                        }
                    }
                )
                logger.info("✅ Supabase connected")
                
                # Test query
                try:
                    test_query = self.supabase.table('users').select('count', count='exact').limit(0).execute()
                    logger.info("✅ Supabase RLS policies verified")
                except Exception as e:
                    logger.warning(f"⚠️ Supabase RLS policy warning: {e}")
            else:
                logger.warning("⚠️ Supabase not configured")
            
            # 2. Initialize Redis (Upstash)
            if self.upstash_redis_url and self.upstash_redis_token:
                try:
                    hostname = self.upstash_redis_url.replace('https://', '').replace('http://', '')
                    
                    self.redis_client = redis.Redis(
                        host=hostname,
                        port=6379,
                        password=self.upstash_redis_token,
                        ssl=True,
                        ssl_cert_reqs=None,
                        decode_responses=True,
                        socket_connect_timeout=5
                    )
                    self.redis_client.ping()
                    logger.info(f"✅ Upstash Redis connected to {hostname}")
                except Exception as e:
                    logger.error(f"❌ Redis connection failed: {e}")
                    self.redis_client = None
            else:
                logger.warning("⚠️ Redis credentials missing")
            
            # 3. Log API status
            self._log_api_status()
            
            logger.info("✅ Database initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def _log_api_status(self):
        """Log which APIs are configured"""
        apis = {
            "OpenAI": self.openai_api_key,
            "Groq": self.groq_api_key,
            "DeepSeek": self.deepseek_api_key,
            "Replicate": self.replicate_api_key,
            "FAL.ai": self.fal_ai_api_key,
            "OpenRouter": self.openrouter_api_key,
            "Google": self.google_api_key,
            "HuggingFace": self.huggingface_api_key,
            "Tavily": self.tavily_api_key,
            "Anthropic": self.anthropic_api_key,
            "Cohere": self.cohere_api_key,
            "Mistral": self.mistral_api_key,
            "TheNewsAPI": self.thenews_api_key,
            "NewsData.io": self.newsdata_io_key,
            "NewsAPI.org": self.newsapi_org_key,
            "AssemblyAI": self.assemblyai_api_key,
            "ElevenLabs": self.elevenlabs_api_key,
            "Kaggle": self.kaggle_api_token,
        }
        
        configured = [name for name, key in apis.items() if key]
        logger.info(f"📊 APIs configured: {', '.join(configured) if configured else 'None'}")
        logger.info(f"📚 Wikipedia languages: {', '.join(self.wikipedia_urls.keys())}")
    
    def get_supabase(self):
        """Get Supabase client"""
        return self.supabase
    
    def get_redis(self):
        """Get Redis client"""
        return self.redis_client
    
    # ========== USER METHODS ==========
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            if not self.supabase:
                return None
            result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            if not self.supabase:
                return None
            result = self.supabase.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    async def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Create new user"""
        try:
            if not self.supabase:
                return None
            result = self.supabase.table('users').insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
        """Update user"""
        try:
            if not self.supabase:
                return None
            result = self.supabase.table('users').update(update_data).eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None
    
    async def track_usage(self, user_id: str, action: str):
        """Track user usage"""
        try:
            if not self.redis_client:
                return
            key = f"usage:{user_id}:{action}:{datetime.now().strftime('%Y-%m-%d')}"
            self.redis_client.incr(key)
            self.redis_client.expire(key, 86400 * 30)
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
    
    # ========== CACHE METHODS ==========
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def cache_set(self, key: str, value: Any, ttl: int = 86400):
        """Set in cache"""
        try:
            if self.redis_client:
                self.redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    # ========== API METHODS ==========
    
    async def call_openai(self, prompt: str, model: str = "gpt-3.5-turbo"):
        """Call OpenAI API"""
        if not self.openai_api_key:
            return {"error": "OpenAI API key not configured"}
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return {"error": str(e)}
    
    async def call_groq(self, prompt: str, model: str = "mixtral-8x7b-32768"):
        """Call Groq API"""
        if not self.groq_api_key:
            return {"error": "Groq API key not configured"}
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return {"error": str(e)}
    
    async def call_tavily(self, query: str, depth: str = "basic"):
        """Call Tavily Search API"""
        if not self.tavily_api_key:
            return {"error": "Tavily API key not configured"}
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": depth
                }
                async with session.post(
                    "https://api.tavily.com/search",
                    json=data
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Tavily error: {e}")
            return {"error": str(e)}
    
    async def call_wikipedia(self, query: str, lang: str = 'en'):
        """Call Wikipedia API"""
        try:
            base_url = self.wikipedia_urls.get(lang, self.wikipedia_urls['en'])
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.wiki_user_agent}
                async with session.get(
                    f"{base_url}/search/page",
                    params={"q": query, "limit": 5},
                    headers=headers
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Wikipedia error: {e}")
            return {"error": str(e)}
    
    # ========== CLEANUP ==========
    
    def close(self):
        """Close connections"""
        try:
            if self.redis_client:
                self.redis_client.close()
                logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

# Create global instance - SINGLETON
db = Database()