// Анимация для Валеры: статичное изображение -> анимация через случайное время
document.addEventListener('DOMContentLoaded', function() {
    const valeraImage = document.querySelector('.valera-image');
    const totalFrames = 121; // Всего кадров от 1 до 121
    const staticUrl = typeof STATIC_URL !== 'undefined' ? STATIC_URL : '';
    const staticImage = staticUrl + 'valera.png'; // Статичное изображение по умолчанию

    const preloadedImages = [];

    function preloadImage(path) {
        const img = new Image();
        img.src = path;
        preloadedImages.push(img);
    }

    function preloadAnimationFrames(folder) {
        for (let i = 1; i <= totalFrames; i++) {
            preloadImage(`${folder}/${i}.png`);
        }
    }

    // Предзагрузка всех кадров анимаций и ключевых изображений
    ['animation/ilde', 'animation/evil', 'animation/run'].forEach(folder => {
        preloadAnimationFrames(staticUrl + folder);
    });
    ['peshhera.png', 'valera.png', 'reshetka.png', 'box.png'].forEach(img => {
        preloadImage(staticUrl + img);
    });

    let currentFrame = 1;
    let isAnimating = false;
    let animationInterval = null;
    let waitTimeout = null;

    const fps = 15; // Скорость анимации (кадров в секунду)
    const frameInterval = 1000 / fps; // Интервал между кадрами в миллисекундах

    // Функция для проигрывания анимации
    function playAnimation() {
        if (isAnimating) return;

        // Сбрасываем масштаб
        if (valeraImage) {
            valeraImage.style.transform = 'translateX(-50%)';
        }

        isAnimating = true;
        currentFrame = 1;

        animationInterval = setInterval(function() {
            if (valeraImage) {
                valeraImage.src = `${staticUrl}animation/ilde/${currentFrame}.png`;
                currentFrame++;

                // Когда анимация завершена, возвращаемся к статичному изображению
                if (currentFrame > totalFrames) {
                    clearInterval(animationInterval);
                    valeraImage.src = staticImage;
                    isAnimating = false;

                    // Запускаем ожидание перед следующей анимацией
                    scheduleNextAnimation();
                }
            }
        }, frameInterval);
    }

    // Функция для планирования следующей анимации
    function scheduleNextAnimation() {
        // Случайное время от 5 до 10 секунд (в миллисекундах)
        const minDelay = 5000;
        const maxDelay = 10000;
        const randomDelay = Math.random() * (maxDelay - minDelay) + minDelay;

        waitTimeout = setTimeout(function() {
            playAnimation();
        }, randomDelay);
    }

    // Запускаем первый цикл ожидания
    scheduleNextAnimation();

    // Функция для проигрывания анимации evil (разово)
    function playEvilAnimation() {
        // Останавливаем текущие анимации и таймеры
        if (animationInterval) {
            clearInterval(animationInterval);
            animationInterval = null;
        }
        if (waitTimeout) {
            clearTimeout(waitTimeout);
            waitTimeout = null;
        }

        // Сбрасываем масштаб
        if (valeraImage) {
            valeraImage.style.transform = 'translateX(-50%)';
        }

        isAnimating = true;
        let evilFrame = 1;
        let evilDirection = 1; // Направление: 1 = вперед, -1 = назад
        const evilFrameInterval = frameInterval / 2.25; // Ускорение в 2.25 раза (1.5 * 1.5)

        animationInterval = setInterval(function() {
            if (valeraImage) {
                valeraImage.src = `${staticUrl}animation/evil/${evilFrame}.png`;

                // Меняем направление на границах
                if (evilFrame >= totalFrames) {
                    evilDirection = -1; // Идем назад
                } else if (evilFrame <= 1 && evilDirection === -1) {
                    // Когда вернулись к первому кадру, завершаем анимацию
                    clearInterval(animationInterval);
                    animationInterval = null;
                    valeraImage.src = staticImage;
                    isAnimating = false;

                    // Запускаем ожидание перед следующей обычной анимацией
                    scheduleNextAnimation();
                    return;
                }

                evilFrame += evilDirection;
            }
        }, evilFrameInterval);
    }

    // Функция для проигрывания анимации run
    function playRunAnimation() {
        // Останавливаем текущие анимации и таймеры
        if (animationInterval) {
            clearInterval(animationInterval);
            animationInterval = null;
        }
        if (waitTimeout) {
            clearTimeout(waitTimeout);
            waitTimeout = null;
        }

        // Скрываем решетку
        const grillImage = document.querySelector('.grill-image');
        if (grillImage) {
            grillImage.style.opacity = '0';
            grillImage.style.transition = 'opacity 0.5s';
        }

        // Сбрасываем масштаб в начале анимации
        if (valeraImage) {
            valeraImage.style.transform = 'translateX(-50%) scale(1.0)';
        }

        isAnimating = true;
        let runFrame = 1;
        const initialScale = 1.0; // Начальный масштаб
        const maxScale = 1.5; // Максимальный масштаб (увеличение на 50%)

        animationInterval = setInterval(function() {
            if (valeraImage) {
                valeraImage.src = `${staticUrl}animation/run/${runFrame}.png`;

                // Вычисляем текущий масштаб (плавное увеличение от 1.0 до 1.5)
                const currentScale = initialScale + (runFrame / totalFrames) * (maxScale - initialScale);
                valeraImage.style.transform = `translateX(-50%) scale(${currentScale})`;

                runFrame++;

                // Когда анимация завершена, показываем последний кадр evil с максимальным масштабом
                if (runFrame > totalFrames) {
                    clearInterval(animationInterval);
                    animationInterval = null;
                    valeraImage.src = `${staticUrl}animation/evil/${totalFrames}.png`;
                    valeraImage.style.transform = `translateX(-50%) scale(${maxScale})`;
                    isAnimating = false;

                    // Показываем текст "Вы проиграли!" и кнопку перезапуска
                    const gameOverText = document.getElementById('gameOverText');
                    const restartBtn = document.getElementById('restartBtn');
                    if (gameOverText) {
                        gameOverText.classList.add('show');
                    }
                    if (restartBtn) {
                        restartBtn.classList.add('show');
                    }
                }
            }
        }, frameInterval);
    }

    // Управление сигнальными кругами
    const redBtn = document.getElementById('redBtn');
    const greenBtn = document.getElementById('greenBtn');
    const signalCircles = document.querySelectorAll('.signal-circle');
    const grillImage = document.querySelector('.grill-image');

    let currentActiveIndex = -1; // Индекс текущего активного круга (-1 означает, что нет активных)

    // Красная кнопка - активирует следующий круг и запускает анимацию evil
    redBtn.addEventListener('click', function() {
        // Управление сигнальными кругами
        if (currentActiveIndex < signalCircles.length - 1) {
            currentActiveIndex++;
            signalCircles[currentActiveIndex].classList.add('active');

            // Если все круги активированы (индексы 0-4, всего 5 кругов)
            if (currentActiveIndex === signalCircles.length - 1) {
                // Запускаем анимацию run
                playRunAnimation();
                return; // Не запускаем анимацию evil
            }
        }

        // Запускаем анимацию evil только если не все круги активированы
        playEvilAnimation();
    });

    // Зеленая кнопка - выключает активный круг
    greenBtn.addEventListener('click', function() {
        // Находим последний активный круг напрямую из DOM
        // Это работает независимо от того, как был активирован круг (кнопка или микрофон)
        let lastActiveIndex = -1;
        for (let i = signalCircles.length - 1; i >= 0; i--) {
            if (signalCircles[i].classList.contains('active')) {
                lastActiveIndex = i;
                break;
            }
        }
        
        if (lastActiveIndex >= 0) {
            signalCircles[lastActiveIndex].classList.remove('active');
            // Синхронизируем currentActiveIndex с реальным состоянием
            currentActiveIndex = lastActiveIndex - 1;

            // Показываем решетку обратно, если не все круги активированы
            const activeCirclesCount = document.querySelectorAll('.signal-circle.active').length;
            if (activeCirclesCount < signalCircles.length) {
                if (grillImage) {
                    grillImage.style.opacity = '1';
                }

                // Скрываем текст "Вы проиграли!" и кнопку перезапуска
                const gameOverText = document.getElementById('gameOverText');
                const restartBtn = document.getElementById('restartBtn');
                if (gameOverText) {
                    gameOverText.classList.remove('show');
                }
                if (restartBtn) {
                    restartBtn.classList.remove('show');
                }

                // Возвращаем персонажа к статичному изображению и нормальному масштабу
                if (valeraImage) {
                    valeraImage.src = staticImage;
                    valeraImage.style.transform = 'translateX(-50%)';
                }
            }
        }
    });

    // Функция сброса игры
    function resetGame() {
        // Сбрасываем все сигнальные круги
        signalCircles.forEach(circle => {
            circle.classList.remove('active');
        });
        currentActiveIndex = -1;

        // Показываем решетку
        if (grillImage) {
            grillImage.style.opacity = '1';
        }

        // Скрываем текст "Вы проиграли!" и кнопку перезапуска
        const gameOverText = document.getElementById('gameOverText');
        const restartBtn = document.getElementById('restartBtn');
        if (gameOverText) {
            gameOverText.classList.remove('show');
        }
        if (restartBtn) {
            restartBtn.classList.remove('show');
        }

        // Возвращаем персонажа к статичному изображению и нормальному масштабу
        if (valeraImage) {
            valeraImage.src = staticImage;
            valeraImage.style.transform = 'translateX(-50%)';
        }

        // Останавливаем текущие анимации и таймеры
        if (animationInterval) {
            clearInterval(animationInterval);
            animationInterval = null;
        }
        if (waitTimeout) {
            clearTimeout(waitTimeout);
            waitTimeout = null;
        }

        isAnimating = false;

        // Запускаем новый цикл ожидания
        scheduleNextAnimation();
    }

    // Кнопка перезапуска
    const restartBtn = document.getElementById('restartBtn');
    if (restartBtn) {
        restartBtn.addEventListener('click', resetGame);
    }

    // Модальное окно с прайсом
    const priceModal = document.getElementById('priceModal');
    const closeModal = document.getElementById('closeModal');
    const priceList = document.getElementById('priceList');

    // Функция обновления баланса учащихся в модальном окне прайса
    async function updatePriceModalBalance() {
        const studentsBalanceInPriceModal = document.getElementById('studentsBalanceInPriceModal');
        if (studentsBalanceInPriceModal) {
            try {
                if (typeof CLASS_ID !== 'undefined') {
                    const response = await fetch(`/api/class/${CLASS_ID}/balance`);
                    const data = await response.json();
                    studentsBalanceInPriceModal.textContent = data.students_balance;
                } else {
                    const balanceElement = document.getElementById('studentsBalance');
                    if (balanceElement) {
                        studentsBalanceInPriceModal.textContent = balanceElement.textContent;
                    }
                }
            } catch (error) {
                console.error('Error updating price modal balance:', error);
            }
        }
    }

    // Переменные для хранения данных о покупке
    let pendingPurchase = {
        itemId: null,
        itemPrice: null,
        itemName: null
    };

    // Функция показа модального окна уведомлений
    function showNotification(title, message, type = 'info') {
        const notificationModal = document.getElementById('notificationModal');
        const notificationIcon = document.getElementById('notificationIcon');
        const notificationTitle = document.getElementById('notificationTitle');
        const notificationMessage = document.getElementById('notificationMessage');
        const notificationModalContent = notificationModal?.querySelector('.notification-modal-content');

        if (!notificationModal || !notificationIcon || !notificationTitle || !notificationMessage) {
            // Если элементы не найдены, используем стандартный alert
            alert(message);
            return;
        }

        // Устанавливаем тип уведомления (success, error, info)
        if (notificationModalContent) {
            notificationModalContent.className = 'modal-content notification-modal-content ' + type;
        }

        // Устанавливаем иконку в зависимости от типа
        switch (type) {
            case 'success':
                notificationIcon.textContent = '✅';
                break;
            case 'error':
                notificationIcon.textContent = '❌';
                break;
            case 'info':
            default:
                notificationIcon.textContent = 'ℹ️';
                break;
        }

        notificationTitle.textContent = title;
        notificationMessage.textContent = message;

        // Показываем модальное окно
        notificationModal.classList.add('show');
    }

    // Функция закрытия модального окна уведомлений
    function closeNotificationModal() {
        const notificationModal = document.getElementById('notificationModal');
        if (notificationModal) {
            notificationModal.classList.remove('show');
        }
    }

    // Функция показа модального окна подтверждения покупки
    async function showConfirmPurchaseModal(itemId, itemPrice, itemName) {
        try {
            // Получаем текущий баланс
            let studentsBalance = 0;
            if (typeof CLASS_ID !== 'undefined') {
                const response = await fetch(`/api/class/${CLASS_ID}/balance`);
                const data = await response.json();
                studentsBalance = data.students_balance || 0;
            } else {
                const balanceElement = document.getElementById('studentsBalance');
                if (balanceElement) {
                    studentsBalance = parseInt(balanceElement.textContent) || 0;
                }
            }

            // Проверяем, достаточно ли монет
            if (studentsBalance < itemPrice) {
                showNotification(
                    'Недостаточно монет',
                    `Нужно ${itemPrice} монет, у вас ${studentsBalance}`,
                    'error'
                );
                return;
            }

            // Сохраняем данные о покупке
            pendingPurchase = {
                itemId: itemId,
                itemPrice: itemPrice,
                itemName: itemName
            };

            // Заполняем модальное окно данными
            const confirmModal = document.getElementById('confirmPurchaseModal');
            const itemNameElement = document.getElementById('confirmPurchaseItemName');
            const priceElement = document.getElementById('confirmPurchasePrice');
            const balanceAfterElement = document.getElementById('confirmPurchaseBalanceAfter');

            if (confirmModal && itemNameElement && priceElement && balanceAfterElement) {
                itemNameElement.textContent = itemName;
                priceElement.textContent = itemPrice;
                balanceAfterElement.textContent = studentsBalance - itemPrice;
                
                // Показываем модальное окно
                confirmModal.classList.add('show');
            }
        } catch (error) {
            console.error('Error showing confirm purchase modal:', error);
            showNotification('Ошибка', 'Ошибка при загрузке данных. Попробуйте еще раз.', 'error');
        }
    }

    // Функция выполнения покупки приза
    async function executePurchase() {
        const { itemId, itemPrice, itemName } = pendingPurchase;
        
        if (!itemId || !itemPrice || !itemName) {
            console.error('No pending purchase data');
            return;
        }

        try {
            // Списываем стоимость приза
            if (typeof updateBalance === 'function') {
                await updateBalance(-itemPrice, 0);
                
                // Обновляем баланс в модальном окне прайса
                await updatePriceModalBalance();
                
                // Обновляем основной баланс на странице
                if (typeof getBalance === 'function') {
                    await getBalance();
                }
                
                // Закрываем модальное окно подтверждения
                closeConfirmPurchaseModal();
                
                // Показываем сообщение об успешной покупке
                showNotification(
                    'Покупка успешна',
                    `Приз "${itemName}" успешно куплен за ${itemPrice} монет!`,
                    'success'
                );
                
                // Сбрасываем данные о покупке
                pendingPurchase = {
                    itemId: null,
                    itemPrice: null,
                    itemName: null
                };
            } else {
                console.error('updateBalance function is not defined');
                showNotification('Ошибка', 'Ошибка: функция обновления баланса не найдена.', 'error');
            }
        } catch (error) {
            console.error('Error executing purchase:', error);
            showNotification('Ошибка', 'Ошибка при покупке приза. Попробуйте еще раз.', 'error');
        }
    }

    // Функции управления модальным окном подтверждения
    function closeConfirmPurchaseModal() {
        const confirmModal = document.getElementById('confirmPurchaseModal');
        if (confirmModal) {
            confirmModal.classList.remove('show');
        }
    }

    function togglePriceModal() {
        if (priceModal) {
            priceModal.classList.toggle('show');
            if (priceModal.classList.contains('show')) {
                // Обновляем баланс при открытии модального окна
                updatePriceModalBalance();
            }
        }
    }

    function closePriceModal() {
        if (priceModal) {
            priceModal.classList.remove('show');
        }
    }

    // Функция расчета монет
    function calculateCoins() {
        const totalCircles = signalCircles.length;
        // Считаем активные круги напрямую из DOM для надежности
        const activeCirclesCount = document.querySelectorAll('.signal-circle.active').length;
        const inactiveCircles = totalCircles - activeCirclesCount;
        const studentsCoins = Math.max(inactiveCircles, 0); // Каждый неактивный круг = 1 монета
        const valeraCoins = activeCirclesCount; // Каждый активный круг = 1 монета для Валеры

        return {
            studentsCoins,
            valeraCoins,
            inactiveCircles,
            activeCircles: activeCirclesCount,
            totalCircles
        };
    }

    // Остановка игры
    function stopGame() {
        // Останавливаем текущие анимации и таймеры
        if (animationInterval) {
            clearInterval(animationInterval);
            animationInterval = null;
        }
        if (waitTimeout) {
            clearTimeout(waitTimeout);
            waitTimeout = null;
        }
        isAnimating = false;
    }

    // Функция расчета финальных монет с учетом автоматических штрафов
    function calculateFinalCoins() {
        const result = calculateCoins();
        let studentsCoins = result.studentsCoins;
        let valeraCoins = result.valeraCoins;
        
        // Автоматические штрафы
        // Если все круги неактивны (0 активных = 5 неактивных), Валере -5
        if (result.activeCircles === 0) {
            valeraCoins -= 5;
        }
        // Если все круги активны (5 активных), учащимся -5
        if (result.activeCircles === 5) {
            studentsCoins -= 5;
        }
        
        // Учитываем чекбокс дополнительного балла
        const extraPointCheckbox = document.getElementById('extraPointCheckbox');
        if (extraPointCheckbox && extraPointCheckbox.checked) {
            studentsCoins += 1;
        } else {
            studentsCoins -= 1;
        }
        
        return {
            studentsCoins: studentsCoins, // Может быть отрицательным для отображения
            valeraCoins: valeraCoins, // Может быть отрицательным для отображения
            originalStudents: result.studentsCoins,
            originalValera: result.valeraCoins
        };
    }

    // Функция обновления отображения монет в модальном окне
    function updateCoinsDisplay() {
        const finalResult = calculateFinalCoins();
        const studentsCoinsAmount = document.getElementById('studentsCoinsAmount');
        const valeraCoinsAmount = document.getElementById('valeraCoinsAmount');

        if (studentsCoinsAmount) {
            // Показываем значение, даже если оно отрицательное
            studentsCoinsAmount.textContent = finalResult.studentsCoins;
            // Добавляем класс для отрицательных значений
            if (finalResult.studentsCoins < 0) {
                studentsCoinsAmount.style.color = '#f44336';
            } else {
                studentsCoinsAmount.style.color = '#4CAF50';
            }
        }

        if (valeraCoinsAmount) {
            // Показываем значение, даже если оно отрицательное
            valeraCoinsAmount.textContent = finalResult.valeraCoins;
            // Добавляем класс для отрицательных значений
            if (finalResult.valeraCoins < 0) {
                valeraCoinsAmount.style.color = '#f44336';
            } else {
                valeraCoinsAmount.style.color = '#f44336'; // Валера всегда красный
            }
        }
    }

    // Функция показа результата расчета монет
    function showCoinsResult() {
        // Останавливаем игру
        stopGame();
        
        // Сбрасываем чекбокс
        const extraPointCheckbox = document.getElementById('extraPointCheckbox');
        if (extraPointCheckbox) {
            extraPointCheckbox.checked = false;
        }
        
        // Обновляем отображение
        updateCoinsDisplay();
        
        const coinsModal = document.getElementById('coinsModal');
        if (coinsModal) {
            coinsModal.classList.add('show');
        }
    }
    
    // Делаем функцию глобальной для доступа из других скриптов
    window.showCoinsResult = showCoinsResult;

    function closeCoinsModal() {
        const coinsModal = document.getElementById('coinsModal');
        if (coinsModal) {
            coinsModal.classList.remove('show');
        }
    }

    // Обработчик клавиши P и F
    document.addEventListener('keydown', function(event) {
        const code = event.code;
        const keyLower = event.key ? event.key.toLowerCase() : '';
        const isPKey = code === 'KeyP' || (!code && (keyLower === 'p' || keyLower === 'р'));
        const isFKey = code === 'KeyF' || (!code && (keyLower === 'f' || keyLower === 'ф'));

        if (isPKey) {
            event.preventDefault();
            togglePriceModal();
        }

        if (isFKey) {
            event.preventDefault();
            showCoinsResult();
        }

        // Закрытие по Escape
        if (event.key === 'Escape') {
            closePriceModal();
            closeCoinsModal();
            closeShopModal();
            closeNotificationModal();
            if (typeof closeStudentsLotteryModal === 'function') {
                closeStudentsLotteryModal();
            }
            if (typeof closeConfirmPurchaseModal === 'function') {
                closeConfirmPurchaseModal();
            }
        }
    });

    // Закрытие по клику на кнопку закрытия
    if (closeModal) {
        closeModal.addEventListener('click', closePriceModal);
    }

    // Закрытие по клику вне модального окна
    if (priceModal) {
        priceModal.addEventListener('click', function(event) {
            if (event.target === priceModal) {
                closePriceModal();
            }
        });
    }

    // Обработчики кликов на элементы списка призов для покупки
    if (priceList) {
        priceList.addEventListener('click', function(event) {
            const priceItem = event.target.closest('.price-item');
            if (priceItem) {
                const itemId = priceItem.dataset.itemId;
                const itemPrice = parseInt(priceItem.dataset.itemPrice);
                const itemName = priceItem.dataset.itemName;
                
                if (itemId && itemPrice && itemName) {
                    // Показываем модальное окно подтверждения
                    showConfirmPurchaseModal(itemId, itemPrice, itemName);
                }
            }
        });
    }

    // Обработчики модального окна подтверждения покупки
    const confirmPurchaseModal = document.getElementById('confirmPurchaseModal');
    const closeConfirmPurchaseModalBtn = document.getElementById('closeConfirmPurchaseModal');
    const confirmPurchaseBtn = document.getElementById('confirmPurchaseBtn');
    const cancelPurchaseBtn = document.getElementById('cancelPurchaseBtn');

    if (closeConfirmPurchaseModalBtn) {
        closeConfirmPurchaseModalBtn.addEventListener('click', closeConfirmPurchaseModal);
    }

    if (confirmPurchaseBtn) {
        confirmPurchaseBtn.addEventListener('click', executePurchase);
    }

    if (cancelPurchaseBtn) {
        cancelPurchaseBtn.addEventListener('click', closeConfirmPurchaseModal);
    }

    if (confirmPurchaseModal) {
        confirmPurchaseModal.addEventListener('click', function(event) {
            if (event.target === confirmPurchaseModal) {
                closeConfirmPurchaseModal();
            }
        });
    }

    // Обработчики модального окна уведомлений
    const notificationModal = document.getElementById('notificationModal');
    const closeNotificationModalBtn = document.getElementById('closeNotificationModal');
    const notificationOkBtn = document.getElementById('notificationOkBtn');

    if (closeNotificationModalBtn) {
        closeNotificationModalBtn.addEventListener('click', closeNotificationModal);
    }

    if (notificationOkBtn) {
        notificationOkBtn.addEventListener('click', closeNotificationModal);
    }

    if (notificationModal) {
        notificationModal.addEventListener('click', function(event) {
            if (event.target === notificationModal) {
                closeNotificationModal();
            }
        });
    }

    // Закрытие модального окна с монетами
    const closeCoinsModalBtn = document.getElementById('closeCoinsModal');
    if (closeCoinsModalBtn) {
        closeCoinsModalBtn.addEventListener('click', closeCoinsModal);
    }

    const coinsModal = document.getElementById('coinsModal');
    if (coinsModal) {
        coinsModal.addEventListener('click', function(event) {
            if (event.target === coinsModal) {
                closeCoinsModal();
            }
        });
    }

    // Обработчик чекбокса дополнительного балла
    const extraPointCheckbox = document.getElementById('extraPointCheckbox');
    if (extraPointCheckbox) {
        extraPointCheckbox.addEventListener('change', function() {
            updateCoinsDisplay();
        });
    }

    // Функция зачисления монет
    async function submitCoins() {
        const finalResult = calculateFinalCoins();
        
        // Проверяем, что функция updateBalance доступна (определена в game.html)
        if (typeof updateBalance === 'function') {
            try {
                // updateBalance принимает изменения, а не абсолютные значения
                // finalResult уже содержит финальные монеты для зачисления (изменения)
                // Отрицательные значения будут уменьшать баланс
                await updateBalance(finalResult.studentsCoins, finalResult.valeraCoins);
                closeCoinsModal();
                // Перезапускаем игру после зачисления
                resetGame();
            } catch (error) {
                console.error('Error submitting coins:', error);
                showNotification('Ошибка', 'Ошибка при зачислении монет. Попробуйте еще раз.', 'error');
            }
        } else {
            console.error('updateBalance function is not defined');
            showNotification('Ошибка', 'Ошибка: функция обновления баланса не найдена.', 'error');
        }
    }

    // Обработчик кнопки "Зачислить"
    const submitCoinsBtn = document.getElementById('submitCoinsBtn');
    if (submitCoinsBtn) {
        submitCoinsBtn.addEventListener('click', submitCoins);
    }

    // Магазин Валеры
    const shopModal = document.getElementById('shopModal');
    const shopGrid = document.getElementById('shopGrid');
    const selectPrizeBtn = document.getElementById('selectPrizeBtn');
    const prizeResult = document.getElementById('prizeResult');
    const closeShopModalBtn = document.getElementById('closeShopModal');

    // Призы - используются из глобальных переменных, если они определены
    // Если призы - объекты, используем их, иначе создаем объекты из строк
    let prizes = [];
    if (typeof VALERA_PRIZES !== 'undefined' && VALERA_PRIZES.length > 0) {
        // Проверяем, являются ли призы объектами или строками
        if (typeof VALERA_PRIZES[0] === 'object' && VALERA_PRIZES[0].name) {
            prizes = VALERA_PRIZES;
        } else {
            // Преобразуем строки в объекты
            prizes = VALERA_PRIZES.map(name => ({ name: name, students_change: 0, valera_change: 0, probability: 'medium' }));
        }
    } else {
        prizes = [
            { name: 'Самостоятельная работа', students_change: 0, valera_change: 0, probability: 'low' },
            { name: 'Дебаф: 1 замечания = 2 красных', students_change: 0, valera_change: 0, probability: 'medium' },
            { name: 'Варишка: забирает у вас 5 монет', students_change: 0, valera_change: 0, probability: 'medium' },
            { name: 'Дебаф: вы не получаете монеты за урок', students_change: 0, valera_change: 0, probability: 'medium' },
            { name: 'Дебаф: вы получаете доп задание домой', students_change: 0, valera_change: 0, probability: 'medium' }
        ];
    }

    // Создание поля 3x3
    function createShopGrid() {
        if (!shopGrid) return;
        
        shopGrid.innerHTML = '';
        const totalCells = 9;
        
        // Распределяем призы по ячейкам (5 призов на 9 ячеек, некоторые повторяются)
        const prizeDistribution = [];
        for (let i = 0; i < totalCells; i++) {
            prizeDistribution.push(prizes[i % prizes.length]);
        }
        
        // Перемешиваем призы для случайного распределения
        for (let i = prizeDistribution.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [prizeDistribution[i], prizeDistribution[j]] = [prizeDistribution[j], prizeDistribution[i]];
        }
        
        for (let i = 0; i < totalCells; i++) {
            const cell = document.createElement('div');
            cell.className = 'shop-cell';
            cell.dataset.index = i;
            // Сохраняем приз как JSON строку для доступа к объекту
            const prize = prizeDistribution[i];
            cell.dataset.prize = typeof prize === 'object' ? prize.name : prize;
            cell.dataset.prizeData = JSON.stringify(prize);
            
            const img = document.createElement('img');
            img.src = staticUrl + 'box.png';
            img.alt = 'Коробка';
            cell.appendChild(img);
            
            shopGrid.appendChild(cell);
        }
    }

    // Инициализация поля при загрузке
    createShopGrid();

    // Функция проверки баланса Валеры и обновления состояния кнопки
    async function updateShopButtonState() {
        if (!selectPrizeBtn) return;
        
        try {
            // Получаем текущий баланс Валеры
            const valeraBalanceElement = document.getElementById('valeraBalanceInShop');
            let valeraBalance = 0;
            
            if (valeraBalanceElement) {
                valeraBalance = parseInt(valeraBalanceElement.textContent) || 0;
            } else {
                // Если элемент не найден, получаем баланс через API
                if (typeof CLASS_ID !== 'undefined' && typeof getBalance === 'function') {
                    await getBalance();
                    const balanceElement = document.getElementById('valeraBalance');
                    if (balanceElement) {
                        valeraBalance = parseInt(balanceElement.textContent) || 0;
                    }
                }
            }
            
            const PRIZE_COST = 5;
            
            // Блокируем кнопку, если баланс недостаточен
            if (valeraBalance < PRIZE_COST) {
                selectPrizeBtn.disabled = true;
                selectPrizeBtn.style.opacity = '0.5';
                selectPrizeBtn.style.cursor = 'not-allowed';
                selectPrizeBtn.title = 'Недостаточно монет (нужно ' + PRIZE_COST + ', есть ' + valeraBalance + ')';
            } else {
                selectPrizeBtn.disabled = false;
                selectPrizeBtn.style.opacity = '1';
                selectPrizeBtn.style.cursor = 'pointer';
                selectPrizeBtn.title = 'Выбрать приз за 5 монет';
            }
        } catch (error) {
            console.error('Error updating shop button state:', error);
        }
    }

    // Функции управления модальным окном магазина
    function toggleShopModal() {
        if (shopModal) {
            shopModal.classList.toggle('show');
            if (shopModal.classList.contains('show')) {
                // Сбрасываем состояние при открытии
                resetShopState();
                // Обновляем состояние кнопки и баланс
                updateShopButtonState();
                updateShopBalanceDisplay();
            }
        }
    }
    
    // Функция обновления отображения баланса в магазине
    async function updateShopBalanceDisplay() {
        const valeraBalanceInShop = document.getElementById('valeraBalanceInShop');
        if (valeraBalanceInShop) {
            try {
                if (typeof CLASS_ID !== 'undefined') {
                    const response = await fetch(`/api/class/${CLASS_ID}/balance`);
                    const data = await response.json();
                    valeraBalanceInShop.textContent = data.valera_balance;
                } else {
                    const balanceElement = document.getElementById('valeraBalance');
                    if (balanceElement) {
                        valeraBalanceInShop.textContent = balanceElement.textContent;
                    }
                }
            } catch (error) {
                console.error('Error updating shop balance display:', error);
            }
        }
    }

    function closeShopModal() {
        if (shopModal) {
            shopModal.classList.remove('show');
            resetShopState();
        }
    }

    function resetShopState() {
        if (prizeResult) {
            prizeResult.innerHTML = '';
            prizeResult.classList.remove('show');
        }
        if (shopGrid) {
            const cells = shopGrid.querySelectorAll('.shop-cell');
            cells.forEach(cell => {
                cell.classList.remove('highlighted', 'selected');
            });
        }
        if (selectPrizeBtn) {
            selectPrizeBtn.disabled = false;
        }
    }

    // Функция выбора приза с учетом вероятности
    function selectPrizeByProbability(prizesList) {
        if (!prizesList || prizesList.length === 0) {
            return null;
        }
        
        // Веса вероятности
        const probabilityWeights = {
            'high': 5,    // Высокая вероятность - вес 5
            'medium': 3,  // Средняя вероятность - вес 3
            'low': 2     // Низкая вероятность - вес 2
        };
        
        // Создаем массив призов с весами
        const weightedPrizes = [];
        prizesList.forEach(prize => {
            const prizeObj = typeof prize === 'object' ? prize : { name: prize, probability: 'medium' };
            const weight = probabilityWeights[prizeObj.probability] || probabilityWeights['medium'];
            
            // Добавляем приз несколько раз в зависимости от веса
            for (let i = 0; i < weight; i++) {
                weightedPrizes.push(prizeObj);
            }
        });
        
        // Выбираем случайный приз из взвешенного списка
        if (weightedPrizes.length === 0) {
            return prizesList[0];
        }
        
        const randomIndex = Math.floor(Math.random() * weightedPrizes.length);
        return weightedPrizes[randomIndex];
    }

    // Функция выбора приза
    async function selectPrize() {
        if (!selectPrizeBtn || selectPrizeBtn.disabled) return;
        
        // Проверяем баланс перед выбором приза
        const PRIZE_COST = 5;
        let valeraBalance = 0;
        
        try {
            if (typeof CLASS_ID !== 'undefined') {
                const response = await fetch(`/api/class/${CLASS_ID}/balance`);
                const data = await response.json();
                valeraBalance = data.valera_balance || 0;
            } else {
                const balanceElement = document.getElementById('valeraBalance');
                if (balanceElement) {
                    valeraBalance = parseInt(balanceElement.textContent) || 0;
                }
            }
            
            // Если баланс недостаточен, не позволяем выбрать приз
            if (valeraBalance < PRIZE_COST) {
                showNotification('Недостаточно монет', `Нужно ${PRIZE_COST} монет, у вас ${valeraBalance}`, 'error');
                return;
            }
        } catch (error) {
            console.error('Error checking balance:', error);
            showNotification('Ошибка', 'Ошибка при проверке баланса', 'error');
            return;
        }
        
        selectPrizeBtn.disabled = true;
        if (prizeResult) {
            prizeResult.textContent = '';
            prizeResult.classList.remove('show');
        }

        const cells = shopGrid.querySelectorAll('.shop-cell');
        if (cells.length === 0) return;

        // Анимация подсветки ячеек
        let currentIndex = 0;
        const highlightDuration = 2000; // 2 секунды анимации
        const highlightInterval = 100; // Интервал между переключениями (100мс)
        const iterations = highlightDuration / highlightInterval;
        let iterationCount = 0;

        // Сбрасываем все подсветки
        cells.forEach(cell => cell.classList.remove('highlighted', 'selected'));

        const highlightIntervalId = setInterval(async () => {
            // Убираем подсветку с предыдущей ячейки
            cells.forEach(cell => cell.classList.remove('highlighted'));
            
            // Подсвечиваем текущую ячейку
            cells[currentIndex].classList.add('highlighted');
            
            currentIndex = (currentIndex + 1) % cells.length;
            iterationCount++;

            // Завершаем анимацию и выбираем случайную ячейку
            if (iterationCount >= iterations) {
                clearInterval(highlightIntervalId);
                
                // Убираем все подсветки
                cells.forEach(cell => cell.classList.remove('highlighted'));
                
                // Выбираем приз с учетом вероятности выпадения
                let selectedPrizeObj = selectPrizeByProbability(prizes);
                
                // Нормализуем объект приза
                if (!selectedPrizeObj || typeof selectedPrizeObj !== 'object') {
                    selectedPrizeObj = { name: selectedPrizeObj || 'Приз', students_change: 0, valera_change: 0, probability: 'medium' };
                }
                
                // Убеждаемся, что у приза есть поле probability
                if (!selectedPrizeObj.probability) {
                    selectedPrizeObj.probability = 'medium';
                }
                
                // Показываем название приза строго как в базе (без рандомизации чисел)
                const prizeName = selectedPrizeObj.name;
                
                // Выбираем случайную ячейку для визуального эффекта
                const randomIndex = Math.floor(Math.random() * cells.length);
                const selectedCell = cells[randomIndex];
                
                // Подсвечиваем выбранную ячейку
                selectedCell.classList.add('selected');
                
                // Показываем результат
                if (prizeResult) {
                    prizeResult.innerHTML = `<div class="prize-text">${prizeName}</div>`;
                    prizeResult.classList.add('show');
                }

                // Списываем стоимость приза и применяем награды
                if (typeof updateBalance === 'function') {
                    try {
                        // Атомарно: стоимость + награды одним вызовом
                        const studentsDelta = selectedPrizeObj.students_change || 0;
                        const valeraDelta = (selectedPrizeObj.valera_change || 0) - PRIZE_COST;
                        await updateBalance(studentsDelta, valeraDelta);
                        // Обновляем отображение баланса в магазине
                        updateShopBalanceDisplay();
                        // Обновляем состояние кнопки
                        updateShopButtonState();
                    } catch (error) {
                        console.error('Error deducting coins:', error);
                    }
                }

                // Восстанавливаем кнопку через некоторое время
                setTimeout(() => {
                    updateShopButtonState();
                }, 3000);
            }
        }, highlightInterval);
    }

    // Обработчики событий для магазина
    if (selectPrizeBtn) {
        selectPrizeBtn.addEventListener('click', selectPrize);
    }

    if (closeShopModalBtn) {
        closeShopModalBtn.addEventListener('click', closeShopModal);
    }

    if (shopModal) {
        shopModal.addEventListener('click', function(event) {
            if (event.target === shopModal) {
                closeShopModal();
            }
        });
    }

    // Добавляем обработчик клавиши R
    document.addEventListener('keydown', function(event) {
        const code = event.code;
        const keyLower = event.key ? event.key.toLowerCase() : '';
        const isRKey = code === 'KeyR' || (!code && (keyLower === 'r' || keyLower === 'к'));

        if (isRKey) {
            event.preventDefault();
            toggleShopModal();
        }

        // Закрытие по Escape
        if (event.key === 'Escape') {
            closeShopModal();
        }
    });

    // Обработчики кнопок магазинов
    const studentsShopBtn = document.getElementById('studentsShopBtn');
    const valeraShopBtn = document.getElementById('valeraShopBtn');

    if (studentsShopBtn) {
        studentsShopBtn.addEventListener('click', function() {
            togglePriceModal();
        });
    }

    if (valeraShopBtn) {
        valeraShopBtn.addEventListener('click', function() {
            toggleShopModal();
        });
    }

    // Лавка для учащихся
    const studentsLotteryModal = document.getElementById('studentsLotteryModal');
    const studentsLotteryGrid = document.getElementById('studentsLotteryGrid');
    const selectStudentsPrizeBtn = document.getElementById('selectStudentsPrizeBtn');
    const studentsPrizeResult = document.getElementById('studentsPrizeResult');
    const closeStudentsLotteryModalBtn = document.getElementById('closeStudentsLotteryModal');
    const studentsLotteryBtn = document.getElementById('studentsLotteryBtn');

    // Призы для учащихся - используются из глобальных переменных, если они определены
    // Если призы - объекты, используем их, иначе создаем объекты из строк
    let studentsPrizes = [];
    if (typeof STUDENTS_PRIZES !== 'undefined' && STUDENTS_PRIZES.length > 0) {
        // Проверяем, являются ли призы объектами или строками
        if (typeof STUDENTS_PRIZES[0] === 'object' && STUDENTS_PRIZES[0].name) {
            studentsPrizes = STUDENTS_PRIZES;
        } else {
            // Преобразуем строки в объекты
            studentsPrizes = STUDENTS_PRIZES.map(name => ({ name: name, students_change: 0, valera_change: 0, probability: 'medium' }));
        }
    } else {
        studentsPrizes = [
            { name: 'Воришка: забирает у Валеры 5 монет', students_change: 0, valera_change: 0, probability: 'medium' },
            { name: 'Бафф: два замечания - 1 кружок', students_change: 0, valera_change: 0, probability: 'medium' },
            { name: 'Бафф: Валера не получает монеты', students_change: 0, valera_change: 0, probability: 'medium' },
            { name: 'Бафф: доступен таймер', students_change: 0, valera_change: 0, probability: 'medium' }
        ];
    }

    // Создание поля 3x3 для лавки учащихся
    function createStudentsLotteryGrid() {
        if (!studentsLotteryGrid) return;
        
        studentsLotteryGrid.innerHTML = '';
        const totalCells = 9;
        
        // Распределяем призы по ячейкам
        const prizeDistribution = [];
        for (let i = 0; i < totalCells; i++) {
            prizeDistribution.push(studentsPrizes[i % studentsPrizes.length]);
        }
        
        // Перемешиваем призы для случайного распределения
        for (let i = prizeDistribution.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [prizeDistribution[i], prizeDistribution[j]] = [prizeDistribution[j], prizeDistribution[i]];
        }
        
        for (let i = 0; i < totalCells; i++) {
            const cell = document.createElement('div');
            cell.className = 'shop-cell';
            cell.dataset.index = i;
            // Сохраняем приз как JSON строку для доступа к объекту
            const prize = prizeDistribution[i];
            cell.dataset.prize = typeof prize === 'object' ? prize.name : prize;
            cell.dataset.prizeData = JSON.stringify(prize);
            
            const img = document.createElement('img');
            img.src = staticUrl + 'box.png';
            img.alt = 'Коробка';
            cell.appendChild(img);
            
            studentsLotteryGrid.appendChild(cell);
        }
    }

    // Инициализация поля при загрузке
    createStudentsLotteryGrid();

    // Функция проверки баланса учащихся и обновления состояния кнопки
    async function updateStudentsShopButtonState() {
        if (!selectStudentsPrizeBtn) return;
        
        try {
            // Получаем текущий баланс учащихся
            const studentsBalanceElement = document.getElementById('studentsBalanceInShop');
            let studentsBalance = 0;
            
            if (studentsBalanceElement) {
                studentsBalance = parseInt(studentsBalanceElement.textContent) || 0;
            } else {
                // Если элемент не найден, получаем баланс через API
                if (typeof CLASS_ID !== 'undefined' && typeof getBalance === 'function') {
                    await getBalance();
                    const balanceElement = document.getElementById('studentsBalance');
                    if (balanceElement) {
                        studentsBalance = parseInt(balanceElement.textContent) || 0;
                    }
                }
            }
            
            const STUDENTS_PRIZE_COST = 8;
            
            // Блокируем кнопку, если баланс недостаточен
            if (studentsBalance < STUDENTS_PRIZE_COST) {
                selectStudentsPrizeBtn.disabled = true;
                selectStudentsPrizeBtn.style.opacity = '0.5';
                selectStudentsPrizeBtn.style.cursor = 'not-allowed';
                selectStudentsPrizeBtn.title = 'Недостаточно монет (нужно 8, есть ' + studentsBalance + ')';
            } else {
                selectStudentsPrizeBtn.disabled = false;
                selectStudentsPrizeBtn.style.opacity = '1';
                selectStudentsPrizeBtn.style.cursor = 'pointer';
                selectStudentsPrizeBtn.title = 'Выбрать приз за 8 монет';
            }
        } catch (error) {
            console.error('Error updating students shop button state:', error);
        }
    }

    // Функция обновления отображения баланса учащихся в магазине
    async function updateStudentsShopBalanceDisplay() {
        const studentsBalanceInShop = document.getElementById('studentsBalanceInShop');
        if (studentsBalanceInShop) {
            try {
                if (typeof CLASS_ID !== 'undefined') {
                    const response = await fetch(`/api/class/${CLASS_ID}/balance`);
                    const data = await response.json();
                    studentsBalanceInShop.textContent = data.students_balance;
                } else {
                    const balanceElement = document.getElementById('studentsBalance');
                    if (balanceElement) {
                        studentsBalanceInShop.textContent = balanceElement.textContent;
                    }
                }
            } catch (error) {
                console.error('Error updating students shop balance display:', error);
            }
        }
    }

    // Функции управления модальным окном лавки учащихся
    function toggleStudentsLotteryModal() {
        if (studentsLotteryModal) {
            studentsLotteryModal.classList.toggle('show');
            if (studentsLotteryModal.classList.contains('show')) {
                resetStudentsLotteryState();
                // Обновляем состояние кнопки и баланс
                updateStudentsShopButtonState();
                updateStudentsShopBalanceDisplay();
            }
        }
    }

    function closeStudentsLotteryModal() {
        if (studentsLotteryModal) {
            studentsLotteryModal.classList.remove('show');
            resetStudentsLotteryState();
        }
    }

    function resetStudentsLotteryState() {
        if (studentsPrizeResult) {
            studentsPrizeResult.innerHTML = '';
            studentsPrizeResult.classList.remove('show');
        }
        if (studentsLotteryGrid) {
            const cells = studentsLotteryGrid.querySelectorAll('.shop-cell');
            cells.forEach(cell => {
                cell.classList.remove('highlighted', 'selected');
            });
        }
        if (selectStudentsPrizeBtn) {
            selectStudentsPrizeBtn.disabled = false;
        }
    }

    // Функция выбора приза для учащихся
    async function selectStudentsPrize() {
        if (!selectStudentsPrizeBtn || selectStudentsPrizeBtn.disabled) return;
        
        // Проверяем баланс перед выбором приза
        const STUDENTS_PRIZE_COST = 8;
        let studentsBalance = 0;
        
        try {
            if (typeof CLASS_ID !== 'undefined') {
                const response = await fetch(`/api/class/${CLASS_ID}/balance`);
                const data = await response.json();
                studentsBalance = data.students_balance || 0;
            } else {
                const balanceElement = document.getElementById('studentsBalance');
                if (balanceElement) {
                    studentsBalance = parseInt(balanceElement.textContent) || 0;
                }
            }
            
            // Если баланс недостаточен, не позволяем выбрать приз
            if (studentsBalance < STUDENTS_PRIZE_COST) {
                showNotification('Недостаточно монет', `Нужно 8 монет, у вас ${studentsBalance}`, 'error');
                return;
            }
        } catch (error) {
            console.error('Error checking balance:', error);
            showNotification('Ошибка', 'Ошибка при проверке баланса', 'error');
            return;
        }
        
        selectStudentsPrizeBtn.disabled = true;
        if (studentsPrizeResult) {
            studentsPrizeResult.innerHTML = '';
            studentsPrizeResult.classList.remove('show');
        }

        const cells = studentsLotteryGrid.querySelectorAll('.shop-cell');
        if (cells.length === 0) return;

        // Анимация подсветки ячеек
        let currentIndex = 0;
        const highlightDuration = 2000;
        const highlightInterval = 100;
        const iterations = highlightDuration / highlightInterval;
        let iterationCount = 0;
        const STUDENTS_PRIZE_COST_FOR_CALLBACK = STUDENTS_PRIZE_COST; // Сохраняем для использования в callback

        cells.forEach(cell => cell.classList.remove('highlighted', 'selected'));

        const highlightIntervalId = setInterval(async () => {
            cells.forEach(cell => cell.classList.remove('highlighted'));
            
            cells[currentIndex].classList.add('highlighted');
            
            currentIndex = (currentIndex + 1) % cells.length;
            iterationCount++;

            if (iterationCount >= iterations) {
                clearInterval(highlightIntervalId);
                
                cells.forEach(cell => cell.classList.remove('highlighted'));
                
                // Выбираем приз с учетом вероятности выпадения
                let selectedPrizeObj = selectPrizeByProbability(studentsPrizes);
                
                // Убеждаемся, что у приза есть поле probability
                if (!selectedPrizeObj.probability) {
                    selectedPrizeObj.probability = 'medium';
                }
                
                // Выбираем случайную ячейку для визуального эффекта
                const randomIndex = Math.floor(Math.random() * cells.length);
                const selectedCell = cells[randomIndex];
                
                // Показываем название приза строго как в базе (без рандомизации чисел)
                const prizeName = selectedPrizeObj.name;
                
                selectedCell.classList.add('selected');
                
                // Показываем результат
                if (studentsPrizeResult) {
                    studentsPrizeResult.innerHTML = `<div class="prize-text">${prizeName}</div>`;
                    studentsPrizeResult.classList.add('show');
                }

                // Списываем стоимость приза и применяем награды
                if (typeof updateBalance === 'function') {
                    try {
                        // Атомарно: стоимость + награды одним вызовом
                        const studentsDelta = (selectedPrizeObj.students_change || 0) - STUDENTS_PRIZE_COST_FOR_CALLBACK;
                        const valeraDelta = selectedPrizeObj.valera_change || 0;
                        await updateBalance(studentsDelta, valeraDelta);
                        // Обновляем отображение баланса в магазине
                        updateStudentsShopBalanceDisplay();
                        // Обновляем состояние кнопки
                        updateStudentsShopButtonState();
                    } catch (error) {
                        console.error('Error deducting coins:', error);
                    }
                }

                setTimeout(() => {
                    updateStudentsShopButtonState();
                }, 3000);
            }
        }, highlightInterval);
    }

    // Обработчики событий для лавки учащихся
    if (selectStudentsPrizeBtn) {
        selectStudentsPrizeBtn.addEventListener('click', selectStudentsPrize);
    }

    if (closeStudentsLotteryModalBtn) {
        closeStudentsLotteryModalBtn.addEventListener('click', closeStudentsLotteryModal);
    }

    if (studentsLotteryModal) {
        studentsLotteryModal.addEventListener('click', function(event) {
            if (event.target === studentsLotteryModal) {
                closeStudentsLotteryModal();
            }
        });
    }

    if (studentsLotteryBtn) {
        studentsLotteryBtn.addEventListener('click', function() {
            toggleStudentsLotteryModal();
        });
    }
});

