const tg = window.Telegram.WebApp;
tg.expand(); // Разворачиваем на весь экран

function renderResults(data) {
    const listContainer = document.getElementById('result-details');
    listContainer.innerHTML = ''; // Очистка

    data.preview.forEach(item => {
        const row = `
            <div class="item-row">
                <div>
                    <span class="badge">${item.reason}</span><br>
                    <small>Заказ: ${item.order_id}</small>
                </div>
                <div style="font-weight:bold">+${item.lost_sum} ₽</div>
            </div>
        `;
        listContainer.innerHTML += row;
    });

    document.getElementById('result-sum').innerText = data.total_sum.toLocaleString();
}

async function runAudit() {
    const apiKey = document.getElementById('api-key').value;
    if (!apiKey) return alert("Введите ключ!");

    // Переключаем на экран загрузки
    document.getElementById('screen-input').style.display = 'none';
    document.getElementById('screen-loading').style.display = 'block';

    try {
        const response = await fetch('/api/start-audit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ api_key: apiKey, marketplace: 'wb' })
        });
        const data = await response.json();

        // Показываем результат
        document.getElementById('screen-loading').style.display = 'none';
        document.getElementById('screen-result').style.display = 'block';
        document.getElementById('result-sum').innerText = data.total_lost.toLocaleString();
        document.getElementById('result-details').innerText = data.masked_data;

    } catch (e) {
        alert("Ошибка связи с сервером");
    }
}