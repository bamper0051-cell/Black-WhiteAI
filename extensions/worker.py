
import redis, json, asyncio
from agent_matrix import run_auto  # ensure run_auto exists as per patch

r = redis.Redis(host="redis", port=6379, decode_responses=True)

async def worker():
    print("[worker] started")
    while True:
        _, job_id = r.brpop("queue")
        job = json.loads(r.get(f"job:{job_id}"))

        async def log(msg):
            r.publish(f"job:{job_id}", json.dumps(msg))

        try:
            await run_auto(job.get("task"), log)
            r.publish(f"job:{job_id}", json.dumps({"type":"result","status":"done"}))
        except Exception as e:
            r.publish(f"job:{job_id}", json.dumps({"type":"error","error": str(e)}))

if __name__ == "__main__":
    asyncio.run(worker())
