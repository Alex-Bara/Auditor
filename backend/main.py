from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddlware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_methods=["*"],
                   allow_headers=["*"]
                  )

def mask_id(identifier: str) -> str:
    """Превращает '123456789' в '123***89'"""
    s = str(identifier)
    if len(s) < 5:
        return "***"
    return f"{s[:3]}***{s[-2:]}"

# Пример обработки списка заказов для превью
def prepare_preview(raw_data: list):
    preview = []
    for item in raw_data[:5]: # Показываем только первые 5 для затравки
        preview.append({
            "order_id": mask_id(item["order_id"]),
            "reason": item["reason"],
            "lost_sum": item["lost_sum"]
        })
    return preview

class AuditRequest(BaseModel):
    api_key: str
    marketplace: str  # 'wb', 'ozon', 'yandex'

# Имитация разных алгоритмов для площадок
async def audit_wb(key: str):
    # Логика для WB: Сверка еженедельных отчетов
    return {"total": 45000, "desc": "Расхождения в логистике Коледино"}

async def audit_ozon(key: str):
    # Логика для Ozon: Поиск утерь при инвентаризации
    return {"total": 28000, "desc": "Недоплата за поврежденный товар"}

@app.post("/api/start-audit")
async def start_audit(request: AuditRequest):
    await asyncio.sleep(2) # Имитация бурной деятельности
    
    if request.api_key == "DEBUG_TEST":
        raw_data = get_mock_data(request.marketplace)
    else:
        # Тут в будущем будет реальный запрос к API ВБ/Озон
        raw_data = {"total_lost": 0, "items": []} 

    # Маскируем данные перед отправкой на фронт
    preview_items = prepare_preview(raw_data["items"])
    
    return {
        "status": "success",
        "total_sum": raw_data["total_lost"],
        "preview": preview_items,
        "count_all": len(raw_data["items"])

    }



