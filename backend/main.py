from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# 3. САМ ЭНДПОИНТ (теперь он будет видеть функции выше)
@app.post("https://auditor-ixog.onrender.com/api/start-audit")
async def start_audit(request: AuditRequest):
    await asyncio.sleep(2) # Имитация работы
    
    if request.api_key == "DEBUG_TEST":
        raw_data = get_mock_data(request.marketplace)
    else:
        # Пока нет интеграции с реальным API, отдаем пустоту
        raw_data = {"total_lost": 0, "items": []}

    preview_items = prepare_preview(raw_data["items"])
    
    return {
        "status": "success",
        "total_sum": raw_data["total_lost"],
        "preview": preview_items,
        "count_all": len(raw_data["items"])
    }
