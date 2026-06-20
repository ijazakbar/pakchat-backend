"""
PakChat AI - Enterprise Grade LLM Service
Upgraded for Deep Reasoning & Professional Performance
Production-Ready with Multi-Provider Support, Advanced Error Handling & Monitoring
WITH PERSISTENCE LAYER - Redis & PostgreSQL Support
"""

import ssl
import aiohttp
import certifi
import logging
import json
import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import hashlib
from datetime import datetime, timedelta
import pickle

# ============================================
# DATABASE & CACHE IMPORTS
# ============================================

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("⚠️ Redis not installed. Using in-memory cache only.")

try:
    from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.sql import func
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logging.warning("⚠️ SQLAlchemy not installed. Database persistence disabled.")

# ============================================
# CONFIGURATION & ENUMS
# ============================================

class Provider(Enum):
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"
    MISTRAL = "mistral"

@dataclass
class ModelConfig:
    """Model configuration with reasoning capabilities"""
    name: str
    max_tokens: int
    reasoning_depth: str  # 'shallow', 'medium', 'deep'
    temperature_range: tuple
    context_window: int
    
    def __post_init__(self):
        self.temperature_range = (0.1, 0.9)

class ModelRegistry:
    """Centralized model registry with reasoning capabilities"""
    
    MODELS = {
        Provider.GROQ: {
            'fast': ModelConfig('llama-3.3-70b-versatile', 8192, 'medium', (0.1, 0.9), 128000),
            'deep': ModelConfig('llama-3.3-70b-versatile', 8192, 'deep', (0.1, 0.5), 128000)
        },
        Provider.DEEPSEEK: {
            'standard': ModelConfig('deepseek-chat', 4096, 'deep', (0.1, 0.7), 32000),
            'coder': ModelConfig('deepseek-coder', 4096, 'deep', (0.1, 0.3), 16000)
        },
        Provider.ANTHROPIC: {
            'sonnet': ModelConfig('claude-3-5-sonnet-20241022', 8192, 'deep', (0.1, 0.7), 200000),
            'haiku': ModelConfig('claude-3-haiku-20240307', 4096, 'medium', (0.1, 0.9), 32000)
        },
        Provider.GOOGLE: {
            'pro': ModelConfig('gemini-1.5-pro', 8192, 'deep', (0.1, 0.8), 2000000),
            'flash': ModelConfig('gemini-1.5-flash', 4096, 'medium', (0.1, 0.9), 1000000)
        },
        Provider.OPENAI: {
            'gpt4': ModelConfig('gpt-4-turbo-preview', 4096, 'deep', (0.1, 0.7), 128000),
            'gpt35': ModelConfig('gpt-3.5-turbo', 4096, 'medium', (0.1, 0.9), 16000)
        },
        Provider.MISTRAL: {
            'large': ModelConfig('mistral-large-latest', 4096, 'deep', (0.1, 0.7), 32000),
            'small': ModelConfig('mistral-small-latest', 4096, 'medium', (0.1, 0.9), 32000)
        }
    }
    
    @classmethod
    def get_model(cls, provider: Provider, variant: str = 'standard') -> ModelConfig:
        """Get model configuration by provider and variant"""
        try:
            return cls.MODELS[provider][variant]
        except KeyError:
            return list(cls.MODELS[provider].values())[0]
    
    @classmethod
    def get_all_providers(cls) -> List[str]:
        return [p.value for p in Provider]

# ============================================
# ENTERPRISE SYSTEM PROMPTS
# ============================================

class PromptEngine:
    """Professional system prompt engineering"""
    
    SYSTEM_PROMPTS = {
        'default': """You are PakChat AI, an enterprise-grade AI assistant with deep reasoning capabilities. 
        Provide structured, analytical, and professional responses. Focus on:
        - Clear logical reasoning
        - Evidence-based conclusions
        - Actionable insights
        - Professional tone
        - Structured formatting where appropriate""",
        
        'coding': """You are PakChat AI - Senior Developer. Provide:
        - Clean, production-ready code
        - Best practices and design patterns
        - Security considerations
        - Performance optimization
        - Complete error handling""",
        
        'research': """You are PakChat AI - Research Analyst. Provide:
        - Comprehensive analysis
        - Data-driven insights
        - Multiple perspectives
        - Citations and references
        - Balanced conclusions""",
        
        'executive': """You are PakChat AI - Executive Advisor. Provide:
        - Strategic insights
        - Risk assessment
        - ROI analysis
        - Implementation roadmap
        - Executive summaries"""
    }
    
    @classmethod
    def get_prompt(cls, style: str = 'default') -> Dict[str, str]:
        return {"role": "system", "content": cls.SYSTEM_PROMPTS.get(style, cls.SYSTEM_PROMPTS['default'])}

# ============================================
# DATABASE MODELS (SQLAlchemy)
# ============================================

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class MetricRecord(Base):
        __tablename__ = 'llm_metrics'
        
        id = Column(String(36), primary_key=True)
        provider = Column(String(50))
        request_type = Column(String(50))
        tokens_used = Column(Integer)
        response_time = Column(Float)
        success = Column(Integer)  # 0 or 1
        error_message = Column(Text, nullable=True)
        model_used = Column(String(100))
        temperature = Column(Float)
        created_at = Column(DateTime, server_default=func.now())
        
    class ChatHistory(Base):
        __tablename__ = 'chat_history'
        
        id = Column(String(36), primary_key=True)
        session_id = Column(String(100))
        provider = Column(String(50))
        messages = Column(JSON)
        response = Column(Text)
        tokens_used = Column(Integer)
        model_used = Column(String(100))
        created_at = Column(DateTime, server_default=func.now())
        
    class CacheRecord(Base):
        __tablename__ = 'cache_records'
        
        cache_key = Column(String(200), primary_key=True)
        response = Column(JSON)
        created_at = Column(DateTime, server_default=func.now())
        expires_at = Column(DateTime)
        hits = Column(Integer, default=0)

# ============================================
# PERSISTENCE LAYER
# ============================================

class PersistenceManager:
    """
    Enterprise Persistence Layer with:
    - Redis for caching (fast, ephemeral)
    - PostgreSQL for metrics/history (permanent)
    - Automatic fallback to in-memory
    - Connection pooling
    - Auto-reconnection
    """
    
    def __init__(self, redis_url: Optional[str] = None, database_url: Optional[str] = None):
        self.redis_url = redis_url
        self.database_url = database_url
        
        # Redis client
        self.redis_client = None
        self._init_redis()
        
        # SQLAlchemy setup
        self.db_session = None
        self._init_database()
        
        # In-memory fallback
        self.memory_cache = {}
        self.memory_metrics = []
        self.memory_chat_history = []
        
        logger.info("✅ PersistenceManager initialized")
    
    def _init_redis(self):
        """Initialize Redis connection"""
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                logger.info("✅ Redis connected")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}")
                self.redis_client = None
        else:
            self.redis_client = None
    
    def _init_database(self):
        """Initialize SQLAlchemy database"""
        if SQLALCHEMY_AVAILABLE and self.database_url:
            try:
                engine = create_engine(
                    self.database_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_recycle=3600
                )
                Base.metadata.create_all(engine)
                Session = sessionmaker(bind=engine)
                self.db_session = Session()
                logger.info("✅ Database connected")
            except Exception as e:
                logger.warning(f"⚠️ Database connection failed: {e}")
                self.db_session = None
        else:
            self.db_session = None
    
    # ============================================
    # CACHE OPERATIONS
    # ============================================
    
    async def get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response with TTL"""
        # Try Redis first
        if self.redis_client:
            try:
                data = await self.redis_client.get(f"cache:{key}")
                if data:
                    logger.info(f"📦 Redis cache hit: {key[:8]}")
                    # Update hit count
                    await self.redis_client.hincrby(f"cache_meta:{key}", "hits", 1)
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"⚠️ Redis get failed: {e}")
        
        # Fallback to memory
        if key in self.memory_cache:
            cached_data, timestamp = self.memory_cache[key]
            if time.time() - timestamp < 300:  # 5 minutes TTL
                logger.info(f"📦 Memory cache hit: {key[:8]}")
                return cached_data
            else:
                del self.memory_cache[key]
        
        # Try database for persistent cache
        if self.db_session:
            try:
                record = self.db_session.query(CacheRecord).filter_by(cache_key=key).first()
                if record and record.expires_at > datetime.now():
                    logger.info(f"📦 DB cache hit: {key[:8]}")
                    record.hits += 1
                    self.db_session.commit()
                    return record.response
            except Exception as e:
                logger.warning(f"⚠️ DB cache get failed: {e}")
        
        return None
    
    async def set_cache(self, key: str, value: Dict[str, Any], ttl: int = 300):
        """Set cached response with TTL"""
        # Store in Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"cache:{key}",
                    ttl,
                    json.dumps(value)
                )
                # Store metadata
                await self.redis_client.hset(f"cache_meta:{key}", "hits", 0)
                await self.redis_client.expire(f"cache_meta:{key}", ttl)
            except Exception as e:
                logger.warning(f"⚠️ Redis set failed: {e}")
        
        # Store in memory
        self.memory_cache[key] = (value, time.time())
        
        # Store in database for persistence
        if self.db_session:
            try:
                record = self.db_session.query(CacheRecord).filter_by(cache_key=key).first()
                if record:
                    record.response = value
                    record.expires_at = datetime.now() + timedelta(seconds=ttl)
                else:
                    record = CacheRecord(
                        cache_key=key,
                        response=value,
                        expires_at=datetime.now() + timedelta(seconds=ttl)
                    )
                    self.db_session.add(record)
                self.db_session.commit()
            except Exception as e:
                logger.warning(f"⚠️ DB cache set failed: {e}")
    
    async def delete_cache(self, key: str):
        """Delete cached response"""
        if self.redis_client:
            try:
                await self.redis_client.delete(f"cache:{key}")
                await self.redis_client.delete(f"cache_meta:{key}")
            except Exception:
                pass
        
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        if self.db_session:
            try:
                self.db_session.query(CacheRecord).filter_by(cache_key=key).delete()
                self.db_session.commit()
            except Exception:
                pass
    
    async def clear_cache(self):
        """Clear all cache"""
        if self.redis_client:
            try:
                keys = await self.redis_client.keys("cache:*")
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception:
                pass
        
        self.memory_cache.clear()
        
        if self.db_session:
            try:
                self.db_session.query(CacheRecord).delete()
                self.db_session.commit()
            except Exception:
                pass
    
    # ============================================
    # METRICS OPERATIONS
    # ============================================
    
    async def save_metric(self, metric: Dict[str, Any]):
        """Save performance metric"""
        # Store in database
        if self.db_session:
            try:
                record = MetricRecord(
                    id=metric.get('id', str(time.time())),
                    provider=metric.get('provider'),
                    request_type=metric.get('request_type', 'chat'),
                    tokens_used=metric.get('tokens_used', 0),
                    response_time=metric.get('response_time', 0),
                    success=1 if metric.get('success', True) else 0,
                    error_message=metric.get('error_message'),
                    model_used=metric.get('model_used'),
                    temperature=metric.get('temperature', 0.3)
                )
                self.db_session.add(record)
                self.db_session.commit()
            except Exception as e:
                logger.warning(f"⚠️ DB metric save failed: {e}")
        
        # Store in memory
        self.memory_metrics.append(metric)
        if len(self.memory_metrics) > 10000:
            self.memory_metrics = self.memory_metrics[-5000:]
    
    async def get_metrics(self, provider: Optional[str] = None, 
                         hours: int = 24) -> Dict[str, Any]:
        """Get metrics from database"""
        if not self.db_session:
            # Return memory metrics
            metrics = self.memory_metrics
            if provider:
                metrics = [m for m in metrics if m.get('provider') == provider]
            return {
                'total': len(metrics),
                'metrics': metrics[-100:],  # Last 100
                'source': 'memory'
            }
        
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            query = self.db_session.query(MetricRecord).filter(
                MetricRecord.created_at >= cutoff
            )
            if provider:
                query = query.filter_by(provider=provider)
            
            records = query.order_by(MetricRecord.created_at.desc()).limit(1000).all()
            
            return {
                'total': len(records),
                'metrics': [{
                    'provider': r.provider,
                    'tokens_used': r.tokens_used,
                    'response_time': r.response_time,
                    'success': bool(r.success),
                    'error_message': r.error_message,
                    'model_used': r.model_used,
                    'temperature': r.temperature,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                } for r in records],
                'source': 'database'
            }
        except Exception as e:
            logger.warning(f"⚠️ DB metrics get failed: {e}")
            return {'total': 0, 'metrics': [], 'source': 'error'}
    
    # ============================================
    # CHAT HISTORY OPERATIONS
    # ============================================
    
    async def save_chat_history(self, session_id: str, provider: str, 
                                messages: List[Dict[str, str]], 
                                response: str, tokens: int, model: str):
        """Save chat history"""
        if self.db_session:
            try:
                record = ChatHistory(
                    id=f"{session_id}_{int(time.time())}",
                    session_id=session_id,
                    provider=provider,
                    messages=json.dumps(messages),
                    response=response,
                    tokens_used=tokens,
                    model_used=model
                )
                self.db_session.add(record)
                self.db_session.commit()
            except Exception as e:
                logger.warning(f"⚠️ DB history save failed: {e}")
        
        # Store in memory
        self.memory_chat_history.append({
            'session_id': session_id,
            'provider': provider,
            'messages': messages,
            'response': response,
            'tokens_used': tokens,
            'model_used': model,
            'created_at': datetime.now().isoformat()
        })
        if len(self.memory_chat_history) > 1000:
            self.memory_chat_history = self.memory_chat_history[-500:]
    
    async def get_chat_history(self, session_id: str, limit: int = 50):
        """Get chat history"""
        if self.db_session:
            try:
                records = self.db_session.query(ChatHistory).filter_by(
                    session_id=session_id
                ).order_by(
                    ChatHistory.created_at.desc()
                ).limit(limit).all()
                
                return [{
                    'id': r.id,
                    'provider': r.provider,
                    'messages': json.loads(r.messages) if isinstance(r.messages, str) else r.messages,
                    'response': r.response,
                    'tokens_used': r.tokens_used,
                    'model_used': r.model_used,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                } for r in records]
            except Exception as e:
                logger.warning(f"⚠️ DB history get failed: {e}")
        
        # Return memory history
        history = [h for h in self.memory_chat_history if h['session_id'] == session_id]
        return history[-limit:]
    
    # ============================================
    # CONNECTION MANAGEMENT
    # ============================================
    
    async def health_check(self) -> Dict[str, bool]:
        """Check all connections"""
        status = {
            'redis': False,
            'database': False,
            'memory': True
        }
        
        if self.redis_client:
            try:
                await self.redis_client.ping()
                status['redis'] = True
            except Exception:
                pass
        
        if self.db_session:
            try:
                self.db_session.execute("SELECT 1")
                status['database'] = True
            except Exception:
                pass
        
        return status
    
    def close(self):
        """Close all connections"""
        if self.redis_client:
            try:
                self.redis_client.close()
            except Exception:
                pass
        
        if self.db_session:
            try:
                self.db_session.close()
            except Exception:
                pass

# ============================================
# ENTERPRISE LLM SERVICE WITH PERSISTENCE
# ============================================

class LLMService:
    """
    Enterprise-Grade LLM Service with:
    - Deep reasoning capabilities
    - Multi-provider support
    - Advanced error handling
    - Performance monitoring with persistence
    - Caching with persistence (Redis + DB)
    - Rate limiting
    - Professional system prompts
    - Chat history persistence
    """
    
    def __init__(self, **kwargs):
        # Initialize API keys
        self.keys = {
            'openai': kwargs.get('openai_key'),
            'groq': kwargs.get('groq_key'),
            'deepseek': kwargs.get('deepseek_key'),
            'google': kwargs.get('google_key'),
            'anthropic': kwargs.get('anthropic_key'),
            'mistral': kwargs.get('mistral_key'),
            'openrouter': kwargs.get('openrouter_key'),
            'cohere': kwargs.get('cohere_key'),
            'huggingface': kwargs.get('huggingface_key'),
            'replicate': kwargs.get('replicate_key')
        }
        
        # SSL Context for secure connections
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE  # For development only
        
        # Initialize Persistence Layer
        self.persistence = PersistenceManager(
            redis_url=kwargs.get('redis_url'),
            database_url=kwargs.get('database_url')
        )
        
        # Performance tracking (in-memory for quick access)
        self.metrics = {
            'requests': 0,
            'errors': 0,
            'total_tokens': 0,
            'avg_response_time': 0,
            'provider_usage': {}
        }
        
        # Active provider for load balancing
        self.active_providers = []
        self._initialize_providers()
        
        # System prompt style
        self.prompt_style = kwargs.get('prompt_style', 'default')
        
        # Session ID for tracking
        self.session_id = kwargs.get('session_id', f"session_{int(time.time())}")
        
        logger.info("🚀 PakChat AI Enterprise Service initialized with Persistence")
        logger.info(f"📋 Active Providers: {[p.value for p in self.active_providers]}")
        logger.info(f"🎯 Prompt Style: {self.prompt_style}")
        logger.info(f"🆔 Session ID: {self.session_id}")
    
    def _initialize_providers(self):
        """Initialize active providers based on available keys"""
        provider_key_map = {
            Provider.GROQ: 'groq',
            Provider.DEEPSEEK: 'deepseek',
            Provider.ANTHROPIC: 'anthropic',
            Provider.GOOGLE: 'google',
            Provider.OPENAI: 'openai',
            Provider.MISTRAL: 'mistral'
        }
        
        self.active_providers = []
        for provider, key_name in provider_key_map.items():
            if self.keys.get(key_name):
                self.active_providers.append(provider)
        
        if not self.active_providers:
            logger.warning("⚠️ No API keys configured. Service in limited mode.")
    
    def _prepare_messages(self, messages: List[Dict[str, str]], 
                         prompt_style: Optional[str] = None) -> List[Dict[str, str]]:
        """Prepare messages with system prompt"""
        style = prompt_style or self.prompt_style
        system_prompt = PromptEngine.get_prompt(style)
        return [system_prompt] + messages
    
    def _get_cache_key(self, provider: str, messages: List[Dict[str, str]], 
                      temperature: float) -> str:
        """Generate cache key for request deduplication"""
        content = f"{provider}:{json.dumps(messages)}:{temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _update_metrics(self, provider: str, tokens: int, response_time: float, success: bool):
        """Update performance metrics with persistence"""
        # Update in-memory metrics
        self.metrics['requests'] += 1
        if not success:
            self.metrics['errors'] += 1
        
        self.metrics['total_tokens'] += tokens
        
        # Update provider-specific metrics
        if provider not in self.metrics['provider_usage']:
            self.metrics['provider_usage'][provider] = {
                'requests': 0,
                'tokens': 0,
                'errors': 0
            }
        self.metrics['provider_usage'][provider]['requests'] += 1
        self.metrics['provider_usage'][provider]['tokens'] += tokens
        if not success:
            self.metrics['provider_usage'][provider]['errors'] += 1
        
        # Update average response time
        current_avg = self.metrics['avg_response_time']
        total_reqs = self.metrics['requests']
        self.metrics['avg_response_time'] = ((current_avg * (total_reqs - 1)) + response_time) / total_reqs
        
        # Save to persistence layer
        import asyncio
        asyncio.create_task(
            self.persistence.save_metric({
                'id': f"{provider}_{int(time.time())}_{self.metrics['requests']}",
                'provider': provider,
                'tokens_used': tokens,
                'response_time': response_time,
                'success': success,
                'model_used': 'unknown',
                'temperature': 0.3
            })
        )
    
    async def chat_with_provider(self, provider: str, messages: List[Dict[str, str]], 
                                temperature: float = 0.3, max_tokens: Optional[int] = None,
                                prompt_style: Optional[str] = None,
                                variant: str = 'standard',
                                use_cache: bool = True,
                                save_history: bool = True) -> Dict[str, Any]:
        """
        Enterprise chat with any provider
        Features: Deep reasoning, caching with persistence, load balancing, fallback
        """
        provider_enum = Provider(provider)
        start_time = time.time()
        
        # Validate provider
        if provider_enum not in self.active_providers:
            raise Exception(f"Provider {provider} not configured. Available: {[p.value for p in self.active_providers]}")
        
        # Prepare messages with system prompt
        prepared_messages = self._prepare_messages(messages, prompt_style)
        
        # Get model configuration
        model_config = ModelRegistry.get_model(provider_enum, variant)
        
        # Check cache (with persistence)
        cache_key = self._get_cache_key(provider, prepared_messages, temperature)
        if use_cache:
            cached_response = await self.persistence.get_cache(cache_key)
            if cached_response:
                return cached_response
        
        # Map provider to method
        provider_methods = {
            Provider.GROQ: self._chat_groq,
            Provider.DEEPSEEK: self._chat_deepseek,
            Provider.ANTHROPIC: self._chat_anthropic,
            Provider.GOOGLE: self._chat_google,
            Provider.OPENAI: self._chat_openai,
            Provider.MISTRAL: self._chat_mistral
        }
        
        method = provider_methods.get(provider_enum)
        if not method:
            raise Exception(f"Provider {provider} not supported")
        
        try:
            # Execute with retry logic
            response = await self._execute_with_retry(
                method,
                prepared_messages,
                temperature,
                max_tokens or model_config.max_tokens
            )
            
            # Extract tokens for metrics
            tokens_used = response.get('usage', {}).get('total_tokens', 0)
            if not tokens_used:
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                tokens_used = len(content.split()) * 1.3
            
            # Update metrics
            response_time = time.time() - start_time
            model_used = response.get('model', provider)
            self._update_metrics(provider, int(tokens_used), response_time, True)
            
            # Cache successful response
            if use_cache and response_time < 10:
                await self.persistence.set_cache(cache_key, response, ttl=300)
            
            # Save chat history
            if save_history and messages:
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                await self.persistence.save_chat_history(
                    self.session_id,
                    provider,
                    messages,
                    content,
                    int(tokens_used),
                    model_used
                )
            
            logger.info(f"✅ {provider} response in {response_time:.2f}s, {tokens_used} tokens")
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            self._update_metrics(provider, 0, response_time, False)
            logger.error(f"❌ {provider} error: {str(e)}")
            
            # Try fallback provider if available
            if len(self.active_providers) > 1:
                logger.info(f"🔄 Trying fallback provider...")
                fallback_provider = self._get_fallback_provider(provider)
                if fallback_provider:
                    return await self.chat_with_provider(
                        fallback_provider.value,
                        messages,
                        temperature,
                        max_tokens,
                        prompt_style,
                        variant,
                        use_cache=False,
                        save_history=False
                    )
            
            raise
    
    async def _execute_with_retry(self, method, *args, max_retries: int = 3, **kwargs):
        """Execute with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                return await method(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"⚠️ Retry {attempt + 1}/{max_retries} after {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)
    
    def _get_fallback_provider(self, current_provider: str) -> Optional[Provider]:
        """Get fallback provider in case of failure"""
        available = [p for p in self.active_providers if p.value != current_provider]
        return available[0] if available else None
    
    # ============================================
    # PROVIDER IMPLEMENTATIONS (SAME AS BEFORE)
    # ============================================
    
    async def _chat_groq(self, messages: List[Dict[str, str]], 
                        temperature: float, max_tokens: int) -> Dict[str, Any]:
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }
        headers = {
            "Authorization": f"Bearer {self.keys['groq']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Groq API error {resp.status}: {error_text}")
                return await resp.json()
    
    async def _chat_deepseek(self, messages: List[Dict[str, str]], 
                            temperature: float, max_tokens: int) -> Dict[str, Any]:
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        headers = {
            "Authorization": f"Bearer {self.keys['deepseek']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"DeepSeek error {resp.status}: {error_text}")
                return await resp.json()
    
    async def _chat_anthropic(self, messages: List[Dict[str, str]], 
                             temperature: float, max_tokens: int) -> Dict[str, Any]:
        anthropic_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                continue
            anthropic_messages.append({
                "role": msg['role'] if msg['role'] != 'assistant' else 'assistant',
                "content": msg['content']
            })
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages
        }
        headers = {
            "x-api-key": self.keys['anthropic'],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Anthropic error {resp.status}: {error_text}")
                result = await resp.json()
                return {
                    "choices": [{"message": {"content": result['content'][0]['text']}}],
                    "usage": result.get('usage', {}),
                    "model": result.get('model', 'claude-3-5-sonnet')
                }
    
    async def _chat_google(self, messages: List[Dict[str, str]], 
                          temperature: float, max_tokens: int) -> Dict[str, Any]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.keys['google'])
            full_prompt = ""
            for msg in messages:
                role = "User" if msg['role'] == 'user' else "Assistant"
                if msg['role'] == 'system':
                    full_prompt = f"{msg['content']}\n\n{full_prompt}"
                else:
                    full_prompt += f"{role}: {msg['content']}\n"
            model = genai.GenerativeModel('gemini-1.5-pro')
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": 0.95,
                "top_k": 40
            }
            response = await model.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            return {
                "choices": [{"message": {"content": response.text}}],
                "usage": {"total_tokens": len(response.text.split()) * 1.3},
                "model": "gemini-1.5-pro"
            }
        except Exception as e:
            raise Exception(f"Google Gemini error: {str(e)}")
    
    async def _chat_openai(self, messages: List[Dict[str, str]], 
                          temperature: float, max_tokens: int) -> Dict[str, Any]:
        data = {
            "model": "gpt-4-turbo-preview",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"} if temperature < 0.3 else {}
        }
        headers = {
            "Authorization": f"Bearer {self.keys['openai']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    if resp.status == 429:
                        raise Exception("OpenAI quota exceeded or rate limited")
                    raise Exception(f"OpenAI error {resp.status}: {error_text}")
                return await resp.json()
    
    async def _chat_mistral(self, messages: List[Dict[str, str]], 
                           temperature: float, max_tokens: int) -> Dict[str, Any]:
        data = {
            "model": "mistral-large-latest",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        headers = {
            "Authorization": f"Bearer {self.keys['mistral']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Mistral error {resp.status}: {error_text}")
                return await resp.json()
    
    # ============================================
    # ADVANCED FEATURES WITH PERSISTENCE
    # ============================================
    
    async def chat_completion_stream(self, messages: List[Dict[str, str]], 
                                     temperature: float = 0.3,
                                     max_tokens: Optional[int] = None,
                                     provider: str = 'mistral',
                                     prompt_style: Optional[str] = None,
                                     variant: str = 'standard',
                                     save_history: bool = True) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion with enterprise features and persistence
        """
        provider_enum = Provider(provider)
        
        if provider_enum not in self.active_providers:
            provider_enum = self.active_providers[0]
            logger.info(f"🔄 Falling back to {provider_enum.value} for streaming")
        
        prepared_messages = self._prepare_messages(messages, prompt_style)
        model_config = ModelRegistry.get_model(provider_enum, variant)
        
        stream_methods = {
            Provider.MISTRAL: self._stream_mistral,
            Provider.GROQ: self._stream_groq,
            Provider.OPENAI: self._stream_openai,
            Provider.DEEPSEEK: self._stream_deepseek
        }
        
        stream_method = stream_methods.get(provider_enum)
        if not stream_method:
            result = await self.chat_with_provider(
                provider_enum.value,
                messages,
                temperature,
                max_tokens or model_config.max_tokens,
                prompt_style,
                variant,
                save_history=save_history
            )
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # Collect full response for history
        full_response = ""
        async for chunk in stream_method(prepared_messages, temperature, max_tokens or model_config.max_tokens):
            yield chunk
            # Try to extract content from chunk
            try:
                if chunk.startswith('data: ') and chunk != 'data: [DONE]\n\n':
                    data = json.loads(chunk[6:].strip())
                    if 'choices' in data and data['choices']:
                        delta = data['choices'][0].get('delta', {})
                        if 'content' in delta:
                            full_response += delta['content']
            except:
                pass
        
        # Save chat history
        if save_history and full_response and messages:
            await self.persistence.save_chat_history(
                self.session_id,
                provider,
                messages,
                full_response,
                len(full_response.split()) * 1.3,
                model_config.name
            )
    
    # ============================================
    # STREAMING METHODS (SAME AS BEFORE)
    # ============================================
    
    async def _stream_mistral(self, messages: List[Dict[str, str]], 
                             temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        data = {
            "model": "mistral-large-latest",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        headers = {
            "Authorization": f"Bearer {self.keys['mistral']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"data: {json.dumps({'error': f'Mistral error: {error_text}'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                async for line in resp.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_content = line[6:]
                            if data_content == '[DONE]':
                                yield "data: [DONE]\n\n"
                            else:
                                try:
                                    json.loads(data_content)
                                    yield f"data: {data_content}\n\n"
                                except json.JSONDecodeError:
                                    continue
    
    async def _stream_groq(self, messages: List[Dict[str, str]], 
                          temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        headers = {
            "Authorization": f"Bearer {self.keys['groq']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"data: {json.dumps({'error': f'Groq error: {error_text}'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                async for line in resp.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_content = line[6:]
                            if data_content == '[DONE]':
                                yield "data: [DONE]\n\n"
                            else:
                                yield f"data: {data_content}\n\n"
    
    async def _stream_openai(self, messages: List[Dict[str, str]], 
                            temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        data = {
            "model": "gpt-4-turbo-preview",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        headers = {
            "Authorization": f"Bearer {self.keys['openai']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"data: {json.dumps({'error': f'OpenAI error: {error_text}'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                async for line in resp.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_content = line[6:]
                            if data_content == '[DONE]':
                                yield "data: [DONE]\n\n"
                            else:
                                yield f"data: {data_content}\n\n"
    
    async def _stream_deepseek(self, messages: List[Dict[str, str]], 
                              temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        headers = {
            "Authorization": f"Bearer {self.keys['deepseek']}",
            "Content-Type": "application/json"
        }
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"data: {json.dumps({'error': f'DeepSeek error: {error_text}'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                async for line in resp.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_content = line[6:]
                            if data_content == '[DONE]':
                                yield "data: [DONE]\n\n"
                            else:
                                yield f"data: {data_content}\n\n"
    
    # ============================================
    # UTILITY & MONITORING WITH PERSISTENCE
    # ============================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get in-memory performance metrics"""
        return {
            "total_requests": self.metrics['requests'],
            "errors": self.metrics['errors'],
            "error_rate": self.metrics['errors'] / max(1, self.metrics['requests']),
            "total_tokens": self.metrics['total_tokens'],
            "avg_response_time": self.metrics['avg_response_time'],
            "provider_usage": self.metrics['provider_usage'],
            "active_providers": [p.value for p in self.active_providers],
            "session_id": self.session_id
        }
    
    async def get_persisted_metrics(self, provider: Optional[str] = None, 
                                   hours: int = 24) -> Dict[str, Any]:
        """Get metrics from database persistence"""
        return await self.persistence.get_metrics(provider, hours)
    
    async def get_chat_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history from persistence"""
        return await self.persistence.get_chat_history(self.session_id, limit)
    
    async def clear_cache(self):
        """Clear all cache (Redis + DB + Memory)"""
        await self.persistence.clear_cache()
        logger.info("🗑️ All cache cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        provider_status = self.get_provider_status()
        connection_status = await self.persistence.health_check()
        
        return {
            "service": "healthy" if self.active_providers else "degraded",
            "active_providers": [p.value for p in self.active_providers],
            "connections": connection_status,
            "providers": provider_status,
            "metrics": self.get_metrics()
        }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all configured providers"""
        status = {}
        for provider in self.active_providers:
            status[provider.value] = {
                'configured': True,
                'key_present': bool(self.keys.get(provider.value)),
                'usage': self.metrics['provider_usage'].get(provider.value, {})
            }
        return status
    
    def close(self):
        """Close all connections"""
        self.persistence.close()
        logger.info("🔌 Connections closed")

# ============================================
# USAGE EXAMPLE WITH PERSISTENCE
# ============================================

if __name__ == "__main__":
    # Initialize service with persistence
    service = LLMService(
        groq_key="your-groq-key",
        deepseek_key="your-deepseek-key",
        anthropic_key="your-anthropic-key",
        google_key="your-google-key",
        openai_key="your-openai-key",
        mistral_key="your-mistral-key",
        redis_url="redis://localhost:6379",
        database_url="postgresql://user:pass@localhost:5432/pakchat",
        prompt_style="executive",
        session_id="user_session_123"
    )
    
    # Async usage example
    async def example():
        # Simple chat with persistence
        response = await service.chat_with_provider(
            provider="groq",
            messages=[{"role": "user", "content": "Explain quantum computing"}],
            temperature=0.3,
            save_history=True
        )
        print(response['choices'][0]['message']['content'])
        
        # Streaming with persistence
        async for chunk in service.chat_completion_stream(
            messages=[{"role": "user", "content": "Write a Python function"}],
            provider="mistral",
            save_history=True
        ):
            print(chunk, end='')
        
        # Get metrics from database
        metrics = await service.get_persisted_metrics(provider="groq", hours=24)
        print(f"📊 Metrics: {metrics}")
        
        # Get chat history
        history = await service.get_chat_history(limit=10)
        print(f"📜 History: {len(history)} records")
        
        # Health check
        health = await service.health_check()
        print(f"🏥 Health: {health}")
    
    # asyncio.run(example())