import random

async def run_audit(marketplace: str, api_key: str):
    # Здесь будет реальная логика запросов к API
    # Пока оставляем улучшенный симулятор
    if api_key == "DEBUG_TEST":
        reasons = {
            "wb": ["Занижение габаритов", "Утеря на складе", "Недоплата по браку"],
            "ozon": ["Ошибка инвентаризации", "Повреждение при доставке"]
        }
        
        found_items = []
        for _ in range(random.randint(5, 12)):
            found_items.append({
                "id": f"ORD-{random.randint(1000, 9999)}",
                "reason": random.choice(reasons.get(marketplace, ["Ошибка"])),
                "amount": random.randint(300, 4500)
            })
        
        return {
            "total": sum(item["amount"] for item in found_items),
            "items": found_items
        }
    return {"total": 0, "items": []}
