"""
PAKCHAT ENTERPRISE SECURITY MIDDLEWARE - FINAL FIXED VERSION
Render health checks allowed, all security features active
"""

import logging
import time
import re
import ipaddress
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

class SecurityConfig:
    """Security configuration - easily adjustable"""
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 100  # requests per window
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_BURST = 20  # extra requests for burst
    
    # IP Blacklist/Whitelist
    IP_BLACKLIST_ENABLED = True
    IP_WHITELIST_ENABLED = False
    IP_WHITELIST: Set[str] = set()
    IP_BLACKLIST: Set[str] = set()
    
    # SQL Injection Patterns
    SQL_INJECTION_PATTERNS = [
        r"(\s|')*(union|select|insert|update|delete|drop|create|alter|exec|execute|truncate|rename|replace|grant|revoke)(\s|')+",
        r"(\s|')*(or|and)(\s|')+.*(=|<|>|in|like|between)",
        r"(\s|')*(;|--|#|/\*|\*/)",
        r"(\s|')*(information_schema|sys.tables|sys.columns)",
        r"(\s|')*(xp_cmdshell|sp_executesql|sp_prepare)",
        r"(\s|')*(sleep|waitfor|benchmark)(\s|')*\(",
    ]
    
    # XSS Patterns
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
        r"<embed[^>]*>.*?</embed>",
        r"<object[^>]*>.*?</object>",
        r"document\.cookie",
        r"document\.location",
        r"window\.location",
        r"eval\s*\(",
        r"alert\s*\(",
        r"prompt\s*\(",
        r"confirm\s*\(",
    ]
    
    # Path Traversal Patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"\.\.%2f",
        r"\.\.%5c",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
    ]
    
    # Command Injection Patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`]",
        r"\$(\(|\{)",
        r"\%[0-9a-fA-F]{2}",
        r"&&",
        r"\|\|",
        r">\s*\/",
        r"<\s*\/",
    ]
    
    # Allowed User Agents (Render and browsers)
    ALLOWED_USER_AGENTS = {
        "go-http-client",  # Render health check
        "render",          # Render bot
        "mozilla",         # Firefox/Chrome
        "chrome",
        "safari",
        "firefox",
        "edge",
        "postman",         # API testing
        "curl",            # Command line
    }
    
    # Security Headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }


# ==================== RATE LIMITER ====================

class AdvancedRateLimiter:
    """Advanced rate limiting with sliding window and burst handling"""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blocked: Dict[str, float] = {}
        self.block_duration = 300  # 5 minutes block
        
    def check(self, ip: str) -> Tuple[bool, str, int]:
        """Check if IP is allowed, returns (allowed, reason, retry_after)"""
        current_time = time.time()
        
        # Check if IP is temporarily blocked
        if ip in self.blocked:
            block_time = self.blocked[ip]
            if current_time - block_time < self.block_duration:
                retry_after = int(self.block_duration - (current_time - block_time))
                return False, "IP temporarily blocked", retry_after
            else:
                del self.blocked[ip]
        
        # Clean old requests
        window_start = current_time - SecurityConfig.RATE_LIMIT_WINDOW
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > window_start
        ]
        
        # Check rate limit with burst allowance
        request_count = len(self.requests[ip])
        if request_count >= SecurityConfig.RATE_LIMIT_REQUESTS + SecurityConfig.RATE_LIMIT_BURST:
            # Block IP for suspicious activity
            self.blocked[ip] = current_time
            logger.warning(f"🚫 IP {ip} blocked for excessive requests")
            return False, "IP blocked for suspicious activity", 300
        
        if request_count >= SecurityConfig.RATE_LIMIT_REQUESTS:
            retry_after = int(SecurityConfig.RATE_LIMIT_WINDOW - (current_time - self.requests[ip][0]))
            return False, "Rate limit exceeded", max(retry_after, 1)
        
        # Add request
        self.requests[ip].append(current_time)
        return True, "Allowed", 0


# ==================== IP VALIDATOR ====================

class IPValidator:
    """Advanced IP validation with whitelist/blacklist support"""
    
    def is_ip_allowed(self, ip: str) -> Tuple[bool, str]:
        """Check if IP is allowed based on whitelist/blacklist"""
        try:
            ip_obj = ipaddress.ip_address(ip)
        except:
            return False, "Invalid IP address"
        
        # Check whitelist first (if enabled)
        if SecurityConfig.IP_WHITELIST_ENABLED:
            if ip not in SecurityConfig.IP_WHITELIST:
                return False, "IP not in whitelist"
        
        # Check blacklist
        if ip in SecurityConfig.IP_BLACKLIST:
            return False, "IP is blacklisted"
        
        return True, "IP allowed"
    
    @staticmethod
    def is_suspicious_user_agent(user_agent: str) -> Tuple[bool, str]:
        """Check if user agent is suspicious"""
        if not user_agent:
            return True, "Missing user agent"
        
        ua_lower = user_agent.lower()
        
        # ✅ ALLOW Render health check and common browsers
        for allowed in SecurityConfig.ALLOWED_USER_AGENTS:
            if allowed in ua_lower:
                return False, "OK"
        
        # Check for suspicious patterns
        suspicious_patterns = ["nikto", "sqlmap", "nmap", "nessus", "openvas"]
        for pattern in suspicious_patterns:
            if pattern in ua_lower:
                return True, f"Suspicious user agent: {pattern}"
        
        # Unknown user agent - allow but log
        logger.info(f"ℹ️ Unknown user agent: {user_agent}")
        return False, "OK"  # Allow unknown agents but don't block


# ==================== INJECTION DETECTOR ====================

class InjectionDetector:
    """Detect various injection attacks in requests"""
    
    @staticmethod
    def check_sql_injection(text: str) -> Tuple[bool, str]:
        """Check for SQL injection patterns"""
        if not text or not isinstance(text, str):
            return False, ""
        
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True, "SQL injection pattern detected"
        return False, ""
    
    @staticmethod
    def check_xss(text: str) -> Tuple[bool, str]:
        """Check for XSS attacks"""
        if not text or not isinstance(text, str):
            return False, ""
        
        for pattern in SecurityConfig.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True, "XSS pattern detected"
        return False, ""
    
    @staticmethod
    def check_path_traversal(path: str) -> Tuple[bool, str]:
        """Check for path traversal attempts"""
        if not path:
            return False, ""
        
        for pattern in SecurityConfig.PATH_TRAVERSAL_PATTERNS:
            if pattern in path.lower():
                return True, "Path traversal detected"
        return False, ""
    
    @staticmethod
    def check_command_injection(text: str) -> Tuple[bool, str]:
        """Check for command injection"""
        if not text or not isinstance(text, str):
            return False, ""
        
        for pattern in SecurityConfig.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text):
                return True, "Command injection detected"
        return False, ""
    
    @staticmethod
    def check_all(text: str) -> Tuple[bool, str]:
        """Check all injection types"""
        if not text or not isinstance(text, str):
            return False, ""
        
        # Skip checks for very short strings
        if len(text) < 10:
            return False, ""
        
        checks = [
            InjectionDetector.check_sql_injection,
            InjectionDetector.check_xss,
            InjectionDetector.check_command_injection,
        ]
        
        for check in checks:
            detected, reason = check(text)
            if detected:
                return True, reason
        return False, ""


# ==================== REQUEST LOGGER ====================

class RequestLogger:
    """Log suspicious requests for monitoring"""
    
    def __init__(self):
        self.suspicious_logs = []
        self.stats = defaultdict(int)
    
    def log_suspicious(self, ip: str, reason: str, path: str, method: str):
        """Log suspicious request"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "ip": ip,
            "reason": reason,
            "path": path,
            "method": method,
        }
        self.suspicious_logs.append(log_entry)
        
        # Update stats
        self.stats[ip] += 1
        self.stats[f"reason:{reason}"] += 1
        
        logger.warning(f"🚨 Suspicious request from {ip}: {reason}")


# ==================== GLOBAL INSTANCES ====================

_rate_limiter = AdvancedRateLimiter()
_ip_validator = IPValidator()
_detector = InjectionDetector()
_req_logger = RequestLogger()


# ==================== MAIN SECURITY MIDDLEWARE FUNCTION ====================

def add_security_middleware(app: FastAPI) -> FastAPI:
    """
    Add ultimate security middleware to FastAPI app
    This is the main function called from main.py
    """
    logger.info("=" * 60)
    logger.info("🔒 ADDING ENTERPRISE SECURITY MIDDLEWARE")
    logger.info("=" * 60)
    
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        """Main security dispatch function"""
        
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method
        
        # ✅ ALWAYS ALLOW these paths (Render health checks, docs, etc.)
        ALWAYS_ALLOW_PATHS = ["/", "/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        
        if path in ALWAYS_ALLOW_PATHS:
            response = await call_next(request)
            # Add security headers even to allowed paths
            for header, value in SecurityConfig.SECURITY_HEADERS.items():
                response.headers[header] = value
            return response
        
        # ✅ ALLOW Render internal requests
        if client_ip == "127.0.0.1" or "go-http-client" in user_agent or "render" in user_agent.lower():
            response = await call_next(request)
            for header, value in SecurityConfig.SECURITY_HEADERS.items():
                response.headers[header] = value
            return response
        
        # === 1. IP Validation ===
        allowed, reason = _ip_validator.is_ip_allowed(client_ip)
        if not allowed:
            _req_logger.log_suspicious(client_ip, reason, path, method)
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied",
                    "reason": reason,
                    "code": "IP_BLOCKED"
                }
            )
        
        # === 2. Rate Limiting ===
        allowed, reason, retry_after = _rate_limiter.check(client_ip)
        if not allowed:
            _req_logger.log_suspicious(client_ip, reason, path, method)
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": reason,
                    "code": "RATE_LIMITED",
                    "retry_after": retry_after
                }
            )
            response.headers["Retry-After"] = str(retry_after)
            return response
        
        # === 3. User Agent Validation ===
        suspicious, reason = _ip_validator.is_suspicious_user_agent(user_agent)
        if suspicious:
            _req_logger.log_suspicious(client_ip, reason, path, method)
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied",
                    "reason": reason,
                    "code": "SUSPICIOUS_UA"
                }
            )
        
        # === 4. Path Traversal Check ===
        detected, reason = _detector.check_path_traversal(path)
        if detected:
            _req_logger.log_suspicious(client_ip, reason, path, method)
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Invalid request path",
                    "reason": reason,
                    "code": "PATH_TRAVERSAL"
                }
            )
        
        # === 5. Request Body Inspection (for POST/PUT requests) ===
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes and len(body_bytes) < 10000:  # Only check small bodies
                    request._body = body_bytes
                    body_str = body_bytes.decode('utf-8', errors='ignore')
                    
                    detected, reason = _detector.check_all(body_str)
                    if detected:
                        _req_logger.log_suspicious(client_ip, reason, path, method)
                        return JSONResponse(
                            status_code=400,
                            content={
                                "detail": "Invalid request content",
                                "reason": reason,
                                "code": "INJECTION_DETECTED"
                            }
                        )
            except Exception as e:
                logger.error(f"Error inspecting request body: {e}")
        
        # === 6. Process the request ===
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request processing error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "code": "SERVER_ERROR"
                }
            )
        
        # === 7. Add security headers ===
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        return response
    
    # Log security features
    logger.info("✅ ENTERPRISE SECURITY MIDDLEWARE: ACTIVE")
    logger.info(f"├─ Rate Limiting: {SecurityConfig.RATE_LIMIT_REQUESTS} requests/{SecurityConfig.RATE_LIMIT_WINDOW}s + burst")
    logger.info("├─ IP Validation: Active")
    logger.info("├─ SQL Injection Protection: Active")
    logger.info("├─ XSS Protection: Active")
    logger.info("├─ Path Traversal Protection: Active")
    logger.info("├─ Command Injection Protection: Active")
    logger.info("├─ Suspicious User Agent Detection: Active (Render allowed)")
    logger.info("└─ Security Headers: Added")
    logger.info("=" * 60)
    
    return app
