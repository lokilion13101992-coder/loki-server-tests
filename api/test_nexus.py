import pytest
import httpx
import asyncio
import json
import time

BASE = "http://localhost:8000"


# =========================
# HELPERS
# =========================

async def wait_for_stream_ready(client: httpx.AsyncClient, job_id: str, timeout=10):
    start = time.time()

    while time.time() - start < timeout:
        r = await client.get(f"{BASE}/metrics")
        if r.status_code == 200:
            return True
        await asyncio.sleep(0.2)

    return False


async def wait_for_tokens(client: httpx.AsyncClient, job_id: str, timeout=30):
    start = time.time()

    tokens = []

    while time.time() - start < timeout:

        try:
            async with client.stream("GET", f"{BASE}/stream/{job_id}") as s:

                async for line in s.aiter_lines():

                    if not line:
                        continue

                    # SSE format: data: {...}
                    if line.startswith("data: "):
                        payload = line.replace("data: ", "")

                        try:
                            obj = json.loads(payload)
                        except:
                            continue

                        if "token" in obj:
                            tokens.append(obj["token"])

                        if obj.get("done"):
                            return tokens

                        if "error" in obj:
                            return tokens

        except httpx.HTTPError:
            await asyncio.sleep(0.2)

    return tokens


# =========================
# TESTS
# =========================

@pytest.mark.asyncio
async def test_generate():
    async with httpx.AsyncClient(timeout=10) as c:

        r = await c.post(f"{BASE}/generate", json={
            "text": "Hello",
            "max_tokens": 10
        })

        assert r.status_code == 200
        data = r.json()

        assert "job_id" in data
        assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_metrics():
    async with httpx.AsyncClient(timeout=10) as c:

        r = await c.get(f"{BASE}/metrics")

        assert r.status_code == 200
        data = r.json()

        assert "total_requests" in data
        assert "completed_requests" in data


@pytest.mark.asyncio
async def test_stream_stable():
    async with httpx.AsyncClient(timeout=60) as c:

        # 1. create job
        r = await c.post(f"{BASE}/generate", json={
            "text": "Write a short poem about AI",
            "max_tokens": 30
        })

        assert r.status_code == 200
        job_id = r.json()["job_id"]

        # 2. wait for system stability (no sleep hack)
        ready = await wait_for_stream_ready(c, job_id)
        assert ready is True

        # 3. stream tokens safely
        tokens = await wait_for_tokens(c, job_id)

        # 4. validation
        assert isinstance(tokens, list)
        assert len(tokens) > 0


@pytest.mark.asyncio
async def test_multiple_requests():
    async with httpx.AsyncClient(timeout=60) as c:

        jobs = []

        for i in range(3):
            r = await c.post(f"{BASE}/generate", json={
                "text": f"Say number {i}",
                "max_tokens": 10
            })
            assert r.status_code == 200
            jobs.append(r.json()["job_id"])

        assert len(jobs) == 3
