from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from celery import Celery
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import requests

app = FastAPI()
BACKEND_URL = "http://api:8000"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

celery_app = Celery("jobmaster", broker="redis://redis:6379/0")

# Diccionario en memoria (para pruebas)
results = {}

class JobData(BaseModel):
    user_id: str
    stock_symbol: str
    quantity: int

@app.post("/job")
def create_job(data: JobData):
    job_id = str(uuid.uuid4())
    celery_app.send_task("tasks.estimate_stock", args=[job_id, data.dict()])
    results[job_id] = {"status": "processing"}
    return {"job_id": job_id}

@app.get("/job/{job_id}")
def get_job_status(job_id: str):
    if job_id not in results:
        raise HTTPException(status_code=404, detail="Job ID no encontrado")
    return results[job_id]

@app.get("/heartbeat")
def heartbeat():
    return True


@app.post("/internal/update_job")
async def update_job(request: Request):
    data = await request.json()
    job_id = data.get("job_id")
    result = data.get("result")
    if job_id and result:
        results[job_id] = result

        #PROBAR LOCAL
        try:
            requests.post("http://api:8000/internal/update_job", json={
                "job_id": job_id,
                "result": result,
                "request_id": result.get("request_id") 
            })
        except Exception as e:
            print("[JobMaster] Error reenviando resultado al backend:", e)

        return {"msg": "ok"}
    else:
        raise HTTPException(status_code=400, detail="Faltan datos")
