import random

def get_mock_data(marketplace: str):
    """Генерирует фейковые ошибки для тестов"""
    reasons = [
        "Неверные габариты (логистика x2)",
        "Товар утерян при приемке",
        "Брак не компенсирован",
        "Ошибка логики удержаний"
    ]
    
    mock_results = []
    total_found = 0
    
    # Генерируем от 10 до 30 «ошибок»
    for _ in range(random.randint(10, 30)):
        lost_sum = random.randint(500, 5000)
        total_found += lost_sum
        mock_results.append({
            "order_id": f"654{random.randint(10000, 99999)}21",
            "reason": random.choice(reasons),
            "lost_sum": lost_sum,
            "warehouse": "Коледино" if marketplace == 'wb' else "Хорoг"
        })
        
    return {
        "total_lost": total_found,
        "items": mock_results
    }