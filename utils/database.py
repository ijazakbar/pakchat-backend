# utils/database.py - Single Database Class
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
import aiosqlite

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
        
        # ========== SQLITE ==========
        self.sqlite_path = "pakchat.db"
        
        # Initialize connections
        self._init_sync()
        self._initialized = True
    
    def _init_sync(self):
        """Synchronous initialization"""
        try:
            logger.info("📦 Initializing database connections...")
            
            # 1. Supabase
            if self.supabase_url and self.supabase_key:
                try:
                    self.supabase = create_client(self.supabase_url, self.supabase_key)
                    logger.info("✅ Supabase connected")
                except Exception as e:
                    logger.error(f"❌ Supabase connection failed: {e}")
                    self.supabase = None
            
            # 2. Redis
            if self.upstash_redis_url and self.upstash_redis_token:
                try:
                    hostname = self.upstash_redis_url.replace('https://', '').replace('http://', '').split('/')[0]
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
                    logger.info(f"✅ Redis connected")
                except Exception as e:
                    logger.error(f"❌ Redis connection failed: {e}")
                    self.redis_client = None
            
            logger.info("✅ Database initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    
    async def init_db(self):
        """Async database initialization"""
        try:
            # Create SQLite tables
            async with aiosqlite.connect(self.sqlite_path) as db:
                # Users table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE,
                        username TEXT,
                        password_hash TEXT,
                        full_name TEXT,
                        credits INTEGER DEFAULT 1000,
                        is_active INTEGER DEFAULT 1,
                        is_verified INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        settings TEXT DEFAULT '{}',
                        metadata TEXT DEFAULT '{}'
                    )
                ''')
                
                # Sessions table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        token TEXT UNIQUE,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Conversations table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT,
                        messages TEXT,
                        model TEXT,
                        tokens INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Files table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS files (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        filename TEXT,
                        file_path TEXT,
                        file_size INTEGER,
                        file_type TEXT,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                await db.commit()
                logger.info("✅ SQLite tables created/verified")
                
        except Exception as e:
            logger.error(f"❌ SQLite initialization failed: {e}")
    
    def get_supabase(self):
        return self.supabase
    
    def get_redis(self):
        return self.redis_client
    
    # ========== USER METHODS ==========
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        try:
            # Try Supabase first
            if self.supabase:
                result = self.supabase.table('users').select('*').eq('id', user_id).execute()
                if result.data:
                    return result.data[0]
            
            # SQLite fallback
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    # Parse JSON fields
                    if 'settings' in data and data['settings']:
                        data['settings'] = json.loads(data['settings'])
                    if 'metadata' in data and data['metadata']:
                        data['metadata'] = json.loads(data['metadata'])
                    return data
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        try:
            if self.supabase:
                result = self.supabase.table('users').select('*').eq('email', email).execute()
                if result.data:
                    return result.data[0]
            
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('SELECT * FROM users WHERE email = ?', (email,))
                row = await cursor.fetchone()
                if row:
                    return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    async def create_user(self, user_data: Dict) -> Optional[Dict]:
        try:
            # Ensure required fields
            if 'id' not in user_data:
                user_data['id'] = str(uuid.uuid4())
            if 'created_at' not in user_data:
                user_data['created_at'] = datetime.now().isoformat()
            if 'updated_at' not in user_data:
                user_data['updated_at'] = datetime.now().isoformat()
            if 'credits' not in user_data:
                user_data['credits'] = 1000
            
            # Convert dict fields to JSON
            if 'settings' in user_data and isinstance(user_data['settings'], dict):
                user_data['settings'] = json.dumps(user_data['settings'])
            if 'metadata' in user_data and isinstance(user_data['metadata'], dict):
                user_data['metadata'] = json.dumps(user_data['metadata'])
            
            # Try Supabase
            if self.supabase:
                try:
                    result = self.supabase.table('users').insert(user_data).execute()
                    if result.data:
                        return result.data[0]
                except Exception as e:
                    logger.warning(f"Supabase insert failed: {e}")
            
            # SQLite fallback
            async with aiosqlite.connect(self.sqlite_path) as db:
                placeholders = ', '.join(['?' for _ in user_data])
                columns = ', '.join(user_data.keys())
                values = list(user_data.values())
                
                await db.execute(f'INSERT INTO users ({columns}) VALUES ({placeholders})', values)
                await db.commit()
                
                return await self.get_user(user_data['id'])
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
        try:
            update_data['updated_at'] = datetime.now().isoformat()
            
            if self.supabase:
                try:
                    result = self.supabase.table('users').update(update_data).eq('id', user_id).execute()
                    if result.data:
                        return result.data[0]
                except Exception as e:
                    logger.warning(f"Supabase update failed: {e}")
            
            async with aiosqlite.connect(self.sqlite_path) as db:
                set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
                values = list(update_data.values())
                values.append(user_id)
                
                await db.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
                await db.commit()
                
                return await self.get_user(user_id)
                
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None
    
    async def track_usage(self, user_id: str, action: str):
        try:
            if self.redis_client:
                key = f"usage:{user_id}:{action}:{datetime.now().strftime('%Y-%m-%d')}"
                self.redis_client.incr(key)
                self.redis_client.expire(key, 86400 * 30)
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
    
    # ========== CACHE METHODS ==========
    
    async def cache_get(self, key: str) -> Optional[Any]:
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def cache_set(self, key: str, value: Any, ttl: int = 86400):
        try:
            if self.redis_client:
                self.redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    # ========== API METHODS ==========
    
    async def call_openai(self, prompt: str, model: str = "gpt-3.5-turbo"):
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
    
    async def close(self):
        try:
            if self.redis_client:
                self.redis_client.close()
                logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

# SINGLE GLOBAL INSTANCE - YAHI USE KARO
db = Database()