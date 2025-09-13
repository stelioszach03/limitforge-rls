import asyncio
import os
import time
import statistics
import httpx


async def worker(idx, base_url, api_key, requests, resource, subject_prefix, latencies):
    async with httpx.AsyncClient(
        base_url=base_url, headers={"X-API-Key": api_key}
    ) as client:
        for i in range(requests):
            payload = {
                "resource": resource,
                "subject": f"{subject_prefix}{idx}",
                "cost": 1,
            }
            t0 = time.perf_counter()
            r = await client.post("/v1/check", json=payload)
            dt = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt)
            _ = r.json() if r.status_code in (200, 429) else None


async def main():
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "")
    resource = os.getenv("RESOURCE", "orders")
    subject_prefix = os.getenv("SUBJECT_PREFIX", "user:")
    workers = int(os.getenv("WORKERS", "10"))
    requests_per_worker = int(os.getenv("REQUESTS", "100"))

    latencies = []
    start = time.perf_counter()
    tasks = [
        worker(
            i,
            base_url,
            api_key,
            requests_per_worker,
            resource,
            subject_prefix,
            latencies,
        )
        for i in range(workers)
    ]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start
    total_reqs = workers * requests_per_worker
    throughput = total_reqs / total_time
    p95 = statistics.quantiles(latencies, n=100)[94] if latencies else 0.0
    print(f"Requests: {total_reqs}, Concurrency: {workers}, Time: {total_time:.2f}s")
    print(f"Throughput: {throughput:.2f} req/s, p95 latency: {p95:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())
