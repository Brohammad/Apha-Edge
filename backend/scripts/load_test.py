#!/usr/bin/env python3
"""Simple load test for AlphaEdge API health and auth endpoints.

Usage:
    python scripts/load_test.py --base-url http://localhost:8000 --requests 200 --concurrency 20
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import httpx


async def worker(
    client: httpx.AsyncClient,
    base_url: str,
    latencies: list[float],
    errors: list[int],
) -> None:
    start = time.perf_counter()
    try:
        resp = await client.get(f"{base_url}/api/v1/health/live")
        latencies.append(time.perf_counter() - start)
        if resp.status_code >= 400:
            errors.append(resp.status_code)
    except Exception:
        errors.append(-1)


async def run(base_url: str, requests: int, concurrency: int) -> None:
    latencies: list[float] = []
    errors: list[int] = []
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=10.0) as client:

        async def bounded() -> None:
            async with sem:
                await worker(client, base_url, latencies, errors)

        started = time.perf_counter()
        await asyncio.gather(*[bounded() for _ in range(requests)])
        elapsed = time.perf_counter() - started

    print(f"Requests:     {requests}")
    print(f"Concurrency:  {concurrency}")
    print(f"Duration:     {elapsed:.2f}s")
    print(f"Throughput:   {requests / elapsed:.1f} req/s")
    if latencies:
        print(f"Latency p50:  {statistics.median(latencies) * 1000:.1f} ms")
        print(f"Latency p95:  {sorted(latencies)[int(len(latencies) * 0.95) - 1] * 1000:.1f} ms")
    print(f"Errors:       {len(errors)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaEdge load test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(run(args.base_url, args.requests, args.concurrency))


if __name__ == "__main__":
    main()
