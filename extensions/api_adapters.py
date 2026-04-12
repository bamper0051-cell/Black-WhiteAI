
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import redis, json, os
from extensions.jobs import create_job

router = APIRouter()
r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=6379, decode_responses=True)

@router.post("/api/matrix/run")
async def run(data: dict):
    job_id = create_job(data)
    return {"job_id": job_id}

@router.get("/api/jobs/{job_id}/stream")
async def stream(job_id: str):
    async def event_stream():
        pub = r.pubsub()
        pub.subscribe(f"job:{job_id}")
        for msg in pub.listen():
            if msg["type"] == "message":
                yield f"data: {msg['data']}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
