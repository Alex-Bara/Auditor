from datetime import datetime, timedelta

# 1. МУЛЯЖ ОТВЕТА API WILDBERRIES
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

# 2. АНАЛИЗАТОР (Бизнес-логика)
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

# 3. ГЛАВНАЯ ФУНКЦИЯ ДЛЯ MAIN.PY
def run_audit(api_key: str, marketplace: str, is_free_tier: bool) -> dict:
    if marketplace != "wb":
        return {"total": 0, "items": [{"id": "0", "reason": "Парсер для Ozon в разработке", "amount": 0}]}

    # Формируем период в зависимости от подписки
    end_date = datetime.now()
    if is_free_tier:
        start_date = end_date - timedelta(days=60) # 2 месяца назад
    else:
        start_date = end_date - timedelta(days=365) # 1 год назад (или кастомно)

    # WB требует формат YYYY-MM-DD
    str_start = start_date.strftime("%Y-%m-%d")
    str_end = end_date.strftime("%Y-%m-%d")

    # Получаем сырые данные
    raw_data = fetch_wb_reportDetailByPeriod(api_key, str_start, str_end)
    
    # Анализируем и возвращаем
    return process_wb_data(raw_data)
