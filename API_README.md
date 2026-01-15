# OmniSense API Documentation

Complete production-ready FastAPI service for OmniSense - 全域数据智能洞察平台

## Features

### 1. Authentication & Authorization
- **JWT Token Authentication**: Secure token-based authentication
- **API Key Support**: Alternative authentication via API keys
- **Rate Limiting**: Per-user rate limiting to prevent abuse

### 2. Core Endpoints

#### Collection
- `POST /api/v1/collect` - Start data collection from platforms
- `GET /api/v1/collect/{task_id}` - Get collection status and results

#### Analysis
- `POST /api/v1/analyze` - Run AI-powered data analysis
- `GET /api/v1/analyze/{task_id}` - Get analysis results

#### Reporting
- `POST /api/v1/report` - Generate reports (PDF, DOCX, HTML, MD)
- `GET /api/v1/report/{task_id}` - Get report generation status

#### Platforms
- `GET /api/v1/platforms` - List all supported platforms
- `GET /api/v1/platforms/{platform}` - Get platform details

#### Statistics
- `GET /api/v1/stats` - System statistics and metrics

### 3. Background Task Processing
- **Celery Integration**: Async task queue with Redis backend
- **Progress Tracking**: Real-time task progress updates
- **Task Management**: Cancel, list, and monitor tasks
- **Flower Dashboard**: Web UI for Celery monitoring (port 5555)

### 4. Monitoring & Observability
- **Prometheus Metrics**: `/metrics` endpoint for monitoring
- **Health Checks**: `/health` endpoint for service status
- **Request Logging**: Detailed logging with Loguru
- **Grafana Dashboards**: Pre-configured visualization

## Quick Start

### 1. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Start Celery worker
celery -A api.celery_app worker --loglevel=info

# Start API server
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 2. Docker Deployment

```bash
# Start all services
docker-compose -f docker-compose.api.yml up -d

# View logs
docker-compose -f docker-compose.api.yml logs -f

# Stop all services
docker-compose -f docker-compose.api.yml down
```

### 3. Production Deployment

```bash
# Build for production
docker-compose -f docker-compose.api.yml build

# Start in production mode
docker-compose -f docker-compose.api.yml up -d

# Scale workers
docker-compose -f docker-compose.api.yml up -d --scale celery_worker=4
```

## API Usage Examples

### 1. Authentication

#### Login to get JWT token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Generate API Key

```bash
curl -X POST "http://localhost:8000/api/v1/auth/apikey" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. Data Collection

#### Start collection task

```bash
curl -X POST "http://localhost:8000/api/v1/collect" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "douyin",
    "keyword": "AI编程",
    "max_count": 50
  }'
```

Response:
```json
{
  "success": true,
  "message": "Collection task started",
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status_url": "/api/v1/collect/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Check collection status

```bash
curl -X GET "http://localhost:8000/api/v1/collect/{task_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "success",
  "progress": 100,
  "result": {
    "platform": "douyin",
    "count": 50,
    "data": [...]
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:32:00Z"
}
```

### 3. Data Analysis

#### Start analysis task

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"title": "Sample video", "description": "Great content"}
    ],
    "agents": ["analyst", "creator"],
    "analysis_types": ["sentiment", "clustering"]
  }'
```

### 4. Report Generation

```bash
curl -X POST "http://localhost:8000/api/v1/report" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis": {
      "sentiment": {"average_score": 0.85},
      "clusters": {"n_clusters": 5}
    },
    "format": "pdf"
  }'
```

### 5. Platform Information

#### List all platforms

```bash
curl -X GET "http://localhost:8000/api/v1/platforms" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Get specific platform info

```bash
curl -X GET "http://localhost:8000/api/v1/platforms/douyin" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. Using API Key Authentication

```bash
curl -X GET "http://localhost:8000/api/v1/stats" \
  -H "X-API-Key: YOUR_API_KEY"
```

## Rate Limits

| Endpoint | Rate Limit |
|----------|-----------|
| `/api/v1/auth/login` | 5/minute |
| `/api/v1/auth/apikey` | 3/minute |
| `/api/v1/collect` | 10/minute |
| `/api/v1/analyze` | 10/minute |
| `/api/v1/report` | 5/minute |
| `/api/v1/platforms` | 30/minute |
| `/api/v1/stats` | 30/minute |
| All GET status endpoints | 30/minute |

## Available Platforms

- **Social Media**: douyin, xiaohongshu, weibo, bilibili, kuaishou, tiktok, youtube, twitter, instagram, facebook
- **Chinese Platforms**: wechat_mp, zhihu, douban, baidu_tieba, toutiao
- **E-commerce**: amazon, taobao, tmall, jd, pinduoduo
- **Reviews**: meituan, dianping
- **Search**: baidu, google
- **Academic**: google_scholar, cnki
- **Tech**: github, csdn, stackoverflow

## Analysis Agents

- **scout**: Data reconnaissance and exploration
- **analyst**: Content and trend analysis
- **ecommerce**: E-commerce insights and metrics
- **academic**: Academic research analysis
- **creator**: Content creator insights
- **report**: Automated report generation

## Analysis Types

- **sentiment**: Sentiment analysis with polarity scoring
- **clustering**: Topic clustering and categorization
- **trend**: Trend analysis and predictions
- **comparison**: Comparative analysis across platforms

## Monitoring

### Access Points

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Flower (Celery)**: http://localhost:5555
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "redis": "healthy",
  "celery": "healthy"
}
```

## Error Handling

All errors follow this format:

```json
{
  "success": false,
  "message": "Error description",
  "error": "Detailed error (only in debug mode)",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

- `200` - Success
- `202` - Accepted (async task started)
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

## Security Best Practices

1. **Change Secret Key**: Always set a strong `SECRET_KEY` in production
2. **Use HTTPS**: Enable SSL/TLS for production deployments
3. **Restrict CORS**: Set specific `CORS_ORIGINS` instead of `*`
4. **API Key Rotation**: Regularly rotate API keys
5. **Rate Limiting**: Keep default rate limits or adjust based on your needs
6. **Trusted Hosts**: Configure `ALLOWED_HOSTS` for production

## Performance Tuning

### API Workers

```bash
# Adjust workers based on CPU cores
uvicorn api:app --workers $((2 * $(nproc) + 1))
```

### Celery Workers

```bash
# Scale workers
celery -A api.celery_app worker --concurrency=8

# Or with autoscaling
celery -A api.celery_app worker --autoscale=10,3
```

### Redis Configuration

```bash
# Increase max memory
redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

## Troubleshooting

### Connection Errors

```bash
# Check Redis connection
redis-cli ping

# Check Celery workers
celery -A api.celery_app inspect active

# Check API health
curl http://localhost:8000/health
```

### Task Issues

```bash
# Purge all tasks
celery -A api.celery_app purge

# Inspect registered tasks
celery -A api.celery_app inspect registered
```

### Logs

```bash
# API logs
tail -f logs/omnisense.log

# Docker logs
docker-compose -f docker-compose.api.yml logs -f api

# Celery logs
docker-compose -f docker-compose.api.yml logs -f celery_worker
```

## Environment Variables

See `.env.example` for all available configuration options.

## Support

- GitHub Issues: [Report bugs or request features]
- Documentation: See `/docs` endpoint
- API Reference: See `/redoc` endpoint

## License

[Your License Here]
