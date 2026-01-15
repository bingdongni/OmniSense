# OmniSense API Documentation

Complete REST API reference for OmniSense platform. This API provides programmatic access to all OmniSense features including data collection, analysis, and report generation.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limits](#rate-limits)
- [Endpoints](#endpoints)
- [Request Examples](#request-examples)
- [Error Handling](#error-handling)
- [Webhooks](#webhooks)
- [SDKs](#sdks)

## Overview

**Base URL**: `http://localhost:8000` (default)

**API Version**: v1

**Content-Type**: `application/json`

**Response Format**: JSON

## Authentication

OmniSense API supports two authentication methods:

### 1. JWT Token Authentication

Obtain a JWT token by logging in, then include it in the Authorization header.

**Login Request:**

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Using the Token:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/platforms
```

### 2. API Key Authentication

Generate an API key for long-term authentication.

**Generate API Key:**

```bash
POST /api/v1/auth/apikey
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response:**

```json
{
  "success": true,
  "message": "API key created successfully",
  "data": {
    "api_key": "omnisense_xxxxxxxxxxxxxx",
    "expires_in_days": 30,
    "usage": "Add header: X-API-Key: omnisense_xxxxxxxxxxxxxx"
  }
}
```

**Using API Key:**

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8000/api/v1/platforms
```

## Rate Limits

Rate limits apply per user/API key:

| Endpoint Category | Rate Limit |
|------------------|------------|
| Authentication | 5 requests/minute |
| Collection | 10 requests/minute |
| Analysis | 10 requests/minute |
| Report Generation | 5 requests/minute |
| Status Check | 30 requests/minute |
| Platform Info | 30 requests/minute |
| Statistics | 30 requests/minute |

**Rate Limit Headers:**

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642435200
```

**Rate Limit Exceeded Response:**

```json
{
  "success": false,
  "message": "Rate limit exceeded",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Endpoints

### Authentication Endpoints

#### POST /api/v1/auth/login

Login with username and password.

**Request Body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200:**

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST /api/v1/auth/apikey

Generate a new API key (requires JWT token).

**Response 200:**

```json
{
  "success": true,
  "message": "API key created successfully",
  "data": {
    "api_key": "string",
    "expires_in_days": 30
  }
}
```

### Data Collection Endpoints

#### POST /api/v1/collect

Start a data collection task.

**Request Body:**

```json
{
  "platform": "string",          // Required: Platform name
  "keyword": "string",            // Optional: Search keyword
  "user_id": "string",            // Optional: User ID
  "url": "string",                // Optional: Direct URL
  "max_count": 100,               // Optional: Max items (1-1000)
  "filters": {                    // Optional: Filter conditions
    "min_likes": 1000,
    "min_views": 10000,
    "min_date": "2024-01-01",
    "max_date": "2024-12-31"
  }
}
```

**Example:**

```json
{
  "platform": "douyin",
  "keyword": "AI编程",
  "max_count": 50
}
```

**Response 202:**

```json
{
  "success": true,
  "message": "Collection task started",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status_url": "/api/v1/collect/550e8400-e29b-41d4-a716-446655440000"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### GET /api/v1/collect/{task_id}

Get collection task status and results.

**Path Parameters:**

- `task_id` (string, required): Task ID

**Response 200:**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "progress": 100,
  "result": {
    "platform": "douyin",
    "count": 50,
    "data": [
      {
        "content_id": "7123456789012345678",
        "platform": "douyin",
        "title": "AI编程教程",
        "description": "详细的AI编程教程...",
        "author": {
          "nickname": "编程大师",
          "user_id": "MS4wLjABAAAA..."
        },
        "like_count": 12500,
        "comment_count": 380,
        "share_count": 560,
        "view_count": 125000,
        "publish_time": "2024-01-15T08:30:00Z",
        "url": "https://www.douyin.com/video/7123456789012345678"
      }
    ],
    "meta": {
      "keyword": "AI编程",
      "filters": null
    }
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

**Task Status Values:**

- `pending`: Task waiting to be executed
- `progress`: Task currently running
- `success`: Task completed successfully
- `failure`: Task failed

### Data Analysis Endpoints

#### POST /api/v1/analyze

Start a data analysis task.

**Request Body:**

```json
{
  "data": {},                     // Required: Data to analyze
  "agents": ["string"],           // Optional: AI agents to use
  "analysis_types": ["string"]    // Optional: Analysis types
}
```

**Available Agents:**

- `scout`: Data reconnaissance and exploration
- `analyst`: Content and trend analysis
- `ecommerce`: E-commerce insights
- `academic`: Academic research analysis
- `creator`: Content creator insights
- `report`: Report generation

**Available Analysis Types:**

- `sentiment`: Sentiment analysis
- `clustering`: Topic clustering
- `trend`: Trend analysis
- `comparison`: Comparative analysis

**Example:**

```json
{
  "data": [
    {"title": "产品评测", "description": "这个产品非常好用"},
    {"title": "使用体验", "description": "质量一般，价格偏高"}
  ],
  "agents": ["analyst"],
  "analysis_types": ["sentiment", "clustering"]
}
```

**Response 202:**

```json
{
  "success": true,
  "message": "Analysis task started",
  "data": {
    "task_id": "660e8400-e29b-41d4-a716-446655440001",
    "status_url": "/api/v1/analyze/660e8400-e29b-41d4-a716-446655440001"
  },
  "timestamp": "2024-01-15T10:40:00Z"
}
```

#### GET /api/v1/analyze/{task_id}

Get analysis task status and results.

**Response 200:**

```json
{
  "task_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "success",
  "progress": 100,
  "result": {
    "agents": {
      "analyst": {
        "sentiment": {
          "average_score": 0.65,
          "positive": 1,
          "negative": 1,
          "neutral": 0,
          "distribution": {
            "very_positive": 0,
            "positive": 1,
            "neutral": 0,
            "negative": 1,
            "very_negative": 0
          }
        }
      }
    },
    "analysis": {
      "sentiment": {
        "average_score": 0.65,
        "details": [...]
      },
      "clustering": {
        "num_clusters": 2,
        "clusters": [
          {
            "cluster_id": 0,
            "label": "positive_reviews",
            "count": 1,
            "keywords": ["好用", "质量好"]
          },
          {
            "cluster_id": 1,
            "label": "critical_reviews",
            "count": 1,
            "keywords": ["价格高", "一般"]
          }
        ]
      }
    }
  },
  "created_at": "2024-01-15T10:40:00Z",
  "updated_at": "2024-01-15T10:42:00Z"
}
```

### Report Generation Endpoints

#### POST /api/v1/report

Generate a report from analysis results.

**Request Body:**

```json
{
  "analysis": {},                 // Required: Analysis results
  "format": "pdf",                // Required: Report format
  "template": "string"            // Optional: Template name
}
```

**Supported Formats:**

- `pdf`: PDF document
- `docx`: Microsoft Word document
- `html`: HTML document
- `md`: Markdown document

**Example:**

```json
{
  "analysis": {
    "sentiment": {
      "average_score": 0.75
    }
  },
  "format": "pdf"
}
```

**Response 202:**

```json
{
  "success": true,
  "message": "Report generation started",
  "data": {
    "task_id": "770e8400-e29b-41d4-a716-446655440002",
    "status_url": "/api/v1/report/770e8400-e29b-41d4-a716-446655440002"
  },
  "timestamp": "2024-01-15T10:45:00Z"
}
```

#### GET /api/v1/report/{task_id}

Get report generation status.

**Response 200:**

```json
{
  "task_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "success",
  "progress": 100,
  "result": {
    "report_path": "/app/reports/report_20240115_104500.pdf"
  },
  "created_at": "2024-01-15T10:45:00Z",
  "updated_at": "2024-01-15T10:46:00Z"
}
```

### Platform Endpoints

#### GET /api/v1/platforms

List all supported platforms.

**Response 200:**

```json
[
  {
    "name": "douyin",
    "display_name": "抖音 (Douyin)",
    "enabled": true,
    "priority": 10,
    "capabilities": ["search", "user_profile", "posts", "comments"]
  },
  {
    "name": "xiaohongshu",
    "display_name": "小红书 (RedNote)",
    "enabled": true,
    "priority": 10,
    "capabilities": ["search", "user_profile", "posts", "comments"]
  }
]
```

#### GET /api/v1/platforms/{platform}

Get detailed information about a specific platform.

**Path Parameters:**

- `platform` (string, required): Platform name

**Response 200:**

```json
{
  "name": "douyin",
  "display_name": "抖音 (Douyin)",
  "enabled": true,
  "priority": 10,
  "capabilities": [
    "search",
    "user_profile",
    "user_posts",
    "post_detail",
    "comments",
    "topic_videos"
  ]
}
```

### Task Management Endpoints

#### GET /api/v1/tasks

List all tasks for the current user.

**Query Parameters:**

- `task_type` (string, optional): Filter by task type (collection, analysis, report)
- `status` (string, optional): Filter by status (pending, progress, success, failure)
- `limit` (integer, optional): Maximum number of tasks (1-100, default: 50)

**Response 200:**

```json
{
  "success": true,
  "message": "Found 3 tasks",
  "data": {
    "tasks": [
      {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "collection",
        "status": "success",
        "created_at": "2024-01-15T10:30:00Z"
      },
      {
        "task_id": "660e8400-e29b-41d4-a716-446655440001",
        "type": "analysis",
        "status": "progress",
        "created_at": "2024-01-15T10:40:00Z"
      }
    ],
    "total": 2
  }
}
```

#### DELETE /api/v1/tasks/{task_id}

Cancel a running task.

**Response 200:**

```json
{
  "success": true,
  "message": "Task 550e8400-e29b-41d4-a716-446655440000 cancelled",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Statistics Endpoints

#### GET /api/v1/stats

Get system statistics.

**Response 200:**

```json
{
  "total_collections": 150,
  "total_analyses": 85,
  "active_tasks": 3,
  "platforms": {
    "douyin": 45,
    "xiaohongshu": 38,
    "weibo": 32
  },
  "uptime": 86400.5
}
```

### General Endpoints

#### GET /

Root endpoint with API information.

**Response 200:**

```json
{
  "success": true,
  "message": "OmniSense API - 全域数据智能洞察平台",
  "data": {
    "version": "1.0.0",
    "docs": "/docs",
    "health": "/health"
  }
}
```

#### GET /health

Health check endpoint.

**Response 200:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "redis": "healthy",
  "celery": "healthy"
}
```

#### GET /metrics

Prometheus metrics endpoint.

**Response 200:** (Prometheus format)

```
# HELP omnisense_requests_total Total request count
# TYPE omnisense_requests_total counter
omnisense_requests_total{method="GET",endpoint="/api/v1/platforms",status="200"} 150
```

## Request Examples

### Python

```python
import requests

# Login
response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'username': 'admin', 'password': 'admin'}
)
token = response.json()['access_token']

# Headers with authentication
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Start collection
collection_response = requests.post(
    'http://localhost:8000/api/v1/collect',
    headers=headers,
    json={
        'platform': 'douyin',
        'keyword': 'AI编程',
        'max_count': 50
    }
)

task_id = collection_response.json()['data']['task_id']
print(f'Task ID: {task_id}')

# Check status
import time
while True:
    status_response = requests.get(
        f'http://localhost:8000/api/v1/collect/{task_id}',
        headers=headers
    )
    status_data = status_response.json()

    if status_data['status'] == 'success':
        print('Collection completed!')
        print(f"Collected {status_data['result']['count']} items")
        break
    elif status_data['status'] == 'failure':
        print(f"Collection failed: {status_data.get('error')}")
        break

    print(f"Progress: {status_data.get('progress', 0)}%")
    time.sleep(5)
```

### cURL

```bash
# Login
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}' \
  | jq -r '.access_token')

# Start collection
TASK_ID=$(curl -X POST "http://localhost:8000/api/v1/collect" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "douyin",
    "keyword": "AI编程",
    "max_count": 50
  }' | jq -r '.data.task_id')

echo "Task ID: $TASK_ID"

# Check status
curl "http://localhost:8000/api/v1/collect/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### JavaScript (fetch)

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin'
  })
});

const { access_token } = await loginResponse.json();

// Start collection
const collectionResponse = await fetch('http://localhost:8000/api/v1/collect', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    platform: 'douyin',
    keyword: 'AI编程',
    max_count: 50
  })
});

const { data: { task_id } } = await collectionResponse.json();
console.log('Task ID:', task_id);

// Poll for status
const checkStatus = async () => {
  const statusResponse = await fetch(
    `http://localhost:8000/api/v1/collect/${task_id}`,
    {
      headers: {
        'Authorization': `Bearer ${access_token}`
      }
    }
  );

  const statusData = await statusResponse.json();

  if (statusData.status === 'success') {
    console.log('Collection completed!');
    console.log('Results:', statusData.result);
    return;
  }

  if (statusData.status === 'failure') {
    console.error('Collection failed:', statusData.error);
    return;
  }

  console.log('Progress:', statusData.progress + '%');
  setTimeout(checkStatus, 5000);
};

checkStatus();
```

## Error Handling

### Standard Error Response

```json
{
  "success": false,
  "message": "Error description",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Task accepted for processing |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Error Scenarios

#### Authentication Failed

```json
{
  "success": false,
  "message": "Invalid authentication credentials",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Invalid Platform

```json
{
  "success": false,
  "message": "Platform 'invalid_platform' not found",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Task Not Found

```json
{
  "success": false,
  "message": "Task not found",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Webhooks

Configure webhooks to receive notifications when tasks complete.

### Webhook Configuration

```python
# Set webhook URL (coming soon)
POST /api/v1/webhooks
{
  "url": "https://your-domain.com/webhook",
  "events": ["task.completed", "task.failed"],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload

```json
{
  "event": "task.completed",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_type": "collection",
  "status": "success",
  "timestamp": "2024-01-15T10:35:00Z",
  "result": {
    "count": 50
  }
}
```

## SDKs

### Python SDK

```python
# Install
pip install omnisense-sdk

# Usage
from omnisense_sdk import OmniSenseAPI

api = OmniSenseAPI(
    base_url='http://localhost:8000',
    username='admin',
    password='admin'
)

# Collect data
task = api.collect(
    platform='douyin',
    keyword='AI编程',
    max_count=50
)

# Wait for completion
result = task.wait()
print(f"Collected {result['count']} items")

# Analyze data
analysis = api.analyze(
    data=result['data'],
    agents=['analyst'],
    analysis_types=['sentiment']
)

# Generate report
report = api.generate_report(
    analysis=analysis,
    format='pdf',
    output='report.pdf'
)
```

### JavaScript SDK

```javascript
// Install
npm install omnisense-sdk

// Usage
import OmniSenseAPI from 'omnisense-sdk';

const api = new OmniSenseAPI({
  baseURL: 'http://localhost:8000',
  username: 'admin',
  password: 'admin'
});

// Collect data
const task = await api.collect({
  platform: 'douyin',
  keyword: 'AI编程',
  maxCount: 50
});

// Wait for completion
const result = await task.wait();
console.log(`Collected ${result.count} items`);
```

## Best Practices

1. **Use API Keys for Production**: Generate API keys for long-running applications instead of storing passwords

2. **Handle Rate Limits**: Implement exponential backoff when rate limits are exceeded

3. **Poll Efficiently**: Don't poll task status too frequently (recommended: 5-10 second intervals)

4. **Error Handling**: Always handle errors gracefully and retry transient failures

5. **Pagination**: For large datasets, use pagination to avoid timeouts

6. **Caching**: Cache platform information and other static data to reduce API calls

7. **Monitoring**: Use the `/metrics` endpoint to monitor API usage and performance

8. **Security**: Always use HTTPS in production and never expose API keys in client-side code

## Support

- **API Issues**: https://github.com/bingdongni/omnisense/issues
- **Documentation**: https://omnisense.readthedocs.io
- **Email**: api-support@omnisense.example.com

## Changelog

### v1.0.0 (2024-01-15)

- Initial API release
- Authentication with JWT and API keys
- Data collection endpoints
- Analysis endpoints
- Report generation endpoints
- Platform information endpoints
- Task management
- Rate limiting
- Metrics and monitoring

---

Last updated: 2024-01-15
