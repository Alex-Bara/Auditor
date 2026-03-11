from datetime import datetime, timedelta
import httpx
import asyncio


# ==========================================
# 1. WILDBERRIES: ГЛУБОКИЙ АНАЛИЗ
# ==========================================
async def fetch_wb_reportDetailByPeriod(api_key: str, date_from: str, date_to: str) -> list:
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod"
    headers = {"Authorization": api_key}
    params = {"dateFrom": date_from, "dateTo": date_to}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 401:
                return {"error": "invalid_key"}
            if response.status_code == 200:
                return response.json() or []
            return []
    except Exception:
        return []


def process_wb_data(raw_data: list) -> dict:
    if isinstance(raw_data, dict) and raw_data.get("error"):
        return raw_data

    discrepancies = []
    total_found = 0

    for item in raw_data:
        amount = 0
        reason = ""
        op_name = item.get("supplier_oper_name", "")

        # Аномальная логистика (выше среднего порога)
        delivery = item.get("delivery_rub", 0)
        if op_name == "Логистика" and delivery > 500:  # Порог можно снизить для точности
            amount = delivery
            reason = f"Проверка тарифа логистики ({item.get('sa_name', 'Товар')})"

        # Штрафы всех типов
        elif "Штраф" in op_name or item.get("penalty", 0) > 0:
            amount = item.get("penalty", 0)
            reason = f"Необоснованный штраф: {item.get('bonus_type_name', 'Причина скрыта')}"

        # Скрытые корректировки (отрицательные выплаты)
        elif op_name == "Корректировка" and item.get("ppvz_vw_with_nds", 0) < 0:
            amount = abs(item.get("ppvz_vw_with_nds", 0))
            reason = f"Скрытая корректировка баланса ({item.get('gi_id', 'ID не указан')})"

        # Доплаты за хранение/приемку (если они аномальны)
        elif "Доплата" in op_name:
            amount = abs(item.get("additional_payment", 0))
            reason = f"Аномальная доплата за складские услуги"

        if amount > 0:
            total_found += amount
            discrepancies.append({
                "id": str(item.get("rrid", "N/A")),
                "reason": reason,
                "amount": round(amount, 2)
            })

    return {"total": round(total_found, 2), "items": discrepancies}


# ==========================================
# 2. OZON: ФИНАНСОВЫЙ РЕНТГЕН
# ==========================================
async def fetch_ozon_transactions(client_id: str, api_key: str, date_from: str, date_to: str) -> list:
    url = "https://api-seller.ozon.ru/v3/finance/transaction/list"
    headers = {"Client-Id": client_id, "Api-Key": api_key, "Content-Type": "application/json"}

    payload = {
        "filter": {
            "date": {"from": f"{date_from}T00:00:00Z", "to": f"{date_to}T23:59:59Z"},
            "transaction_type": "all"
        },
        "page": 1, "page_size": 1000
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 401:
                return {"error": "invalid_key"}
            if response.status_code == 200:
                return response.json().get("result", {}).get("operations", [])
            return []
    except Exception:
        return []


def process_ozon_data(raw_data: list) -> dict:
    if isinstance(raw_data, dict) and raw_data.get("error"):
        return raw_data

    discrepancies = []
    total_found = 0

    for item in raw_data:
        op_type = item.get("operation_type", "")
        amount = 0
        reason = ""

        # Услуги по возвратам (DirectClick, ReturnFlow) - зона частых ошибок
        if "Return" in op_type or "Cancel" in op_type:
            amount = abs(item.get("amount", 0))
            reason = f"Списание за возврат/отмену (Проверка обоснованности)"

        # Скрытые сервисные сборы (LastMile, Fulfillment)
        elif op_type in ["MarketplaceServiceItemFulfillment", "MarketplaceServiceItemDirectClick"]:
            charge = abs(item.get("amount", 0))
            if charge > 200:  # Фильтруем мелочь, ищем крупные аномалии
                amount = charge
                reason = f"Завышенный сервисный сбор ({op_type})"

        # Прямые штрафы
        elif "Penalty" in op_type or "Defect" in op_type:
            amount = abs(item.get("amount", 0))
            reason = f"Штраф Ozon за дефект/нарушение"

        if amount > 0:
            total_found += amount
            discrepancies.append({
                "id": str(item.get("operation_id", "N/A")),
                "reason": reason,
                "amount": round(amount, 2)
            })

    return {"total": round(total_found, 2), "items": discrepancies}


# ==========================================
# 3. ГЛАВНЫЙ ВХОД
# ==========================================
async def run_audit(api_key: str, marketplace: str, is_free_tier: bool, client_id: str = None) -> dict:
    end_date = datetime.now()
    days = 60 if is_free_tier else 365
    start_date = end_date - timedelta(days=days)
    str_start, str_end = start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    if marketplace == "wb":
        raw = await fetch_wb_reportDetailByPeriod(api_key, str_start, str_end)
        return process_wb_data(raw)
    elif marketplace == "ozon":
        if not client_id: return {"total": 0, "items": [], "error": "Missing Client-ID"}
        raw = await fetch_ozon_transactions(client_id, api_key, str_start, str_end)
        return process_ozon_data(raw)

    return {"total": 0, "items": []}