from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, JSONResponse

from llama_cpp import Llama

import multiprocessing
import time
import os
import uuid
import json
import threading
import asyncio
import signal
import sqlite3
from queue import Queue, Empty, Full


# =========================
# PERFORMANCE / SAFETY
# =========================

CPU_CORES = multiprocessing.cpu_count()
os.environ["OMP_NUM_THREADS"] = str(max(1, CPU_CORES // 2))
os.environ["MKL_NUM_THREADS"] = str(max(1, CPU_CORES // 2))

CPU_THREADS = max(1, CPU_CORES // 2)

CTX_SIZE = 2048
N_BATCH = 1

MAX_PROMPT_CHARS = 12000
MAX_TOKENS_LIMIT = 512
MAX_GENERATION_TIME = 300

QUEUE_MAXSIZE = 50
STREAM_QUEUE_SIZE = 256

MAX_ACTIVE_GENERATIONS = 1

JOB_TTL_SEC = 300
STREAM_TIMEOUT_SEC = 30
DB_CLEANUP_INTERVAL = 60


MODEL_PATH = "../models/mistral/openhermes-2.5-mistral-7b.Q4_K_M.gguf"
SYSTEM_PROMPT_PATH = "system_prompt.txt"
DB_PATH = "nexus_jobs.db"


# =========================
# SYSTEM PROMPT
# =========================

def load_system_prompt():
    if os.path.exists(SYSTEM_PROMPT_PATH):
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "You are Nexus Core AI."

SYSTEM_PROMPT = load_system_prompt()


# =========================
# MODEL
# =========================

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=CTX_SIZE,
    n_threads=CPU_THREADS,
    n_batch=N_BATCH,
    verbose=False
)

try:
    llm("warmup", max_tokens=1)
except:
    pass


# =========================
# SQLITE STORE (ENHANCED)
# =========================

class JobStore:
    def __init__(self, db_path):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init()

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init(self):
        with self._conn() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT,
                prompt TEXT,
                response TEXT,
                max_tokens INTEGER,
                temperature REAL,
                created REAL,
                updated REAL
            )
            """)
            c.commit()

    def create(self, job_id, prompt, max_tokens, temperature):
        with self.lock, self._conn() as c:
            now = time.time()
            c.execute("""
                INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, "queued", prompt, None, max_tokens, temperature, now, now))
            c.commit()

    def update(self, job_id, **fields):
        with self.lock, self._conn() as c:
            keys = ", ".join([f"{k}=?" for k in fields])
            vals = list(fields.values())
            vals.append(job_id)
            c.execute(f"""
                UPDATE jobs
                SET {keys}, updated=?
                WHERE id=?
            """, vals + [time.time()])
            c.commit()

    def get(self, job_id):
        with self.lock, self._conn() as c:
            return c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()

    def recover(self):
        with self.lock, self._conn() as c:
            return c.execute("""
                SELECT id, prompt, max_tokens, temperature
                FROM jobs
                WHERE status IN ('queued','processing')
            """).fetchall()

    def cleanup_old(self):
        with self.lock, self._conn() as c:
            c.execute("""
                DELETE FROM jobs
                WHERE status IN ('done','error')
                AND updated < ?
            """, (time.time() - JOB_TTL_SEC,))
            c.commit()


job_store = JobStore(DB_PATH)


# =========================
# STREAM MANAGER (FIXED)
# =========================

class StreamManager:
    def __init__(self):
        self.streams = {}
        self.lock = threading.RLock()

    def create(self, job_id):
        with self.lock:
            self.streams[job_id] = Queue(maxsize=STREAM_QUEUE_SIZE)

    def wait_for(self, job_id, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                if job_id in self.streams:
                    return self.streams[job_id]
            time.sleep(0.05)
        return None

    def get(self, job_id):
        with self.lock:
            return self.streams.get(job_id)

    def close(self, job_id):
        with self.lock:
            q = self.streams.get(job_id)
            if q:
                try:
                    q.put_nowait(None)
                except:
                    pass

    def cleanup(self):
        with self.lock:
            to_delete = []
            for k, v in self.streams.items():
                if v.empty():
                    to_delete.append(k)
            for k in to_delete:
                self.streams.pop(k, None)


stream_manager = StreamManager()


# =========================
# METRICS (SAFE)
# =========================

class Metrics:
    def __init__(self):
        self.lock = threading.RLock()
        self.data = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "tokens_generated": 0,
            "active": 0
        }

    def inc(self, k, v=1):
        with self.lock:
            self.data[k] += v

    def snapshot(self):
        with self.lock:
            return dict(self.data)


metrics = Metrics()


# =========================
# QUEUE + SEMAPHORE
# =========================

request_queue = Queue(maxsize=QUEUE_MAXSIZE)
semaphore = threading.Semaphore(MAX_ACTIVE_GENERATIONS)
shutdown_event = threading.Event()


# =========================
# FASTAPI
# =========================

app = FastAPI()


class PromptRequest(BaseModel):
    text: str
    max_tokens: int = 128
    temperature: float = 0.7


# =========================
# PRESSURE CONTROL
# =========================

def queue_pressure():
    q = request_queue.qsize()
    if q > 40:
        return 503
    if q > 25:
        return 429
    return 200


# =========================
# WORKER
# =========================

def worker():
    while not shutdown_event.is_set():
        try:
            job_id, prompt, max_tokens, temp = request_queue.get(timeout=1)
        except Empty:
            continue

        semaphore.acquire()

        try:
            metrics.inc("active")
            job_store.update(job_id, status="processing")

            stream_manager.create(job_id)

            q = stream_manager.wait_for(job_id, timeout=5)

            chunks = []
            start = time.time()
            tokens = 0
            started = False

            for chunk in llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temp,
                stop=["</s>", "<USER>", "<SYSTEM>"],
                stream=True
            ):
                if time.time() - start > MAX_GENERATION_TIME:
                    raise RuntimeError("timeout")

                token = chunk["choices"][0]["text"]
                chunks.append(token)
                tokens += 1

                if not started:
                    job_store.update(job_id, status="streaming")
                    started = True

                if q:
                    try:
                        q.put_nowait(token)
                    except Full:
                        pass

            response = "".join(chunks)

            job_store.update(job_id, status="done", response=response)

            metrics.inc("completed_requests")
            metrics.inc("tokens_generated", tokens)

            stream_manager.close(job_id)

        except Exception as e:
            job_store.update(job_id, status="error", response=str(e))
            metrics.inc("failed_requests")
            stream_manager.close(job_id)

        finally:
            metrics.inc("active", -1)
            semaphore.release()
            request_queue.task_done()


threading.Thread(target=worker, daemon=True).start()


# =========================
# TTL CLEANERS
# =========================

def ttl_loop():
    while not shutdown_event.is_set():
        time.sleep(DB_CLEANUP_INTERVAL)
        job_store.cleanup_old()
        stream_manager.cleanup()

threading.Thread(target=ttl_loop, daemon=True).start()


# =========================
# API
# =========================

@app.get("/")
def root():
    return {
        "status": "online",
        "queue": request_queue.qsize(),
        "pressure": queue_pressure(),
        "metrics": metrics.snapshot()
    }


@app.get("/metrics")
def get_metrics():
    return {
        **metrics.snapshot(),
        "queue": request_queue.qsize(),
        "pressure": queue_pressure()
    }


@app.post("/generate")
def generate(req: PromptRequest):

    if len(req.text) > MAX_PROMPT_CHARS:
        return JSONResponse(400, {"error": "too_large"})

    code = queue_pressure()
    if code != 200:
        return JSONResponse(code, {"error": "overload"})

    job_id = str(uuid.uuid4())

    prompt = f"""<SYSTEM>
{SYSTEM_PROMPT}
</SYSTEM>

<USER>
{req.text}
</USER>

<ASSISTANT>
"""

    job_store.create(job_id, prompt, min(req.max_tokens, MAX_TOKENS_LIMIT), req.temperature)

    metrics.inc("total_requests")

    request_queue.put((job_id, prompt, min(req.max_tokens, MAX_TOKENS_LIMIT), req.temperature))

    return {"job_id": job_id, "status": "queued"}


@app.get("/stream/{job_id}")
async def stream(job_id: str, request: Request):

    q = stream_manager.wait_for(job_id, timeout=5)

    if not q:
        return JSONResponse(404, {"error": "stream_not_ready"})

    async def gen():
        wait = 0

        while True:

            if await request.is_disconnected():
                break

            try:
                token = await asyncio.to_thread(q.get, True, STREAM_TIMEOUT_SEC)
            except Empty:
                yield "data: {\"error\":\"timeout\"}\n\n"
                break

            if token is None:
                yield "data: {\"done\":true}\n\n"
                break

            yield f"data: {json.dumps({'token': token})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# =========================
# SHUTDOWN
# =========================

def shutdown(sig, frame):
    shutdown_event.set()


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


# =========================
# RECOVERY
# =========================

def recover():
    for job_id, prompt, mt, temp in job_store.recover():
        request_queue.put((job_id, prompt, mt, temp))


recover()
