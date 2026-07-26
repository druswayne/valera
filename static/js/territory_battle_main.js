(function () {
    'use strict';

    function whenVisible(el, callback) {
        if (!el || typeof IntersectionObserver === 'undefined') {
            callback();
            return;
        }
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    callback();
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.2 });
        observer.observe(el);
    }

    function delay(ms) {
        var scale = (typeof window !== 'undefined' && window.__TB_PROMO_SCALE__) || 1;
        return new Promise(function (resolve) { setTimeout(resolve, ms * scale); });
    }

    var DEMO_TASK_POOL = [
        'Вычислите: 15 − 7 = ?',
        'Найдите значение: 7 + 5 = ?',
        'Сколько будет 3/4 + 1/8?',
        'Найдите 20% от 150',
        'НОД(24, 36) = ?',
        'Упростите: 18/24',
        '2,5 × 0,4 = ?',
        'Решите: x + 12 = 35',
        'Площадь квадрата со стороной 6',
        'Сколько минут в 2,5 часа?'
    ];
    var DEMO_TASK_ANSWERS = ['8', '12', '7/8', '30', '12', '3/4', '1', '23', '36', '150'];
    var _demoTaskIdx = 0;

    function nextDemoTask() {
        var i = _demoTaskIdx % DEMO_TASK_POOL.length;
        _demoTaskIdx += 1;
        return { text: DEMO_TASK_POOL[i], answer: DEMO_TASK_ANSWERS[i] };
    }

    function applyDemoTask(stage, task) {
        if (!stage || !task) return;
        stage.querySelectorAll('.task-text, .demo-task-text, .demo-pvp-task').forEach(function (el) {
            el.textContent = task.text;
        });
    }

    function setCaption(stage, text, fade) {
        var cap = stage.querySelector('.demo-step-caption');
        if (!cap) return;
        cap.textContent = text;
        cap.classList.toggle('fade', !!fade);
    }

    function setOpacity(els, val) {
        (els.length !== undefined ? els : [els]).forEach(function (el) {
            if (el) el.setAttribute('opacity', String(val));
        });
    }

    function animateStrengthCount(el, from, to, steps, interval) {
        return new Promise(function (resolve) {
            if (!el) { resolve(); return; }
            var current = from;
            var step = to > from ? 1 : -1;
            var count = 0;
            var maxSteps = Math.abs(to - from);
            var timer = setInterval(function () {
                if (count >= maxSteps) {
                    el.textContent = String(to);
                    clearInterval(timer);
                    resolve();
                    return;
                }
                current += step * Math.max(1, Math.ceil(maxSteps / steps));
                if ((step > 0 && current > to) || (step < 0 && current < to)) current = to;
                el.textContent = String(current);
                count++;
            }, interval);
        });
    }

    function flyItem(flying, stage, fromEl, toEl, duration) {
        return new Promise(function (resolve) {
            if (!flying || !fromEl || !toEl) { resolve(); return; }
            var sRect = stage.getBoundingClientRect();
            var a = fromEl.getBoundingClientRect();
            var b = toEl.getBoundingClientRect();
            var startX = a.left - sRect.left + a.width / 2 - 20;
            var startY = a.top - sRect.top + a.height / 2 - 20;
            var endX = b.left - sRect.left + b.width / 2 - 20;
            var endY = b.top - sRect.top + b.height / 2 - 20;
            flying.style.transition = 'none';
            flying.style.left = startX + 'px';
            flying.style.top = startY + 'px';
            flying.style.opacity = '1';
            flying.style.transform = 'scale(1)';
            flying.classList.add('trail');
            void flying.offsetWidth;
            flying.style.transition = 'left ' + duration + 'ms cubic-bezier(0.4, 0, 0.2, 1), top ' + duration + 'ms cubic-bezier(0.4, 0, 0.2, 1), transform ' + duration + 'ms ease';
            flying.style.left = endX + 'px';
            flying.style.top = endY + 'px';
            flying.style.transform = 'scale(0.85)';
            setTimeout(function () {
                flying.style.opacity = '0';
                flying.classList.remove('trail');
                resolve();
            }, duration);
        });
    }

    /* --- Захват --- */
    function initCaptureDemo(stage) {
        var targetRegion = stage.querySelector('.demo-target-region');
        var targetPath = targetRegion ? targetRegion.querySelector('.region-path') : null;
        var confirm = stage.querySelector('.demo-confirm');
        var yesBtn = stage.querySelector('.demo-confirm-yes');
        var taskModal = stage.querySelector('.demo-task-modal');
        var taskInput = stage.querySelector('.demo-task-input');
        var submitBtn = stage.querySelector('.demo-submit-flash');
        var toast = stage.querySelector('.demo-toast');
        var cursor = stage.querySelector('.demo-map-cursor');
        var mapViewport = stage.querySelector('.map-viewport');
        var strengthText = stage.querySelector('.demo-strength-text');
        var overlay = stage.querySelector('.demo-region-overlay');
        var flag = overlay ? overlay.querySelector('.region-flag') : null;
        var strengthBg = overlay ? overlay.querySelector('.region-strength-value-bg') : null;

        async function run() {
            if (targetRegion) targetRegion.classList.remove('demo-region-highlight');
            if (targetPath) {
                targetPath.classList.remove('owned');
                targetPath.style.removeProperty('--region-color');
            }
            if (confirm) confirm.classList.remove('open');
            if (taskModal) taskModal.classList.remove('open');
            if (toast) toast.classList.remove('show');
            if (taskInput) taskInput.value = '';
            if (cursor) cursor.style.opacity = '0';
            setOpacity([flag, strengthBg, strengthText], 0);
            if (strengthText) strengthText.textContent = '0';
            setCaption(stage, 'Карта битвы');
            await delay(900);

            setCaption(stage, 'Выбор области');
            if (targetRegion) targetRegion.classList.add('demo-region-highlight');
            if (cursor && mapViewport && targetRegion) {
                var sRect = stage.getBoundingClientRect();
                var mRect = mapViewport.getBoundingClientRect();
                var rRect = targetRegion.getBoundingClientRect();
                cursor.style.left = (mRect.left - sRect.left + mRect.width * 0.3) + 'px';
                cursor.style.top = (mRect.top - sRect.top + mRect.height * 0.5) + 'px';
                cursor.style.opacity = '1';
                await delay(700);
                cursor.style.left = (rRect.left - sRect.left + rRect.width / 2 - 8) + 'px';
                cursor.style.top = (rRect.top - sRect.top + rRect.height / 2 - 8) + 'px';
            }
            await delay(1000);

            setCaption(stage, 'Подтверждение захвата');
            if (cursor) cursor.style.opacity = '0';
            if (confirm) confirm.classList.add('open');
            await delay(1300);
            if (yesBtn) yesBtn.style.transform = 'scale(0.95)';
            await delay(220);
            if (yesBtn) yesBtn.style.transform = '';
            await delay(500);

            var task = nextDemoTask();
            applyDemoTask(stage, task);
            setCaption(stage, 'Решение задачи');
            if (confirm) confirm.classList.remove('open');
            if (taskModal) taskModal.classList.add('open');
            await delay(800);
            if (taskInput) {
                taskInput.value = '';
                var ans = String(task.answer);
                for (var i = 1; i <= ans.length; i++) {
                    taskInput.value = ans.slice(0, i);
                    await delay(280);
                }
            }
            if (submitBtn) submitBtn.style.filter = 'brightness(1.2)';
            await delay(350);
            if (submitBtn) submitBtn.style.filter = '';
            await delay(400);

            if (taskModal) taskModal.classList.remove('open');
            if (targetPath) {
                targetPath.classList.add('owned');
                targetPath.style.setProperty('--region-color', 'rgba(212,168,75,0.55)');
            }
            if (targetRegion) targetRegion.classList.remove('demo-region-highlight');
            setOpacity([flag, strengthBg, strengthText], 1);
            await animateStrengthCount(strengthText, 0, 25, 12, 100);
            setCaption(stage, 'Сила клана выросла!');
            if (toast) toast.classList.add('show');
            await delay(3200);
            if (toast) toast.classList.remove('show');
            await delay(700);
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Задачи --- */
    function initTaskDemo(stage) {
        var taskModal = stage.querySelector('.demo-task-modal');
        var taskInput = stage.querySelector('.demo-task-input');
        var toast = stage.querySelector('.demo-toast');
        var xpFill = stage.querySelector('.demo-xp-fill');
        var energyEl = stage.querySelector('.demo-energy');
        var energy = 8;
        var xp = 45;

        async function run() {
            if (taskModal) taskModal.classList.remove('open');
            if (toast) toast.classList.remove('show');
            if (taskInput) taskInput.value = '';
            setCaption(stage, 'Карточка игрока');
            await delay(900);

            var task = nextDemoTask();
            applyDemoTask(stage, task);
            setCaption(stage, 'Открытие задания');
            if (taskModal) taskModal.classList.add('open');
            await delay(700);
            if (taskInput) {
                var ans = String(task.answer);
                for (var i = 1; i <= ans.length; i++) {
                    taskInput.value = ans.slice(0, i);
                    await delay(300);
                }
            }
            await delay(700);

            setCaption(stage, 'Награда за ответ');
            if (taskModal) taskModal.classList.remove('open');
            energy = Math.max(1, energy - 1);
            xp = Math.min(92, xp + 12);
            if (energyEl) energyEl.textContent = String(energy);
            if (xpFill) xpFill.style.width = xp + '%';
            if (toast) {
                toast.textContent = 'Верно! +16 XP · +12 Нумов · −1 ⚡';
                toast.classList.add('show');
            }
            await delay(2800);
            if (toast) toast.classList.remove('show');
            if (energy <= 2) {
                energy = 8;
                xp = 45;
                if (energyEl) energyEl.textContent = '8';
                if (xpFill) xpFill.style.width = '45%';
            }
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Предметы: лавка → инвентарь → использование → бафф --- */
    function initItemDemo(stage) {
        var shopTile = stage.querySelector('.demo-shop-tile');
        var shopCol = stage.querySelector('.demo-shop-col');
        var invCol = stage.querySelector('.demo-inventory-col');
        var targetCol = stage.querySelector('.demo-target-col');
        var inventory = stage.querySelector('.demo-inventory-source');
        var useBtn = stage.querySelector('.demo-use-btn');
        var popover = stage.querySelector('.demo-use-popover');
        var flying = stage.querySelector('.demo-flying-item');
        var buffSlot = stage.querySelector('.demo-buff-slot');
        var targetCard = stage.querySelector('.demo-buff-target-card');
        var atkBefore = stage.querySelector('.demo-atk-before');
        var statPop = stage.querySelector('.demo-stat-pop');
        var buffTimer = stage.querySelector('.demo-buff-timer');
        var numsCost = stage.querySelector('.demo-nums-cost');
        var conn1 = stage.querySelector('.demo-conn-1');
        var conn2 = stage.querySelector('.demo-conn-2');
        var shopModal = stage.querySelector('.demo-shop-modal');
        var btnBuy = stage.querySelector('.demo-btn-buy');
        var numsBalance = stage.querySelector('.demo-nums-balance');

        function reset() {
            if (shopModal) shopModal.classList.remove('open');
            if (btnBuy) btnBuy.classList.remove('flash');
            if (numsBalance) {
                numsBalance.textContent = '340';
                numsBalance.classList.remove('spent');
            }
            if (shopTile) {
                shopTile.classList.remove('highlight', 'visible');
                shopTile.style.opacity = '';
            }
            if (shopCol) shopCol.classList.add('active');
            if (invCol) invCol.classList.add('dim');
            if (targetCol) targetCol.classList.add('dim');
            if (inventory) {
                inventory.classList.remove('visible', 'selected', 'used');
            }
            if (useBtn) useBtn.classList.remove('visible', 'pulse');
            if (popover) popover.classList.remove('show');
            if (buffSlot) buffSlot.classList.remove('visible');
            if (targetCard) targetCard.classList.remove('buffed');
            if (atkBefore) {
                atkBefore.textContent = '10';
                atkBefore.classList.remove('bump');
            }
            if (statPop) statPop.classList.remove('show');
            if (buffTimer) buffTimer.classList.remove('show');
            if (numsCost) numsCost.classList.remove('show');
            if (conn1) conn1.classList.remove('lit');
            if (conn2) conn2.classList.remove('lit');
            if (flying) {
                flying.style.opacity = '0';
                flying.classList.remove('trail');
            }
        }

        async function run() {
            reset();
            setCaption(stage, 'Лавка — выбор предмета');
            if (shopTile) shopTile.classList.add('visible');
            await delay(500);
            if (shopTile) shopTile.classList.add('highlight');
            await delay(700);

            setCaption(stage, 'Модалка покупки');
            if (shopModal) shopModal.classList.add('open');
            await delay(900);
            if (btnBuy) btnBuy.classList.add('flash');
            await delay(250);
            if (btnBuy) btnBuy.classList.remove('flash');
            if (shopModal) shopModal.classList.remove('open');

            setCaption(stage, 'Покупка за Нумы');
            if (numsBalance) {
                numsBalance.textContent = '220';
                numsBalance.classList.add('spent');
            }
            if (numsCost) numsCost.classList.add('show');
            await delay(700);
            if (shopTile) shopTile.classList.remove('highlight');
            if (shopCol) shopCol.classList.remove('active');
            if (shopCol) shopCol.classList.add('dim');
            if (conn1) conn1.classList.add('lit');
            await delay(400);

            setCaption(stage, 'Предмет в инвентаре');
            if (invCol) invCol.classList.remove('dim');
            if (invCol) invCol.classList.add('active');
            if (inventory) inventory.classList.add('visible');
            await delay(800);

            setCaption(stage, 'Нажмите «Использовать»');
            if (inventory) inventory.classList.add('selected');
            if (useBtn) {
                useBtn.classList.add('visible');
                await delay(400);
                useBtn.classList.add('pulse');
            }
            await delay(1200);

            setCaption(stage, 'Применение усиления');
            if (useBtn) useBtn.classList.remove('pulse');
            if (popover && useBtn) {
                var sRect = stage.getBoundingClientRect();
                var bRect = useBtn.getBoundingClientRect();
                popover.style.left = (bRect.left - sRect.left - 10) + 'px';
                popover.style.top = (bRect.top - sRect.top - 36) + 'px';
                popover.classList.add('show');
            }
            await delay(700);
            if (popover) popover.classList.remove('show');
            if (conn2) conn2.classList.add('lit');
            if (targetCol) {
                targetCol.classList.remove('dim');
                targetCol.classList.add('active');
            }

            var flyFrom = inventory ? inventory.querySelector('.item-icon-main') || inventory : inventory;
            var flyTo = buffSlot || targetCard;
            await flyItem(flying, stage, flyFrom, flyTo, 750);

            if (inventory) {
                inventory.classList.remove('selected');
                inventory.classList.add('used');
            }
            if (buffSlot) buffSlot.classList.add('visible');
            if (targetCard) targetCard.classList.add('buffed');
            if (buffTimer) buffTimer.classList.add('show');

            if (statPop && targetCard) {
                var sr = stage.getBoundingClientRect();
                var tr = targetCard.getBoundingClientRect();
                statPop.style.left = (tr.right - sr.left - 60) + 'px';
                statPop.style.top = (tr.top - sr.top - 8) + 'px';
                statPop.classList.add('show');
            }
            if (atkBefore) {
                await delay(200);
                atkBefore.textContent = '16';
                atkBefore.classList.add('bump');
            }
            setCaption(stage, 'Атака +6 на 30 минут');
            await delay(2800);
            if (statPop) statPop.classList.remove('show');
            if (atkBefore) atkBefore.classList.remove('bump');
            await delay(400);
            if (window.__TB_PROMO_ONCE__) return;
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Сундук --- */
    function initChestDemo(stage) {
        var chestTile = stage.querySelector('.demo-chest-tile');
        var openScene = stage.querySelector('.demo-chest-open-scene');
        var chestIcon = stage.querySelector('.demo-chest-icon');
        var sparkles = stage.querySelector('.demo-chest-sparkles');
        var dropResult = stage.querySelector('.demo-drop-result');
        var rewardTile = stage.querySelector('.demo-chest-reward-tile');

        async function run() {
            if (chestTile) chestTile.classList.remove('highlight');
            if (openScene) openScene.classList.remove('visible');
            if (chestIcon) chestIcon.classList.remove('opening', 'opened');
            if (sparkles) sparkles.classList.remove('active');
            if (dropResult) dropResult.classList.remove('show');
            if (rewardTile) rewardTile.classList.remove('visible');
            setCaption(stage, 'Сундук в инвентаре');
            await delay(600);

            setCaption(stage, 'Нажмите «Открыть»');
            if (chestTile) chestTile.classList.add('highlight');
            await delay(900);

            setCaption(stage, 'Открытие сундука…');
            if (chestTile) chestTile.classList.remove('highlight');
            if (openScene) openScene.classList.add('visible');
            await delay(400);
            if (chestIcon) chestIcon.classList.add('opening');
            if (sparkles) sparkles.classList.add('active');
            await delay(1400);
            if (chestIcon) {
                chestIcon.classList.remove('opening');
                chestIcon.classList.add('opened');
            }

            setCaption(stage, 'Выпал предмет!');
            if (dropResult) dropResult.classList.add('show');
            await delay(900);

            setCaption(stage, 'Предмет в инвентаре');
            if (rewardTile) rewardTile.classList.add('visible');
            await delay(2600);
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Поиск клана --- */
    function initClanSearchDemo(stage) {
        var primaryAd = stage.querySelector('.demo-clan-ad-primary');
        var applyBtn = stage.querySelector('.demo-clan-apply-btn');
        var pending = stage.querySelector('.demo-clan-pending');
        var modal = stage.querySelector('.demo-clan-modal');
        var confirmBtn = stage.querySelector('.demo-clan-modal-confirm');
        var secondaryAd = stage.querySelector('.demo-clan-ad-secondary');

        async function run() {
            if (primaryAd) primaryAd.classList.remove('highlight', 'dim');
            if (secondaryAd) secondaryAd.classList.remove('dim');
            if (applyBtn) {
                applyBtn.classList.remove('pulse', 'hidden');
            }
            if (pending) pending.classList.remove('show');
            if (modal) modal.classList.remove('open');
            if (confirmBtn) confirmBtn.classList.remove('flash');
            setCaption(stage, 'Объявления кланов');
            await delay(700);

            setCaption(stage, 'Выбор клана «Соколы»');
            if (primaryAd) primaryAd.classList.add('highlight');
            if (secondaryAd) secondaryAd.classList.add('dim');
            await delay(800);

            setCaption(stage, 'Подать заявку');
            if (applyBtn) applyBtn.classList.add('pulse');
            await delay(900);
            if (applyBtn) applyBtn.classList.remove('pulse');
            if (modal) modal.classList.add('open');
            await delay(700);

            setCaption(stage, 'Подтверждение');
            if (confirmBtn) confirmBtn.classList.add('flash');
            await delay(350);
            if (confirmBtn) confirmBtn.classList.remove('flash');
            if (modal) modal.classList.remove('open');

            setCaption(stage, 'Заявка отправлена');
            if (applyBtn) applyBtn.classList.add('hidden');
            if (pending) pending.classList.add('show');
            if (primaryAd) primaryAd.classList.remove('highlight');
            await delay(2800);
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Чат --- */
    function initChatDemo(stage) {
        var panel = stage.querySelector('.demo-clan-chat-panel');
        var ownMsg = stage.querySelector('.demo-chat-own-msg');
        var ownText = stage.querySelector('.demo-chat-own-text');
        var chatInput = stage.querySelector('.demo-chat-input');
        var sendBtn = stage.querySelector('.demo-chat-send');
        var message = 'Иду на Sofia-Grad! 🗺';
        var promoRunning = false;

        async function run() {
            // в промо — строго один проход (иначе в кадре видно сброс и повторный набор)
            if (window.__TB_PROMO_ONCE__) {
                if (stage.dataset.promoChatDone === '1' || promoRunning) return;
                promoRunning = true;
            }
            if (panel) panel.classList.add('open');
            if (ownMsg) ownMsg.classList.remove('visible');
            if (ownText) ownText.textContent = '';
            if (chatInput) chatInput.value = '';
            if (sendBtn) sendBtn.classList.remove('flash');
            setCaption(stage, 'Переписка в чате клана');
            await delay(1100);

            setCaption(stage, 'Пишем ответ');
            if (chatInput) {
                for (var i = 1; i <= message.length; i++) {
                    chatInput.value = message.slice(0, i);
                    await delay(55);
                }
            }
            if (sendBtn) sendBtn.classList.add('flash');
            await delay(200);
            if (sendBtn) sendBtn.classList.remove('flash');

            setCaption(stage, 'Сообщение отправлено');
            if (ownText) ownText.textContent = message;
            if (ownMsg) ownMsg.classList.add('visible');
            if (chatInput) chatInput.value = '';
            await delay(2800);
            if (window.__TB_PROMO_ONCE__) {
                stage.dataset.promoChatDone = '1';
                promoRunning = false;
                return;
            }
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Кланы --- */
    function initClansDemo(stage) {
        var avatar = stage.querySelector('.demo-leader-avatar');
        var name = stage.querySelector('.demo-leader-name');
        var count = stage.querySelector('.demo-leader-count');
        var row = stage.querySelector('.demo-leader-row');
        var clans = [
            { letter: 'С', color: '#3b82f6', name: 'Соколы', territories: 8 },
            { letter: 'Д', color: '#ef4444', name: 'Драконы', territories: 7 }
        ];
        var idx = 0;

        async function run() {
            var c = clans[idx % clans.length];
            idx++;
            setCaption(stage, 'Лидер: ' + c.name);
            if (row) {
                row.style.opacity = '0';
                row.style.transform = 'translateY(6px)';
            }
            await delay(100);
            if (avatar) {
                avatar.textContent = c.letter;
                avatar.style.background = c.color;
            }
            if (name) name.textContent = c.name;
            if (count) count.textContent = c.territories + ' из 28 обл.';
            if (row) {
                row.style.transition = 'opacity 0.4s, transform 0.4s';
                row.style.opacity = '1';
                row.style.transform = 'translateY(0)';
            }
            clans[0].territories = 7 + Math.floor(Math.random() * 3);
            clans[1].territories = 6 + Math.floor(Math.random() * 3);
            if (clans[0].territories <= clans[1].territories) {
                clans[0].territories = clans[1].territories + 1;
            }
            await delay(2800);
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Экипировка --- */
    function initEquipDemo(stage) {
        var slots = [
            { sel: '[data-slot="helmet"]', key: 'helmet', img: stage.dataset.equipHelmet, atk: 2, def: 1, label: 'Шлем' },
            { sel: '[data-slot="weapon_main"]', key: 'weapon_main', img: stage.dataset.equipWeapon, atk: 4, def: 0, label: 'Оружие' },
            { sel: '[data-slot="chest"]', key: 'chest', img: stage.dataset.equipChest, atk: 0, def: 3, label: 'Нагрудник' },
            { sel: '[data-slot="gloves"]', key: 'gloves', img: stage.dataset.equipGloves, atk: 1, def: 1, label: 'Перчатки' }
        ];
        var atkEl = stage.querySelector('.demo-equip-atk');
        var defEl = stage.querySelector('.demo-equip-def');
        var atkStat = stage.querySelector('.demo-equip-stat:first-child');
        var defStat = stage.querySelector('.demo-equip-stat:last-child');
        var flying = stage.querySelector('.demo-equip-flying');
        var baseAtk = 12;
        var baseDef = 10;

        function getInvItem(key) {
            return stage.querySelector('.demo-equip-inv-item[data-for="' + key + '"]');
        }

        async function run() {
            stage.querySelectorAll('.equipment-slot').forEach(function (slot) {
                slot.classList.add('equipment-slot--inactive');
                slot.classList.remove('equipment-slot--equipped', 'demo-equip-active');
                slot.style.boxShadow = '';
                var body = slot.querySelector('.equipment-slot-body');
                if (body) {
                    body.style.backgroundImage = '';
                    body.style.backgroundSize = '';
                }
            });
            stage.querySelectorAll('.demo-equip-inv-item').forEach(function (item) {
                item.classList.remove('active', 'used');
            });
            if (flying) flying.style.opacity = '0';
            if (atkEl) atkEl.textContent = String(baseAtk);
            if (defEl) defEl.textContent = String(baseDef);
            setCaption(stage, 'Предметы из инвентаря');
            var atk = baseAtk;
            var def = baseDef;
            await delay(600);

            for (var i = 0; i < slots.length; i++) {
                var slotData = slots[i];
                var invItem = getInvItem(slotData.key);
                var slotEl = stage.querySelector(slotData.sel);
                if (!slotEl) continue;

                setCaption(stage, 'Надеваем: ' + slotData.label);
                if (invItem) invItem.classList.add('active');
                await delay(450);

                var body = slotEl.querySelector('.equipment-slot-body');
                slotEl.classList.add('demo-equip-active');
                if (invItem && flying && body) {
                    flying.src = slotData.img;
                    await flyItem(flying, stage, invItem.querySelector('img') || invItem, body, 650);
                }

                slotEl.classList.remove('equipment-slot--inactive', 'demo-equip-active');
                slotEl.classList.add('equipment-slot--equipped');
                if (body && slotData.img) {
                    body.style.backgroundImage = 'url("' + slotData.img + '")';
                    body.style.backgroundSize = 'contain';
                }
                if (invItem) {
                    invItem.classList.remove('active');
                    invItem.classList.add('used');
                }

                atk += slotData.atk;
                def += slotData.def;
                if (atkEl) {
                    atkEl.textContent = String(atk);
                    if (atkStat) {
                        atkStat.classList.add('bump');
                        setTimeout(function () { atkStat.classList.remove('bump'); }, 400);
                    }
                }
                if (defEl) {
                    defEl.textContent = String(def);
                    if (defStat && slotData.def > 0) {
                        defStat.classList.add('bump');
                        setTimeout(function () { defStat.classList.remove('bump'); }, 400);
                    }
                }
                await delay(700);
            }
            setCaption(stage, 'Бонусы применены');
            await delay(2200);
            run();
        }

        whenVisible(stage, run);
    }

    /* --- PvP --- */
    function initPvpDemo(stage) {
        var challengeScene = stage.querySelector('.demo-pvp-challenge-scene');
        var duelLayout = stage.querySelector('.demo-layout-pvp');
        var participant = stage.querySelector('.demo-pvp-participant');
        var wagerModal = stage.querySelector('.demo-pvp-wager-modal');
        var wagerSubmit = stage.querySelector('.demo-pvp-wager-submit');
        var startBanner = stage.querySelector('.demo-pvp-start-banner');
        var taskText = stage.querySelector('.demo-pvp-task');
        var taskInput = stage.querySelector('.demo-pvp-input');
        var submitBtn = stage.querySelector('.demo-pvp-submit');
        var hpFill = stage.querySelector('.demo-opp-hp');
        var hpText = stage.querySelector('.demo-opp-hp-text');
        var hit = stage.querySelector('.demo-pvp-hit');
        var opp = stage.querySelector('.demo-pvp-opp');
        var hp = 100;
        var tasks = [
            { q: 'Найдите значение: 2³ = ?', a: '8' },
            { q: '√81 = ?', a: '9' },
            { q: '12 × 5 = ?', a: '60' },
            { q: 'Сколько будет 3/5 от 40?', a: '24' },
            { q: '15% от 200 = ?', a: '30' },
            { q: 'НОК(6, 8) = ?', a: '24' },
            { q: '1,25 + 0,75 = ?', a: '2' },
            { q: 'Решите: 2x = 18', a: '9' }
        ];
        var idx = 0;

        function resetChallengeScene() {
            if (challengeScene) challengeScene.classList.remove('hidden');
            if (duelLayout) duelLayout.classList.remove('visible');
            if (participant) participant.classList.remove('highlight');
            if (wagerModal) wagerModal.classList.remove('open');
            if (wagerSubmit) wagerSubmit.classList.remove('flash');
            if (startBanner) startBanner.classList.remove('show');
        }

        async function runChallengeIntro() {
            resetChallengeScene();
            setCaption(stage, 'Арена PvP');
            await delay(600);

            setCaption(stage, 'Выбор соперника');
            if (participant) participant.classList.add('highlight');
            await delay(900);

            setCaption(stage, 'Вызов на дуэль');
            if (wagerModal) wagerModal.classList.add('open');
            await delay(750);
            if (wagerSubmit) wagerSubmit.classList.add('flash');
            await delay(280);
            if (wagerSubmit) wagerSubmit.classList.remove('flash');
            if (wagerModal) wagerModal.classList.remove('open');
            if (participant) participant.classList.remove('highlight');

            setCaption(stage, 'Соперник принял вызов');
            if (startBanner) startBanner.classList.add('show');
            await delay(1100);
            if (startBanner) startBanner.classList.remove('show');

            if (challengeScene) challengeScene.classList.add('hidden');
            if (duelLayout) duelLayout.classList.add('visible');
            await delay(350);
        }

        async function runDuelTurn() {
            if (taskText) taskText.classList.remove('show');
            if (hit) hit.classList.remove('show');
            if (taskInput) taskInput.value = '';
            setCaption(stage, 'Ход соперника завершён');
            await delay(500);

            var t = tasks[idx % tasks.length];
            idx++;
            setCaption(stage, 'Ваш ход — решите задачу');
            if (taskText) {
                taskText.textContent = t.q;
                taskText.classList.add('show');
            }
            await delay(600);
            if (taskInput) {
                for (var i = 1; i <= t.a.length; i++) {
                    taskInput.value = t.a.slice(0, i);
                    await delay(160);
                }
            }
            if (submitBtn) submitBtn.style.filter = 'brightness(1.25)';
            await delay(200);
            if (submitBtn) submitBtn.style.filter = '';

            hp = Math.max(12, hp - 22);
            if (hpFill) hpFill.style.width = hp + '%';
            if (hpText) hpText.textContent = hp + ' / 100';
            setCaption(stage, 'Попадание! −22 HP');
            if (hit && opp) {
                var sRect = stage.getBoundingClientRect();
                var oRect = opp.getBoundingClientRect();
                hit.style.left = (oRect.left - sRect.left + 48) + 'px';
                hit.style.top = (oRect.top - sRect.top + 2) + 'px';
                hit.classList.add('show');
                setTimeout(function () { hit.classList.remove('show'); }, 850);
            }
            if (taskText) taskText.classList.remove('show');
            if (hp <= 20) {
                hp = 100;
                if (hpFill) hpFill.style.width = '100%';
                if (hpText) hpText.textContent = '100 / 100';
            }
            await delay(2000);
        }

        async function run() {
            await runChallengeIntro();
            await runDuelTurn();
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Регистрация --- */
    function initRegisterDemo(stage) {
        var guestScene = stage.querySelector('.demo-register-guest');
        var formScene = stage.querySelector('.demo-register-form-scene');
        var doneScene = stage.querySelector('.demo-register-done');
        var loginBtn = stage.querySelector('.demo-register-login-btn');
        var usernameInput = stage.querySelector('.demo-reg-username');
        var characterInput = stage.querySelector('.demo-reg-character');
        var submitBtn = stage.querySelector('.demo-reg-submit');
        var successBanner = stage.querySelector('.demo-register-success');
        var playerCard = stage.querySelector('.demo-register-player');
        var username = 'knight42';
        var character = 'Рыцарь Математики';

        function showScene(name) {
            [guestScene, formScene, doneScene].forEach(function (el) {
                if (el) el.classList.remove('active');
            });
            if (name === 'guest' && guestScene) guestScene.classList.add('active');
            if (name === 'form' && formScene) formScene.classList.add('active');
            if (name === 'done' && doneScene) doneScene.classList.add('active');
        }

        async function typeInput(input, text, speed) {
            if (!input) return;
            input.value = '';
            for (var i = 1; i <= text.length; i++) {
                input.value = text.slice(0, i);
                await delay(speed || 50);
            }
        }

        async function run() {
            if (loginBtn) loginBtn.classList.remove('pulse', 'flash');
            if (submitBtn) submitBtn.classList.remove('flash');
            if (successBanner) successBanner.classList.remove('show');
            if (playerCard) playerCard.classList.remove('visible');
            if (usernameInput) usernameInput.value = '';
            if (characterInput) characterInput.value = '';
            showScene('guest');
            setCaption(stage, 'Без входа — только просмотр');
            await delay(900);

            setCaption(stage, 'Переход к регистрации');
            if (loginBtn) loginBtn.classList.add('pulse');
            await delay(850);
            if (loginBtn) loginBtn.classList.remove('pulse');
            showScene('form');
            await delay(400);

            setCaption(stage, 'Заполнение формы');
            await typeInput(usernameInput, username, 55);
            await delay(250);
            await typeInput(characterInput, character, 45);
            await delay(500);

            setCaption(stage, 'Создание аккаунта');
            if (submitBtn) submitBtn.classList.add('flash');
            await delay(400);
            if (submitBtn) submitBtn.classList.remove('flash');
            showScene('done');
            if (successBanner) successBanner.classList.add('show');
            await delay(350);
            setCaption(stage, 'Можно участвовать в битве');
            if (playerCard) playerCard.classList.add('visible');
            await delay(2800);
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Время битвы --- */
    function initTimeDemo(stage) {
        var startScene = stage.querySelector('.demo-time-start');
        var battleScene = stage.querySelector('.demo-time-battle');
        var resultsScene = stage.querySelector('.demo-time-results');
        var startEl = stage.querySelector('.demo-countdown-start');
        var endEl = stage.querySelector('.demo-countdown-end');
        var finishedBanner = stage.querySelector('.demo-time-finished-banner');
        var winnerBlock = stage.querySelector('.demo-time-winner-block');

        function pad(n) {
            return n < 10 ? '0' + n : String(n);
        }

        function formatHMS(totalSec) {
            var h = Math.floor(totalSec / 3600);
            var m = Math.floor((totalSec % 3600) / 60);
            var s = totalSec % 60;
            return pad(h) + ':' + pad(m) + ':' + pad(s);
        }

        function showScene(name) {
            [startScene, battleScene, resultsScene].forEach(function (el) {
                if (el) el.classList.remove('active');
            });
            if (name === 'start' && startScene) startScene.classList.add('active');
            if (name === 'battle' && battleScene) battleScene.classList.add('active');
            if (name === 'results' && resultsScene) resultsScene.classList.add('active');
        }

        async function tickDown(el, fromSec, toSec, interval) {
            if (!el) return;
            for (var t = fromSec; t >= toSec; t--) {
                el.textContent = formatHMS(t);
                await delay(interval);
            }
        }

        async function run() {
            if (finishedBanner) finishedBanner.classList.remove('show');
            if (winnerBlock) winnerBlock.classList.remove('visible');
            if (startEl) startEl.textContent = '02:15:00';
            if (endEl) endEl.textContent = '05:42:18';
            showScene('start');
            setCaption(stage, 'Обратный отсчёт до старта');
            await delay(600);
            await tickDown(startEl, 8100, 8094, 180);
            await delay(400);

            showScene('battle');
            setCaption(stage, 'Битва идёт — таймер до конца');
            await delay(500);
            await tickDown(endEl, 20538, 20532, 180);
            await delay(500);

            showScene('results');
            setCaption(stage, 'Итоги битвы');
            if (finishedBanner) finishedBanner.classList.add('show');
            await delay(450);
            if (winnerBlock) winnerBlock.classList.add('visible');
            await delay(2800);
            run();
        }

        whenVisible(stage, run);
    }

    /* --- Навыки и умения --- */
    function initSkillsDemo(stage) {
        var panel = stage.querySelector('.demo-skills-panel');
        var tabStats = stage.querySelector('.demo-skills-tab--stats');
        var tabAbilities = stage.querySelector('.demo-skills-tab--abilities');
        var sceneStats = stage.querySelector('.demo-skills-scene--stats');
        var sceneClass = stage.querySelector('.demo-skills-scene--class');
        var sceneTree = stage.querySelector('.demo-skills-scene--tree');
        var pointsVal = stage.querySelector('.demo-skills-points-val');
        var atkCard = stage.querySelector('.demo-skills-stat-card[data-stat="atk"]');
        var atkVal = atkCard ? atkCard.querySelector('.demo-skills-stat-value') : null;
        var atkPlus = atkCard ? atkCard.querySelector('.demo-skills-stat-plus') : null;
        var saveBtn = stage.querySelector('.demo-skills-save-btn');
        var classesRow = stage.querySelector('.demo-skills-classes');
        var chooseBtn = stage.querySelector('.demo-skills-choose-btn');
        var abilityPointsVal = stage.querySelector('.demo-skills-ability-points-val');
        var rootNode = stage.querySelector('.demo-sk-node--root');
        var rootStatus = rootNode ? rootNode.querySelector('.demo-sk-node-status') : null;
        var rootPips = rootNode ? rootNode.querySelectorAll('.demo-sk-node-pips--root span') : [];
        var rootRank = rootNode ? rootNode.querySelector('.demo-sk-node-rank') : null;
        var nodeBtn = rootNode ? rootNode.querySelector('.demo-sk-node-btn') : null;
        var forkLeft = stage.querySelector('.demo-sk-node--fork-left');
        var forkLeftStatus = forkLeft ? forkLeft.querySelector('.demo-sk-node-status') : null;
        var bonusesLine = stage.querySelector('.demo-skills-bonuses-line');
        var bonusToast = stage.querySelector('.demo-skills-bonus-toast');
        var toastRank = stage.querySelector('.demo-sk-toast-rank');

        function setTab(which) {
            var onAbilities = which === 'class' || which === 'tree';
            if (tabStats) tabStats.classList.toggle('active', which === 'stats');
            if (tabAbilities) tabAbilities.classList.toggle('active', onAbilities);
            if (sceneStats) sceneStats.classList.toggle('active', which === 'stats');
            if (sceneClass) sceneClass.classList.toggle('active', which === 'class');
            if (sceneTree) sceneTree.classList.toggle('active', which === 'tree');
            if (panel) panel.classList.toggle('demo-skills-panel--tree', which === 'tree');
        }

        function reset() {
            setTab('stats');
            if (pointsVal) pointsVal.textContent = '3';
            if (atkVal) {
                atkVal.textContent = '12';
                atkVal.classList.remove('bump');
            }
            if (atkCard) atkCard.classList.remove('highlight');
            if (atkPlus) atkPlus.classList.remove('pulse');
            if (saveBtn) saveBtn.classList.remove('ready', 'flash');
            if (classesRow) classesRow.style.transform = '';
            stage.querySelectorAll('.demo-skills-class').forEach(function(el) {
                el.classList.remove('demo-skills-class--target');
            });
            var guardian = stage.querySelector('.demo-skills-class[data-class="guardian"]');
            if (guardian) guardian.classList.add('demo-skills-class--target');
            if (chooseBtn) chooseBtn.classList.remove('ready', 'pulse');
            if (abilityPointsVal) {
                abilityPointsVal.textContent = '2';
                abilityPointsVal.classList.remove('bump');
            }
            if (rootNode) {
                rootNode.classList.remove('demo-sk-node--glow', 'demo-sk-node--progress');
                rootNode.classList.add('demo-sk-node--available');
            }
            if (rootStatus) {
                rootStatus.className = 'demo-sk-node-status demo-sk-node-status--available';
                rootStatus.textContent = 'Доступно';
            }
            rootPips.forEach(function(p) { p.classList.remove('on', 'pop'); });
            if (rootRank) rootRank.textContent = '0';
            if (nodeBtn) nodeBtn.classList.remove('pulse');
            if (forkLeft) {
                forkLeft.classList.remove('demo-sk-node--available', 'demo-sk-node--path-chosen', 'demo-sk-node--glow');
                forkLeft.classList.add('demo-sk-node--locked');
            }
            if (forkLeftStatus) {
                forkLeftStatus.className = 'demo-sk-node-status demo-sk-node-status--locked';
                forkLeftStatus.textContent = 'Заблокировано';
            }
            if (bonusesLine) {
                bonusesLine.className = 'demo-skills-bonuses-line demo-skills-bonuses-line--empty';
                bonusesLine.textContent = 'Активные бонусы появятся после прокачки';
            }
            if (bonusToast) bonusToast.classList.remove('show');
            if (toastRank) toastRank.textContent = '1';
        }

        async function run() {
            reset();
            setCaption(stage, 'Характеристики героя');
            await delay(700);

            setCaption(stage, 'Распределение очков');
            if (atkCard) atkCard.classList.add('highlight');
            await delay(500);
            if (atkPlus) atkPlus.classList.add('pulse');
            await delay(200);
            if (atkPlus) atkPlus.classList.remove('pulse');
            if (atkVal) {
                atkVal.textContent = '13';
                atkVal.classList.add('bump');
            }
            if (pointsVal) pointsVal.textContent = '2';
            await delay(400);
            if (atkVal) atkVal.classList.remove('bump');
            if (saveBtn) saveBtn.classList.add('ready');
            await delay(350);
            if (saveBtn) saveBtn.classList.add('flash');
            await delay(200);
            if (saveBtn) saveBtn.classList.remove('flash');
            await delay(500);

            setCaption(stage, 'Вкладка «Умения»');
            setTab('class');
            if (sceneClass) {
                sceneClass.classList.remove('active');
                void sceneClass.offsetWidth;
                sceneClass.classList.add('active');
            }
            await delay(600);

            setCaption(stage, 'Выбор класса');
            if (classesRow) classesRow.style.transform = 'translateX(-24px)';
            await delay(700);
            if (chooseBtn) chooseBtn.classList.add('ready');
            await delay(400);
            if (chooseBtn) chooseBtn.classList.add('pulse');
            await delay(180);
            if (chooseBtn) chooseBtn.classList.remove('pulse');
            await delay(450);

            setCaption(stage, 'Дерево умений');
            setTab('tree');
            if (sceneTree) {
                sceneTree.classList.remove('active');
                void sceneTree.offsetWidth;
                sceneTree.classList.add('active');
            }
            await delay(700);
            if (rootNode) rootNode.classList.add('demo-sk-node--glow');
            setCaption(stage, 'Прокачка «Стойкости»');
            await delay(650);
            if (nodeBtn) nodeBtn.classList.add('pulse');
            await delay(180);
            if (nodeBtn) nodeBtn.classList.remove('pulse');
            if (rootPips[0]) {
                rootPips[0].classList.add('on', 'pop');
                await delay(200);
                rootPips[0].classList.remove('pop');
            }
            if (rootRank) rootRank.textContent = '1';
            if (rootNode) {
                rootNode.classList.remove('demo-sk-node--available', 'demo-sk-node--glow');
                rootNode.classList.add('demo-sk-node--progress');
            }
            if (rootStatus) {
                rootStatus.className = 'demo-sk-node-status demo-sk-node-status--progress';
                rootStatus.textContent = 'В процессе';
            }
            if (abilityPointsVal) {
                abilityPointsVal.textContent = '1';
                abilityPointsVal.classList.add('bump');
                await delay(250);
                abilityPointsVal.classList.remove('bump');
            }
            if (bonusesLine) {
                bonusesLine.className = 'demo-skills-bonuses-line demo-skills-bonuses-line--active';
                bonusesLine.innerHTML = '<strong>Активные бонусы:</strong> +3% защита';
            }
            if (bonusToast) bonusToast.classList.add('show');
            await delay(1400);
            if (bonusToast) bonusToast.classList.remove('show');

            setCaption(stage, 'Второй ранг — открывается развилка');
            if (rootNode) rootNode.classList.add('demo-sk-node--glow');
            await delay(500);
            if (nodeBtn) nodeBtn.classList.add('pulse');
            await delay(180);
            if (nodeBtn) nodeBtn.classList.remove('pulse');
            if (rootPips[1]) {
                rootPips[1].classList.add('on', 'pop');
                await delay(200);
                rootPips[1].classList.remove('pop');
            }
            if (rootRank) rootRank.textContent = '2';
            if (rootNode) rootNode.classList.remove('demo-sk-node--glow');
            if (bonusesLine) {
                bonusesLine.innerHTML = '<strong>Активные бонусы:</strong> +6% защита';
            }
            if (toastRank) toastRank.textContent = '2';
            if (bonusToast) bonusToast.classList.add('show');
            await delay(1200);
            if (bonusToast) bonusToast.classList.remove('show');
            await delay(300);

            setCaption(stage, 'Развилка — выберите путь');
            if (forkLeft) {
                forkLeft.classList.remove('demo-sk-node--locked');
                forkLeft.classList.add('demo-sk-node--available', 'demo-sk-node--glow');
            }
            if (forkLeftStatus) {
                forkLeftStatus.className = 'demo-sk-node-status demo-sk-node-status--available';
                forkLeftStatus.textContent = 'Доступно';
            }
            await delay(2200);
            run();
        }

        whenVisible(stage, run);
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-demo="register"]').forEach(initRegisterDemo);
        document.querySelectorAll('[data-demo="capture"]').forEach(initCaptureDemo);
        document.querySelectorAll('[data-demo="task"]').forEach(initTaskDemo);
        document.querySelectorAll('[data-demo="skills"]').forEach(initSkillsDemo);
        document.querySelectorAll('[data-demo="item"]').forEach(initItemDemo);
        document.querySelectorAll('[data-demo="clans"]').forEach(initClansDemo);
        document.querySelectorAll('[data-demo="equip"]').forEach(initEquipDemo);
        document.querySelectorAll('[data-demo="chest"]').forEach(initChestDemo);
        document.querySelectorAll('[data-demo="clan-search"]').forEach(initClanSearchDemo);
        document.querySelectorAll('[data-demo="chat"]').forEach(initChatDemo);
        document.querySelectorAll('[data-demo="pvp"]').forEach(initPvpDemo);
        document.querySelectorAll('[data-demo="time"]').forEach(initTimeDemo);
    });
})();
