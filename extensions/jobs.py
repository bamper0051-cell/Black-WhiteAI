
import redis, json, uuid, os

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True
)

def create_job(task):
    job_id = str(uuid.uuid4())
    r.set(f"job:{job_id}", json.dumps({"task": task}))
    r.lpush("queue", job_id)
    return job_id
