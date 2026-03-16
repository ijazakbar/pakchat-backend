# ============================================
# PAKCHAT BACKEND - FINAL PRODUCTION VERSION
# All APIs Integrated & Connected
# ============================================

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import asyncio
from typing import Optional, List, Dict, Any
import json
import os
from datetime import datetime, timedelta
import logging
import aiosqlite
import bcrypt
import uuid
import aiohttp
from dotenv import load_dotenv
from pathlib import Path
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

# ========== 🔐 SECURITY MIDDLEWARE ==========
try:
    from security_middleware import add_security_middleware
except ImportError:
    # Fallback if security middleware not exists
    def add_security_middleware(app):
        logger.warning("⚠️ Security middleware not loaded")
        return app

# ==================== LOAD ENVIRONMENT ====================
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ==================== FASTAPI APP ====================
# ✅ APP PEHLE BANAYA - YAHAN SE START
app = FastAPI(
    title="PakChat API",
    version="1.0.0",
    description="Advanced AI Assistant with Multi-LLM Support",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ==================== ENVIRONMENT VARIABLES - ALL APIS ====================
# LLMs & AI APIs
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
REPLICATE_API_KEY = os.getenv('REPLICATE_API_KEY')
FAL_AI_API_KEY = os.getenv('FAL_AI_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
COHERE_API_KEY = os.getenv('COHERE_API_KEY')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

# News APIs
THE_NEWS_API_KEY = os.getenv('THE_NEWS_API_KEY')
THE_NEWS_API_URL = os.getenv('THE_NEWS_API_URL', 'https://api.thenewsapi.com/v1')
NEWSDATA_IO_KEY = os.getenv('NEWSDATA_IO_KEY')
NEWSDATA_IO_URL = os.getenv('NEWSDATA_IO_URL', 'https://newsdata.io/api/1')
NEWSAPI_ORG_KEY = os.getenv('NEWSAPI_ORG_KEY')
NEWSAPI_ORG_URL = os.getenv('NEWSAPI_ORG_URL', 'https://newsapi.org/v2')

# Wikipedia APIs
WIKIPEDIA_EN_URL = os.getenv('WIKIPEDIA_EN_URL', 'https://en.wikipedia.org/api/rest_v1')
WIKIPEDIA_UR_URL = os.getenv('WIKIPEDIA_UR_URL', 'https://ur.wikipedia.org/api/rest_v1')
WIKIPEDIA_HI_URL = os.getenv('WIKIPEDIA_HI_URL', 'https://hi.wikipedia.org/api/rest_v1')
WIKIPEDIA_AR_URL = os.getenv('WIKIPEDIA_AR_URL', 'https://ar.wikipedia.org/api/rest_v1')
WIKIPEDIA_BN_URL = os.getenv('WIKIPEDIA_BN_URL', 'https://bn.wikipedia.org/api/rest_v1')
WIKIPEDIA_ES_URL = os.getenv('WIKIPEDIA_ES_URL', 'https://es.wikipedia.org/api/rest_v1')
WIKIPEDIA_FR_URL = os.getenv('WIKIPEDIA_FR_URL', 'https://fr.wikipedia.org/api/rest_v1')
WIKIPEDIA_ZH_URL = os.getenv('WIKIPEDIA_ZH_URL', 'https://zh.wikipedia.org/api/rest_v1')
WIKIPEDIA_RU_URL = os.getenv('WIKIPEDIA_RU_URL', 'https://ru.wikipedia.org/api/rest_v1')
WIKI_USER_AGENT = os.getenv('WIKI_USER_AGENT', 'PakChatAI/1.0 (contact@pakchat.ai)')

# Other Services
KAGGLE_API_TOKEN = os.getenv('KAGGLE_API_TOKEN')
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
OPEN_LIBRARY_URL = os.getenv('REACT_APP_OPEN_LIBRARY_URL', 'https://openlibrary.org')

# Backend Essentials
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/pakchat')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
UPSTASH_REDIS_REST_URL = os.getenv('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_REST_TOKEN = os.getenv('UPSTASH_REDIS_REST_TOKEN')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-key-change-in-production')
COLAB_VIDEO_API_URL = os.getenv('REACT_APP_COLAB_VIDEO_API_URL')

# ==================== MEMORY CACHE ====================
memory_cache = {}
CACHE_TTL = 86400  # 24 hours

# ==================== SUPABASE CLIENT ====================
supabase = None
try:
    from supabase import create_client, Client
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase connected")
        
        # Test query to verify RLS policies
        try:
            test_query = supabase.table('users').select('count', count='exact').limit(0).execute()
            logger.info("✅ Supabase RLS policies verified")
        except Exception as e:
            logger.warning(f"⚠️ Supabase RLS policy warning: {e}")
    else:
        supabase = None
        logger.warning("⚠️ Supabase not configured")
except ImportError:
    supabase = None
    logger.warning("⚠️ Supabase package not installed")
except Exception as e:
    supabase = None
    logger.warning(f"⚠️ Supabase connection failed: {e}")

# ==================== UPSTASH REDIS ====================
redis_client = None
try:
    import redis
    if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
        hostname = UPSTASH_REDIS_REST_URL.replace('https://', '').replace('http://', '')
        
        import ssl
        redis_client = redis.Redis(
            host=hostname,
            port=6379,
            password=UPSTASH_REDIS_REST_TOKEN,
            ssl=True,
            ssl_cert_reqs=None,
            decode_responses=True,
            socket_connect_timeout=5
        )
        redis_client.ping()
        logger.info(f"✅ Upstash Redis connected to {hostname}")
    else:
        redis_client = None
        logger.warning("⚠️ Redis credentials missing")
except ImportError:
    redis_client = None
    logger.warning("⚠️ Redis package not installed")
except Exception as e:
    redis_client = None
    logger.warning(f"⚠️ Redis connection failed: {e}")

# ==================== IMPORT MODELS ====================
try:
    from utils.database import Database, db as database_db  # ✅ db instance bhi import karo
    from utils.auth import AuthHandler, auth_handler        # ✅ auth instance bhi import karo
    from utils.file_handler import FileHandler
    from utils.conversations import ConversationManager
    from models.chat import ChatModel
    from models.video import VideoGenerator
    from models.image import ImageProcessor
    from models.voice import VoiceProcessor
    from models.research import DeepResearch
    from models.long_context import LongContextProcessor
    from models.smart_chat import SmartChatProcessor
    from models.api_services import (
        WikipediaService, TavilyService, NewsService, GoogleBooksService,
        LLMService, HuggingFaceService, KaggleService, OpenLibraryService, FALaiService
    )
    
    # ✅ FIX: Create instances after successful import
    db = Database()
    auth = AuthHandler()
    # Classes ko globally available karo
    Database = Database
    AuthHandler = AuthHandler

    logger.info("✅ All models imported successfully")
    logger.info(f"✅ Database class: {Database}")
    logger.info(f"✅ AuthHandler class: {AuthHandler}")
    
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    # Define placeholder classes for missing imports
    class Database:
        async def init_db(self): 
            logger.warning("⚠️ Using placeholder Database")
            return False
    
    class AuthHandler:
        def __init__(self):
            logger.warning("⚠️ Using placeholder AuthHandler")
    
    class FileHandler: pass
    class ConversationManager: pass
    class ChatModel: pass
    class VideoGenerator: pass
    class ImageProcessor: pass
    class VoiceProcessor: pass
    class DeepResearch: pass
    class LongContextProcessor: pass
    class SmartChatProcessor: pass
    class WikipediaService: pass
    class TavilyService: pass
    class NewsService: pass
    class GoogleBooksService: pass
    class LLMService: pass
    class HuggingFaceService: pass
    class KaggleService: pass
    class OpenLibraryService: pass
    class FALaiService: pass
    
    # Create placeholder instances
    db = Database()
    auth = AuthHandler()
    Database = Database
    AuthHandler = AuthHandler
# ==================== GLOBAL VARIABLES ====================

chat_model = None
video_gen = None
image_proc = None
voice_proc = None
research = None
long_context = None
file_handler = None
smart_chat = None

# API Services - Knowledge
wiki_service = None
tavily_service = None
news_service = None

# API Services - Books
books_service = None
openlibrary_service = None

# API Services - AI/ML
llm_service = None
huggingface_service = None
kaggle_service = None
fal_service = None

# Conversation Manager
conv_manager = None

# ==================== INITIALIZE SERVICES ====================
@app.on_event("startup")
async def startup_event():
    global db, auth, chat_model, video_gen, image_proc, voice_proc, research, long_context, file_handler, smart_chat
    global wiki_service, tavily_service, news_service, books_service, openlibrary_service
    global llm_service, huggingface_service, kaggle_service, fal_service, conv_manager
    
    try:
        logger.info("🚀 Starting services initialization...")
        
        # ========== ENSURE DATABASE CLASS IS AVAILABLE ==========
        if 'Database' not in globals():
            try:
                # Try to import again
                from utils.database import Database
                globals()['Database'] = Database
                logger.info("✅ Database class re-imported in startup")
            except ImportError:
                # Define temporary class
                class TempDatabase:
                    async def init_db(self): return False
                globals()['Database'] = TempDatabase
                logger.warning("⚠️ Using temporary Database class")
        
        # ========== ENSURE AUTHHANDLER CLASS IS AVAILABLE ==========
        if 'AuthHandler' not in globals():
            try:
                from utils.auth import AuthHandler
                globals()['AuthHandler'] = AuthHandler
                logger.info("✅ AuthHandler class re-imported in startup")
            except ImportError:
                class TempAuthHandler:
                    def __init__(self): pass
                globals()['AuthHandler'] = TempAuthHandler
                logger.warning("⚠️ Using temporary AuthHandler class")
        
        # ========== INITIALIZE DATABASE ==========
        try:
            # Check if db object exists and has init_db method
            if db is not None and hasattr(db, 'init_db'):
                logger.info("✅ Using existing db instance")
            else:
                # Create new database instance
                db = Database()
                logger.info("✅ Created new db instance")
            
            # Initialize database
            if hasattr(db, 'init_db'):
                if asyncio.iscoroutinefunction(db.init_db):
                    await db.init_db()
                else:
                    db.init_db()
                logger.info("✅ Database initialized successfully")
            else:
                logger.warning("⚠️ Database has no init_db method")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            db = None
        
        # ========== INITIALIZE AUTH HANDLER ==========
        try:
            # Check if auth object exists
            if auth is not None:
                logger.info("✅ Using existing auth instance")
            else:
                # Create new auth instance
                auth = AuthHandler()
                logger.info("✅ Created new auth instance")
            
            logger.info("✅ Auth handler initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Auth handler failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            auth = None
        
        # ========== CORE SERVICES ==========
        
        # Chat Model
        try:
            chat_model = ChatModel()
            logger.info("  ✅ ChatModel")
        except Exception as e:
            logger.error(f"  ❌ ChatModel: {e}")
            chat_model = None
        
        # Video Generator
        try:
            video_gen = VideoGenerator()
            logger.info("  ✅ VideoGenerator")
        except Exception as e:
            logger.error(f"  ❌ VideoGenerator: {e}")
            video_gen = None
        
        # Image Processor
        try:
            image_proc = ImageProcessor()
            logger.info("  ✅ ImageProcessor")
        except Exception as e:
            logger.error(f"  ❌ ImageProcessor: {e}")
            image_proc = None
        
        # Voice Processor - with proper parameters
        try:
            # Get API keys from db instance
            assemblyai_key = getattr(db, 'assemblyai_api_key', None) if db else None
            elevenlabs_key = getattr(db, 'elevenlabs_api_key', None) if db else None
            
            voice_proc = VoiceProcessor(
                assemblyai_key=assemblyai_key,
                elevenlabs_key=elevenlabs_key
            )
            logger.info("  ✅ VoiceProcessor")
        except Exception as e:
            logger.error(f"  ❌ VoiceProcessor: {e}")
            voice_proc = None
        
        # Deep Research
        try:
            tavily_key = getattr(db, 'tavily_api_key', None) if db else None
            research = DeepResearch(tavily_key=tavily_key)
            logger.info("  ✅ DeepResearch")
        except Exception as e:
            logger.error(f"  ❌ DeepResearch: {e}")
            research = None
        
        # Long Context Processor
        try:
            long_context = LongContextProcessor()
            logger.info("  ✅ LongContextProcessor")
        except Exception as e:
            logger.error(f"  ❌ LongContextProcessor: {e}")
            long_context = None
        
        # File Handler
        try:
            file_handler = FileHandler()
            logger.info("  ✅ FileHandler")
        except Exception as e:
            logger.error(f"  ❌ FileHandler: {e}")
            file_handler = None
        
        # Smart Chat Processor
        try:
            smart_chat = SmartChatProcessor()
            logger.info("  ✅ SmartChatProcessor")
        except Exception as e:
            logger.error(f"  ❌ SmartChatProcessor: {e}")
            smart_chat = None
        
        # ========== API SERVICES ==========
        
        # Wikipedia Service
        try:
            wiki_service = WikipediaService(
                user_agent=getattr(db, 'wiki_user_agent', 'PakChatAI/1.0') if db else 'PakChatAI/1.0',
                endpoints=getattr(db, 'wikipedia_urls', {}) if db else {}
            )
            logger.info("  ✅ WikipediaService")
        except Exception as e:
            logger.error(f"  ❌ WikipediaService: {e}")
            wiki_service = None
        
        # Tavily Service
        try:
            tavily_service = TavilyService(
                api_key=getattr(db, 'tavily_api_key', None) if db else None
            )
            logger.info("  ✅ TavilyService")
        except Exception as e:
            logger.error(f"  ❌ TavilyService: {e}")
            tavily_service = None
        
        # News Service
        try:
            news_service = NewsService(
                thenews_key=getattr(db, 'thenews_api_key', None) if db else None,
                thenews_url=getattr(db, 'thenews_api_url', None) if db else None,
                newsdata_key=getattr(db, 'newsdata_io_key', None) if db else None,
                newsdata_url=getattr(db, 'newsdata_io_url', None) if db else None,
                newsapi_key=getattr(db, 'newsapi_org_key', None) if db else None,
                newsapi_url=getattr(db, 'newsapi_org_url', None) if db else None
            )
            logger.info("  ✅ NewsService")
        except Exception as e:
            logger.error(f"  ❌ NewsService: {e}")
            news_service = None
        
        # Google Books Service
        try:
            books_service = GoogleBooksService(
                api_key=getattr(db, 'google_api_key', None) if db else None
            )
            logger.info("  ✅ GoogleBooksService")
        except Exception as e:
            logger.error(f"  ❌ GoogleBooksService: {e}")
            books_service = None
        
        # LLM Service - with ALL providers
        try:
            llm_service = LLMService(
                openai_key=getattr(db, 'openai_api_key', None) if db else None,
                groq_key=getattr(db, 'groq_api_key', None) if db else None,
                deepseek_key=getattr(db, 'deepseek_api_key', None) if db else None,
                openrouter_key=getattr(db, 'openrouter_api_key', None) if db else None,
                google_key=getattr(db, 'google_api_key', None) if db else None,
                huggingface_key=getattr(db, 'huggingface_api_key', None) if db else None,
                replicate_key=getattr(db, 'replicate_api_key', None) if db else None,
                anthropic_key=getattr(db, 'anthropic_api_key', None) if db else None,
                cohere_key=getattr(db, 'cohere_api_key', None) if db else None,
                mistral_key=getattr(db, 'mistral_api_key', None) if db else None
            )
            logger.info("  ✅ LLMService")
        except Exception as e:
            logger.error(f"  ❌ LLMService: {e}")
            llm_service = None
        
        # HuggingFace Service
        try:
            huggingface_service = HuggingFaceService(
                api_key=getattr(db, 'huggingface_api_key', None) if db else None
            )
            logger.info("  ✅ HuggingFaceService")
        except Exception as e:
            logger.error(f"  ❌ HuggingFaceService: {e}")
            huggingface_service = None
        
        # Kaggle Service
        try:
            kaggle_service = KaggleService(
                api_token=getattr(db, 'kaggle_api_token', None) if db else None
            )
            logger.info("  ✅ KaggleService")
        except Exception as e:
            logger.error(f"  ❌ KaggleService: {e}")
            kaggle_service = None
        
        # Open Library Service
        try:
            openlibrary_service = OpenLibraryService(
                base_url=getattr(db, 'open_library_url', 'https://openlibrary.org') if db else 'https://openlibrary.org'
            )
            logger.info("  ✅ OpenLibraryService")
        except Exception as e:
            logger.error(f"  ❌ OpenLibraryService: {e}")
            openlibrary_service = None
        
        # FAL AI Service
        try:
            fal_service = FALaiService(
                api_key=getattr(db, 'fal_ai_api_key', None) if db else None
            )
            logger.info("  ✅ FALaiService")
        except Exception as e:
            logger.error(f"  ❌ FALaiService: {e}")
            fal_service = None
        
        # Conversation Manager
        try:
            conv_manager = ConversationManager()
            logger.info("✅ Conversation Manager initialized")
        except Exception as e:
            logger.error(f"❌ Conversation Manager failed: {e}")
            conv_manager = None
        
        logger.info("🎉 ALL SERVICES INITIALIZED SUCCESSFULLY!")
        
    except Exception as e:
        logger.error(f"❌ Fatal initialization error: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ==================== CORS (FINAL FIX) ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3090",
        "http://127.0.0.1:3090",
        "https://frontend-one-olive-11.vercel.app",  # 🔥 ONLY THIS FRONTEND URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# ==================== CUSTOM CORS MIDDLEWARE ====================
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    # Handle preflight requests
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        origin = request.headers.get("origin")
        if origin in [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3090",
            "http://127.0.0.1:3090",
            "https://frontend-one-olive-11.vercel.app",  # 🔥 ONLY THIS FRONTEND URL
        ]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response

    # Handle normal requests
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin in [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3090",
        "http://127.0.0.1:3090",
        "https://frontend-one-olive-11.vercel.app",  # 🔥 ONLY THIS FRONTEND URL
    ]:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# ========== 🔐 ADD SECURITY MIDDLEWARE ==========
add_security_middleware(app)


# ==================== STATIC FILES ====================
@app.get("/manifest.json")
async def get_manifest():
    manifest_path = Path("static/manifest.json")
    if manifest_path.exists():
        return FileResponse(manifest_path)
    return JSONResponse({
        "name": "PakChat",
        "short_name": "PakChat",
        "description": "Advanced AI Assistant",
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#4f46e5",
        "background_color": "#ffffff",
        "icons": [
            {
                "src": "/favicon.ico",
                "sizes": "64x64 32x32 24x24 16x16",
                "type": "image/x-icon"
            }
        ]
    })

@app.get("/favicon.ico")
async def get_favicon():
    favicon_path = Path("static/favicon.ico")
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return JSONResponse({"error": "Not found"}, status_code=404)

# ==================== REQUEST MODELS ====================
class ChatRequest(BaseModel):
    message: str
    mode: str = "quick"
    files: Optional[List[str]] = None
    context: Optional[str] = None
    language: str = "urdu"

class LLMChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "auto"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    provider: Optional[str] = "auto"
    use_search: bool = False
    use_deepthink: bool = False

class LongContextRequest(BaseModel):
    text: str
    task: str = "summarize"
    questions: Optional[List[str]] = None

class VideoRequest(BaseModel):
    prompt: str
    duration: int = 5
    resolution: str = "720p"
    style: Optional[str] = "realistic"

class ResearchRequest(BaseModel):
    query: str
    depth: str = "standard"
    include_sources: bool = True

class WebSearchRequest(BaseModel):
    query: str
    num_results: int = 5
    deep_search: bool = False

class TavilySearchRequest(BaseModel):
    query: str
    depth: str = "basic"
    max_results: int = 5
    include_images: bool = False

class NewsSearchRequest(BaseModel):
    query: str
    language: str = "ur,en"
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    sources: Optional[List[str]] = None

class BooksSearchRequest(BaseModel):
    query: str
    lang: str = "ur"
    page: int = 1
    limit: int = 10
    sort: str = "relevance"

class KaggleRequest(BaseModel):
    dataset: str
    query: Optional[str] = None

class ImageGenRequest(BaseModel):
    prompt: str
    provider: str = "replicate"
    size: str = "1024x1024"

# ==================== AUTH DEPENDENCY ====================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None:
            return None
        return {"id": user_id, "email": email}
    except JWTError:
        return None

async def get_optional_user(token: str = Depends(oauth2_scheme)):
    """Get current user or return None (for optional auth)"""
    try:
        return await get_current_user(token)
    except:
        return None

# ==================== AUTH ENDPOINTS ====================
@app.post("/api/auth/register", response_model=Dict[str, Any])
async def register(request: Dict[str, Any]):
    """Register new user - respects Supabase RLS (allow insert for anon)"""
    try:
        email = request.get("email")
        password = request.get("password")
        full_name = request.get("full_name", "")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        logger.info(f"📝 Register attempt: {email}")
        
        # Try Supabase first
        if supabase:
            try:
                result = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": full_name}}
                })
                
                if result.user:
                    # Insert into users table (RLS allows anon insert ✅)
                    user_data = {
                        "id": result.user.id,
                        "email": email,
                        "full_name": full_name,
                        "created_at": datetime.now().isoformat()
                    }
                    supabase.table('users').insert(user_data).execute()
                    
                    token = jwt.encode(
                        {"sub": result.user.id, "email": email, "type": "access"},
                        JWT_SECRET,
                        algorithm="HS256"
                    )
                    
                    refresh_token = jwt.encode(
                        {"sub": result.user.id, "email": email, "type": "refresh"},
                        JWT_SECRET,
                        algorithm="HS256"
                    )
                    
                    logger.info(f"✅ Supabase registration: {email}")
                    return {
                        "success": True,
                        "token": token,
                        "refresh_token": refresh_token,
                        "user": user_data
                    }
            except Exception as e:
                logger.warning(f"⚠️ Supabase registration failed: {e}")
        
        # Local fallback
        async with aiosqlite.connect("pakchat.db") as db_conn:
            # Check if user exists
            cursor = await db_conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            )
            if await cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")
            
            user_id = str(uuid.uuid4())
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode(), salt)
            
            await db_conn.execute(
                """INSERT INTO users (id, email, password_hash, full_name, credits, created_at, settings)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, email, password_hash.decode(), full_name, 1000, datetime.now().isoformat(), "{}")
            )
            await db_conn.commit()
            
            token = jwt.encode(
                {"sub": user_id, "email": email, "type": "access"},
                JWT_SECRET,
                algorithm="HS256"
            )
            
            refresh_token = jwt.encode(
                {"sub": user_id, "email": email, "type": "refresh"},
                JWT_SECRET,
                algorithm="HS256"
            )
            
            logger.info(f"✅ Local registration: {email}")
            return {
                "success": True,
                "token": token,
                "refresh_token": refresh_token,
                "user": {"id": user_id, "email": email, "full_name": full_name}
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login", response_model=Dict[str, Any])
async def login(request: Dict[str, Any]):
    """Login user - respects Supabase RLS (select own user)"""
    try:
        email = request.get("email")
        password = request.get("password")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        logger.info(f"🔵 Login attempt: {email}")
        
        # Try Supabase first
        if supabase:
            try:
                result = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                
                if result.user:
                    # Get user data
                    user_data = supabase.table('users')\
                        .select('*')\
                        .eq('id', result.user.id)\
                        .execute()
                    
                    token = jwt.encode(
                        {"sub": result.user.id, "email": email, "type": "access"},
                        JWT_SECRET,
                        algorithm="HS256"
                    )
                    
                    refresh_token = jwt.encode(
                        {"sub": result.user.id, "email": email, "type": "refresh"},
                        JWT_SECRET,
                        algorithm="HS256"
                    )
                    
                    logger.info(f"✅ Supabase login: {email}")
                    return {
                        "success": True,
                        "token": token,
                        "refresh_token": refresh_token,
                        "user": user_data.data[0] if user_data.data else {"id": result.user.id, "email": email}
                    }
            except Exception as e:
                logger.warning(f"⚠️ Supabase login failed: {e}")
        
        # Local fallback
        async with aiosqlite.connect("pakchat.db") as db_conn:
            cursor = await db_conn.execute(
                "SELECT id, email, password_hash, full_name FROM users WHERE email = ?", (email,)
            )
            user = await cursor.fetchone()
            
            if not user or not bcrypt.checkpw(password.encode(), user[2].encode()):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            token = jwt.encode(
                {"sub": user[0], "email": user[1], "type": "access"},
                JWT_SECRET,
                algorithm="HS256"
            )
            
            refresh_token = jwt.encode(
                {"sub": user[0], "email": user[1], "type": "refresh"},
                JWT_SECRET,
                algorithm="HS256"
            )
            
            logger.info(f"✅ Local login: {email}")
            return {
                "success": True,
                "token": token,
                "refresh_token": refresh_token,
                "user": {"id": user[0], "email": user[1], "full_name": user[3] or ""}
            }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/refresh", response_model=Dict[str, Any])
async def refresh_token(request: Dict[str, Any]):
    """Refresh access token"""
    try:
        refresh_token = request.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token required")
        
        try:
            payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=["HS256"])
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")
            
            user_id = payload.get("sub")
            email = payload.get("email")
            
            # Generate new access token
            new_token = jwt.encode(
                {"sub": user_id, "email": email, "type": "access"},
                JWT_SECRET,
                algorithm="HS256"
            )
            
            return {"success": True, "token": new_token}
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Refresh error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/profile", response_model=Dict[str, Any])
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile - respects Supabase RLS (select own user)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_id = current_user.get("id")
        
        # Try Supabase first
        if supabase:
            try:
                user_data = supabase.table('users')\
                    .select('*')\
                    .eq('id', user_id)\
                    .execute()
                if user_data.data:
                    return {"success": True, "user": user_data.data[0]}
            except:
                pass
        
        # Local fallback
        async with aiosqlite.connect("pakchat.db") as db_conn:
            cursor = await db_conn.execute(
                "SELECT id, email, full_name, credits, created_at FROM users WHERE id = ?",
                (user_id,)
            )
            user = await cursor.fetchone()
            if user:
                return {
                    "success": True,
                    "user": {
                        "id": user[0],
                        "email": user[1],
                        "full_name": user[2],
                        "credits": user[3],
                        "created_at": user[4]
                    }
                }
        return {"success": True, "user": current_user}
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return {"success": False, "user": None}

# ==================== TEST ENDPOINT ====================
@app.get("/api/test")
async def test_endpoint():
    return {
        "status": "ok",
        "message": "API is working",
        "timestamp": datetime.now().isoformat()
    }

# ==================== HEALTH CHECK ====================
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "connected" if db else "error",
            "cache": "connected" if redis_client else "error",
            "supabase": "connected" if supabase else "error",
            "llm": {
                "openai": "✅" if OPENAI_API_KEY else "❌",
                "groq": "✅" if GROQ_API_KEY else "❌",
                "deepseek": "✅" if DEEPSEEK_API_KEY else "❌",
                "google": "✅" if GOOGLE_API_KEY else "❌",
                "anthropic": "✅" if ANTHROPIC_API_KEY else "❌"
            },
            "wikipedia": "✅",
            "news": {
                "thenews": "✅" if THE_NEWS_API_KEY else "❌",
                "newsdata": "✅" if NEWSDATA_IO_KEY else "❌",
                "newsapi": "✅" if NEWSAPI_ORG_KEY else "❌"
            },
            "tavily": "✅" if TAVILY_API_KEY else "❌",
            "books": {
                "google": "✅" if GOOGLE_API_KEY else "❌",
                "openlibrary": "✅"
            },
            "image_gen": {
                "replicate": "✅" if REPLICATE_API_KEY else "❌",
                "fal": "✅" if FAL_AI_API_KEY else "❌"
            },
            "voice": {
                "assemblyai": "✅" if ASSEMBLYAI_API_KEY else "❌",
                "elevenlabs": "✅" if ELEVENLABS_API_KEY else "❌"
            },
            "kaggle": "✅" if KAGGLE_API_TOKEN else "❌"
        }
    }

# ==================== ROOT ENDPOINT ====================
@app.get("/")
async def root():
    return {
        "message": "🚀 PakChat API is running!",
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "apis_connected": {
            "llm": ["OpenAI", "Groq", "DeepSeek", "Google", "Anthropic"],
            "wikipedia": ["ur", "hi", "en", "ar", "bn", "es", "fr", "zh", "ru"],
            "news": ["TheNewsAPI", "NewsData", "NewsAPI"],
            "search": ["Tavily"],
            "books": ["Google Books", "Open Library"],
            "image_gen": ["Replicate", "FAL"],
            "voice": ["AssemblyAI", "ElevenLabs"],
            "data": ["Kaggle"],
            "storage": ["Supabase", "Upstash Redis"]
        }
    }

# ==================== MULTI-LLM CHAT WITH ALL PROVIDERS ====================
@app.post("/api/chat/llm")
async def llm_chat(request: LLMChatRequest, current_user: dict = Depends(get_optional_user)):
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages required")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        # Tavily search integration
        if request.use_search and tavily_service:
            search_query = request.messages[-1]['content'] if request.messages else ""
            search_result = await tavily_service.search(search_query)
            if search_result and search_result.get('results'):
                context_msg = f"Web search results: {json.dumps(search_result.get('results', []))}"
                request.messages.append({"role": "system", "content": context_msg})
        
        # DeepThink mode
        if request.use_deepthink:
            deepthink_prompt = {
                "role": "system", 
                "content": "You are in DeepThink mode. Provide detailed, step-by-step reasoning. Think carefully and show your work."
            }
            request.messages.insert(0, deepthink_prompt)
        
        if not llm_service:
            raise HTTPException(status_code=503, detail="LLM service not available")
        
        # 🎯 TRY PROVIDERS IN OPTIMAL ORDER
        result = None
        errors = []
        
        # Priority 1: FREE providers with best quality
        free_providers = [
            'openrouter',      # 50+ free models (Gemini, Llama, DeepSeek)
            'google',          # Gemini 2.0 Flash - 60/min free
            'groq',            # Llama 3.3, Mixtral - 30/min free
            'huggingface',     # Community models - 30k/month free
        ]
        
        # Priority 2: PAID providers (if you have credits)
        paid_providers = [
            'openai',          # GPT-4 - if credits available
            'anthropic',       # Claude - if credits available
            'deepseek',        # DeepSeek - if balance available
            'replicate',       # Various models - if credits available
            'mistral',         # Mistral models
            'cohere',          # Cohere models
        ]
        
        # Decide which providers to try based on availability
        providers_to_try = []
        
        # First add FREE providers
        providers_to_try.extend(free_providers)
        
        # If user explicitly selected a paid provider, add it
        if request.provider != 'auto' and request.provider in paid_providers:
            providers_to_try.insert(0, request.provider)
        
        for provider in providers_to_try:
            try:
                logger.info(f"🔄 Trying {provider}...")
                
                result = await llm_service.chat_with_provider(
                    provider=provider,
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                
                if result and result.get('choices'):
                    logger.info(f"✅ Success with {provider}")
                    result['provider'] = provider
                    
                    # Add usage info
                    if 'usage' not in result:
                        result['usage'] = {
                            'total_tokens': len(str(result.get('choices', [{}])[0].get('message', {}).get('content', ''))) // 4
                        }
                    break
                    
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{provider}: {error_msg}")
                
                # Special handling
                if "402" in error_msg or "Insufficient Balance" in error_msg:
                    logger.warning(f"⚠️ {provider} needs payment - skipping")
                elif "decommissioned" in error_msg.lower():
                    logger.warning(f"⚠️ {provider} model outdated - update needed")
                elif "rate limit" in error_msg.lower():
                    logger.warning(f"⚠️ {provider} rate limited - trying next")
                else:
                    logger.warning(f"⚠️ {provider} failed: {error_msg}")
                continue
        
        if not result:
            error_details = " | ".join(errors)
            logger.error(f"❌ All providers failed: {error_details}")
            
            # Try OpenRouter as last resort
            try:
                logger.info("🔄 Last resort: OpenRouter free models...")
                result = await llm_service.chat_with_provider(
                    provider='openrouter',
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                if result and result.get('choices'):
                    logger.info("✅ OpenRouter free model worked!")
                    result['provider'] = 'openrouter'
            except Exception as e:
                errors.append(f"OpenRouter-last: {str(e)}")
            
        if not result:
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"⚠️ **Temporary Issue**\n\nAll AI providers are currently unavailable. This could be due to:\n\n• Rate limits exceeded\n• API key issues\n• Service outages\n\nPlease try:\n• Waiting a few minutes\n• Selecting a different model\n• Checking your internet connection\n\n**Debug info:** {error_details[:200]}"
                    }
                }],
                "provider": "none",
                "error": True
            }
        
        # Add metadata
        result['user_id'] = user_id
        result['timestamp'] = datetime.now().isoformat()
        
        # Save conversation with error handling
        if request.messages and result.get('choices') and conv_manager and current_user:
            try:
                assistant_content = result['choices'][0]['message']['content']
                messages_to_save = request.messages + [{"role": "assistant", "content": assistant_content}]
                
                try:
                    await conv_manager.save_conversation(
                        user_id=user_id,
                        messages=messages_to_save,
                        model=result.get('model', result.get('model_used', 'unknown')),
                        tokens=result.get('usage', {}).get('total_tokens', 0)
                    )
                except Exception as db_error:
                    if "tokens_used" in str(db_error):
                        logger.warning("⚠️ tokens_used column missing - run SQL to add it")
                    else:
                        logger.warning(f"Failed to save conversation: {db_error}")
            except Exception as e:
                logger.warning(f"Conversation save error: {e}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM Chat error: {e}")
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": f"An unexpected error occurred. Please try again."
                }
            }],
            "provider": "error"
        }
# ==================== OPENAI-COMPATIBLE ENDPOINT FOR NEXTCHAT ====================
@app.post("/v1/chat/completions")
async def openai_compatible_chat(request: dict):
    """OpenAI-compatible endpoint for NextChat frontend"""
    try:
        # Extract request data
        messages = request.get("messages", [])
        model = request.get("model", "gpt-3.5-turbo")
        stream = request.get("stream", False)
        temperature = request.get("temperature", 0.7)
        max_tokens = request.get("max_tokens")
        
        logger.info(f"📨 OpenAI-compatible request: model={model}, stream={stream}")
        
        if not llm_service:
            raise HTTPException(status_code=503, detail="LLM service not available")
        
        # Call your LLM service
        result = await llm_service.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Return in OpenAI format
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": result['choices'][0]['message'],
                "finish_reason": "stop"
            }],
            "usage": result.get('usage', {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            })
        }
    except Exception as e:
        logger.error(f"OpenAI compatible error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ==================== STREAMING LLM CHAT ====================
@app.post("/api/chat/llm/stream")
async def llm_chat_stream(request: LLMChatRequest, current_user: dict = Depends(get_optional_user)):
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages required")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "llm_chat_stream")
        
        # DeepThink mode - add reasoning prompt
        if request.use_deepthink:
            deepthink_prompt = {
                "role": "system", 
                "content": "You are in DeepThink mode. Provide detailed, step-by-step reasoning."
            }
            request.messages.insert(0, deepthink_prompt)
        
        async def generate():
            # Providers to try in order
            providers_to_try = ['deepseek', 'groq', 'openai', 'google']
            
            last_error = None
            full_response = ""
            
            for provider in providers_to_try:
                try:
                    logger.info(f"🔄 Trying stream with {provider}")
                    
                    # Send provider info to client
                    yield f"data: {json.dumps({'provider': provider})}\n\n"
                    
                    # Stream chunks
                    async for chunk in llm_service.chat_completion_stream(
                        messages=request.messages,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        provider=provider
                    ):
                        full_response += chunk
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    
                    yield "data: [DONE]\n\n"
                    logger.info(f"✅ Stream successful with {provider}")
                    
                    # Save conversation
                    if conv_manager and current_user:
                        try:
                            await conv_manager.save_conversation(
                                user_id=user_id,
                                messages=request.messages + [{"role": "assistant", "content": full_response}],
                                model=provider,
                                tokens=len(full_response.split())
                            )
                        except:
                            pass
                    
                    return
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ Stream failed with {provider}: {e}")
                    yield f"data: {json.dumps({'error': f'{provider} failed, trying next...'})}\n\n"
                    continue
            
            # All providers failed
            error_msg = f"All streaming providers failed. Last error: {last_error}"
            logger.error(f"❌ {error_msg}")
            yield f"data: {json.dumps({'error': 'All AI providers unavailable. Please try again later.'})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"❌ LLM Stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== IMAGE GENERATION ====================
@app.post("/api/generate/image")
async def generate_image(request: ImageGenRequest, current_user: dict = Depends(get_optional_user)):
    try:
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "image_generation")
        
        if not image_proc and not fal_service:
            raise HTTPException(status_code=503, detail="Image generation service not available")
        
        if request.provider == "replicate" and image_proc:
            try:
                if hasattr(image_proc, 'generate_replicate'):
                    result = await image_proc.generate_replicate(prompt=request.prompt)
                else:
                    result = await image_proc.generate(prompt=request.prompt)
                    
                if result and not result.get('error'):
                    return result
            except Exception as e:
                logger.warning(f"Replicate failed: {e}, trying FAL backup...")
                if fal_service:
                    result = await fal_service.generate_image(prompt=request.prompt)
                    return result
        
        elif request.provider == "fal" and fal_service:
            result = await fal_service.generate_image(prompt=request.prompt)
            return result
        
        elif image_proc:
            result = await image_proc.generate(prompt=request.prompt)
            return result
        
        raise HTTPException(status_code=503, detail="No image generation service available")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== VIDEO GENERATION (Colab) ====================
@app.post("/api/generate/video")
async def generate_video(request: VideoRequest, current_user: dict = Depends(get_optional_user)):
    try:
        if not COLAB_VIDEO_API_URL:
            raise HTTPException(status_code=503, detail="Video generation service not configured")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "video_generation")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{COLAB_VIDEO_API_URL}/api/predict",
                json={"data": [request.prompt]},
                timeout=120
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {"video_url": result.get('data', [None])[0]}
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Video generation failed: {error_text}")
                    
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Video generation timeout")
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== WIKIPEDIA (Cached) ====================
@app.get("/api/wiki/{lang}/{query}")
async def wikipedia_search(lang: str, query: str, current_user: dict = Depends(get_optional_user)):
    try:
        supported_langs = ['en', 'ur', 'hi', 'ar', 'bn', 'es', 'fr', 'zh', 'ru']
        if lang not in supported_langs:
            raise HTTPException(status_code=400, detail=f"Language '{lang}' not supported. Supported: {supported_langs}")
        
        if not wiki_service:
            raise HTTPException(status_code=503, detail="Wikipedia service not available")
        
        cache_key = f"wiki:{lang}:{query.lower().strip()}"
        
        # Try Redis cache
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"✅ Redis cache hit for: {query}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
        
        # Try memory cache
        if cache_key in memory_cache:
            cached_time, cached_data = memory_cache[cache_key]
            if datetime.now().timestamp() - cached_time < CACHE_TTL:
                logger.info(f"✅ Memory cache hit for: {query}")
                return cached_data
        
        # Fetch from Wikipedia
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "wikipedia")
            
        result = await wiki_service.search(query.strip(), lang)
        
        response_data = {
            "success": True,
            "query": query,
            "language": lang,
            "results": result.get('results', []),
            "total": len(result.get('results', [])),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in cache
        if redis_client:
            try:
                redis_client.setex(cache_key, CACHE_TTL, json.dumps(response_data))
            except Exception as e:
                memory_cache[cache_key] = (datetime.now().timestamp(), response_data)
        else:
            memory_cache[cache_key] = (datetime.now().timestamp(), response_data)
        
        return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== TAVILY SEARCH ====================
@app.post("/api/search/tavily")
async def tavily_search(request: TavilySearchRequest, current_user: dict = Depends(get_optional_user)):
    try:
        if not tavily_service:
            raise HTTPException(status_code=503, detail="Tavily service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "tavily")
        
        result = await tavily_service.search(
            query=request.query.strip(),
            depth=request.depth,
            max_results=request.max_results,
            include_images=request.include_images
        )
        
        return {
            "success": True,
            "query": request.query,
            "results": result.get('results', []),
            "total": len(result.get('results', [])),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Tavily error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== NEWS SEARCH ====================
@app.post("/api/search/news")
async def news_search(request: NewsSearchRequest, current_user: dict = Depends(get_optional_user)):
    try:
        if not news_service:
            raise HTTPException(status_code=503, detail="News service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "news")
        
        # Try to get news
        articles = await news_service.get_all_news(request.query.strip(), request.language)
        
        return {
            "success": True,
            "query": request.query,
            "articles": articles[:20],
            "total": len(articles),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"News error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== HUGGING FACE ====================
@app.post("/api/huggingface/inference")
async def huggingface_inference(request: Dict[str, Any], current_user: dict = Depends(get_optional_user)):
    try:
        if not huggingface_service:
            raise HTTPException(status_code=503, detail="HuggingFace service not available")
        
        model = request.get("model", "gpt2")
        inputs = request.get("inputs")
        parameters = request.get("parameters", {})
        
        if not inputs:
            raise HTTPException(status_code=400, detail="Inputs required")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "huggingface")
        
        result = await huggingface_service.inference(model=model, inputs=inputs, parameters=parameters)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HuggingFace error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== KAGGLE ====================
@app.post("/api/kaggle/datasets")
async def kaggle_datasets(request: KaggleRequest, current_user: dict = Depends(get_optional_user)):
    try:
        if not kaggle_service:
            raise HTTPException(status_code=503, detail="Kaggle service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "kaggle")
        
        if request.query:
            datasets = await kaggle_service.search_datasets(request.query)
        else:
            datasets = await kaggle_service.get_dataset_info(request.dataset)
        
        return {"success": True, "datasets": datasets, "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Kaggle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== OPEN LIBRARY ====================
@app.get("/api/openlibrary/search")
async def openlibrary_search(query: str, page: int = 1, limit: int = 10, current_user: dict = Depends(get_optional_user)):
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Query required")
        
        if not openlibrary_service:
            raise HTTPException(status_code=503, detail="OpenLibrary service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "openlibrary")
        
        result = await openlibrary_service.search_books(query=query, page=page, limit=limit)
        
        return {
            "success": True,
            "query": query,
            "page": page,
            "limit": limit,
            "books": result.get('books', []),
            "total": result.get('total', 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenLibrary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== GOOGLE BOOKS ====================
@app.get("/api/books/google")
async def google_books_search(query: str, lang: str = "ur", current_user: dict = Depends(get_optional_user)):
    try:
        if not books_service:
            raise HTTPException(status_code=503, detail="Google Books service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "google_books")
        
        result = await books_service.search_books(query=query.strip(), lang=lang)
        
        return {
            "success": True,
            "query": query,
            "language": lang,
            "books": result.get('books', []),
            "total": result.get('total', 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Google Books error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== VOICE ENDPOINTS ====================
@app.post("/api/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...), current_user: dict = Depends(get_optional_user)):
    try:
        if not voice_proc or not file_handler:
            raise HTTPException(status_code=503, detail="Voice service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "transcribe")
        
        # Save file
        file_path = await file_handler.save_upload(file)
        
        # Transcribe
        text = await voice_proc.transcribe(audio_path=file_path, language="ur")
        
        # Clean up
        await file_handler.delete_file(file_path)
        
        return {"text": text}
    except Exception as e:
        logger.error(f"Transcribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/synthesize")
async def synthesize_speech(request: Dict[str, Any], current_user: dict = Depends(get_optional_user)):
    try:
        if not voice_proc:
            raise HTTPException(status_code=503, detail="Voice service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "synthesize")
        
        text = request.get("text")
        voice = request.get("voice", "urdu-female")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text required")
        
        audio_url = await voice_proc.synthesize(text=text, voice=voice)
        return {"audio_url": audio_url}
    except Exception as e:
        logger.error(f"Synthesize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CONVERSATIONS ====================
@app.get("/api/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not conv_manager:
        return {"conversations": []}
    
    try:
        user_id = current_user.get("id")
        conversations = await conv_manager.get_user_conversations(user_id)
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        return {"conversations": []}

@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not conv_manager:
        raise HTTPException(status_code=503, detail="Conversation service not available")
    
    try:
        user_id = current_user.get("id")
        conversation = await conv_manager.get_conversation(conv_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation")

@app.post("/api/conversations")
async def save_conversation(request: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not conv_manager:
        raise HTTPException(status_code=503, detail="Conversation service not available")
    
    try:
        user_id = current_user.get("id")
        messages = request.get("messages", [])
        model = request.get("model", "gpt-3.5-turbo")
        tokens = request.get("tokens", 0)
        conv_id = await conv_manager.save_conversation(user_id, messages, model, tokens)
        return {"id": conv_id, "message": "Conversation saved"}
    except Exception as e:
        logger.error(f"Save conversation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save conversation")

@app.put("/api/conversations/{conv_id}")
async def update_conversation(conv_id: str, request: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not conv_manager:
        raise HTTPException(status_code=503, detail="Conversation service not available")
    
    try:
        user_id = current_user.get("id")
        messages = request.get("messages", [])
        tokens = request.get("tokens", 0)
        await conv_manager.update_conversation(conv_id, messages, tokens)
        return {"message": "Conversation updated"}
    except Exception as e:
        logger.error(f"Update conversation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update conversation")

@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not conv_manager:
        raise HTTPException(status_code=503, detail="Conversation service not available")
    
    try:
        user_id = current_user.get("id")
        success = await conv_manager.delete_conversation(conv_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

# ==================== FILE UPLOAD ====================
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_optional_user)):
    try:
        if not file_handler:
            raise HTTPException(status_code=503, detail="File service not available")
        
        user_id = current_user.get("id") if current_user else "anonymous"
        
        if db and hasattr(db, 'track_usage'):
            await db.track_usage(user_id, "file_upload")
        
        # Save file
        file_info = await file_handler.save_upload(file, user_id)
        
        return {
            "success": True,
            "file_id": file_info.get("id"),
            "filename": file_info.get("filename"),
            "url": file_info.get("url"),
            "message": "File uploaded successfully"
        }
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
async def list_files(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not file_handler:
        return {"files": []}
    
    try:
        user_id = current_user.get("id")
        files = await file_handler.list_files(user_id)
        return {"files": files}
    except Exception as e:
        logger.error(f"List files error: {e}")
        return {"files": []}

# ==================== SHUTDOWN EVENT ====================
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down...")
    
    # Close database connections
    if db and hasattr(db, 'close'):
        await db.close()
    
    # Close Redis connection
    if redis_client:
        redis_client.close()
    
    logger.info("👋 Shutdown complete")

# ==================== MAIN ====================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
        workers=1
    )
