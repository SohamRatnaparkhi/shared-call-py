# Database Load Benchmark

**Scenario**: Simulating a realistic database with connection pool limits and latency degradation under concurrent load.

## Setup

- **Database**: Connection pool limited to 10 concurrent queries
- **Latency Model**: 50ms base + 10ms per concurrent query (realistic contention)
- **Load**: 100 concurrent requests for the same resource
- **Query**: `SELECT * FROM resources WHERE id = 42`

## Methodology

### Without Coalescing
```python
async def fetch_resource(resource_id: int):
    # Direct database hit - no protection
    return await db.query(resource_id)

# 100 concurrent calls
tasks = [fetch_resource(42) for _ in range(100)]
await asyncio.gather(*tasks)
```

All 100 requests hit the database simultaneously:
- Connection pool (10) exhausted immediately
- 90 requests queue up waiting for connections
- Each query experiences increasing latency due to contention
- Total system thrashing

### With Coalescing
```python
shared = AsyncSharedCall()

@shared.group()
async def fetch_resource(resource_id: int):
    return await db.query(resource_id)

# 100 concurrent calls
tasks = [fetch_resource(42) for _ in range(100)]
await asyncio.gather(*tasks)
```

Only 1 request hits the database:
- First request becomes leader, executes query
- Other 99 requests wait for leader's result
- No connection pool exhaustion
- Minimal latency

## Results

### ❌ WITHOUT Request Coalescing

```
Concurrent Requests:   100
Actual DB Queries:     100
Coalescing Rate:       0.0%
Total Duration:        6.012s
Avg Latency:           2232.42ms
p99 Latency:           6010.56ms
```

**Analysis:**
- **Every request** executed independently
- Connection pool saturated (only 10 connections for 100 queries)
- Severe queuing effects: later requests waited 6+ seconds
- Average latency 2.2 seconds (vs 50ms baseline)
- p99 latency catastrophic: 6 seconds

### ✅ WITH Request Coalescing

```
Concurrent Requests:   100
Actual DB Queries:     1
Coalescing Rate:       99.0%
Total Duration:        0.065s
Avg Latency:           60.19ms
p99 Latency:           62.05ms
```

**Analysis:**
- **Only 1 query** executed (99% reduction)
- No connection pool pressure
- All requests completed in ~60ms
- Latency close to baseline (50ms) + minimal overhead

## Performance Improvement

```
📊 PERFORMANCE IMPROVEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Speedup:         92.6x faster
Avg Latency:           37.1x faster
p99 Latency:           96.9x faster
DB Queries Eliminated: 99
Load Reduction:        99.0%
```

## Visualization

### Latency Distribution

**Without Coalescing:**
```
|     ████████████████████████████████████  <- Queue buildup
|   ████████████████████████████████████
| ████████████████████████████████████
|██████████████████████████████████
└──────────────────────────────────
  0ms         3000ms         6000ms
```

**With Coalescing:**
```
|█  <- All requests clustered at ~60ms
|
|
|
└──────────────────────────────────
  0ms          60ms          120ms
```

## Real-World Impact

### Before (No Coalescing)
- 🔴 Database connection pool constantly exhausted
- 🔴 Timeouts and errors under load
- 🔴 Need to over-provision database capacity
- 🔴 Poor user experience (multi-second latencies)
- 🔴 Cascading failures to dependent services

### After (With Coalescing)
- 🟢 Connection pool stays healthy
- 🟢 Consistent sub-100ms latencies
- 🟢 Right-sized database capacity
- 🟢 Excellent user experience
- 🟢 System resilience under burst traffic

## When This Matters Most

1. **High-Traffic Endpoints**: Homepage, popular products, trending content
2. **Cache Invalidation**: When cache expires and all requests hit DB
3. **Morning Rush**: Traffic spikes at business open
4. **Viral Content**: Sudden burst of requests for same resource
5. **Microservices**: Multiple services querying same data

## Code Example

Run the benchmark yourself:

```bash
cd examples/
python mock_db_query.py
```

**Source**: [`examples/mock_db_query.py`](../../examples/mock_db_query.py)

## Key Takeaways

1. **99% query reduction** - From 100 queries to 1
2. **92.6x total speedup** - System processes requests dramatically faster
3. **37x latency improvement** - Users see nearly instant responses
4. **Connection pool protection** - No more pool exhaustion errors
5. **Cost savings** - Reduced database load = smaller instances needed

## Environment

- Python 3.12
- asyncio
- Simulated PostgreSQL-like database
- 10 connection pool limit (typical for cloud databases)
- Realistic latency degradation model

---

**Conclusion**: Request coalescing transforms database-bound applications from thrashing to thriving under concurrent load.
