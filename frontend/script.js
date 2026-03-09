const tg = window.Telegram.WebApp;
let lastAuditData = { total: 0, marketplace: 'wb' };
tg.expand(); // Разворачиваем на весь экран

function renderResults(data) {
    const listContainer = document.getElementById('result-details');
    if (!listContainer) return;
    listContainer.innerHTML = ''; 

    // Проверяем, что preview существует и это массив
    if (data.preview && Array.isArray(data.preview)) {
        data.preview.forEach(item => {
            const row = `
                <div class="item-row" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div>
                        <span class="badge" style="background: #2481cc; color: white; padding: 2px 5px; border-radius: 4px; font-size: 10px;">${item.reason}</span><br>
                        <small>ID: ${item.order_id}</small>
                    </div>
                    <div style="font-weight:bold; color: #31b545;">+${item.totalt_sum} ₽</div>
                </div>
                `;
            listContainer.innerHTML += row;
        });
    }
}

async function runAudit() {
    const apiKey = document.getElementById('api-key').value;
    if (!apiKey) return alert("Введите ключ!");

    // Переключаем на экран загрузки
    document.getElementById('screen-input').style.display = 'none';
    document.getElementById('screen-loading').style.display = 'block';

    try {
        const response = await fetch('https://auditor-ixog.onrender.com/api/start-audit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ api_key: apiKey, marketplace: 'wb' })
        });
        const data = await response.json();
        // Сохраняем данные для будущего скачивания
        lastAuditData.total = data.total_sum;
        lastAuditData.marketplace = document.querySelector('input[name="marketplace"]:checked').value;
        
        // Показываем кнопку скачивания
        document.getElementById('download-btn').style.display = 'block';
        
        renderResults(data);

        // Показываем результат
        document.getElementById('screen-loading').style.display = 'none';
        document.getElementById('screen-result').style.display = 'block';
        document.getElementById('result-sum').innerText = data.total_sum.toLocaleString();
        document.getElementById('result-details').innerText = data.masked_data;

    } catch (e) {
        alert("Ошибка связи с сервером! Попробуйте позже.");
    }

}








