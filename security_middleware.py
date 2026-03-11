"""
PAKCHAT SECURITY MIDDLEWARE
Enterprise-grade security with protection against:
- SQL Injection
- XSS (Cross-Site Scripting)
- CSRF (Cross-Site Request Forgery)
- Path Traversal
- Command Injection
- Rate Limiting
- DDoS Protection
- Bot Detection
- IP Blacklisting
- Malicious User Agents
"""

import logging
import re
import time
from typing import Dict, List, Set, Tuple
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
import ipaddress
import hashlib
import hmac
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

class SecurityConfig:
    """Security configuration settings"""
    
    # Rate limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 100  # requests per window
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # IP Blacklisting
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
        r"onreset\s*=",
        r"onselect\s*=",
        r"onabort\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<embed[^>]*>.*?</embed>",
        r"<object[^>]*>.*?</object>",
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
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`]",
        r"\$(\(|\{)",
        r"\%[0-9a-fA-F]{2}",
    ]
    
    # Suspicious user agents
    SUSPICIOUS_USER_AGENTS = {
        "nikto",
        "sqlmap",
        "nmap",
        "nessus",
        "openvas",
        "wpscan",
        "joomscan",
        "droopescan",
        "whatweb",
        "gobuster",
        "dirbuster",
        "wfuzz",
        "hydra",
        "medusa",
        "ncrack",
        "zmap",
        "masscan",
        "python-requests",
        "go-http-client",
        "scrapy",
        "curl",
        "wget",
    }
    
    # CSRF protection
    CSRF_ENABLED = True
    CSRF_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    CSRF_TOKEN_EXPIRY = 3600  # 1 hour


# ==================== RATE LIMITER ====================

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blacklist: Set[str] = set()
        self.suspicious: Set[str] = set()
        
    def check(self, ip: str) -> Tuple[bool, str]:
        """Check if IP is allowed"""
        # Check blacklist
        if ip in self.blacklist:
            return False, "IP blacklisted"
            
        # Check if suspicious (temporary block)
        if ip in self.suspicious:
            return False, "IP temporarily blocked"
            
        # Clean old requests
        current_time = time.time()
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if current_time - req_time < SecurityConfig.RATE_LIMIT_WINDOW
        ]
        
        # Check rate limit
        if len(self.requests[ip]) >= SecurityConfig.RATE_LIMIT_REQUESTS:
            self.suspicious.add(ip)
            return False, "Rate limit exceeded"
            
        # Add request
        self.requests[ip].append(current_time)
        return True, "Allowed"
    
    def blacklist_ip(self, ip: str):
        """Add IP to permanent blacklist"""
        self.blacklist.add(ip)
        if ip in self.requests:
            del self.requests[ip]
        if ip in self.suspicious:
            self.suspicious.remove(ip)
            
    def whitelist_ip(self, ip: str):
        """Remove IP from blacklist"""
        if ip in self.blacklist:
            self.blacklist.remove(ip)


# ==================== CSRF PROTECTION ====================

class CSRFProtection:
    """CSRF token protection"""
    
    def __init__(self):
        self.tokens: Dict[str, Dict] = {}
        
    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token for session"""
        timestamp = int(time.time())
        message = f"{session_id}:{timestamp}".encode()
        token = hmac.new(
            SecurityConfig.CSRF_SECRET.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        
        self.tokens[session_id] = {
            "token": token,
            "timestamp": timestamp
        }
        return token
    
    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate CSRF token"""
        if session_id not in self.tokens:
            return False
            
        stored = self.tokens[session_id]
        current_time = time.time()
        
        # Check expiry
        if current_time - stored["timestamp"] > SecurityConfig.CSRF_TOKEN_EXPIRY:
            del self.tokens[session_id]
            return False
            
        # Check token
        return hmac.compare_digest(stored["token"], token)
    
    def invalidate_token(self, session_id: str):
        """Invalidate CSRF token for session"""
        if session_id in self.tokens:
            del self.tokens[session_id]


# ==================== INJECTION DETECTOR ====================

class InjectionDetector:
    """Detect various injection attacks"""
    
    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """Check for SQL injection patterns"""
        if not text or not isinstance(text, str):
            return False
            
        text_lower = text.lower()
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern} in {text[:50]}...")
                return True
        return False
    
    @staticmethod
    def check_xss(text: str) -> bool:
        """Check for XSS patterns"""
        if not text or not isinstance(text, str):
            return False
            
        for pattern in SecurityConfig.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"XSS pattern detected: {pattern} in {text[:50]}...")
                return True
        return False
    
    @staticmethod
    def check_path_traversal(path: str) -> bool:
        """Check for path traversal attempts"""
        if not path or not isinstance(path, str):
            return False
            
        for pattern in SecurityConfig.PATH_TRAVERSAL_PATTERNS:
            if pattern in path.lower():
                logger.warning(f"Path traversal detected: {pattern} in {path}")
                return True
        return False
    
    @staticmethod
    def check_command_injection(text: str) -> bool:
        """Check for command injection patterns"""
        if not text or not isinstance(text, str):
            return False
            
        for pattern in SecurityConfig.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text):
                logger.warning(f"Command injection pattern detected: {pattern} in {text}")
                return True
        return False


# ==================== IP VALIDATOR ====================

class IPValidator:
    """IP address validation and geolocation (simplified)"""
    
    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """Check if IP is private"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return (
                ip_obj.is_private or
                ip_obj.is_loopback or
                ip_obj.is_link_local or
                ip_obj.is_multicast or
                ip_obj.is_reserved
            )
        except:
            return True
    
    @staticmethod
    def is_suspicious_user_agent(user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        if not user_agent:
            return True
            
        ua_lower = user_agent.lower()
        for suspicious in SecurityConfig.SUSPICIOUS_USER_AGENTS:
            if suspicious in ua_lower:
                logger.warning(f"Suspicious user agent detected: {user_agent}")
                return True
        return False


# ==================== MAIN SECURITY MIDDLEWARE ====================

class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware that combines all protections"""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.csrf = CSRFProtection()
        self.detector = InjectionDetector()
        self.validator = IPValidator()
        
        # Load IP blacklist from file if exists
        self._load_blacklist()
        
    def _load_blacklist(self):
        """Load IP blacklist from file"""
        try:
            with open("ip_blacklist.txt", "r") as f:
                for line in f:
                    ip = line.strip()
                    if ip and not ip.startswith("#"):
                        SecurityConfig.IP_BLACKLIST.add(ip)
                        self.rate_limiter.blacklist_ip(ip)
            logger.info(f"Loaded {len(SecurityConfig.IP_BLACKLIST)} IPs to blacklist")
        except FileNotFoundError:
            logger.info("No IP blacklist file found, starting fresh")
    
    async def dispatch(self, request: Request, call_next):
        """Main dispatch function that processes each request"""
        
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method
        
        # === 1. IP Validation ===
        if client_ip == "unknown":
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request source"}
            )
        
        # Check IP blacklist
        if client_ip in SecurityConfig.IP_BLACKLIST:
            logger.warning(f"Blocked blacklisted IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # === 2. Rate Limiting ===
        if SecurityConfig.RATE_LIMIT_ENABLED:
            allowed, reason = self.rate_limiter.check(client_ip)
            if not allowed:
                logger.warning(f"Rate limit exceeded for IP {client_ip}: {reason}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Too many requests: {reason}"}
                )
        
        # === 3. User Agent Validation ===
        if self.validator.is_suspicious_user_agent(user_agent):
            logger.warning(f"Suspicious user agent from IP {client_ip}: {user_agent}")
            self.rate_limiter.suspicious.add(client_ip)
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # === 4. Path Traversal Check ===
        if self.detector.check_path_traversal(path):
            logger.warning(f"Path traversal attempt from IP {client_ip}: {path}")
            self.rate_limiter.blacklist_ip(client_ip)
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid request path"}
            )
        
        # === 5. CSRF Protection (for state-changing methods) ===
        if SecurityConfig.CSRF_ENABLED and method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Skip CSRF for auth endpoints (login, register)
            if not path.startswith("/api/auth/"):
                csrf_token = request.headers.get("X-CSRF-Token")
                session_id = request.cookies.get("session_id")
                
                if not session_id or not csrf_token:
                    logger.warning(f"Missing CSRF token from IP {client_ip}")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF token missing"}
                    )
                
                if not self.csrf.validate_token(session_id, csrf_token):
                    logger.warning(f"Invalid CSRF token from IP {client_ip}")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Invalid CSRF token"}
                    )
        
        # === 6. Request Body Inspection ===
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                
                # Recursively check all string values for injections
                def check_value(value):
                    if isinstance(value, str):
                        if self.detector.check_sql_injection(value):
                            return True
                        if self.detector.check_xss(value):
                            return True
                        if self.detector.check_command_injection(value):
                            return True
                    elif isinstance(value, dict):
                        for v in value.values():
                            if check_value(v):
                                return True
                    elif isinstance(value, list):
                        for v in value:
                            if check_value(v):
                                return True
                    return False
                
                if check_value(body):
                    logger.warning(f"Injection attack detected from IP {client_ip}")
                    self.rate_limiter.suspicious.add(client_ip)
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid request content"}
                    )
                    
            except Exception:
                # Not JSON body, skip inspection
                pass
        
        # === 7. Process the request ===
        response = await call_next(request)
        
        # === 8. Add security headers ===
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # === 9. Add CSRF token to response for new sessions ===
        if method == "POST" and path == "/api/auth/login":
            session_id = request.cookies.get("session_id")
            if not session_id:
                # Generate new session ID
                session_id = hashlib.sha256(f"{client_ip}:{time.time()}".encode()).hexdigest()
                response.set_cookie(
                    key="session_id",
                    value=session_id,
                    httponly=True,
                    secure=True,
                    samesite="strict",
                    max_age=3600
                )
            
            # Generate CSRF token
            csrf_token = self.csrf.generate_token(session_id)
            response.headers["X-CSRF-Token"] = csrf_token
        
        return response


# ==================== EXPORT FUNCTION ====================

def add_security_middleware(app: FastAPI):
    """
    Add security middleware to FastAPI app
    This is the main function called from main.py
    """
    logger.info("🔒 Adding enterprise-grade security middleware...")
    
    # Add main security middleware
    app.add_middleware(SecurityMiddleware)
    
    # Log security status
    logger.info("✅ Security middleware loaded successfully")
    logger.info(f"   - Rate Limiting: {SecurityConfig.RATE_LIMIT_ENABLED}")
    logger.info(f"   - CSRF Protection: {SecurityConfig.CSRF_ENABLED}")
    logger.info(f"   - IP Blacklist: {len(SecurityConfig.IP_BLACKLIST)} IPs")
    logger.info("   - SQL Injection Protection: Enabled")
    logger.info("   - XSS Protection: Enabled")
    logger.info("   - Path Traversal Protection: Enabled")
    logger.info("   - Command Injection Protection: Enabled")
    
    return app