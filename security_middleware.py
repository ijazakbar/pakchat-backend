"""
PAKCHAT ENTERPRISE SECURITY MIDDLEWARE
Production-ready security with comprehensive protection
"""

import logging
import time
import re
import ipaddress
import hashlib
import hmac
import os
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

class SecurityConfig:
    """Enterprise security configuration"""
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 60  # requests per minute
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # IP Blacklist
    IP_BLACKLIST_ENABLED = True
    IP_BLACKLIST: Set[str] = set()
    
    # SQL Injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\s|')*(union|select|insert|update|delete|drop|create|alter|exec|execute|truncate|rename|replace|grant|revoke)(\s|')+",
        r"(\s|')*(or|and)(\s|')+.*(=|<|>|in|like|between)",
        r"(\s|')*(;|--|#|/\*|\*/)",
        r"(\s|')*(information_schema|sys.tables|sys.columns)",
        r"(\s|')*(xp_cmdshell|sp_executesql|sp_prepare)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"onfocus\s*=",
        r"onblur\s*=",
        r"onchange\s*=",
        r"onsubmit\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"document\.cookie",
        r"document\.location",
        r"window\.location",
        r"eval\s*\(",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"\.\.%2f",
        r"\.\.%5c",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
    ]
    
    # Suspicious user agents
    SUSPICIOUS_USER_AGENTS = {
        "nikto", "sqlmap", "nmap", "nessus", "openvas",
        "wpscan", "joomscan", "droopescan", "whatweb",
        "gobuster", "dirbuster", "wfuzz", "hydra", "medusa",
        "ncrack", "zmap", "masscan", "python-requests",
        "go-http-client", "scrapy", "curl", "wget"
    }


# ==================== RATE LIMITER ====================

class RateLimiter:
    """Advanced rate limiting with sliding window"""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blacklist: Set[str] = set()
        
    def check(self, ip: str) -> Tuple[bool, str]:
        """Check if IP is allowed"""
        if ip in self.blacklist:
            return False, "IP permanently blocked"
        
        current_time = time.time()
        window_start = current_time - SecurityConfig.RATE_LIMIT_WINDOW
        
        # Clean old requests
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > window_start
        ]
        
        # Check rate limit
        if len(self.requests[ip]) >= SecurityConfig.RATE_LIMIT_REQUESTS:
            return False, f"Rate limit exceeded ({SecurityConfig.RATE_LIMIT_REQUESTS} requests per {SecurityConfig.RATE_LIMIT_WINDOW}s)"
        
        # Add request
        self.requests[ip].append(current_time)
        return True, "Allowed"


# ==================== INJECTION DETECTOR ====================

class InjectionDetector:
    """Comprehensive injection attack detection"""
    
    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """Check for SQL injection"""
        if not text or not isinstance(text, str):
            return False
        text_lower = text.lower()
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                logger.warning(f"SQL injection detected: {pattern}")
                return True
        return False
    
    @staticmethod
    def check_xss(text: str) -> bool:
        """Check for XSS attacks"""
        if not text or not isinstance(text, str):
            return False
        for pattern in SecurityConfig.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"XSS attack detected: {pattern}")
                return True
        return False
    
    @staticmethod
    def check_path_traversal(path: str) -> bool:
        """Check for path traversal attempts"""
        if not path:
            return False
        for pattern in SecurityConfig.PATH_TRAVERSAL_PATTERNS:
            if pattern in path.lower():
                logger.warning(f"Path traversal detected: {pattern}")
                return True
        return False
    
    @staticmethod
    def check_all(text: str) -> bool:
        """Check all injection types"""
        return (InjectionDetector.check_sql_injection(text) or
                InjectionDetector.check_xss(text) or
                InjectionDetector.check_path_traversal(text))


# ==================== IP VALIDATOR ====================

class IPValidator:
    """IP address validation and threat detection"""
    
    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """Check if IP is private/internal"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return (ip_obj.is_private or ip_obj.is_loopback or 
                    ip_obj.is_link_local or ip_obj.is_multicast or 
                    ip_obj.is_reserved)
        except:
            return True
    
    @staticmethod
    def is_suspicious_user_agent(user_agent: str) -> bool:
        """Check for suspicious user agents"""
        if not user_agent:
            return True
        ua_lower = user_agent.lower()
        for suspicious in SecurityConfig.SUSPICIOUS_USER_AGENTS:
            if suspicious in ua_lower:
                logger.warning(f"Suspicious UA detected: {user_agent}")
                return True
        return False


# ==================== MAIN SECURITY MIDDLEWARE ====================

class EnterpriseSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enterprise-grade security middleware with comprehensive protection
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.detector = InjectionDetector()
        self.validator = IPValidator()
        self._load_blacklist()
    
    def _load_blacklist(self):
        """Load IP blacklist"""
        try:
            with open("ip_blacklist.txt", "r") as f:
                for line in f:
                    ip = line.strip()
                    if ip and not ip.startswith("#"):
                        SecurityConfig.IP_BLACKLIST.add(ip)
                        self.rate_limiter.blacklist.add(ip)
            logger.info(f"✅ Loaded {len(SecurityConfig.IP_BLACKLIST)} IPs to blacklist")
        except FileNotFoundError:
            logger.info("ℹ️ No IP blacklist file found, starting fresh")
    
    async def dispatch(self, request: Request, call_next):
        """Main security dispatch function"""
        
        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method
        
        # === 1. IP Blacklist Check ===
        if client_ip in SecurityConfig.IP_BLACKLIST:
            logger.warning(f"🚫 Blocked blacklisted IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # === 2. Rate Limiting ===
        if SecurityConfig.RATE_LIMIT_ENABLED:
            allowed, reason = self.rate_limiter.check(client_ip)
            if not allowed:
                logger.warning(f"🚫 Rate limit for IP {client_ip}: {reason}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": reason}
                )
        
        # === 3. User Agent Validation ===
        if self.validator.is_suspicious_user_agent(user_agent):
            logger.warning(f"🚫 Suspicious UA from IP {client_ip}: {user_agent}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # === 4. Path Traversal Check ===
        if self.detector.check_path_traversal(path):
            logger.warning(f"🚫 Path traversal attempt from IP {client_ip}: {path}")
            self.rate_limiter.blacklist.add(client_ip)
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid request path"}
            )
        
        # === 5. Request Body Inspection (for POST/PUT/PATCH) ===
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    # Reset body for later consumption
                    request._body = body_bytes
                    
                    # Convert to string for inspection
                    body_str = body_bytes.decode('utf-8', errors='ignore')
                    
                    # Check for injection attacks
                    if self.detector.check_all(body_str):
                        logger.warning(f"🚫 Injection attack from IP {client_ip}")
                        self.rate_limiter.blacklist.add(client_ip)
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Invalid request content"}
                        )
            except Exception as e:
                logger.error(f"Error inspecting request body: {e}")
        
        # === 6. Process Request ===
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request processing error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
        
        # === 7. Add Security Headers ===
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


# ==================== EXPORT FUNCTION ====================

def add_security_middleware(app: FastAPI) -> FastAPI:
    """
    Add enterprise-grade security middleware to FastAPI app
    This is the main function called from main.py
    """
    logger.info("=" * 50)
    logger.info("🔒 ADDING ENTERPRISE SECURITY MIDDLEWARE")
    logger.info("=" * 50)
    
    # Add security middleware
    app.add_middleware(EnterpriseSecurityMiddleware)
    
    # Log security status
    logger.info("✅ Enterprise Security Middleware: LOADED")
    logger.info("├─ Rate Limiting: 60 requests/minute")
    logger.info("├─ SQL Injection Protection: ACTIVE")
    logger.info("├─ XSS Protection: ACTIVE")
    logger.info("├─ Path Traversal Protection: ACTIVE")
    logger.info("├─ IP Blacklisting: ACTIVE")
    logger.info("├─ Suspicious UA Detection: ACTIVE")
    logger.info("└─ Security Headers: ADDED")
    logger.info("=" * 50)
    
    return app
