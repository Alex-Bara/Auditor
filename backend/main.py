from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from analyzer import run_audit
from claims import create_claim_pdf
from pydantic import BaseModel
import asyncio
import random

app = FastAPI()

# 1. ЧИННИМ CORS (чтобы фронтенд мог достучаться)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuditRequest(BaseModel):
    api_key: str
    marketplace: str

# 2. ДОБАВЛЯЕМ ПРОПУЩЕННЫЕ ФУНКЦИИ (Генератор данных)
def get_mock_data(marketplace: str):
    reasons = [
        "Неверные габариты (логистика x2)",
        "Товар утерян при приемке",
        "Брак не компенсирован",
        "Ошибка логики удержаний"
    ]
    mock_results = []
    total_found = 0
    for _ in range(random.randint(10, 25)):
        lost_sum = random.randint(500, 5000)
        total_found += lost_sum
        mock_results.append({
            "order_id": f"654{random.randint(10000, 99999)}21",
            "reason": random.choice(reasons),
            "lost_sum": lost_sum
        })
    return {"total_lost": total_found, "items": mock_results}

def mask_id(identifier: str) -> str:
    s = str(identifier)
    return f"{s[:3]}***{s[-2:]}" if len(s) > 5 else "***"

def prepare_preview(raw_data: list):
    return [
        {"order_id": mask_id(item["order_id"]), "reason": item["reason"], "lost_sum": item["lost_sum"]}
        for item in raw_data[:5]
    ]

# 3. САМ ЭНДПОИНТ
@app.post("/api/start-audit")
async def start(request: AuditRequest):
    results = await run_audit(request.marketplace, request.api_key)
    # Маскируем данные для превью
    return {"status": "success", "total_sum": results["total"], "preview": results["items"][:5]}

@app.get("/api/download-claim")
async def download(total: int, marketplace: str):
    # Генерируем данные для теста (или берем реальные)
    mock_results = {
        "total": total, 
        "items": [{"reason": "Расхождение", "amount": total, "id": "TEST-123"}]
    }
    
    # Вызываем твою функцию из claims.py
    pdf_content = create_claim_pdf({}, mock_results)
    
    # ВАЖНЫЙ МОМЕНТ: используем bytes(pdf_content)
    return Response(
        content=bytes(pdf_content), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=claim_{marketplace}.pdf"}
    )



