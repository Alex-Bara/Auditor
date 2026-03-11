from datetime import datetime, timedelta

# МУЛЯЖ ОТВЕТА API WILDBERRIES
# Структура данных на 100% повторяет реальный JSON от API статистики
def fetch_wb_reportDetailByPeriod(api_key: str, date_from: str, date_to: str) -> list:
    """
    В будущем здесь будет:
    headers = {"Authorization": api_key}
    response = httpx.get(f"https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod?dateFrom={date_from}&dateTo={date_to}", headers=headers)
    return response.json()
    """
    print(f"[API MOCK] Запрос к WB. Ключ: {api_key[:5]}... Период: {date_from} - {date_to}")
    
    return [
        {
            "rrid": "884920111", "nm_id": 112233, "sa_name": "Товар А",
            "supplier_oper_name": "Продажа", "delivery_rub": 0, "penalty": 0
        },
        {
            "rrid": "884920112", "nm_id": 112234, "sa_name": "Товар Б",
            "supplier_oper_name": "Логистика", "delivery_rub": 2500, "penalty": 0 # Аномально дорогая логистика
        },
        {
            "rrid": "884920113", "nm_id": 112235, "sa_name": "Товар В",
            "supplier_oper_name": "Штраф", "delivery_rub": 0, "penalty": 10000 # Крупный штраф (часто за габариты или ИЗ)
        },
        {
            "rrid": "884920114", "nm_id": 112233, "sa_name": "Товар А",
            "supplier_oper_name": "Логистика", "delivery_rub": 55, "penalty": 0 # Нормальная логистика
        }
    ]

# АНАЛИЗАТОР WB (Бизнес-логика)
def process_wb_data(raw_data: list) -> dict:
    discrepancies = []
    total_found = 0

    for item in raw_data:
        # Логика 1: Ищем аномально дорогую логистику (например, больше 1000 руб за единицу)
        # В реальности тут нужно сверять с базовым тарифом по габаритам
        if item.get("supplier_oper_name") == "Логистика" and item.get("delivery_rub", 0) > 1000:
            amount = item["delivery_rub"]
            total_found += amount
            discrepancies.append({
                "id": item["rrid"],
                "reason": f"Завышенная логистика ({item['sa_name']})",
                "amount": amount
            })

        # Логика 2: Вылавливаем все штрафы для дальнейшего оспаривания
        if item.get("supplier_oper_name") == "Штраф" and item.get("penalty", 0) > 0:
            amount = item["penalty"]
            total_found += amount
            discrepancies.append({
                "id": item["rrid"],
                "reason": f"Необоснованный штраф ({item['sa_name']})",
                "amount": amount
            })

    return {
        "total": total_found,
        "items": discrepancies
    }


# ==========================================
# МУЛЯЖ ОТВЕТА API OZON
# ==========================================
def fetch_ozon_transactions(api_key: str, date_from: str, date_to: str) -> list:
    """
    В реальности эндпоинт: https://api-seller.ozon.ru/v3/finance/transaction/list
    Требует заголовки: {"Client-Id": client_id, "Api-Key": api_key}
    """
    print(f"[API MOCK] Запрос к OZON. Период: {date_from} - {date_to}")

    return [
        {
            "operation_id": "11223344-1", "operation_type": "Delivery",
            "delivery_charge": 2500, "amount": -2500, "items": [{"name": "Товар X", "sku": 778899}]
        },  # Аномально дорогая логистика
        {
            "operation_id": "11223344-2", "operation_type": "ReturnAndCancellation",
            "delivery_charge": 0, "amount": 0, "items": [{"name": "Товар Y", "sku": 778890}]
        },  # Отмена, статус завис (потеряшка)
        {
            "operation_id": "11223344-3", "operation_type": "ItemDefectPenalty",
            "delivery_charge": 0, "amount": -8000, "items": [{"name": "Товар Z", "sku": 778891}]
        },  # Штраф за брак (спорный)
        {
            "operation_id": "11223344-4", "operation_type": "Delivery",
            "delivery_charge": 75, "amount": -75, "items": [{"name": "Товар X", "sku": 778899}]
        }  # Нормальная логистика
    ]


# ==========================================
# АНАЛИЗАТОР OZON (Бизнес-логика)
# ==========================================
def process_ozon_data(raw_data: list) -> dict:
    discrepancies = []
    total_found = 0

    for item in raw_data:
        item_name = item.get("items", [{}])[0].get("name", "Неизвестный товар")

        # Логика 1: Аномально дорогая логистика (сбой расчета объемного веса)
        if item.get("operation_type") == "Delivery" and item.get("delivery_charge", 0) > 1000:
            amount = item["delivery_charge"]
            total_found += amount
            discrepancies.append({
                "id": item["operation_id"],
                "reason": f"Завышенная логистика ({item_name})",
                "amount": amount
            })

        # Логика 2: Штрафы за брак/повреждения (часто вина логистики Ozon)
        if item.get("operation_type") in ["ItemDefectPenalty", "Penalty"]:
            amount = abs(item.get("amount", 0))
            if amount > 0:
                total_found += amount
                discrepancies.append({
                    "id": item["operation_id"],
                    "reason": f"Спорный штраф ({item_name})",
                    "amount": amount
                })

        # Логика 3: Потеряшки при отмене
        if item.get("operation_type") == "ReturnAndCancellation" and item.get("amount") == 0:
            amount = 3500  # Примерная оценочная стоимость утерянного товара
            total_found += amount
            discrepancies.append({
                "id": item["operation_id"],
                "reason": f"Утеряно при отмене ({item_name})",
                "amount": amount
            })

    return {
        "total": total_found,
        "items": discrepancies
    }

# ГЛАВНАЯ ФУНКЦИЯ ДЛЯ MAIN.PY
def run_audit(api_key: str, marketplace: str, is_free_tier: bool, client_id: str = None) -> dict:
    # Определяем период
    end_date = datetime.now()
    if is_free_tier:
        start_date = end_date - timedelta(days=60)
    else:
        start_date = end_date - timedelta(days=365)

    str_start = start_date.strftime("%Y-%m-%d")
    str_end = end_date.strftime("%Y-%m-%d")

    # Маршрутизатор маркетплейсов
    if marketplace == "wb":
        raw_data = fetch_wb_reportDetailByPeriod(api_key, str_start, str_end)
        return process_wb_data(raw_data)

    elif marketplace == "ozon":
        # В будущем мы передадим client_id в реальный запрос
        raw_data = fetch_ozon_transactions(api_key, str_start, str_end)
        return process_ozon_data(raw_data)

    else:
        raise ValueError("Неизвестный маркетплейс")
