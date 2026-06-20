"""
PAKCHAT ENTERPRISE SECURITY MIDDLEWARE - ENHANCED FIXED VERSION
- Fixed command injection false positives for chat messages
- Render health checks allowed
- Swagger UI /docs fixed
- Chat-friendly validation
"""

import logging
import time
import re
import json
import ipaddress
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

class SecurityConfig:
    """Security configuration - chat-optimized"""
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 200  # Increased for chat
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_BURST = 30  # extra requests for burst
    
    # IP Blacklist/Whitelist
    IP_BLACKLIST_ENABLED = True
    IP_WHITELIST_ENABLED = False
    IP_WHITELIST: Set[str] = set()
    IP_BLACKLIST: Set[str] = set()
    
    # ========== UPDATED PATTERNS - CHAT FRIENDLY ==========
    
    # SQL Injection - tightened, avoids chat false positives
    SQL_INJECTION_PATTERNS = [
        r"\b(union\s+all|union)\b\s+select\b",
        r"\b(select|insert|update|delete|drop|create|alter|truncate)\b\s+.*\b(from|into|set|table|database|values)\b",
        r"\b(information_schema|sys\.tables|pg_catalog|pg_tables|mysql\.db)\b",
        r"\b(xp_cmdshell|sp_executesql|sp_prepare|sp_execute)\b",
        r"\b(sleep|waitfor|benchmark)\b\s*\(",
        r"(;|\|)\s*(select|insert|update|delete|drop|create|alter)\b",
        r"(\b(or|and)\b\s+(['\"]?\w+['\"]?)\s*(=|<|>|in|like|between)\b\s*(['\"]?\w+['\"]?|true|false|null))",
        r"(\b(or|and)\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?\s*--)",
        r"(\b(or|and)\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?\s*#)",
    ]
    
    # XSS - updated for better detection
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript\s*:",
        r"onerror\s*=\s*['\"]",
        r"onload\s*=\s*['\"]",
        r"onclick\s*=\s*['\"]",
        r"onmouseover\s*=\s*['\"]",
        r"onfocus\s*=\s*['\"]",
        r"onblur\s*=\s*['\"]",
        r"onchange\s*=\s*['\"]",
        r"onsubmit\s*=\s*['\"]",
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
        r"<[^>]*on\w+\s*=.*?>",  # Any on* event handler
        r"<[^>]*src\s*=.*?javascript:.*?>",  # src with javascript
        r"<[^>]*href\s*=.*?javascript:.*?>",  # href with javascript
    ]
    
    # Path Traversal - unchanged
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"\.\.%2f",
        r"\.\.%5c",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"\.\.%252f",
        r"\.\.%255c",
    ]
    
    # ========== FIXED: Command Injection - Chat Friendly ==========
    # Only detect actual command injection, not chat symbols
    COMMAND_INJECTION_PATTERNS = [
        # Must have command after the separator
        r"[;&|`]\s*(ping|nslookup|curl|wget|nc|netcat|telnet|ssh|scp|rsync|whoami|id|uname|cat|ls|dir|echo|print|system|exec|passthru|shell_exec|popen|proc_open|pcntl_exec)",
        r"\$\s*\(\s*(ping|nslookup|curl|wget|nc|netcat|telnet|ssh|scp|rsync|whoami|id|uname|cat|ls|dir|echo|system|exec)",
        r"\$\{\s*(ping|nslookup|curl|wget|nc|netcat|telnet|ssh|scp|rsync|whoami|id|uname|cat|ls|dir|echo|system|exec)",
        r"`\s*(ping|nslookup|curl|wget|nc|netcat|telnet|ssh|scp|rsync|whoami|id|uname|cat|ls|dir|echo|system|exec)",
        r"(ping|nslookup|curl|wget|nc|netcat|telnet|ssh|scp|rsync|whoami|id|uname|cat|ls|dir)\s+[\w\-\.]+",  # Command with arguments
        r"(system|exec|passthru|shell_exec|popen|proc_open|pcntl_exec)\s*\(['\"]",
        r"(rm\s+-rf\s+[/\\])",  # Dangerous rm
        r"(dd\s+if=.*of=.*)",  # Dangerous dd
        r"(mkfs|format|fdisk)\s+[/\\]",  # Dangerous disk commands
        r"(chmod\s+777|chmod\s+[\d]{4})\s+",  # Dangerous chmod
        r"(wget|curl)\s+.*\|.*(sh|bash|python|perl)",  # Piped remote execution
    ]
    
    # Allowed User Agents
    ALLOWED_USER_AGENTS = {
        "go-http-client",
        "render",
        "mozilla",
        "chrome",
        "safari",
        "firefox",
        "edge",
        "postman",
        "curl",
        "python-requests",
        "axios",
        "fetch",
    }
    
    # Security Headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    # ========== CHAT-SPECIFIC ALLOWED PATTERNS ==========
    # These patterns look suspicious but are common in chat
    CHAT_ALLOWED_PATTERNS = [
        r"\|\|",  # OR operator in logic
        r"&&",    # AND operator in logic
        r"[&|]\s*[a-z]",  # Single & or | with letter
        r"`[^`]*`",  # Backticks for code formatting
        r"\$[a-zA-Z_]",  # Variables in code
        r"\$\([^)]*\)",  # Shell-like but common in code
        r"ping\s+[a-zA-Z]",  # Ping in chat context
        r"cat\s+[a-zA-Z]",  # Cat command in code
        r"ls\s+[a-zA-Z]",   # ls in code
        r"echo\s+[a-zA-Z]",  # echo in code
        r"rm\s+[a-zA-Z]",   # rm in code context
        r"curl\s+[a-zA-Z]",  # curl in chat
        r"wget\s+[a-zA-Z]",  # wget in chat
    ]


# ==================== RATE LIMITER ====================

class AdvancedRateLimiter:
    """Advanced rate limiting with sliding window and burst handling"""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blocked: Dict[str, float] = {}
        self.block_duration = 300
        
    def check(self, ip: str) -> Tuple[bool, str, int]:
        """Check if IP is allowed"""
        current_time = time.time()
        
        if ip in self.blocked:
            block_time = self.blocked[ip]
            if current_time - block_time < self.block_duration:
                retry_after = int(self.block_duration - (current_time - block_time))
                return False, "IP temporarily blocked", retry_after
            else:
                del self.blocked[ip]
        
        window_start = current_time - SecurityConfig.RATE_LIMIT_WINDOW
        self.requests[ip] = [t for t in self.requests[ip] if t > window_start]
        
        request_count = len(self.requests[ip])
        if request_count >= SecurityConfig.RATE_LIMIT_REQUESTS + SecurityConfig.RATE_LIMIT_BURST:
            self.blocked[ip] = current_time
            logger.warning(f"🚫 IP {ip} blocked for excessive requests")
            return False, "IP blocked for suspicious activity", 300
        
        if request_count >= SecurityConfig.RATE_LIMIT_REQUESTS:
            retry_after = int(SecurityConfig.RATE_LIMIT_WINDOW - (current_time - self.requests[ip][0]))
            return False, "Rate limit exceeded", max(retry_after, 1)
        
        self.requests[ip].append(current_time)
        return True, "Allowed", 0


# ==================== IP VALIDATOR ====================

class IPValidator:
    """Advanced IP validation"""
    
    @staticmethod
    def is_ip_allowed(ip: str) -> Tuple[bool, str]:
        try:
            ip_obj = ipaddress.ip_address(ip)
        except:
            return False, "Invalid IP address"
        
        if SecurityConfig.IP_WHITELIST_ENABLED:
            if ip not in SecurityConfig.IP_WHITELIST:
                return False, "IP not in whitelist"
        
        if ip in SecurityConfig.IP_BLACKLIST:
            return False, "IP is blacklisted"
        
        return True, "IP allowed"
    
    @staticmethod
    def is_suspicious_user_agent(user_agent: str) -> Tuple[bool, str]:
        if not user_agent:
            return True, "Missing user agent"
        
        ua_lower = user_agent.lower()
        
        # Allow all common user agents
        for allowed in SecurityConfig.ALLOWED_USER_AGENTS:
            if allowed in ua_lower:
                return False, "OK"
        
        # Check for scanner/attack tools
        suspicious = ["nikto", "sqlmap", "nmap", "nessus", "openvas", "metasploit", "wpscan"]
        for pattern in suspicious:
            if pattern in ua_lower:
                return True, f"Suspicious user agent: {pattern}"
        
        # Unknown user agent - allow but log
        logger.info(f"ℹ️ Unknown user agent: {user_agent}")
        return False, "OK"


# ==================== INJECTION DETECTOR ====================

class InjectionDetector:
    """Detect various injection attacks - Chat Optimized"""
    
    @staticmethod
    def _is_chat_allowed(text: str) -> bool:
        """Check if text matches allowed chat patterns"""
        for pattern in SecurityConfig.CHAT_ALLOWED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def check_sql_injection(text: str) -> Tuple[bool, str]:
        if not text or not isinstance(text, str):
            return False, ""
        
        # Skip if chat allowed
        if InjectionDetector._is_chat_allowed(text):
            return False, ""
        
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Extra verification: check if it's actually SQL
                if any(keyword in text.lower() for keyword in ['select', 'insert', 'delete', 'drop', 'union']):
                    return True, "SQL injection pattern detected"
        return False, ""
    
    @staticmethod
    def check_xss(text: str) -> Tuple[bool, str]:
        if not text or not isinstance(text, str):
            return False, ""
        
        # Skip if chat allowed
        if InjectionDetector._is_chat_allowed(text):
            return False, ""
        
        # Check for actual XSS patterns
        for pattern in SecurityConfig.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Verify it's not just code discussion
                if '<' in text and 'script' in text.lower():
                    return True, "XSS pattern detected"
        return False, ""
    
    @staticmethod
    def check_path_traversal(path: str) -> Tuple[bool, str]:
        if not path:
            return False, ""
        
        for pattern in SecurityConfig.PATH_TRAVERSAL_PATTERNS:
            if pattern in path.lower():
                return True, "Path traversal detected"
        return False, ""
    
    @staticmethod
    def check_command_injection(text: str) -> Tuple[bool, str]:
        """Fixed: Only detect actual command injection, not chat content"""
        if not text or not isinstance(text, str):
            return False, ""
        
        # Skip short strings
        if len(text) < 5:
            return False, ""
        
        # Skip if chat allowed patterns
        if InjectionDetector._is_chat_allowed(text):
            return False, ""
        
        # Check for command injection patterns
        for pattern in SecurityConfig.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Verify it's not just code discussion
                # If it has code-like formatting, it's probably legit
                if '`' in text and any(cmd in text.lower() for cmd in ['ping', 'curl', 'wget']):
                    # Only flag if it's clearly malicious
                    if 'http' in text.lower() and '|' in text:
                        return True, "Command injection detected"
                    # Don't flag single commands in chat
                    continue
                return True, "Command injection detected"
        return False, ""
    
    @staticmethod
    def extract_text_fields(payload: Any) -> List[str]:
        """Extract text fields from JSON payload"""
        texts: List[str] = []
        if isinstance(payload, str):
            texts.append(payload)
        elif isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, (str, dict, list)):
                    texts.extend(InjectionDetector.extract_text_fields(value))
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, (str, dict, list)):
                    texts.extend(InjectionDetector.extract_text_fields(item))
        return texts

    @staticmethod
    def check_all(text: str) -> Tuple[bool, str]:
        """Check all injection types"""
        if not text or not isinstance(text, str):
            return False, ""
        
        if len(text) < 10:
            return False, ""
        
        # Skip if chat allowed
        if InjectionDetector._is_chat_allowed(text):
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
    """Log suspicious requests"""
    
    def __init__(self):
        self.suspicious_logs = []
        self.stats = defaultdict(int)
    
    def log_suspicious(self, ip: str, reason: str, path: str, method: str):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "ip": ip,
            "reason": reason,
            "path": path,
            "method": method,
        }
        self.suspicious_logs.append(log_entry)
        self.stats[ip] += 1
        self.stats[f"reason:{reason}"] += 1
        logger.warning(f"🚨 Suspicious request from {ip}: {reason}")


# ==================== GLOBAL INSTANCES ====================

_rate_limiter = AdvancedRateLimiter()
_ip_validator = IPValidator()
_detector = InjectionDetector()
_req_logger = RequestLogger()


# ==================== MAIN SECURITY MIDDLEWARE ====================

def add_security_middleware(app: FastAPI) -> FastAPI:
    """
    Add enterprise security middleware to FastAPI app
    """
    logger.info("=" * 60)
    logger.info("🔒 ADDING ENTERPRISE SECURITY MIDDLEWARE (CHAT OPTIMIZED)")
    logger.info("=" * 60)
    
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        """Main security dispatch function"""
        
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method
        
        # ✅ ALWAYS ALLOW these paths
        ALWAYS_ALLOW_PATHS = ["/", "/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        
        if path in ALWAYS_ALLOW_PATHS:
            response = await call_next(request)
            if path in ["/docs", "/redoc", "/openapi.json"]:
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
            else:
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
                content={"detail": "Access denied", "reason": reason, "code": "IP_BLOCKED"}
            )
        
        # === 2. Rate Limiting ===
        allowed, reason, retry_after = _rate_limiter.check(client_ip)
        if not allowed:
            _req_logger.log_suspicious(client_ip, reason, path, method)
            response = JSONResponse(
                status_code=429,
                content={"detail": reason, "code": "RATE_LIMITED", "retry_after": retry_after}
            )
            response.headers["Retry-After"] = str(retry_after)
            return response
        
        # === 3. User Agent Validation ===
        suspicious, reason = _ip_validator.is_suspicious_user_agent(user_agent)
        if suspicious:
            _req_logger.log_suspicious(client_ip, reason, path, method)
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied", "reason": reason, "code": "SUSPICIOUS_UA"}
            )
        
        # === 4. Path Traversal Check ===
        detected, reason = _detector.check_path_traversal(path)
        if detected:
            _req_logger.log_suspicious(client_ip, reason, path, method)
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request path", "reason": reason, "code": "PATH_TRAVERSAL"}
            )
        
        # === 5. Request Body Inspection ===
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes and len(body_bytes) < 50000:  # Increased limit for chat
                    request._body = body_bytes
                    body_str = body_bytes.decode('utf-8', errors='ignore')
                    
                    try:
                        payload = json.loads(body_str)
                        text_fields = InjectionDetector.extract_text_fields(payload)
                    except json.JSONDecodeError:
                        text_fields = [body_str]
                    
                    for field_text in text_fields:
                        if len(field_text) < 10:
                            continue
                        detected, reason = _detector.check_all(field_text)
                        if detected:
                            # Log but don't block for minor issues
                            if "command injection" in reason.lower():
                                # Double-check: are there actual commands?
                                if any(cmd in field_text.lower() for cmd in ['ping', 'curl', 'wget', 'rm', 'cat', 'ls']):
                                    _req_logger.log_suspicious(client_ip, reason, path, method)
                                    return JSONResponse(
                                        status_code=400,
                                        content={"detail": "Invalid request content", "reason": reason, "code": "INJECTION_DETECTED"}
                                    )
                            else:
                                _req_logger.log_suspicious(client_ip, reason, path, method)
                                return JSONResponse(
                                    status_code=400,
                                    content={"detail": "Invalid request content", "reason": reason, "code": "INJECTION_DETECTED"}
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
                content={"detail": "Internal server error", "code": "SERVER_ERROR"}
            )
        
        # === 7. Security Headers ===
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        return response
    
    # Log security features
    logger.info("✅ ENTERPRISE SECURITY MIDDLEWARE: ACTIVE")
    logger.info(f"├─ Rate Limiting: {SecurityConfig.RATE_LIMIT_REQUESTS} requests/{SecurityConfig.RATE_LIMIT_WINDOW}s + burst")
    logger.info("├─ IP Validation: Active")
    logger.info("├─ SQL Injection Protection: Active (Chat-optimized)")
    logger.info("├─ XSS Protection: Active (Chat-optimized)")
    logger.info("├─ Path Traversal Protection: Active")
    logger.info("├─ Command Injection Protection: Active (Chat-optimized)")
    logger.info("├─ Suspicious User Agent Detection: Active (Render allowed)")
    logger.info("└─ Security Headers: Added")
    logger.info("=" * 60)
    
    return app