const tg = window.Telegram.WebApp;
let lastAuditData = { total: 0, marketplace: 'wb' };
let loadingInterval;

const BACKEND_URL = "https://auditor-ixog.onrender.com";
tg.expand(); 

function safeAlert(message) {
    try {
        if (tg.isVersionAtLeast && tg.isVersionAtLeast('6.2')) {
            tg.showAlert(message);
        } else {
            alert(message);
        }
    } catch (e) {
        alert(message);
    }
}

function showResultScreen(data) {
    lastAuditData.total = data.total_sum;
    const selectedMarketplace = document.querySelector('input[name="marketplace"]:checked');
    lastAuditData.marketplace = selectedMarketplace ? selectedMarketplace.value : 'wb';

    document.getElementById('result-sum').innerText = data.total_sum.toLocaleString() + " ₽";
    renderResults(data);

    document.getElementById('screen-loading').style.display = 'none';
    document.getElementById('screen-input').style.display = 'none';
    document.getElementById('screen-result').style.display = 'block';
}

function runDemo() {
    startLoadingAnimation('wb');

    // Переключаем на экран загрузки
    document.getElementById('screen-input').style.display = 'none';
    document.getElementById('screen-loading').style.display = 'block';

    setTimeout(() => {
        stopLoadingAnimation();

        const demoData = {
            status: "success",
            total_sum: 84350,
            preview: [
                { article: "Платье миди шелк", reason: "Логистика: неверные габариты", amount: 12500, id: "DEMO-1" },
                { article: "Сумка кожаная", reason: "Дублирование штрафа", amount: 4800, id: "DEMO-2" },
                { article: "Туфли Classic", reason: "Неучтенный возврат", amount: 3200, id: "DEMO-3" }
            ],
            is_demo: true
        };

        showResultScreen(demoData);

        // Проверяем, нет ли уже баннера, чтобы не плодить их при повторном нажатии
        if (!document.getElementById('demo-banner')) {
            const resultsScreen = document.getElementById('screen-result');
            const demoNotice = document.createElement('div');
            demoNotice.id = 'demo-banner';
            demoNotice.innerHTML = `
                <div style="background: #fff3cd; color: #856404; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; text-align: center;">
                    🚀 Это демонстрационные данные. Чтобы найти реальные ошибки, введите ваши API-ключи.
                </div>
            `;
            resultsScreen.prepend(demoNotice);
        }

        const downloadBtn = document.getElementById('download-btn');
        if (downloadBtn) {
            downloadBtn.onclick = () => {
                alert("Скачивание PDF доступно только после реального аудита вашего кабинета.");
                showInputScreen();
            };
        }

    }, 1500);
}

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
    }, 2000);
}

function stopLoadingAnimation() {
    if (loadingInterval) clearInterval(loadingInterval);
}

let userId;
if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    userId = tg.initDataUnsafe.user.id;
} else {
    userId = 123456789;
}

function showHelp(type) {
    let message = "";
    if (type === 'api') {
        message = "1. Зайдите в Личный кабинет селлера.\n" +
            "      2. Перейдите в Настройки -> API.\n" +
            "      3. Создайте новый ключ с типом 'Статистика'.\n\n" +
            "      Это безопасно: мы не имеем доступа к вашим заказам или изменению цен.";
    }
    safeAlert(message);
}

async function pay(method, amount) {
    if (method === 'stars') {
        // Логика для Telegram Stars (Invoice)
        const response = await fetch(`${BACKEND_URL}/api/create-stars-invoice?tg_id=${userId}&amount=${amount}`);
        const data = await response.json();

        if (data.link) {
            tg.openInvoice(data.link, (status) => {
                if (status === 'paid') {
                    safeAlert("Оплата принята! Перезапуск...");
                    location.reload(); // Обновляем, чтобы подтянулась подписка
                }
            });
        }
    } else {
        // Логика для Карт (ЮKassa/Robokassa)
        safeAlert("Оплата картами временно через менеджера или внешнюю ссылку.");
        // Здесь будет переход на платежную форму эквайринга
        // window.location.href = data.payment_url;
    }
}

async function buySubscription(starsAmount) {
    try {
        // 1. Запрашиваем ссылку у нашего бэкенда
        const response = await fetch(`${BACKEND_URL}/api/create-stars-invoice?tg_id=${userId}&amount=${starsAmount}`);
        const data = await response.json();

        if (data.link) {
            // 2. Открываем нативное окно оплаты
            tg.openInvoice(data.link, (status) => {
                if (status === 'paid') {
                    safeAlert("Оплата принята!");
                    // Перезагружаем или переключаем экран
                    window.location.reload();
                } else if (status === 'cancelled') {
                    tg.showConfirm("Оплата отменена.");
                }
            });
        }
    } catch (e) {
        safeAlert("Ошибка при создании счета. Попробуйте позже.");
    }
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
        safeAlert("Данные успешно сохранены!");
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
    const marketplace = lastAuditData.marketplace || 'wb';
    // Просто переходим по ссылке с ID пользователя
    const url = `${BACKEND_URL}/api/download-claim?tg_id=${userId}&marketplace=${marketplace}`;

    // Используем стандартный метод Telegram для открытия ссылок
    tg.openLink(url);
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

function showSubscriptionOffers() {
    // Скрываем форму ввода, показываем блок с кнопками оплаты
    document.getElementById('screen-input').style.display = 'none';
    document.getElementById('screen-subscription').style.display = 'block';
}

async function runAudit() {
    const apiKey = document.getElementById('api-key').value;
    const marketplace = document.querySelector('input[name="marketplace"]:checked').value;
    const clientId = document.getElementById('client-id').value;
    const infoBlock = document.querySelector(".info-title");
    if (infoBlock) infoBlock.style.display = "none";

    if (!apiKey) return safeAlert("Введите API-ключ!");
    if (marketplace === 'ozon' && !clientId) return safeAlert("Введите Client-ID для Ozon!");

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

        const data = await response.json();
        stopLoadingAnimation();

        if (data.status === "payment_required") {
            // Прячем всё лишнее и показываем экран оплаты
            document.getElementById('screen-loading').style.display = 'none';
            showSubscriptionOffers(); // Функция, которая выводит тарифы
            return;
        }

        if (data.status === "success") {
            // Показываем результат (он теперь всегда разблокирован, раз мы сюда дошли)
            showResultScreen(data);
        } else {
            safeAlert(data.message);
            showInputScreen();
        }
    } catch (e) {
        stopLoadingAnimation();
        console.error(e);
        document.getElementById('screen-loading').style.display = 'none';
        safeAlert("Ошибка: " + e.message);
        showInputScreen();
    }
}
