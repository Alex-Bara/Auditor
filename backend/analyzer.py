from datetime import datetime, timedelta
import httpx
import asyncio

async def fetch_wb_seller_info(api_key: str) -> dict:
    """Получаем данные о продавце из WB (используем эндпоинт лимитов или тарифов)"""
    url = "https://common-api.wildberries.ru/api/v1/info" # Пример эндпоинта
    headers = {"Authorization": api_key}
    async with httpx.AsyncClient() as client:
        try:
            # Если спец. эндпоинта нет под рукой, WB часто отдает заголовок или
            # данные о владельце в других запросах.
            # Для теста вернем пустой или парсим из доступных.
            return {"name": "ООО Загрузка...", "inn": ""}
        except:
            return {}

async def fetch_ozon_seller_info(client_id: str, api_key: str) -> dict:
    """Ozon в некоторых отчетах сразу пишет название компании"""
    # В v3/finance/transaction/list данных о самом селлере мало,
    # но их можно вытянуть из /v1/whoami (условный эндпоинт)
    return {"name": f"Seller #{client_id}", "inn": ""}

# ==========================================
# 1. WILDBERRIES: РАБОТА С API СТАТИСТИКИ
# ==========================================
async def fetch_wb_reportDetailByPeriod(api_key: str, date_from: str, date_to: str) -> list:
    if api_key == "TEST":
        # Возвращаем те самые данные, которые были у нас раньше в муляже
        return [
            {"rrid": "123", "supplier_oper_name": "Логистика", "delivery_rub": 1500, "sa_name": "Тест Товар"},
            {"rrid": "124", "supplier_oper_name": "Штраф", "penalty": 5000, "sa_name": "Брак"}
        ]
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod"
    headers = {"Authorization": api_key}
    params = {"dateFrom": date_from, "dateTo": date_to}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json() or []
            elif response.status_code == 401:
                print("Ошибка: Неверный токен WB")
                return []
            else:
                print(f"WB API Error {response.status_code}: {response.text}")
                return []
    except Exception as e:
        print(f"Ошибка сети WB: {e}")
        return []


def process_wb_data(raw_data: list) -> dict:
    discrepancies = []
    total_found = 0

    for item in raw_data:
        # Логика: Завышенная логистика
        # rrid - уникальный ID операции в WB
        delivery = item.get("delivery_rub", 0)
        if item.get("supplier_oper_name") == "Логистика" and delivery > 1000:
            total_found += delivery
            discrepancies.append({
                "id": str(item.get("rrid", "N/A")),
                "reason": f"Завышенная логистика WB ({item.get('sa_name', 'Товар')})",
                "amount": delivery
            })

        # Логика: Штрафы
        penalty = item.get("penalty", 0)
        if item.get("supplier_oper_name") == "Штраф" and penalty > 0:
            total_found += penalty
            discrepancies.append({
                "id": str(item.get("rrid", "N/A")),
                "reason": f"Штраф WB ({item.get('sa_name', 'Товар')})",
                "amount": penalty
            })

    return {"total": total_found, "items": discrepancies}


# ==========================================
# 2. OZON: РАБОТА С ФИНАНСОВЫМ API
# ==========================================
async def fetch_ozon_transactions(client_id: str, api_key: str, date_from: str, date_to: str) -> list:
    url = "https://api-seller.ozon.ru/v3/finance/transaction/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }

    # Ozon требует строгий формат ISO8601
    payload = {
        "filter": {
            "date": {
                "from": f"{date_from}T00:00:00Z",
                "to": f"{date_to}T23:59:59Z"
            },
            "transaction_type": "all"
        },
        "page": 1,
        "page_size": 1000
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json().get("result", {}).get("operations", [])
            else:
                print(f"Ozon API Error {response.status_code}: {response.text}")
                return []
    except Exception as e:
        print(f"Ошибка сети Ozon: {e}")
        return []


def process_ozon_data(raw_data: list) -> dict:
    discrepancies = []
    total_found = 0

    for item in raw_data:
        # У Ozon название товара зарыто в массиве items
        items_list = item.get("items", [])
        item_name = items_list[0].get("name", "Товар Ozon") if items_list else "Товар Ozon"

        # Логика: Аномальная логистика
        delivery = abs(item.get("delivery_charge", 0))
        if item.get("operation_type") == "Delivery" and delivery > 1000:
            total_found += delivery
            discrepancies.append({
                "id": str(item.get("operation_id", "N/A")),
                "reason": f"Логистика Ozon ({item_name})",
                "amount": delivery
            })

        # Логика: Спорные штрафы
        if item.get("operation_type") in ["ItemDefectPenalty", "Penalty"]:
            penalty = abs(item.get("amount", 0))
            if penalty > 0:
                total_found += penalty
                discrepancies.append({
                    "id": str(item.get("operation_id", "N/A")),
                    "reason": f"Штраф Ozon ({item_name})",
                    "amount": penalty
                })

    return {"total": total_found, "items": discrepancies}


# ==========================================
# 3. ГЛАВНЫЙ ВХОД (ASYNC)
# ==========================================
async def run_audit(api_key: str, marketplace: str, is_free_tier: bool, client_id: str = None) -> dict:
    end_date = datetime.now()
    days = 60 if is_free_tier else 365
    start_date = end_date - timedelta(days=days)

    str_start = start_date.strftime("%Y-%m-%d")
    str_end = end_date.strftime("%Y-%m-%d")

    if marketplace == "wb":
        raw = await fetch_wb_reportDetailByPeriod(api_key, str_start, str_end)
        return process_wb_data(raw)

    elif marketplace == "ozon":
        if not client_id:
            return {"total": 0, "items": [], "error": "Missing Client-ID"}
        raw = await fetch_ozon_transactions(client_id, api_key, str_start, str_end)
        return process_ozon_data(raw)

    return {"total": 0, "items": []}