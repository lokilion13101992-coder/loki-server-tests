from fastapi import FastAPI
from pydantic import BaseModel
import uuid

from qdrant_client import QdrantClient
import redis
import psycopg2

app = FastAPI()

# --- connections ---
qdrant = QdrantClient(host="localhost", port=6333)
rdb = redis.Redis(host="localhost", port=6379, decode_responses=True)

pg = psycopg2.connect(
    dbname="nexusdb",
    user="nexus",
    password="nexuspass",
    host="localhost",
    port=5432
)

# --- models ---
class Memory(BaseModel):
    text: str

# --- API ---

@app.get("/")
def root():
    return {"status": "NEXUS CORE ONLINE"}

@app.post("/memory/add")
def add_memory(mem: Memory):
    mem_id = str(uuid.uuid4())

    # 1. Redis (short-term memory)
    rdb.set(mem_id, mem.text)

    # 2. Postgres (long-term log)
    cur = pg.cursor()
    cur.execute(
        "INSERT INTO memories (id, text) VALUES (%s, %s)",
        (mem_id, mem.text)
    )
    pg.commit()

    return {"id": mem_id, "status": "stored"}

@app.get("/memory/get/{mem_id}")
def get_memory(mem_id: str):
    value = rdb.get(mem_id)
    return {"id": mem_id, "text": value}
