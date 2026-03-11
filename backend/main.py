from datetime import datetime

from fastapi import FastAPI, Response, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from analyzer import run_audit
from claims import create_claim_pdf
from pydantic import BaseModel
from supabase import create_client, Client
from typing import Optional
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
class UserProfile(BaseModel):
    seller_name: str
    inn: str
    address: str
    account: str
    bik: str
    phone: Optional[str] = None

class AuditRequest(BaseModel):
    api_key: str
    marketplace: str
    client_id: Optional[str] = None

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
# 3.Портим данные перед отправкой, если is_blurred = True
def mask_results(results, should_mask):
    if not should_mask:
        return results

    masked_items = []
    for item in results["items"]:
        masked_items.append({
            "id": "ID_HIDDEN",  # Вместо реального ID
            "reason": item["reason"],  # Причину можно оставить для интереса
            "amount": "???"  # Прячем сумму
        })
    return {"total": results["total"], "items": masked_items}

# 4. ЭНДПОИНТЫ
@app.post("/api/start-audit")
async def start_audit(request: AuditRequest, tg_id: int = Query(...)):
    user_query = supabase.table("users").select("*").eq("tg_id", tg_id).execute()

    # 1. Регистрация нового или получение старого пользователя
    if not user_query.data:
        new_user = {"tg_id": tg_id, "is_first_audit_free": True, "has_subscription": False}
        supabase.table("users").insert(new_user).execute()
        is_first_free, has_subscription = True, False
        user_data = new_user
    else:
        user_data = user_query.data[0]
        is_first_free = user_data.get("is_first_audit_free", False)
        has_subscription = user_data.get("has_subscription", False)

    # 2. ЖЕСТКАЯ ПРОВЕРКА ДОСТУПА
    if not (is_first_free or has_subscription):
        return {
            "status": "payment_required",
            "message": "Бесплатный период окончен. Для продолжения выберите тариф."
        }

    # 3. ЕСЛИ ДОСТУП ЕСТЬ — РАБОТАЕМ
    try:
        results = await run_audit(
            api_key=request.api_key,
            marketplace=request.marketplace,
            is_free_tier=not has_subscription, # Если подписки нет, значит это free_tier (2 месяца)
            client_id=request.client_id
        )

        if isinstance(results, dict) and results.get("error") == "invalid_key":
            return {"status": "error", "message": "Неверный API-ключ"}

        # Сохраняем результаты в JSONB для будущего PDF
        supabase.table("users").update({
            "last_audit_results": results,
            "is_first_audit_free": False # Сразу сгорает попытка после успешного анализа
        }).eq("tg_id", tg_id).execute()

        return {
            "status": "success",
            "total_sum": results["total"],
            "preview": results["items"]
        }

    except Exception as e:
        return {"status": "error", "message": f"Ошибка анализа: {str(e)}"}

@app.get("/api/download-claim")
async def download(tg_id: int = Query(...), marketplace: str = "wb"):
    try:
        # 1. Достаем данные пользователя и его последний аудит из базы
        user_query = supabase.table("users").select("*").eq("tg_id", tg_id).execute()

        if not user_query.data:
            return {"status": "error", "message": "Пользователь не найден"}

        user_data = user_query.data[0]

        # 2. Формируем словарь селлера (из того, что он сохранил в профиле)
        seller_info = {
            "name": user_data.get("seller_name", "Не указано"),
            "inn": user_data.get("inn", "0"),
            "address": user_data.get("address", "-"),
            "account": user_data.get("account", "-"),
            "bik": user_data.get("bik", "-")
        }

        # 3. Достаем результаты последнего аудита (которые мы сохранили в start_audit)
        # Предполагаем, что ты сохраняешь их в колонку last_audit_results (JSONB)
        audit_results = user_data.get("last_audit_results")

        if not audit_results:
            return {"status": "error", "message": "Сначала запустите аудит"}

        # 4. Генерируем PDF с реальными артикулами и ID
        pdf_content = create_claim_pdf(audit_results, seller_info, marketplace)

        return Response(
            content=bytes(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Pretenziya_{marketplace}_{tg_id}.pdf"
            }
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/save-profile")
async def save_profile(profile: UserProfile, tg_id: int = Query(...)):
    try:
        data = {
            "seller_name": profile.seller_name,
            "inn": profile.inn,
            "address": profile.address,
            "account": profile.account,
            "bik": profile.bik,
            "phone": profile.phone
        }

        result = supabase.table("users").update(data).eq("tg_id", tg_id).execute()

        return {"status": "success", "message": "Реквизиты сохранены"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Также обновим получение данных, чтобы при входе в приложение
# мы могли подтянуть старые реквизиты
@app.get("/api/get-profile")
async def get_profile(tg_id: int = Query(...)):
    user = supabase.table("users").select("*").eq("tg_id", tg_id).execute()
    if user.data:
        return {"status": "success", "profile": user.data[0]}
    return {"status": "error", "message": "User not found"}