from fastapi import FastAPI, Response, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from analyzer import run_audit
from claims import create_claim_pdf
from pydantic import BaseModel
from supabase import create_client, Client
import os
import asyncio
import random

app = FastAPI()
# Данные берем из переменных окружения Render (Environment Variables)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# 3. ЭНДПОИНТЫ
@app.post("/api/start-audit")
async def start_audit(request: AuditRequest, tg_id: int = Query(...)): # Закрыли скобку тут
    # 1. Проверяем юзера в базе
    user_query = supabase.table("users").select("*").eq("tg_id", tg_id).execute()
    
    if not user_query.data:
        supabase.table("users").insert({"tg_id": tg_id}).execute()
        can_audit = True
    else:
        can_audit = user_query.data[0]["is_first_audit_free"]

    if not can_audit:
        return {"status": "error", "message": "Бесплатная попытка использована. Оплатите доступ."}

    # 2. Логика анализа (имитация или реальный вызов)
    # Предположим, results берется из твоего модуля analyzer
    results = {"total": 14195, "items": [{"reason": "Утеря", "amount": 14195, "id": "WB-99"}]} 

    # 3. Помечаем попытку как использованную
    supabase.table("users").update({"is_first_audit_free": False}).eq("tg_id", tg_id).execute()
    
    return {"status": "success", "total_sum": results["total"], "preview": results["items"]}

@app.get("/api/download-claim")
async def download(
    total: str = "0", 
    marketplace: str = "wb", 
    seller_name: str = "Не указано", 
    seller_inn: str = "0", 
    seller_address: str = "-", 
    account: str = "-", 
    bik: str = "-"
):
    # Теперь, если фронт что-то забудет, сервер подставит дефолтное значение и не выдаст 422
    seller_info = {
        "name": seller_name,
        "inn": seller_inn,
        "address": seller_address,
        "account": account,
        "bik": bik
    }
    
    mock_results = {
        "total": total, 
        "items": [{"reason": "Расхождение по отчету", "amount": total, "id": "AUTO-GEN"}]
    }
    
    # ПЕРЕДАЕМ реальный словарь с данными, а не пустой {}
    pdf_content = create_claim_pdf(mock_results, seller_info)
    
    return Response(
        content=bytes(pdf_content), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=claim_{marketplace}.pdf"}
    )









