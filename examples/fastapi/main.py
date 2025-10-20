"""
FastAPI example demonstrating request coalescing with PostgreSQL.

This example shows the performance difference between:
1. Normal endpoint - Every request hits the database
2. Coalesced endpoint - Concurrent requests share a single database query
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared_call_py import AsyncSharedCall


# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Initialize request coalescing
shared = AsyncSharedCall()

# Database connection pool
db_pool = None


class Product(BaseModel):
    """Product model"""

    id: int
    name: str
    price: float
    description: str


class QueryStats(BaseModel):
    """Query statistics"""

    query_time_ms: float
    timestamp: float
    product: Product
    endpoint_type: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database connection pool"""
    global db_pool
    # Startup: Create connection pool
    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=10,
        command_timeout=60,
    )
    print("✅ Database connection pool created")
    yield
    # Shutdown: Close connection pool
    await db_pool.close()
    print("👋 Database connection pool closed")


app = FastAPI(
    title="SharedCall FastAPI Example",
    description="Demonstrates request coalescing with PostgreSQL",
    lifespan=lifespan,
)


async def fetch_product_from_db(product_id: int) -> Product:
    """
    Fetch product from database - simulates a slow query.

    This function adds artificial delay to simulate expensive operations like:
    - Complex joins
    - Aggregations
    - External API calls
    """
    async with db_pool.acquire() as conn:
        # Simulate slow query
        await asyncio.sleep(0.5)

        row = await conn.fetchrow(
            """
            SELECT id, name, price, description
            FROM products
            WHERE id = $1
            """,
            product_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        return Product(
            id=row["id"],
            name=row["name"],
            price=float(row["price"]),
            description=row["description"],
        )


@shared.group()
async def fetch_product_coalesced(product_id: int) -> Product:
    """
    Coalesced version - multiple concurrent requests share the same DB query.

    When 100 requests come in simultaneously for the same product,
    only ONE database query executes. The other 99 wait and receive
    the same result.
    """
    return await fetch_product_from_db(product_id)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SharedCall FastAPI Example",
        "endpoints": {
            "/product/normal/{id}": "Normal endpoint - every request hits DB",
            "/product/coalesced/{id}": "Coalesced endpoint - requests share DB query",
            "/stats": "View coalescing statistics",
            "/health": "Health check",
        },
        "load_test": {
            "normal": "bash load_test_normal.sh",
            "coalesced": "bash load_test_coalesced.sh",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/product/normal/{product_id}", response_model=QueryStats)
async def get_product_normal(product_id: int):
    """
    Normal endpoint - EVERY request hits the database.

    With 1000 concurrent requests:
    - 1000 database queries execute
    - Connection pool gets exhausted
    - High latency due to queuing
    """
    start_time = time.perf_counter()

    product = await fetch_product_from_db(product_id)

    query_time = (time.perf_counter() - start_time) * 1000

    return QueryStats(
        query_time_ms=round(query_time, 2),
        timestamp=time.time(),
        product=product,
        endpoint_type="normal",
    )


@app.get("/product/coalesced/{product_id}", response_model=QueryStats)
async def get_product_coalesced(product_id: int):
    """
    Coalesced endpoint - concurrent requests SHARE a single database query.

    With 1000 concurrent requests:
    - Only 1 database query executes
    - 999 requests wait for the result
    - Low latency, no connection pool exhaustion
    """
    start_time = time.perf_counter()

    product = await fetch_product_coalesced(product_id)

    query_time = (time.perf_counter() - start_time) * 1000

    return QueryStats(
        query_time_ms=round(query_time, 2),
        timestamp=time.time(),
        product=product,
        endpoint_type="coalesced",
    )


@app.get("/stats")
async def get_stats():
    """Get coalescing statistics"""
    stats = await shared.get_stats()
    return {
        "hits": stats.hits,
        "misses": stats.misses,
        "errors": stats.errors,
        "active_calls": stats.active,
        "hit_rate": f"{stats.hit_rate:.1%}",
        "total_requests": stats.hits + stats.misses,
        "queries_prevented": stats.hits,
    }


@app.post("/stats/reset")
async def reset_stats():
    """Reset coalescing statistics"""
    await shared.reset_stats()
    return {"message": "Statistics reset successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
