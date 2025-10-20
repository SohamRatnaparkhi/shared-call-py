# FastAPI + PostgreSQL Request Coalescing Example

This example demonstrates the **real-world impact** of request coalescing using `shared-call-py` with FastAPI and PostgreSQL.

## 🎯 What This Demo Shows

When 1000 concurrent requests hit your API endpoint:

- **WITHOUT coalescing**: 1000 database queries execute, exhausting connection pools and creating high latency
- **WITH coalescing**: Only 1 database query executes, with all other requests sharing the result

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL database (local or cloud)
- `curl` (for load testing)
- `bc` (for calculations in bash scripts)

## 🚀 Quick Start

### 1. Set Up PostgreSQL

You can use any PostgreSQL instance:

**Option A: Local PostgreSQL**
```bash
# Install PostgreSQL (macOS)
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb shared_call_demo
```

**Option B: Docker**
```bash
docker run --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=shared_call_demo \
  -p 5432:5432 \
  -d postgres:15
```

**Option C: Cloud Database** (Supabase, Neon, Railway, Render, etc.)
- Create a database instance
- Copy the connection string

### 2. Install Dependencies

```bash
cd examples/fastapi

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your database URL
# Example: DATABASE_URL=postgresql://postgres:password@localhost:5432/shared_call_demo
```

### 4. Initialize Database

```bash
python init_db.py
```

This creates the `products` table and populates it with sample data.

### 5. Start the Server

```bash
python main.py
```

The server will start at http://localhost:8000

Visit http://localhost:8000 to see the API documentation.

## 🧪 Run Load Tests

### Test Normal Endpoint (No Coalescing)

```bash
bash load_test_normal.sh
```

This sends 1000 requests to `/product/normal/1` where **every request hits the database**.

Expected behavior:
- High database load (1000 queries)
- Connection pool exhaustion
- Increased latency due to queuing
- Average response time: 1000-3000ms

### Test Coalesced Endpoint (With Coalescing)

```bash
bash load_test_coalesced.sh
```

This sends 1000 requests to `/product/coalesced/1` where **requests are coalesced**.

Expected behavior:
- Low database load (~1-10 queries)
- No connection pool issues
- Low, consistent latency
- Average response time: 500-700ms
- **99% hit rate** (999 out of 1000 requests shared the result!)

## 📊 Understanding the Results

### Normal Endpoint Output
```
╔════════════════════════════════════════════════════════════════╗
║                    NORMAL ENDPOINT RESULTS                     ║
╠════════════════════════════════════════════════════════════════╣
║ Total Requests:        1000
║ Successful:            1000
║ Failed:                0
║ Total Duration:        12.45s
║ Requests/sec:          80.32
║
║ Response Times (ms):
║   Average:             2341.23
║   p50 (median):        2198.45
║   p95:                 3012.67
║   p99:                 3245.89
╚════════════════════════════════════════════════════════════════╝
```

### Coalesced Endpoint Output
```
╔════════════════════════════════════════════════════════════════╗
║                  COALESCED ENDPOINT RESULTS                    ║
╠════════════════════════════════════════════════════════════════╣
║ Total Requests:        1000
║ Successful:            1000
║ Failed:                0
║ Total Duration:        5.23s
║ Requests/sec:          191.20
║
║ Response Times (ms):
║   Average:             623.45
║   p50 (median):        598.12
║   p95:                 701.34
║   p99:                 745.67
╚════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════╗
║                     COALESCING IMPACT                          ║
╠════════════════════════════════════════════════════════════════╣
║ Database queries WITHOUT coalescing:  ~1000
║ Database queries WITH coalescing:     ~1
║ Queries prevented:                    999
║ Hit rate:                             99.9%
║
║ 💡 Request coalescing reduced DB load by ~99.9%!
╚════════════════════════════════════════════════════════════════╝
```

## 🔍 API Endpoints

### GET /
Homepage with API information and endpoints list

### GET /health
Health check endpoint
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### GET /product/normal/{product_id}
Normal endpoint - every request hits the database

**Example:**
```bash
curl http://localhost:8000/product/normal/1
```

**Response:**
```json
{
  "query_time_ms": 523.45,
  "timestamp": 1697812345.678,
  "product": {
    "id": 1,
    "name": "MacBook Pro 16-inch",
    "price": 2499.99,
    "description": "Powerful laptop with M3 Pro chip"
  },
  "endpoint_type": "normal"
}
```

### GET /product/coalesced/{product_id}
Coalesced endpoint - concurrent requests share database query

**Example:**
```bash
curl http://localhost:8000/product/coalesced/1
```

**Response:**
```json
{
  "query_time_ms": 512.34,
  "timestamp": 1697812345.678,
  "product": {
    "id": 1,
    "name": "MacBook Pro 16-inch",
    "price": 2499.99,
    "description": "Powerful laptop with M3 Pro chip"
  },
  "endpoint_type": "coalesced"
}
```

### GET /stats
View coalescing statistics

**Response:**
```json
{
  "hits": 999,
  "misses": 1,
  "errors": 0,
  "active_calls": 0,
  "hit_rate": "99.9%",
  "total_requests": 1000,
  "queries_prevented": 999
}
```

### POST /stats/reset
Reset coalescing statistics

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Load Test Script                       │
│              (1000 concurrent HTTP requests)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  /product/normal/{id}    /product/coalesced/{id}     │  │
│  │         │                          │                  │  │
│  │         │                          ▼                  │  │
│  │         │                 ┌─────────────────┐        │  │
│  │         │                 │ AsyncSharedCall │        │  │
│  │         │                 │   (Coalescing)  │        │  │
│  │         │                 └────────┬────────┘        │  │
│  │         │                          │                  │  │
│  │         └──────────────┬───────────┘                  │  │
│  │                        ▼                              │  │
│  │              fetch_product_from_db()                  │  │
│  └───────────────────────┬───────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   PostgreSQL Pool    │
                  │   (5-10 connections) │
                  └──────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  PostgreSQL Database │
                  │   (products table)   │
                  └──────────────────────┘
```

## 💡 Key Concepts

### Request Coalescing

When multiple requests arrive for the same resource:

1. **First request** (leader) executes the database query
2. **Subsequent requests** (followers) wait for the leader's result
3. **All requests** receive the same result
4. **Database** only processes 1 query instead of N

### Why This Matters

**Cache Stampede Prevention**: When cache expires, only one request refills it

**Database Protection**: Connection pool doesn't get exhausted

**Rate Limit Compliance**: External APIs receive fewer calls

**Cost Reduction**: Lower database/API usage = lower bills

## 🎛️ Configuration

### Database Pool Settings

In `main.py`, adjust connection pool:

```python
db_pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=5,      # Minimum connections
    max_size=10,     # Maximum connections
    command_timeout=60,
)
```

### Simulated Query Delay

In `fetch_product_from_db()`, adjust delay:

```python
await asyncio.sleep(0.5)  # Simulate slow query (500ms)
```

Increase to simulate slower queries and see more dramatic coalescing benefits.

### Load Test Configuration

In load test scripts, adjust:

```bash
TOTAL_REQUESTS=1000   # Total number of requests
CONCURRENT=100        # Concurrent requests per batch
```

## 🐛 Troubleshooting

### Server won't start

**Error**: `ValueError: DATABASE_URL environment variable is required`

**Solution**: Make sure `.env` file exists and contains valid `DATABASE_URL`

### Database connection fails

**Error**: `could not connect to server`

**Solution**: 
- Check PostgreSQL is running: `pg_isready`
- Verify connection string in `.env`
- Test connection: `psql $DATABASE_URL`

### Load test fails

**Error**: `Server is not running at http://localhost:8000`

**Solution**: Start the server first: `python main.py`

### Permission denied on bash scripts

**Error**: `bash: ./load_test_normal.sh: Permission denied`

**Solution**: Make scripts executable:
```bash
chmod +x load_test_normal.sh load_test_coalesced.sh
```

## 📚 Learn More

- [shared-call-py Documentation](../../README.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)

## 🤝 Contributing

Found a bug or have an improvement? Open an issue or submit a PR!

## 📄 License

MIT License - see [LICENSE](../../LICENSE) file for details.
