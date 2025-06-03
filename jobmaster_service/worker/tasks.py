from celery import Celery
import requests
from datetime import datetime, timedelta

BACKEND_URL = "http://3.148.5.72"
app = Celery("tasks", broker="redis://redis:6379/0")

@app.task(name="tasks.estimate_stock")
def estimate_stock(job_id, data):
    print(f"Procesando job {job_id} con data: {data}")
    symbol = data["stock_symbol"]
    quantity = data["quantity"]
    request_id = data.get("request_id")
    price = data.get("price")  # Precio actual enviado desde backend

    try:
        today = datetime.utcnow().date()
        last_month = today - timedelta(days=60)  # Ventana extendida a 60 días

        resp = requests.get(f"{BACKEND_URL}/stocks/{symbol}/event_log?page=1&count=100")
        if resp.status_code != 200:
            raise Exception("No se pudo obtener precios históricos")

        data_points = resp.json().get("event_log", [])
        filtered = [
            p for p in data_points
            if "price" in p and "timestamp" in p and
               last_month <= datetime.fromisoformat(p["timestamp"]).date() <= today
        ]

        if len(filtered) >= 2:
            filtered.sort(key=lambda x: x["timestamp"])
            start = filtered[0]
            end = filtered[-1]

            days_between = (datetime.fromisoformat(end["timestamp"]) - datetime.fromisoformat(start["timestamp"])).days
            if days_between == 0:
                estimated_gain = 0
            else:
                m = (end["price"] - start["price"]) / days_between
                projected_price = end["price"] + (m * 30)
                estimated_gain = round((projected_price - end["price"]) * quantity, 2)

        else:
            # Con uno o ningún punto histórico, ganancia estimada = 0
            estimated_gain = 0

    except Exception as e:
        print("Error en estimación:", e)
        # En caso de error, igual dejamos ganancia en 0
        estimated_gain = 0

    resultado = {
        "status": "completed",
        "estimated_gain": estimated_gain,
        "request_id": request_id
    }

    try:
        print(f"[Tasks] Enviando estimación al backend: {resultado}")
        response = requests.post(f"{BACKEND_URL}/internal/update_job", json={
            "job_id": job_id,
            "result": resultado
        })
        print(f"[Tasks] Respuesta backend: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[Tasks] Error al enviar resultado al backend: {e}")

    return resultado
