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
    # 1. Получаем полные данные пользователя
    user_query = supabase.table("users").select("*").eq("tg_id", tg_id).execute()

    if not user_query.data:
        # Новый пользователь
        supabase.table("users").insert(
            {"tg_id": tg_id, "is_first_audit_free": True, "has_subscription": False}).execute()
        is_first_free = True
        has_subscription = False
    else:
        # Существующий пользователь
        is_first_free = user_query.data[0]["is_first_audit_free"]
        has_subscription = user_query.data[0].get("has_subscription", False)

    # 2. РЕШАЕМ: Делаем работу или нет?
    # Работаем, если это первый раз ИЛИ если куплена подписка
    can_see_details = is_first_free or has_subscription
    user_data = user_query.data[0] if user_query.data else {}
    try:
        if can_see_details:
        # ВЫПОЛНЯЕМ РЕАЛЬНЫЙ АНАЛИЗ
        results = await run_audit(
            api_key=request.api_key,
            marketplace=request.marketplace,
            is_free_tier=not has_subscription,
            client_id=request.client_id
        )
        is_blurred = False
        if results.get("error") == "invalid_key":
            return {"status": "error", "message": "Неверный API-ключ. Проверьте его в кабинете селлера."}

        # --- МАГИЯ АВТОЗАПОЛНЕНИЯ (теперь здесь!) ---
        # Если в базе еще нет имени селлера, пробуем его зафиксировать
        if results.get("total", 0) >= 0 and not user_data.get("seller_name"):
            # Формируем техническое имя, чтобы юзер видел, что данные подтянулись
            new_name = f"Селлер {request.marketplace.upper()}"
            supabase.table("users").update({"seller_name": new_name}).eq("tg_id", tg_id).execute()

        # Списываем бесплатную попытку
        if is_first_free:
            supabase.table("users").update({"is_first_audit_free": False}).eq("tg_id", tg_id).execute()
        else:
        # ОТКАЗ В ДОСТУПЕ: Заблюренные данные
        results = {
            "total": 42000,
            "items": [
                {"reason": "Аномальная логистика", "amount": "✱✱✱", "id": "скрыто"},
                {"reason": "Ошибка в отчете реализации", "amount": "✱✱✱", "id": "скрыто"}
            ]
        }
    except Exception as e:
        return {"status": "error", "message": f"Ошибка сервера: {str(e)}"}
        is_blurred = True
    return {
        "status": "success",
        "total_sum": results["total"],
        "preview": results["items"],
        "is_blurred": is_blurred
    }

@app.get("/api/download-claim", response_model=None)
async def download(
    total: str = "0", 
    marketplace: str = "wb", 
    seller_name: str = "Не указано", 
    seller_inn: str = "0", 
    seller_address: str = "-", 
    account: str = "-", 
    bik: str = "-"
):
    # Если фронт что-то забудет, сервер подставит дефолтное значение и не выдаст 422
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
    pdf_content = create_claim_pdf(mock_results, seller_info)
    
    return Response(
        content=bytes(pdf_content), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=claim_{marketplace}.pdf"}
    )


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