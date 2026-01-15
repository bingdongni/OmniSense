"""
OmniSense FastAPI Service
Production-ready API with JWT auth, rate limiting, and async task processing
"""

import os
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI, HTTPException, Depends, status, BackgroundTasks,
    Request, Header, Query
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import jwt
from passlib.context import CryptContext
from prometheus_client import Counter, Histogram, generate_latest
import redis.asyncio as aioredis
from celery import Celery
import logging
from loguru import logger

from omnisense.core import OmniSense
from omnisense.config import config
from omnisense.utils.logger import get_logger

# ==================== Configuration ====================

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# API Key Configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Celery configuration
celery_app = Celery(
    "omnisense_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "omnisense_requests_total",
    "Total request count",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "omnisense_request_duration_seconds",
    "Request latency",
    ["endpoint"]
)

# Logger
api_logger = get_logger("api")


# ==================== Lifespan Management ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    api_logger.info("Starting OmniSense API...")

    # Initialize Redis connection
    app.state.redis = await aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"),
        encoding="utf-8",
        decode_responses=True
    )

    # Initialize OmniSense
    app.state.omnisense = OmniSense()

    api_logger.info("OmniSense API started successfully")

    yield

    # Shutdown
    api_logger.info("Shutting down OmniSense API...")
    await app.state.omnisense.close()
    await app.state.redis.close()
    api_logger.info("OmniSense API shut down")


# ==================== FastAPI Application ====================

app = FastAPI(
    title="OmniSense API",
    description="全域数据智能洞察平台 - Production-ready API with authentication, rate limiting, and async tasks",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ==================== Middleware ====================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted hosts
if not config.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    )


# Request logging and metrics middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests and track metrics"""
    start_time = datetime.utcnow()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)

    # Log request
    api_logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
    )

    return response


# ==================== Pydantic Models ====================

class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserLogin(BaseModel):
    """User login credentials"""
    username: str
    password: str


class User(BaseModel):
    """User model"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False


class CollectionRequest(BaseModel):
    """Data collection request"""
    platform: str = Field(..., description="Platform name (douyin, xiaohongshu, etc.)")
    keyword: Optional[str] = Field(None, description="Search keyword")
    user_id: Optional[str] = Field(None, description="User ID")
    url: Optional[str] = Field(None, description="Direct URL")
    max_count: int = Field(100, ge=1, le=1000, description="Maximum items to collect")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter conditions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "douyin",
                "keyword": "AI编程",
                "max_count": 50
            }
        }
    )


class AnalysisRequest(BaseModel):
    """Analysis request"""
    data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(..., description="Data to analyze")
    agents: Optional[List[str]] = Field(
        None,
        description="AI agents to use (scout, analyst, ecommerce, academic, creator, report)"
    )
    analysis_types: Optional[List[str]] = Field(
        None,
        description="Analysis types (sentiment, clustering, trend, comparison)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [{"title": "Sample content", "description": "Sample description"}],
                "agents": ["analyst"],
                "analysis_types": ["sentiment", "clustering"]
            }
        }
    )


class ReportRequest(BaseModel):
    """Report generation request"""
    analysis: Dict[str, Any] = Field(..., description="Analysis results")
    format: str = Field("pdf", description="Report format (pdf, docx, html, md)")
    template: Optional[str] = Field(None, description="Report template")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis": {"sentiment": {"average_score": 0.8}},
                "format": "pdf"
            }
        }
    )


class TaskStatus(BaseModel):
    """Task status response"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PlatformInfo(BaseModel):
    """Platform information"""
    name: str
    display_name: str
    enabled: bool
    priority: int
    capabilities: List[str]


class StatsResponse(BaseModel):
    """Statistics response"""
    total_collections: int
    total_analyses: int
    active_tasks: int
    platforms: Dict[str, int]
    uptime: float


# ==================== Authentication ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    """Get current authenticated user (JWT or API Key)"""

    # Try API Key first
    if api_key:
        # Validate API key from Redis
        stored_user = await request.app.state.redis.get(f"apikey:{api_key}")
        if stored_user:
            return User(username=stored_user)

    # Try JWT token
    if credentials:
        try:
            payload = jwt.decode(
                credentials.credentials,
                SECRET_KEY,
                algorithms=[ALGORITHM]
            )
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            return User(username=username)
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ==================== Celery Tasks ====================

@celery_app.task(bind=True, name="tasks.collect_data")
def collect_data_task(self, task_id: str, params: dict):
    """Celery task for data collection"""
    try:
        # Update task status
        self.update_state(state="PROGRESS", meta={"progress": 0})

        # Initialize OmniSense
        omni = OmniSense()

        # Collect data
        self.update_state(state="PROGRESS", meta={"progress": 50})
        result = omni.collect(**params)

        self.update_state(state="PROGRESS", meta={"progress": 100})
        return {
            "success": True,
            "task_id": task_id,
            "result": result
        }

    except Exception as e:
        api_logger.error(f"Collection task failed: {e}")
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e)
        }


@celery_app.task(bind=True, name="tasks.analyze_data")
def analyze_data_task(self, task_id: str, params: dict):
    """Celery task for data analysis"""
    try:
        self.update_state(state="PROGRESS", meta={"progress": 0})

        omni = OmniSense()

        self.update_state(state="PROGRESS", meta={"progress": 50})
        result = omni.analyze(**params)

        self.update_state(state="PROGRESS", meta={"progress": 100})
        return {
            "success": True,
            "task_id": task_id,
            "result": result
        }

    except Exception as e:
        api_logger.error(f"Analysis task failed: {e}")
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e)
        }


@celery_app.task(bind=True, name="tasks.generate_report")
def generate_report_task(self, task_id: str, params: dict):
    """Celery task for report generation"""
    try:
        self.update_state(state="PROGRESS", meta={"progress": 0})

        omni = OmniSense()

        self.update_state(state="PROGRESS", meta={"progress": 50})
        report_path = omni.generate_report(**params)

        self.update_state(state="PROGRESS", meta={"progress": 100})
        return {
            "success": True,
            "task_id": task_id,
            "result": {"report_path": report_path}
        }

    except Exception as e:
        api_logger.error(f"Report generation task failed: {e}")
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e)
        }


# ==================== Helper Functions ====================

async def store_task_info(redis_client, task_id: str, info: dict):
    """Store task information in Redis"""
    await redis_client.hset(f"task:{task_id}", mapping=info)
    await redis_client.expire(f"task:{task_id}", 86400)  # 24 hours


async def get_task_info(redis_client, task_id: str) -> Optional[dict]:
    """Get task information from Redis"""
    data = await redis_client.hgetall(f"task:{task_id}")
    return data if data else None


# ==================== API Endpoints ====================

@app.get("/", response_model=APIResponse, tags=["General"])
async def root():
    """Root endpoint"""
    return APIResponse(
        success=True,
        message="OmniSense API - 全域数据智能洞察平台",
        data={
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }
    )


@app.get("/health", tags=["General"])
async def health_check(request: Request):
    """Health check endpoint"""
    try:
        # Check Redis connection
        await request.app.state.redis.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": redis_status,
        "celery": "healthy" if celery_app.control.inspect().active() else "unknown"
    }


@app.get("/metrics", tags=["General"])
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()


# ==================== Authentication Endpoints ====================

@app.post("/api/v1/auth/login", response_model=Token, tags=["Authentication"])
@limiter.limit("5/minute")
async def login(request: Request, user_login: UserLogin):
    """
    Login with username and password to get JWT token

    **Note**: In production, validate against your user database.
    This is a simplified example.
    """
    # Mock user validation (replace with real database check)
    if user_login.username == "admin" and user_login.password == "admin":
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_login.username},
            expires_delta=access_token_expires
        )
        return Token(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )


@app.post("/api/v1/auth/apikey", tags=["Authentication"])
@limiter.limit("3/minute")
async def create_api_key(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new API key for authenticated user
    """
    api_key = secrets.token_urlsafe(32)

    # Store API key in Redis
    await request.app.state.redis.set(
        f"apikey:{api_key}",
        current_user.username,
        ex=86400 * 30  # 30 days
    )

    return APIResponse(
        success=True,
        message="API key created successfully",
        data={
            "api_key": api_key,
            "expires_in_days": 30,
            "usage": f"Add header: {API_KEY_NAME}: {api_key}"
        }
    )


# ==================== Data Collection Endpoints ====================

@app.post("/api/v1/collect", tags=["Collection"], status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def start_collection(
    request: Request,
    collection_req: CollectionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Start data collection task

    **Rate Limit**: 10 requests per minute per user

    **Example**:
    ```json
    {
        "platform": "douyin",
        "keyword": "AI编程",
        "max_count": 50
    }
    ```
    """
    # Generate task ID
    task_id = str(uuid.uuid4())

    # Create Celery task
    task = collect_data_task.apply_async(
        args=[task_id, collection_req.model_dump()],
        task_id=task_id
    )

    # Store task info
    await store_task_info(
        request.app.state.redis,
        task_id,
        {
            "type": "collection",
            "status": "pending",
            "user": current_user.username,
            "created_at": datetime.utcnow().isoformat(),
            "params": str(collection_req.model_dump())
        }
    )

    api_logger.info(f"Collection task started: {task_id} by {current_user.username}")

    return APIResponse(
        success=True,
        message="Collection task started",
        data={
            "task_id": task_id,
            "status_url": f"/api/v1/collect/{task_id}"
        }
    )


@app.get("/api/v1/collect/{task_id}", response_model=TaskStatus, tags=["Collection"])
@limiter.limit("30/minute")
async def get_collection_status(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get collection task status and results

    **Task States**:
    - `PENDING`: Task is waiting to be executed
    - `PROGRESS`: Task is currently running
    - `SUCCESS`: Task completed successfully
    - `FAILURE`: Task failed with error
    """
    # Get task info from Celery
    task = celery_app.AsyncResult(task_id)

    # Get stored info
    task_info = await get_task_info(request.app.state.redis, task_id)

    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Build response
    response_data = {
        "task_id": task_id,
        "status": task.state.lower(),
        "created_at": datetime.fromisoformat(task_info.get("created_at")),
        "updated_at": datetime.utcnow()
    }

    # Add progress and result based on state
    if task.state == "PROGRESS":
        response_data["progress"] = task.info.get("progress", 0)
    elif task.state == "SUCCESS":
        response_data["progress"] = 100
        response_data["result"] = task.result.get("result")
    elif task.state == "FAILURE":
        response_data["error"] = str(task.info)

    return TaskStatus(**response_data)


# ==================== Analysis Endpoints ====================

@app.post("/api/v1/analyze", tags=["Analysis"], status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def start_analysis(
    request: Request,
    analysis_req: AnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Start data analysis task

    **Rate Limit**: 10 requests per minute per user

    **Available Agents**:
    - `scout`: Data reconnaissance and exploration
    - `analyst`: Content and trend analysis
    - `ecommerce`: E-commerce insights
    - `academic`: Academic research analysis
    - `creator`: Content creator insights
    - `report`: Report generation

    **Analysis Types**:
    - `sentiment`: Sentiment analysis
    - `clustering`: Topic clustering
    - `trend`: Trend analysis
    - `comparison`: Comparative analysis
    """
    task_id = str(uuid.uuid4())

    task = analyze_data_task.apply_async(
        args=[task_id, analysis_req.model_dump()],
        task_id=task_id
    )

    await store_task_info(
        request.app.state.redis,
        task_id,
        {
            "type": "analysis",
            "status": "pending",
            "user": current_user.username,
            "created_at": datetime.utcnow().isoformat()
        }
    )

    api_logger.info(f"Analysis task started: {task_id} by {current_user.username}")

    return APIResponse(
        success=True,
        message="Analysis task started",
        data={
            "task_id": task_id,
            "status_url": f"/api/v1/analyze/{task_id}"
        }
    )


@app.get("/api/v1/analyze/{task_id}", response_model=TaskStatus, tags=["Analysis"])
@limiter.limit("30/minute")
async def get_analysis_status(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get analysis task status and results"""
    task = celery_app.AsyncResult(task_id)
    task_info = await get_task_info(request.app.state.redis, task_id)

    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    response_data = {
        "task_id": task_id,
        "status": task.state.lower(),
        "created_at": datetime.fromisoformat(task_info.get("created_at")),
        "updated_at": datetime.utcnow()
    }

    if task.state == "PROGRESS":
        response_data["progress"] = task.info.get("progress", 0)
    elif task.state == "SUCCESS":
        response_data["progress"] = 100
        response_data["result"] = task.result.get("result")
    elif task.state == "FAILURE":
        response_data["error"] = str(task.info)

    return TaskStatus(**response_data)


# ==================== Report Endpoints ====================

@app.post("/api/v1/report", tags=["Report"], status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
async def generate_report(
    request: Request,
    report_req: ReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate report from analysis results

    **Rate Limit**: 5 requests per minute per user

    **Supported Formats**:
    - `pdf`: PDF document
    - `docx`: Microsoft Word document
    - `html`: HTML document
    - `md`: Markdown document
    """
    task_id = str(uuid.uuid4())

    task = generate_report_task.apply_async(
        args=[task_id, report_req.model_dump()],
        task_id=task_id
    )

    await store_task_info(
        request.app.state.redis,
        task_id,
        {
            "type": "report",
            "status": "pending",
            "user": current_user.username,
            "created_at": datetime.utcnow().isoformat()
        }
    )

    api_logger.info(f"Report task started: {task_id} by {current_user.username}")

    return APIResponse(
        success=True,
        message="Report generation started",
        data={
            "task_id": task_id,
            "status_url": f"/api/v1/report/{task_id}"
        }
    )


@app.get("/api/v1/report/{task_id}", response_model=TaskStatus, tags=["Report"])
@limiter.limit("30/minute")
async def get_report_status(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get report generation status"""
    task = celery_app.AsyncResult(task_id)
    task_info = await get_task_info(request.app.state.redis, task_id)

    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    response_data = {
        "task_id": task_id,
        "status": task.state.lower(),
        "created_at": datetime.fromisoformat(task_info.get("created_at")),
        "updated_at": datetime.utcnow()
    }

    if task.state == "PROGRESS":
        response_data["progress"] = task.info.get("progress", 0)
    elif task.state == "SUCCESS":
        response_data["progress"] = 100
        response_data["result"] = task.result.get("result")
    elif task.state == "FAILURE":
        response_data["error"] = str(task.info)

    return TaskStatus(**response_data)


# ==================== Platform Endpoints ====================

@app.get("/api/v1/platforms", response_model=List[PlatformInfo], tags=["Platforms"])
@limiter.limit("30/minute")
async def list_platforms(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    List all supported platforms

    Returns information about all available platforms including:
    - Platform name and display name
    - Whether platform is enabled
    - Platform priority
    - Available capabilities
    """
    omni = request.app.state.omnisense
    platforms = omni.get_supported_platforms()

    result = []
    for platform in platforms:
        info = omni.get_platform_info(platform)
        platform_config = config.get_platform_config(platform)

        result.append(PlatformInfo(
            name=platform,
            display_name=info.get("display_name", platform),
            enabled=platform_config.get("enabled", True),
            priority=platform_config.get("priority", 5),
            capabilities=info.get("capabilities", ["search", "user_profile", "posts"])
        ))

    return result


@app.get("/api/v1/platforms/{platform}", response_model=PlatformInfo, tags=["Platforms"])
@limiter.limit("30/minute")
async def get_platform_info(
    request: Request,
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific platform"""
    omni = request.app.state.omnisense

    try:
        info = omni.get_platform_info(platform)
        platform_config = config.get_platform_config(platform)

        return PlatformInfo(
            name=platform,
            display_name=info.get("display_name", platform),
            enabled=platform_config.get("enabled", True),
            priority=platform_config.get("priority", 5),
            capabilities=info.get("capabilities", ["search", "user_profile", "posts"])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform '{platform}' not found"
        )


# ==================== Statistics Endpoints ====================

@app.get("/api/v1/stats", response_model=StatsResponse, tags=["Statistics"])
@limiter.limit("30/minute")
async def get_statistics(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get system statistics

    Returns:
    - Total collections performed
    - Total analyses performed
    - Active background tasks
    - Platform usage statistics
    - System uptime
    """
    redis_client = request.app.state.redis

    # Get task counts
    task_keys = await redis_client.keys("task:*")

    collections = 0
    analyses = 0
    active_tasks = 0
    platform_stats = {}

    for key in task_keys:
        task_info = await redis_client.hgetall(key)
        task_type = task_info.get("type", "")
        task_status = task_info.get("status", "")

        if task_type == "collection":
            collections += 1
        elif task_type == "analysis":
            analyses += 1

        if task_status in ["pending", "running"]:
            active_tasks += 1

    # Get Celery stats
    inspect = celery_app.control.inspect()
    active_celery = inspect.active()
    if active_celery:
        active_tasks = sum(len(tasks) for tasks in active_celery.values())

    return StatsResponse(
        total_collections=collections,
        total_analyses=analyses,
        active_tasks=active_tasks,
        platforms=platform_stats,
        uptime=0.0  # TODO: Track actual uptime
    )


# ==================== Task Management Endpoints ====================

@app.delete("/api/v1/tasks/{task_id}", tags=["Tasks"])
@limiter.limit("10/minute")
async def cancel_task(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a running task"""
    task = celery_app.AsyncResult(task_id)

    if task.state in ["PENDING", "PROGRESS"]:
        task.revoke(terminate=True)

        return APIResponse(
            success=True,
            message=f"Task {task_id} cancelled",
            data={"task_id": task_id}
        )
    else:
        return APIResponse(
            success=False,
            message=f"Task {task_id} cannot be cancelled (status: {task.state})",
            data={"task_id": task_id, "status": task.state}
        )


@app.get("/api/v1/tasks", tags=["Tasks"])
@limiter.limit("30/minute")
async def list_tasks(
    request: Request,
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """List all tasks for current user"""
    redis_client = request.app.state.redis

    # Get all task keys
    task_keys = await redis_client.keys("task:*")

    tasks = []
    for key in task_keys[:limit]:
        task_info = await redis_client.hgetall(key)

        # Filter by user
        if task_info.get("user") != current_user.username:
            continue

        # Filter by type
        if task_type and task_info.get("type") != task_type:
            continue

        # Filter by status
        if status and task_info.get("status") != status:
            continue

        task_id = key.split(":")[-1]
        tasks.append({
            "task_id": task_id,
            "type": task_info.get("type"),
            "status": task_info.get("status"),
            "created_at": task_info.get("created_at")
        })

    return APIResponse(
        success=True,
        message=f"Found {len(tasks)} tasks",
        data={"tasks": tasks, "total": len(tasks)}
    )


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    api_logger.error(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if config.debug else "An error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=config.debug,
        workers=int(os.getenv("API_WORKERS", 4)),
        log_level=config.log_level.lower(),
        access_log=True
    )
