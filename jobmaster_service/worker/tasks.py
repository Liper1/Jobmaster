from celery import Celery
import time
import requests

app = Celery("tasks", broker="redis://redis:6379/0")

@app.task(name="tasks.estimate_stock")
def estimate_stock(job_id, data):
    print(f"Procesando job {job_id} con data: {data}")
    time.sleep(5)  # Simula tiempo de cálculo

    # Resultado simulado
    resultado = {
        "status": "completed",
        "estimated_gain": round(data["quantity"] * 12.5, 2)
    }

    # Enviar resultado de vuelta al JobMaster
    try:
        requests.post(f"http://jobmaster:8000/internal/update_job", json={
            "job_id": job_id,
            "result": resultado
        })
    except Exception as e:
        print(f"Error al enviar resultado: {e}")
