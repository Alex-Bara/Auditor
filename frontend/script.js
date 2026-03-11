const tg = window.Telegram.WebApp;
let lastAuditData = { total: 0, marketplace: 'wb' };
const userId = tg.initDataUnsafe?.user?.id || 12345; 
const BACKEND_URL = "https://auditor-ixog.onrender.com";
tg.expand(); 


// Слушатель переключателей маркетплейсов
document.querySelectorAll('input[name="marketplace"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const clientIdGroup = document.getElementById('client-id-group');
        const apiKeyLabel = document.getElementById('api-key-label');
        const apiKeyInput = document.getElementById('api-key');

        if (this.value === 'ozon') {
            // Показываем Client ID, меняем подсказки для Ozon
            clientIdGroup.style.display = 'block';
            apiKeyLabel.innerText = 'API-ключ (Ozon)';
            apiKeyInput.placeholder = 'Вставьте API-ключ Ozon...';
        } else {
            // Прячем Client ID, возвращаем подсказки для WB
            clientIdGroup.style.display = 'none';
            apiKeyLabel.innerText = 'API-ключ (Статистика WB)';
            apiKeyInput.placeholder = 'Вставьте токен WB...';
        }
    });
});

function downloadPDF() {
    // Собираем данные из полей
    const name = document.getElementById('seller-name').value;
    const inn = document.getElementById('seller-inn').value;
    const address = document.getElementById('seller-address').value;
    const bik = document.getElementById('seller-bik')?.value || ""; 
    const acc = document.getElementById('seller-account')?.value || ""; 

    const params = new URLSearchParams({
        total: lastAuditData.total || 0,
        marketplace: lastAuditData.marketplace,
        seller_name: name,
        seller_inn: inn,
        seller_address: address,
        account: acc,
        bik: bik
    });
    
    const url = `${BACKEND_URL}/api/download-claim?${params.toString()}`;
    Telegram.WebApp.openLink(url);
}

function renderResults(data) {
    const listContainer = document.getElementById('result-details');
    listContainer.innerHTML = '';

    data.preview.forEach(item => {
        // Если данные заблюрены, добавляем класс.
        // Но даже если его уберут, там будет текст "ID_HIDDEN"
        const blurClass = data.is_blurred ? 'masked-list' : '';

        const row = `
            <div class="item-row ${blurClass}">
                <div>
                    <span>${item.reason}</span><br>
                    <small>ID: ${item.id}</small>
                </div>
                <div class="amount">+${item.amount} ₽</div>
            </div>
        `;
        listContainer.innerHTML += row;
    });
}

async function runAudit() {
    const apiKey = document.getElementById('api-key').value;
    const marketplace = document.querySelector('input[name="marketplace"]:checked').value;
    const clientId = document.getElementById('client-id').value; // Берем Client ID

    if (!apiKey) return alert("Введите ключ!");
    // Валидация: если выбран Ozon, Client ID обязателен
    if (marketplace === 'ozon' && !clientId) return alert("Введите Client-ID для Ozon!");

    // Собираем объект данных для отправки
    const auditData = {
        api_key: apiKey,
        marketplace: marketplace,
        client_id: marketplace === 'ozon' ? clientId : null // Добавили поле
    };

    // Переключаем экраны
    document.getElementById('screen-input').style.display = 'none';
    document.getElementById('screen-loading').style.display = 'block';

    try {
        const response = await fetch(`${BACKEND_URL}/api/start-audit?tg_id=${userId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(auditData)
        });

        const data = await response.json();

        if (data.status === "success") {
            lastAuditData.total = data.total_sum;
            lastAuditData.marketplace = marketplace;

            document.getElementById('screen-loading').style.display = 'none';
            document.getElementById('screen-result').style.display = 'block';

            document.getElementById('result-sum').innerText = data.total_sum.toLocaleString();

            renderResults(data);

            const unlockContainer = document.getElementById('unlock-container');
            const downloadBtn = document.getElementById('download-btn');

            // Если данные НЕ заблюрены (первый раз или есть подписка) - показываем скачивание PDF
            if (data.is_blurred) {
                // ПОКАЗЫВАЕМ кнопку оплаты, ПРЯЧЕМ кнопку скачивания
                unlockContainer.style.display = 'block';
                downloadBtn.style.display = 'none';
                document.getElementById('found-sum-hint').innerText = data.total_sum.toLocaleString();
            } else {
                document.getElementById('download-btn').style.display = 'block';
                unlockContainer.style.display = 'none';
            }
        } else {
            const errorMsg = data.message || JSON.stringify(data.detail) || "Неизвестная ошибка";
            alert("Ошибка: " + errorMsg);
            // Возвращаем на главный экран при ошибке
            document.getElementById('screen-loading').style.display = 'none';
            document.getElementById('screen-input').style.display = 'block';
        }

    } catch (e) {
        console.error(e);
        alert("Ошибка связи с сервером!");
        document.getElementById('screen-loading').style.display = 'none';
        document.getElementById('screen-input').style.display = 'block';
    }
}

