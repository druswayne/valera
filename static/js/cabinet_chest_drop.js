// ==================== ДРОП: СУНДУК (UI) ====================
const DROP_AUTO_OPEN_DELAY_MS = 2000; // ожидание (тряска) перед открытием
const DROP_OPEN_ANIMATION_MS = 2000;  // длительность открытия
let dropStartOpenTimeoutId = null;
let dropRevealTimeoutId = null;
let dropChest3D = null;
let dropFireworks = null;

function normalizeDropProbability(value) {
    const raw = String(value ?? '').trim().toLowerCase();
    if (!raw) return 'high';
    if (raw === 'very_low' || raw === 'very-low' || raw === 'low' || raw === 'низкий' || raw === 'низкая' || raw.includes('очень')) return 'very_low';
    if (raw === 'medium' || raw === 'средний' || raw === 'средняя') return 'medium';
    return 'high';
}

function applyDropThemeToDom(chestWrap, probability) {
    if (!chestWrap) return;
    chestWrap.classList.remove('drop-theme-high', 'drop-theme-medium', 'drop-theme-very-low');
    const p = normalizeDropProbability(probability);
    const cls = p === 'very_low' ? 'drop-theme-very-low' : `drop-theme-${p}`;
    chestWrap.classList.add(cls);
}

function clearDropTheme(chestWrap) {
    if (!chestWrap) return;
    chestWrap.classList.remove('drop-theme-high', 'drop-theme-medium', 'drop-theme-very-low');
}

function createChestFireworks(canvas) {
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return null;

    let running = false;
    let rafId = null;
    let lastTs = 0;
    let w = 1;
    let h = 1;
    let dpr = 1;
    let ro = null;

    const rockets = [];
    const particles = [];

    const COLORS = [
        [255, 90, 90],
        [255, 214, 102],
        [125, 211, 252],
        [167, 243, 208],
        [196, 181, 253],
        [252, 165, 165]
    ];

    const rand = (min, max) => min + Math.random() * (max - min);
    const pickColor = () => COLORS[Math.floor(Math.random() * COLORS.length)];

    function resize() {
        const cw = Math.max(1, canvas.clientWidth);
        const ch = Math.max(1, canvas.clientHeight);
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        w = cw;
        h = ch;
        canvas.width = Math.round(cw * dpr);
        canvas.height = Math.round(ch * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function explode(x, y, base) {
        const count = Math.floor(rand(26, 38));
        for (let i = 0; i < count; i++) {
            const a = (Math.PI * 2 * i) / count + rand(-0.15, 0.15);
            const sp = rand(1.8, 3.6);
            particles.push({
                x,
                y,
                vx: Math.cos(a) * sp,
                vy: Math.sin(a) * sp,
                g: rand(2.6, 3.4),
                life: rand(0.75, 1.25),
                age: 0,
                r: base.r,
                gC: base.g,
                b: base.b
            });
        }
    }

    function launch(originX, originY) {
        const [r, g, b] = pickColor();
        rockets.push({
            x: originX,
            y: originY,
            vx: rand(-0.35, 0.35),
            vy: rand(-6.2, -7.6),
            t: 0,
            explodeAt: rand(0.48, 0.68),
            r, g, b
        });
    }

    function step(ts) {
        if (!running) return;
        if (!lastTs) lastTs = ts;
        const dt = Math.min(34, ts - lastTs) / 1000;
        lastTs = ts;

        ctx.clearRect(0, 0, w, h);

        // Ракеты (выстрелы)
        for (let i = rockets.length - 1; i >= 0; i--) {
            const r = rockets[i];
            r.t += dt;
            r.vy += 5.0 * dt;
            r.x += r.vx * 60 * dt;
            r.y += r.vy * 60 * dt;

            ctx.globalCompositeOperation = 'lighter';
            ctx.strokeStyle = `rgba(${r.r},${r.g},${r.b},0.65)`;
            ctx.lineWidth = 2.0;
            ctx.beginPath();
            ctx.moveTo(r.x, r.y);
            ctx.lineTo(r.x - r.vx * 22, r.y - r.vy * 0.5);
            ctx.stroke();
            ctx.globalCompositeOperation = 'source-over';

            if (r.t >= r.explodeAt || r.vy > -1.0) {
                explode(r.x, r.y, r);
                rockets.splice(i, 1);
            }
        }

        // Вспышки
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.age += dt;
            const k = Math.max(0, 1 - p.age / p.life);
            p.vy += p.g * 60 * dt * 0.06;
            p.x += p.vx * 60 * dt;
            p.y += p.vy * 60 * dt;

            ctx.fillStyle = `rgba(${p.r},${p.gC},${p.b},${0.9 * k})`;
            ctx.beginPath();
            ctx.arc(p.x, p.y, 2.2, 0, Math.PI * 2);
            ctx.fill();

            if (p.age >= p.life || p.y > h + 40 || p.x < -40 || p.x > w + 40) {
                particles.splice(i, 1);
            }
        }

        if (rockets.length === 0 && particles.length === 0) {
            stop();
            return;
        }

        rafId = requestAnimationFrame(step);
    }

    function start() {
        if (running) return;
        running = true;
        lastTs = 0;
        resize();
        ro = new ResizeObserver(() => resize());
        ro.observe(canvas);
        rafId = requestAnimationFrame(step);
    }

    function stop() {
        running = false;
        if (rafId) cancelAnimationFrame(rafId);
        rafId = null;
        lastTs = 0;
        rockets.length = 0;
        particles.length = 0;
        try { ro?.disconnect?.(); } catch (e) { /* noop */ }
        ro = null;
        try { ctx.clearRect(0, 0, w, h); } catch (e) { /* noop */ }
    }

    function shootFromChest() {
        start();
        const ox = w * 0.5;
        const oy = h * 0.52; // примерно “изнутри” сундука
        launch(ox + rand(-6, 6), oy);
        setTimeout(() => launch(ox + rand(-10, 10), oy), 120);
        setTimeout(() => launch(ox + rand(-8, 8), oy), 240);
    }

    return { start, stop, shootFromChest };
}

function stopDropFireworks() {
    try { dropFireworks?.stop?.(); } catch (e) { /* noop */ }
    dropFireworks = null;
}

function playDropFireworks() {
    const canvas = document.getElementById('dropFireworks');
    if (!canvas) return;
    stopDropFireworks();
    dropFireworks = createChestFireworks(canvas);
    dropFireworks?.shootFromChest?.();
}

function initDropChest3D() {
    const container = document.getElementById('dropChest');
    const fallback = document.getElementById('dropChestFallback');

    if (!container) return;
    if (!window.THREE) {
        // three.js не загрузился → показываем fallback
        if (fallback) fallback.style.display = 'block';
        container.style.display = 'none';
        return;
    }

    // Быстрая проверка WebGL
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) throw new Error('no-webgl');
    } catch (e) {
        if (fallback) fallback.style.display = 'block';
        container.style.display = 'none';
        return;
    }

    // Создаём рендер один раз
    if (dropChest3D) return;

    const THREE = window.THREE;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 2.35, 6.2);
    camera.lookAt(0, 0.25, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Свет
    const hemi = new THREE.HemisphereLight(0xffffff, 0x2b2b2b, 1.05);
    scene.add(hemi);
    const dir = new THREE.DirectionalLight(0xffffff, 1.1);
    dir.position.set(3.5, 6, 4);
    scene.add(dir);

    // Материалы (low-poly/мультяшно)
    const woodLightMat = new THREE.MeshStandardMaterial({ color: 0xb6763a, roughness: 0.85, metalness: 0.03, flatShading: true });
    const woodDarkMat = new THREE.MeshStandardMaterial({ color: 0x7b4b24, roughness: 0.9, metalness: 0.02, flatShading: true });
    const metalGoldMat = new THREE.MeshStandardMaterial({ color: 0xf2c14e, roughness: 0.35, metalness: 0.65, flatShading: true });
    const metalDarkMat = new THREE.MeshStandardMaterial({ color: 0x5b4b22, roughness: 0.55, metalness: 0.35, flatShading: true });
    const outlineMat = new THREE.MeshBasicMaterial({ color: 0x1b1b1b, side: THREE.BackSide });

    // Тема сундука по вероятности дропа
    const CHEST_THEMES = {
        high: {
            woodLight: 0xb6763a,
            woodDark: 0x7b4b24,
            metalMain: 0xf2c14e,
            metalMainRough: 0.35,
            metalMainMetal: 0.65,
            metalDark: 0x5b4b22,
            metalDarkRough: 0.55,
            metalDarkMetal: 0.35
        },
        medium: {
            // аметистовый сундук
            woodLight: 0x9b59b6,
            woodDark: 0x5b2c6f,
            metalMain: 0xcbd5e1,   // серебро
            metalMainRough: 0.28,
            metalMainMetal: 0.78,
            metalDark: 0x334155,
            metalDarkRough: 0.45,
            metalDarkMetal: 0.6
        },
        very_low: {
            // алмазный сундук (ледяной циан)
            woodLight: 0x67e8f9,
            woodDark: 0x0284c7,
            metalMain: 0xf8fafc,
            metalMainRough: 0.16,
            metalMainMetal: 0.92,
            metalDark: 0x22d3ee,
            metalDarkRough: 0.24,
            metalDarkMetal: 0.78
        }
    };

    function applyChestTheme(probability) {
        const p = normalizeDropProbability(probability);
        const t = CHEST_THEMES[p] || CHEST_THEMES.high;
        woodLightMat.color.setHex(t.woodLight);
        woodDarkMat.color.setHex(t.woodDark);
        metalGoldMat.color.setHex(t.metalMain);
        metalGoldMat.roughness = t.metalMainRough;
        metalGoldMat.metalness = t.metalMainMetal;
        metalDarkMat.color.setHex(t.metalDark);
        metalDarkMat.roughness = t.metalDarkRough;
        metalDarkMat.metalness = t.metalDarkMetal;
    }

    applyChestTheme('high');

    const addOutline = (mesh, scale = 1.045) => {
        const outline = new THREE.Mesh(mesh.geometry, outlineMat);
        outline.scale.set(scale, scale, scale);
        mesh.add(outline);
    };

    const chestGroup = new THREE.Group();
    scene.add(chestGroup);

    // Подложка/подиум + тень
    const pad = new THREE.Mesh(
        new THREE.CylinderGeometry(1.85, 1.95, 0.22, 28),
        new THREE.MeshStandardMaterial({ color: 0x2b2b2b, roughness: 0.9, metalness: 0.0, flatShading: true })
    );
    pad.position.y = -0.82;
    addOutline(pad, 1.02);
    chestGroup.add(pad);

    const padTop = new THREE.Mesh(
        new THREE.CylinderGeometry(1.75, 1.85, 0.06, 28),
        new THREE.MeshStandardMaterial({ color: 0x3a3a3a, roughness: 0.85, metalness: 0.0, flatShading: true })
    );
    padTop.position.y = -0.70;
    addOutline(padTop, 1.02);
    chestGroup.add(padTop);

    const shadow = new THREE.Mesh(
        new THREE.CircleGeometry(1.35, 28),
        new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.18 })
    );
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = -0.60;
    chestGroup.add(shadow);

    // свечение отключено полностью

    // ===== СУНДУК: полое основание (стенки + дно + внутренняя обшивка) =====
    const OUTER_W = 2.28;
    const OUTER_H = 0.96;
    const OUTER_D = 1.56;
    const BASE_CENTER_Y = -0.02;
    const WALL_THICK = 0.14;
    const FLOOR_THICK = 0.14;
    const LINER_THICK = 0.02;

    const innerW = OUTER_W - 2 * WALL_THICK;
    const innerD = OUTER_D - 2 * WALL_THICK;
    const wallH = OUTER_H - FLOOR_THICK;
    const bottomY = BASE_CENTER_Y - OUTER_H / 2;
    const floorY = bottomY + FLOOR_THICK / 2;
    const wallY = bottomY + FLOOR_THICK + wallH / 2;

    const interiorMat = new THREE.MeshStandardMaterial({
        color: 0x2a1a0f,
        roughness: 0.98,
        metalness: 0.0,
        flatShading: true,
        // важно: внутренности должны быть видны изнутри/под углами
        side: THREE.DoubleSide
    });

    // Наружные стенки/дно (дерево)
    const floorOuter = new THREE.Mesh(new THREE.BoxGeometry(innerW, FLOOR_THICK, innerD), woodLightMat);
    floorOuter.position.set(0, floorY, 0);
    chestGroup.add(floorOuter);

    const wallFrontOuter = new THREE.Mesh(new THREE.BoxGeometry(innerW, wallH, WALL_THICK), woodLightMat);
    wallFrontOuter.position.set(0, wallY, OUTER_D / 2 - WALL_THICK / 2);
    chestGroup.add(wallFrontOuter);

    const wallBackOuter = wallFrontOuter.clone();
    wallBackOuter.position.z = -OUTER_D / 2 + WALL_THICK / 2;
    chestGroup.add(wallBackOuter);

    const wallLeftOuter = new THREE.Mesh(new THREE.BoxGeometry(WALL_THICK, wallH, innerD), woodLightMat);
    wallLeftOuter.position.set(-OUTER_W / 2 + WALL_THICK / 2, wallY, 0);
    chestGroup.add(wallLeftOuter);

    const wallRightOuter = wallLeftOuter.clone();
    wallRightOuter.position.x = OUTER_W / 2 - WALL_THICK / 2;
    chestGroup.add(wallRightOuter);

    // Внутренняя обшивка (тёмная) — чтобы сундук выглядел полым
    const floorInner = new THREE.Mesh(new THREE.BoxGeometry(innerW, LINER_THICK, innerD), interiorMat);
    floorInner.position.set(0, floorY + FLOOR_THICK / 2 + LINER_THICK / 2 + 0.002, 0);
    chestGroup.add(floorInner);

    const innerFront = new THREE.Mesh(new THREE.BoxGeometry(innerW, wallH, LINER_THICK), interiorMat);
    innerFront.position.set(0, wallY, OUTER_D / 2 - WALL_THICK - LINER_THICK / 2 - 0.002);
    chestGroup.add(innerFront);

    const innerBack = innerFront.clone();
    innerBack.position.z = -OUTER_D / 2 + WALL_THICK + LINER_THICK / 2 + 0.002;
    chestGroup.add(innerBack);

    const innerLeft = new THREE.Mesh(new THREE.BoxGeometry(LINER_THICK, wallH, innerD), interiorMat);
    innerLeft.position.set(-OUTER_W / 2 + WALL_THICK + LINER_THICK / 2 + 0.002, wallY, 0);
    chestGroup.add(innerLeft);

    const innerRight = innerLeft.clone();
    innerRight.position.x = OUTER_W / 2 - WALL_THICK - LINER_THICK / 2 - 0.002;
    chestGroup.add(innerRight);

    // Верхняя окантовка НЕ должна перекрывать отверстие — делаем 4 бортика
    const RIM_W = OUTER_W + 0.06;
    const RIM_D = OUTER_D + 0.06;
    const RIM_H = 0.12;
    const RIM_T = 0.12;
    const rimY = bottomY + OUTER_H - RIM_H / 2;

    const rimFront = new THREE.Mesh(new THREE.BoxGeometry(RIM_W, RIM_H, RIM_T), woodDarkMat);
    rimFront.position.set(0, rimY, RIM_D / 2 - RIM_T / 2);
    addOutline(rimFront, 1.03);
    chestGroup.add(rimFront);

    const rimBack = rimFront.clone();
    rimBack.position.z = -RIM_D / 2 + RIM_T / 2;
    chestGroup.add(rimBack);

    const rimSideGeo = new THREE.BoxGeometry(RIM_T, RIM_H, RIM_D - 2 * RIM_T);
    const rimLeft = new THREE.Mesh(rimSideGeo, woodDarkMat);
    rimLeft.position.set(-RIM_W / 2 + RIM_T / 2, rimY, 0);
    addOutline(rimLeft, 1.03);
    chestGroup.add(rimLeft);

    const rimRight = rimLeft.clone();
    rimRight.position.x = RIM_W / 2 - RIM_T / 2;
    chestGroup.add(rimRight);

    const baseBottomRim = new THREE.Mesh(new THREE.BoxGeometry(2.34, 0.12, 1.62), woodDarkMat);
    baseBottomRim.position.set(0, -0.50, 0);
    addOutline(baseBottomRim);
    chestGroup.add(baseBottomRim);

    // Передняя панель + боковые панели
    const frontPanel = new THREE.Mesh(new THREE.BoxGeometry(1.92, 0.58, 0.06), woodDarkMat);
    frontPanel.position.set(0, -0.06, 0.79);
    addOutline(frontPanel, 1.035);
    chestGroup.add(frontPanel);

    const sidePanelL = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.58, 1.34), woodDarkMat);
    sidePanelL.position.set(-1.14, -0.06, 0);
    addOutline(sidePanelL, 1.035);
    chestGroup.add(sidePanelL);

    const sidePanelR = sidePanelL.clone();
    sidePanelR.position.x = 1.14;
    chestGroup.add(sidePanelR);

    // Ножки
    const footGeo = new THREE.BoxGeometry(0.26, 0.18, 0.26);
    const footPositions = [
        [-0.95, -0.62, 0.62],
        [0.95, -0.62, 0.62],
        [-0.95, -0.62, -0.62],
        [0.95, -0.62, -0.62]
    ];
    footPositions.forEach(([x, y, z]) => {
        const foot = new THREE.Mesh(footGeo, woodDarkMat);
        foot.position.set(x, y, z);
        addOutline(foot, 1.04);
        chestGroup.add(foot);
    });

    // Металлические уголки (простые, но читаемые)
    const cornerGeo = new THREE.BoxGeometry(0.16, 0.72, 0.16);
    const cornerPositions = [
        [-1.12, -0.08, 0.76],
        [1.12, -0.08, 0.76],
        [-1.12, -0.08, -0.76],
        [1.12, -0.08, -0.76]
    ];
    cornerPositions.forEach(([x, y, z]) => {
        const corner = new THREE.Mesh(cornerGeo, metalDarkMat);
        corner.position.set(x, y, z);
        addOutline(corner, 1.03);
        chestGroup.add(corner);
    });

    // Центральный ремень (вертикальный) + поперечины
    const bandV = new THREE.Mesh(new THREE.BoxGeometry(0.26, 1.02, 0.10), metalGoldMat);
    bandV.position.set(0, -0.02, 0.79);
    addOutline(bandV, 1.03);
    chestGroup.add(bandV);

    const bandTop = new THREE.Mesh(new THREE.BoxGeometry(2.36, 0.08, 0.10), metalGoldMat);
    bandTop.position.set(0, 0.24, 0.79);
    addOutline(bandTop, 1.03);
    chestGroup.add(bandTop);

    const bandBottom = new THREE.Mesh(new THREE.BoxGeometry(2.36, 0.08, 0.10), metalGoldMat);
    bandBottom.position.set(0, -0.40, 0.79);
    addOutline(bandBottom, 1.03);
    chestGroup.add(bandBottom);

    // Замок (пластина + язычок)
    const lockPlate = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.34, 0.10), metalDarkMat);
    lockPlate.position.set(0, 0.02, 0.86);
    addOutline(lockPlate, 1.03);
    chestGroup.add(lockPlate);

    const lockBody = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.26, 0.12), metalGoldMat);
    lockBody.position.set(0, 0.02, 0.92);
    addOutline(lockBody, 1.03);
    chestGroup.add(lockBody);

    const lockTongue = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.16, 0.06), metalGoldMat);
    lockTongue.position.set(0, -0.12, 0.95);
    addOutline(lockTongue, 1.03);
    chestGroup.add(lockTongue);

    // ===== СУНДУК: крышка (округлая, на шарнире) =====
    const lidPivot = new THREE.Group();
    lidPivot.position.set(0, 0.44, -0.78);
    chestGroup.add(lidPivot);

    // Нижняя "доска" крышки
    const lidBase = new THREE.Mesh(new THREE.BoxGeometry(2.28, 0.22, 1.56), woodLightMat);
    lidBase.position.set(0, 0.11, 0.78);
    addOutline(lidBase);
    lidPivot.add(lidBase);

    // Округлая верхушка крышки (полуцилиндр)
    const lidCurveGeo = new THREE.CylinderGeometry(0.78, 0.78, 2.28, 18, 1, false, 0, Math.PI);
    const lidCurve = new THREE.Mesh(lidCurveGeo, woodDarkMat);
    lidCurve.rotation.z = Math.PI / 2; // ось по X
    lidCurve.rotation.y = Math.PI;     // развернуть дугу "вверх"
    lidCurve.position.set(0, 0.32, 0.78);
    addOutline(lidCurve, 1.03);
    lidPivot.add(lidCurve);

    // Внутренняя сторона крышки (чтобы сундук выглядел полым при открытии)
    const lidInnerBase = new THREE.Mesh(
        new THREE.BoxGeometry(2.28 - 2 * WALL_THICK, LINER_THICK, 1.56 - 2 * WALL_THICK),
        interiorMat
    );
    // низ крышки около линии стыка с основанием
    lidInnerBase.position.set(0, 0.02, 0.78);
    lidPivot.add(lidInnerBase);

    const lidInnerCurveGeo = new THREE.CylinderGeometry(0.74, 0.74, 2.20, 16, 1, false, 0, Math.PI);
    const lidInnerCurve = new THREE.Mesh(lidInnerCurveGeo, interiorMat);
    lidInnerCurve.rotation.z = Math.PI / 2;
    lidInnerCurve.rotation.y = Math.PI;
    lidInnerCurve.position.set(0, 0.30, 0.78);
    lidPivot.add(lidInnerCurve);

    // Металлический обруч на крышке + "передняя кромка"
    const lidBand = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.62, 0.10), metalGoldMat);
    lidBand.position.set(0, 0.22, 1.00);
    addOutline(lidBand, 1.03);
    lidPivot.add(lidBand);

    const lidFrontLip = new THREE.Mesh(new THREE.BoxGeometry(2.36, 0.10, 0.10), metalDarkMat);
    lidFrontLip.position.set(0, 0.08, 1.55);
    addOutline(lidFrontLip, 1.03);
    lidPivot.add(lidFrontLip);

    // Петли (намёк)
    const hingeGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.34, 10);
    const hingeL = new THREE.Mesh(hingeGeo, metalDarkMat);
    hingeL.rotation.z = Math.PI / 2;
    hingeL.position.set(-0.72, 0.06, -0.02);
    addOutline(hingeL, 1.03);
    lidPivot.add(hingeL);

    const hingeR = hingeL.clone();
    hingeR.position.x = 0.72;
    lidPivot.add(hingeR);

    // Анимация
    let rafId = null;
    let visible = false;
    let openingStart = null;
    let openingDuration = DROP_OPEN_ANIMATION_MS;
    let opened = false;
    let rotating = false;
    let rotateStart = null;
    const ROTATE_DURATION_MS = DROP_AUTO_OPEN_DELAY_MS; // вращение ровно на время ожидания
    let baseRotY = 0; // "лицом вперёд" = 0
    let baseRotX = 0.10;
    let baseY = -0.06;
    // свечение отключено полностью

    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

    function renderFrame(now) {
        if (!visible) return;

        // Ожидание: плавное вращение на подиуме
        if (rotating && !opened && openingStart === null) {
            if (rotateStart === null) rotateStart = now;
            const elapsed = now - rotateStart;
            const t = Math.max(0, Math.min(1, elapsed / ROTATE_DURATION_MS));
            chestGroup.rotation.y = baseRotY + (Math.PI * 2) * t;
            if (t >= 1) {
                // заканчиваем ожидание строго "лицом вперёд"
                rotating = false;
                rotateStart = null;
                chestGroup.rotation.y = baseRotY;
            }
        } else {
            rotateStart = null;
            chestGroup.rotation.y = baseRotY;
        }

        // Спокойное положение по X/Z и позиции
        chestGroup.rotation.x = baseRotX;
        chestGroup.rotation.z = 0;
        chestGroup.position.x = 0;
        chestGroup.position.y = baseY;

        if (openingStart !== null && !opened) {
            const t = Math.min(1, (now - openingStart) / openingDuration);
            const k = easeOutCubic(t);
            lidPivot.rotation.x = -Math.PI * 0.62 * k; // ~112°
            if (t >= 1) {
                opened = true;
                openingStart = null;
            }
        }

        // свечение отключено полностью

        renderer.render(scene, camera);
        rafId = requestAnimationFrame(renderFrame);
    }

    function resize() {
        const w = Math.max(1, container.clientWidth);
        const h = Math.max(1, container.clientHeight);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h, false);
    }

    const ro = new ResizeObserver(() => resize());
    ro.observe(container);
    resize();

    // Показ/скрытие fallback
    if (fallback) fallback.style.display = 'none';
    container.style.display = 'block';

    dropChest3D = {
        show() {
            visible = true;
            if (!rafId) rafId = requestAnimationFrame(renderFrame);
        },
        hide() {
            visible = false;
            if (rafId) {
                cancelAnimationFrame(rafId);
                rafId = null;
            }
        },
        reset() {
            opened = false;
            openingStart = null;
            rotating = false;
            rotateStart = null;
            // свечение отключено полностью
            lidPivot.rotation.x = 0;
            chestGroup.rotation.y = baseRotY;
            chestGroup.rotation.x = baseRotX;
            chestGroup.rotation.z = 0;
            chestGroup.position.set(0, baseY, 0);
            // свечение отключено полностью
            renderer.render(scene, camera);
        },
        startRotate() {
            rotating = true;
            rotateStart = null;
        },
        stopRotate() {
            // останавливаем и ставим "лицом вперёд"
            rotating = false;
            rotateStart = null;
            baseRotY = 0;
            chestGroup.rotation.y = baseRotY;
        },
        startOpen(ms = DROP_OPEN_ANIMATION_MS) {
            openingDuration = ms;
            opened = false;
            openingStart = performance.now();
            // свечение отключено полностью
        },
        openInstant() {
            opened = true;
            openingStart = null;
            lidPivot.rotation.x = -Math.PI * 0.62;
            renderer.render(scene, camera);
        },
        setTheme(probability) {
            applyChestTheme(probability);
            renderer.render(scene, camera);
        }
    };
}

function fillCabinetDropResult(resultEl, dropName, grantImageUrl, resultOpts) {
    resultOpts = resultOpts || {};
    const chestEmpty = !!resultOpts.chestEmpty;
    if (!resultEl) return;
    resultEl.textContent = '';
    resultEl.innerHTML = '';
    const line = document.createElement('div');
    line.className = 'drop-result-line';
    if (grantImageUrl && !chestEmpty) {
        const img = document.createElement('img');
        img.src = grantImageUrl;
        img.alt = '';
        img.className = 'drop-result-grant-icon';
        img.decoding = 'async';
        line.appendChild(img);
    }
    const cap = document.createElement('div');
    cap.className = 'drop-result-caption';
    cap.textContent = chestEmpty ? String(dropName || 'Сундук оказался пустым.') : `Выпало: ${dropName}`;
    line.appendChild(cap);
    resultEl.appendChild(line);
}

function closeDropModal() {
    const dropModal = document.getElementById('dropModal');
    const chest = document.getElementById('dropChest');
    const chestWrap = document.getElementById('dropChestWrap');
    const result = document.getElementById('dropResult');
    const fallback = document.getElementById('dropChestFallback');
    if (dropStartOpenTimeoutId) {
        clearTimeout(dropStartOpenTimeoutId);
        dropStartOpenTimeoutId = null;
    }
    if (dropRevealTimeoutId) {
        clearTimeout(dropRevealTimeoutId);
        dropRevealTimeoutId = null;
    }

    stopDropFireworks();

    if (dropModal) {
        dropModal.classList.remove('show');
        dropModal.style.display = 'none';
    }
    const titleEl = document.getElementById('dropTitle');
    if (titleEl) {
        titleEl.style.display = '';
    }
    if (chest) {
        chest.classList.remove('opening', 'opened');
    }
    if (chestWrap) {
        chestWrap.classList.remove('opened');
        clearDropTheme(chestWrap);
    }
    if (result) {
        result.textContent = '';
        result.innerHTML = '';
    }
    if (fallback) {
        fallback.classList.remove('waiting', 'opening');
    }

    // 3D: останавливаем рендер
    try {
        dropChest3D?.hide?.();
    } catch (e) {
        // noop
    }
    try {
        if (typeof window.onCabinetDropModalClosed === 'function') {
            window.onCabinetDropModalClosed();
        }
    } catch (e) {
        // noop
    }
}

function showDropChest(dropName, probability = 'high', options) {
    options = options || {};
    const dropModal = document.getElementById('dropModal');
    const title = document.getElementById('dropTitle');
    const chest = document.getElementById('dropChest');
    const chestWrap = document.getElementById('dropChestWrap');
    const result = document.getElementById('dropResult');
    const fallback = document.getElementById('dropChestFallback');
    if (!dropModal || !chest || !result || !chestWrap) {
        // fallback на случай, если DOM не совпал
        alert(`🎁 Дроп: ${dropName}`);
        return;
    }

    if (dropStartOpenTimeoutId) {
        clearTimeout(dropStartOpenTimeoutId);
        dropStartOpenTimeoutId = null;
    }
    if (dropRevealTimeoutId) {
        clearTimeout(dropRevealTimeoutId);
        dropRevealTimeoutId = null;
    }

    stopDropFireworks();

    if (title) {
        if (Object.prototype.hasOwnProperty.call(options, 'headerTitle')) {
            title.textContent = options.headerTitle || '';
            title.style.display = options.headerTitle === '' ? 'none' : '';
        } else {
            title.textContent = '🎁 Дроп получен!';
            title.style.display = '';
        }
    }
    result.textContent = '';
    result.innerHTML = '';
    result.classList.remove('show');
    chest.classList.remove('opening', 'opened');
    chestWrap.classList.remove('opened');
    applyDropThemeToDom(chestWrap, probability);
    if (fallback) {
        fallback.classList.remove('waiting', 'opening');
    }

    dropModal.classList.add('show');
    dropModal.style.display = 'flex';

    // 3D: лениво инициализируем и запускаем рендер
    try {
        initDropChest3D();
        dropChest3D?.setTheme?.(probability);
        dropChest3D?.reset?.();
        dropChest3D?.show?.();
        dropChest3D?.startRotate?.();
    } catch (e) {
        // если что-то пошло не так — останется fallback
    }

    // Fallback: тряска 2 секунды
    if (fallback && fallback.style.display === 'block') {
        fallback.classList.add('waiting');
    }

    const reveal = () => {
        chest.classList.add('opened');
        chestWrap.classList.add('opened');
        fillCabinetDropResult(result, dropName, options.grantItemImageUrl || null, {
            chestEmpty: !!options.chestEmpty,
        });
        result.classList.add('show');
        playDropFireworks();
    };

    const startOpenAnimation = () => {
        try {
            dropChest3D?.stopRotate?.();
        } catch (e) {
            // noop
        }
        if (fallback) {
            fallback.classList.remove('waiting');
            fallback.classList.add('opening');
        }

        // визуальный "поп" при открытии
        void chest.offsetWidth;
        chest.classList.add('opening');

        // 3D: начинаем открытие крышки
        try {
            dropChest3D?.startOpen?.(DROP_OPEN_ANIMATION_MS);
        } catch (e) {
            // noop
        }
        // свечение отключено полностью
        dropRevealTimeoutId = setTimeout(reveal, DROP_OPEN_ANIMATION_MS);
    };

    // автоматически: 2с тряска -> стоп -> 2с открытие -> результат
    dropStartOpenTimeoutId = setTimeout(startOpenAnimation, DROP_AUTO_OPEN_DELAY_MS);

    // по клику/Enter/Space — открыть сразу (скип ожидания)
    const openNow = () => {
        if (dropStartOpenTimeoutId) {
            clearTimeout(dropStartOpenTimeoutId);
            dropStartOpenTimeoutId = null;
        }
        if (dropRevealTimeoutId) {
            clearTimeout(dropRevealTimeoutId);
            dropRevealTimeoutId = null;
        }
        if (fallback) {
            fallback.classList.remove('waiting', 'opening');
        }
        try { dropChest3D?.stopRotate?.(); } catch (e) { /* noop */ }
        try {
            dropChest3D?.openInstant?.();
        } catch (e) {
            // noop
        }
        reveal();
    };
    chestWrap.onclick = openNow;
    chestWrap.onkeydown = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openNow();
        }
    };
}
