const tg = window.Telegram.WebApp;
let lastAuditData = { total: 0, marketplace: 'wb' };
let loadingInterval;

const BACKEND_URL = "https://auditor-ixog.onrender.com";
tg.expand(); 

function startLoadingAnimation(marketplace) {
    const loadingText = document.getElementById('loading-text');
    const steps = [
        "Проверка ключей доступа...",
        "Подключение к API " + (marketplace === 'wb' ? 'Wildberries' : 'Ozon') + "...",
        "Загрузка финансовых отчетов за 60 дней...",
        "Анализ тарифов логистики...",
        "Поиск необоснованных штрафов...",
        "Сверка возвратов и отмен...",
        "Формирование итогового отчета..."
    ];

    let currentStep = 0;
    loadingText.innerText = steps[0];

    loadingInterval = setInterval(() => {
        currentStep++;
        if (currentStep < steps.length) {
            loadingText.innerText = steps[currentStep];
        }
    }, 2000); // Меняем текст каждые 2 секунды
}

function stopLoadingAnimation() {
    if (loadingInterval) clearInterval(loadingInterval);
}

let userId;
if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    userId = tg.initDataUnsafe.user.id;
} else {
    userId = 123456789;
    console.warn("Telegram WebApp не обнаружен. Используем тестовый ID.");
}

function showHelp(type) {
    let message = "";
    if (type === 'api') {
        message = "1. Зайдите в Личный кабинет селлера.\n2. Перейдите в Настройки -> API.\n3. Создайте новый ключ с типом 'Статистика'.\n\nЭто безопасно: мы не имеем доступа к вашим заказам или изменению цен.";
    }
    tg.showAlert(message);
}

function showInputScreen() {
    document.getElementById('screen-loading').style.display = 'none';
    document.getElementById('screen-result').style.display = 'none'; // Скрываем результаты
    document.getElementById('screen-input').style.display = 'block'; // Показываем ввод
}

async function loadUserData() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/get-profile?tg_id=${userId}`);
        const data = await response.json();

        if (data.status === "success" && data.profile) {
            const p = data.profile;
            const fields = {
                'seller-name': p.seller_name,
                'seller-inn': p.inn,
                'seller-address': p.address,
                'seller-bik': p.bik,
                'seller-account': p.account
            };

            // Заполняем поля только если они существуют в DOM
            for (const [id, value] of Object.entries(fields)) {
                const el = document.getElementById(id);
                if (el) el.value = value || '';
            }
        }
    } catch (e) {
        console.error("Ошибка загрузки данных профиля:", e);
    }
}

async function saveProfile() {
    const profile = {
        seller_name: document.getElementById('seller-name').value,
        inn: document.getElementById('seller-inn').value,
        address: document.getElementById('seller-address').value,
        bik: document.getElementById('seller-bik').value,
        account: document.getElementById('seller-account').value
    };

    const tg_id = window.Telegram.WebApp.initDataUnsafe.user.id;

    const response = await fetch(`/api/save-profile?tg_id=${tg_id}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(profile)
    });

    const res = await response.json();
    if(res.status === 'success') {
        tg.showAlert("Данные успешно сохранены!");
    }
}

document.querySelectorAll('input[name="marketplace"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const clientIdGroup = document.getElementById('client-id-group');
        const apiKeyLabel = document.getElementById('api-key-label');
        const apiKeyInput = document.getElementById('api-key');

        if (this.value === 'ozon') {
            clientIdGroup.style.display = 'block';
            apiKeyLabel.innerText = 'API-ключ (Ozon)';
            apiKeyInput.placeholder = 'Вставьте API-ключ Ozon...';
        } else {
            clientIdGroup.style.display = 'none';
            apiKeyLabel.innerText = 'API-ключ (Статистика WB)';
            apiKeyInput.placeholder = 'Вставьте токен WB...';
        }
    });
});

function downloadPDF() {
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
    const clientId = document.getElementById('client-id').value;

    if (!apiKey) return tg.showAlert("Введите API-ключ!");
    if (marketplace === 'ozon' && !clientId) return tg.showAlert("Введите Client-ID для Ozon!");

    const auditData = {
        api_key: apiKey,
        marketplace: marketplace,
        client_id: marketplace === 'ozon' ? clientId : null
    };

    // Переключаем экраны
    document.getElementById('screen-input').style.display = 'none';
    document.getElementById('screen-loading').style.display = 'block';

    // Запускаем анимацию шагов
    startLoadingAnimation(marketplace);

    try {
        const response = await fetch(`${BACKEND_URL}/api/start-audit?tg_id=${userId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(auditData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || "Ошибка сервера");
        }

        const data = await response.json();
        stopLoadingAnimation();

        if (data.status === "success") {
            lastAuditData.total = data.total_sum;
            lastAuditData.marketplace = marketplace;

            document.getElementById('screen-loading').style.display = 'none';
            document.getElementById('screen-result').style.display = 'block';
            document.getElementById('result-sum').innerText = data.total_sum.toLocaleString();

            renderResults(data);
            await loadUserData();

            const unlockContainer = document.getElementById('unlock-container');
            const downloadBtn = document.getElementById('download-btn');

            if (data.is_blurred) {
                unlockContainer.style.display = 'block';
                downloadBtn.style.display = 'none';
                document.getElementById('found-sum-hint').innerText = data.total_sum.toLocaleString();
            } else {
                unlockContainer.style.display = 'none';
                downloadBtn.style.display = 'block';
            }
        } else {
            tg.showAlert(data.message || "Ошибка при сканировании");
            showInputScreen();
        }
    } catch (e) {
        stopLoadingAnimation();
        console.error(e);
        tg.showAlert("Ошибка: " + e.message);
        showInputScreen();
    }
}
