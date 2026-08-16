#!/usr/bin/env python3
"""Снимает анимации с /territory-battle/rules и собирает ролик для Instagram.

Форматы:
  stories / reels — 1080x1920 (9:16), safe-zone по центру
  feed            — 1080x1080 (1:1)
  feed45          — 1080x1350 (4:5)

Выход: MP4 (H.264) — основной формат для Instagram; опционально GIF.
"""

from __future__ import annotations

import argparse
import io
import math
import os
import sys
import time
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "exports" / "instagram"

# Instagram-пресеты (чётные размеры — требование yuv420p)
FORMATS = {
    "stories": {"w": 1080, "h": 1920, "safe_top": 210, "safe_bottom": 200, "label": "Stories/Reels 9:16"},
    "reels": {"w": 1080, "h": 1920, "safe_top": 210, "safe_bottom": 200, "label": "Reels 9:16"},
    "feed": {"w": 1080, "h": 1080, "safe_top": 24, "safe_bottom": 24, "label": "Feed 1:1"},
    "feed45": {"w": 1080, "h": 1350, "safe_top": 40, "safe_bottom": 40, "label": "Feed 4:5"},
}

# --- Сценарий v5.1: обзор проекта (без flash, темы отдельным блоком) ---
# docs/TERRITORY_PROMO_SCENARIO.md
# Базовый хронометраж (1.0 = без замедления; раньше 1.2 ≈ −20% скорости)
TIME_SCALE = 1.0

SCENES = [
    ("task", "Задачи и XP", 12.0),
    ("skills", "Навыки", 9.5),
    ("capture", "Захват карты", 14.0),
    ("equip", "Снаряжение", 7.0),
    ("item", "Предметы", 7.0),
    ("chest", "Сундуки", 6.0),
    ("pvp", "PvP арена", 8.5),
    ("chat", "Чат клана", 11.0),
]

HIT_SCENES = "task,skills,capture,equip,item,chest,pvp,chat"

# Темы генераторов — полный список (docs/TERRITORY_GENERATOR_NAMES.md)
SKILL_TOPICS = [
    "Вычисления",
    "Уравнения",
    "НОД и НОК",
    "Основное свойство дроби",
    "Общий знаменатель",
    "Правильные/неправильные дроби",
    "Сложение и вычитание дробей",
    "Умножение и деление дробей",
    "Задачи на движение",
    "Задачи на дроби",
    "Сумма/разность и части",
    "Геометрия",
    "Величины",
    "Проценты",
    "Выражения с переменными",
    "Несколько действий с дробями",
    "Смешанные числа",
    "Совместная работа",
    "Перевод дробей",
    "Сложение и вычитание десятичных",
    "Умножение и деление десятичных",
    "Задачи на десятичные дроби",
]

# Еле заметные формулы на стартовом фоне
MATH_WALLPAPER = [
    "15 - 7 = ?",
    "3/4 + 1/2",
    "x + 5 = 12",
    "20% от 80",
    "НОД(24, 36)",
    "a^2 + b^2",
    "2,5 · 1,4",
    "S = a · b",
    "1/2 + 1/3",
    "v = s / t",
    "(x - 3)(x + 2)",
    "45% = 0,45",
    "НОК(8, 12)",
    "7/8 - 1/4",
    "2x = 18",
    "P = 2(a + b)",
]

CITY_LABELS = [
    "Sofia-Grad", "Plovdiv", "Varna", "Burgas", "Ruse",
    "Stara Zagora", "Pleven", "Sliven", "Dobrich", "Shumen",
]

SCENE_POPUPS = {
    "task": [
        (0.08, 2.4, "ВЕРНО! +XP", "Уровень растёт", "top"),
    ],
    "skills": [
        (0.10, 2.4, "ПРОКАЧАЙ ХАРАКТЕРИСТИКИ", "", "top"),
        (0.55, 2.4, "ВЫБЕРИ КЛАСС И ВЕТКУ", "", "bottom"),
    ],
    "capture": [
        (0.08, 2.4, "ЗАХВАТЫВАЙ ОБЛАСТИ", "", "top"),
        (0.50, 2.6, "ВЕРНО РЕШИЛ - ОБЛАСТЬ ТВОЯ", "+ сила клана", "bottom"),
    ],
    "equip": [
        (0.10, 2.6, "ЭКИПИРУЙ СНАРЯЖЕНИЕ", "+ к атаке и защите", "top"),
    ],
    "item": [
        (0.10, 2.6, "ПОКУПАЙ И ИСПОЛЬЗУЙ", "Усиления в бою", "top"),
    ],
    "chest": [
        (0.10, 2.4, "ЛУТ ИЗ СУНДУКОВ", "", "top"),
    ],
    "pvp": [
        (0.08, 2.4, "ДУЭЛЬ НА АРЕНЕ", "Проверь силу героя", "top"),
        (0.55, 2.4, "МАТЕМАТИКА РЕШАЕТ БОЙ", "", "bottom"),
    ],
    "chat": [
        (0.03, 1.4, "ЧАТ КЛАНА", "Планируй захваты вместе", "top"),
    ],
}

SCENE_CHAPTERS = {}

BG = (26, 14, 8)
GOLD = (212, 168, 75)
GOLD_LIGHT = (232, 200, 106)
MUTED = (184, 160, 136)

PROMO_CSS = """
.rules-support-float, .navbar, nav, header, .rules-nav-wrap,
.rules-page h1, .rules-intro, .rules-intro-updates-wrap,
.tb-demo-copy, .rules-section-heading, .tb-section-lead,
.rules-nav-footer { display: none !important; }
.rules-page { padding: 0 !important; background: #1a0e08 !important; }
.rules-demos-section, .rules-inner-wide { max-width: none !important; margin: 0 !important; padding: 0 !important; }
.tb-demo-rows { gap: 0 !important; }
.tb-demo-row {
    display: block !important;
    margin: 0 !important;
    padding: 12px !important;
    background: transparent !important;
    border: none !important;
}
.tb-demo-stage-wrap {
    width: 100% !important;
    max-width: 860px !important;
    margin: 0 auto !important;
    min-height: 0 !important;
    overflow: visible !important;
}
.tb-demo-stage,
.tb-demo-stage--tall,
.tb-demo-stage--items,
.tb-demo-stage--equip,
.tb-demo-stage--pvp,
.tb-demo-stage--skills,
.tb-demo-stage--chest,
.tb-demo-stage--time,
.tb-demo-stage--register,
.tb-demo-stage--chat {
    min-height: 0 !important;
    height: auto !important;
    overflow: hidden !important;
    padding: 14px 14px 16px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    /* border в боксе скриншота (box-shadow Playwright часто обрезает) */
    border: 2px solid rgba(212,168,75,0.85) !important;
    border-radius: 10px !important;
    box-shadow: 0 12px 40px rgba(0,0,0,0.45) !important;
    background: linear-gradient(160deg, #3a2818 0%, #2a1a10 55%, #1c100a 100%) !important;
    position: relative !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
/* PvP: баннер в потоке, без наезда на рамку/участников */
.tb-demo-stage[data-demo="pvp"] .demo-pvp-start-banner {
    position: relative !important;
    left: auto !important;
    top: auto !important;
    transform: none !important;
    margin: 8px auto 0 !important;
    opacity: 0 !important;
    display: none !important;
}
.tb-demo-stage[data-demo="pvp"] .demo-pvp-start-banner.show {
    display: block !important;
    opacity: 1 !important;
    transform: none !important;
}
.tb-demo-stage[data-demo="pvp"] .demo-pvp-arena-block {
    max-width: 100% !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}
/* захват: карта и подтверждение целиком в кадре */
.tb-demo-stage[data-demo="capture"] .map-wrap {
    width: 100% !important;
    max-width: 520px !important;
    margin: 0 auto !important;
}
.tb-demo-stage[data-demo="capture"] .map-viewport {
    max-height: 260px !important;
    overflow: hidden !important;
}
.tb-demo-stage[data-demo="capture"] .territory-confirm-wrap {
    position: relative !important;
    left: auto !important;
    right: auto !important;
    bottom: auto !important;
    transform: none !important;
    width: 100% !important;
    max-width: 480px !important;
    margin: 8px auto 0 !important;
    opacity: 1 !important;
    pointer-events: none !important;
}
.tb-demo-stage[data-demo="capture"] .territory-confirm-wrap:not(.open) {
    display: none !important;
}
.tb-demo-stage[data-demo="capture"] .task-modal-overlay {
    position: absolute !important;
    inset: 0 !important;
}
/* предметы: баланс и −Нумы внутри рамки, без height:100% «дыр» */
.tb-demo-stage[data-demo="item"] {
    overflow: hidden !important;
    max-width: 460px !important;
    width: 100% !important;
    box-sizing: border-box !important;
    padding: 10px 12px 14px !important;
    gap: 6px !important;
}
.tb-demo-stage[data-demo="item"] .demo-step-caption {
    position: relative !important;
    margin: 0 0 4px !important;
    max-width: 100% !important;
}
.tb-demo-stage[data-demo="item"] .demo-shop-balance {
    position: static !important;
    top: auto !important;
    right: auto !important;
    left: auto !important;
    width: 100% !important;
    display: flex !important;
    justify-content: flex-end !important;
    margin: 0 0 4px !important;
    z-index: 1 !important;
    box-sizing: border-box !important;
}
.tb-demo-stage[data-demo="item"] .nums-balance-block {
    padding: 4px 10px !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
.tb-demo-stage[data-demo="item"] .nums-balance-block .nums-value {
    font-size: 0.95rem !important;
}
.tb-demo-stage[data-demo="item"] .nums-balance-block .nums-suffix {
    font-size: 0.78rem !important;
}
.tb-demo-stage[data-demo="item"] .shop-item-modal.demo-shop-modal {
    position: relative !important;
    inset: auto !important;
    left: auto !important;
    top: auto !important;
    width: 100% !important;
    max-width: 100% !important;
    background: rgba(20, 12, 6, 0.55) !important;
    display: flex !important;
    padding: 6px !important;
    box-sizing: border-box !important;
}
.tb-demo-stage[data-demo="item"] .shop-item-modal.demo-shop-modal:not(.open) {
    display: none !important;
}
.tb-demo-stage[data-demo="item"] .shop-item-modal .modal-box {
    max-width: 100% !important;
    width: 100% !important;
    margin: 0 auto !important;
    box-sizing: border-box !important;
    padding: 10px !important;
}
.tb-demo-stage[data-demo="item"] .demo-item-flow {
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
    align-items: flex-start !important;
    padding: 4px 4px 8px !important;
    gap: 4px !important;
}
.tb-demo-stage[data-demo="item"] .demo-item-connector {
    padding-bottom: 28px !important;
    align-self: center !important;
}
.tb-demo-stage[data-demo="item"] .demo-item-col {
    max-width: 32% !important;
    min-width: 0 !important;
    overflow: hidden !important;
    gap: 4px !important;
}
.tb-demo-stage[data-demo="item"] .shop-item-tile,
.tb-demo-stage[data-demo="item"] .inventory-tile {
    width: 76px !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
.tb-demo-stage[data-demo="item"] .demo-nums-cost {
    font-size: 0.68rem !important;
    max-width: 100% !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
    margin: 0 !important;
    padding-bottom: 2px !important;
}
.tb-demo-stage[data-demo="item"] .demo-use-popover {
    left: 50% !important;
    right: auto !important;
    transform: translateX(-50%) scale(0.9) !important;
    max-width: calc(100% - 16px) !important;
    white-space: normal !important;
    text-align: center !important;
    box-sizing: border-box !important;
}
.tb-demo-stage[data-demo="item"] .demo-use-popover.show {
    transform: translateX(-50%) scale(1) !important;
}
.tb-demo-stage[data-demo="item"] .demo-flying-item,
.tb-demo-stage[data-demo="item"] .demo-stat-pop {
    max-width: 100% !important;
}
.tb-demo-stage > .demo-step-caption {
    position: static !important;
    align-self: stretch !important;
    text-align: center !important;
    margin: 0 0 4px !important;
    font-size: 0.95rem !important;
    color: #e8c86a !important;
}
.tb-demo-stage > :not(.demo-step-caption) {
    flex: 0 0 auto !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
}
.tb-demo-stage .task-result-toast.demo-toast,
.tb-demo-stage .task-result-toast {
    left: 50% !important;
    right: auto !important;
    transform: translateX(-50%) !important;
    bottom: 10px !important;
}
.tb-demo-stage .task-result-toast.show {
    transform: translateX(-50%) translateY(0) !important;
}
.map-wrap, .map-viewport {
    margin-left: auto !important;
    margin-right: auto !important;
    overflow: visible !important;
}
.territory-map {
    overflow: visible !important;
}
.demo-layout-task, .demo-layout-pvp,
.demo-layout-equip, .demo-layout-chest, .demo-item-flow,
.demo-skills-panel, .demo-layout-clans, .demo-time-scenes,
.demo-register-scenes, .demo-clan-search-list {
    margin-left: auto !important;
    margin-right: auto !important;
    overflow: visible !important;
}
.territory-confirm-wrap, .task-modal-overlay, .demo-task-modal {
    overflow: visible !important;
}

/* Playwright screenshot клипает overflow — модалки в потоке stage */
.tb-demo-stage {
    position: relative !important;
    font-family: Georgia, 'Segoe UI Emoji', 'Segoe UI Symbol', 'Apple Color Emoji', serif !important;
}
.tb-demo-stage .task-modal-overlay,
.tb-demo-stage .demo-task-modal {
    position: relative !important;
    inset: auto !important;
    left: auto !important;
    top: auto !important;
    right: auto !important;
    bottom: auto !important;
    width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    background: transparent !important;
    display: none !important;
    align-items: stretch !important;
    justify-content: center !important;
    padding: 8px 0 0 !important;
    z-index: 5 !important;
    transform: none !important;
    opacity: 1 !important;
    pointer-events: none !important;
}
.tb-demo-stage .task-modal-overlay.open,
.tb-demo-stage .demo-task-modal.open {
    display: block !important;
}
.tb-demo-stage .task-modal {
    position: relative !important;
    margin: 0 auto !important;
    max-width: 100% !important;
    width: min(100%, 420px) !important;
    transform: none !important;
    box-shadow: 0 8px 28px rgba(0,0,0,0.45) !important;
}
.tb-demo-stage .territory-confirm-wrap {
    position: relative !important;
    inset: auto !important;
    display: none !important;
    margin: 8px auto 0 !important;
    width: 100% !important;
    transform: none !important;
    background: transparent !important;
}
.tb-demo-stage .territory-confirm-wrap.open {
    display: block !important;
}
.tb-demo-stage .territory-confirm-box {
    margin: 0 auto !important;
    max-width: 100% !important;
}
.tb-demo-stage .task-result-toast.demo-toast,
.tb-demo-stage .task-result-toast {
    position: relative !important;
    left: auto !important;
    right: auto !important;
    bottom: auto !important;
    transform: none !important;
    display: none !important;
    margin: 10px auto 0 !important;
    width: fit-content !important;
    max-width: 100% !important;
}
.tb-demo-stage .task-result-toast.show {
    display: block !important;
    transform: none !important;
    opacity: 1 !important;
}
/* эмодзи — отдельный стек, чтобы не ломались Georgia */
.tb-demo-stage {
    position: relative !important;
}
.tb-demo-stage .territory-player-avatar-placeholder,
.tb-demo-stage .avatar-placeholder,
.tb-demo-stage .demo-skills-stat-icon,
.tb-demo-stage .demo-skills-class-icon,
.tb-demo-stage .demo-sk-node-orb,
.tb-demo-stage .demo-chest-emoji,
.tb-demo-stage .demo-chest-icon,
.tb-demo-stage .demo-pvp-participant-avatar,
.tb-demo-stage .demo-map-cursor,
.tb-demo-stage .territory-player-energy {
    font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', 'Apple Color Emoji', sans-serif !important;
    font-style: normal !important;
}
"""


def _font(size: int, bold: bool = False):
    # Segoe UI лучше тянет символы; Georgia — для «игрового» вида заголовков
    candidates = (
        ("C:/Windows/Fonts/georgiab.ttf" if bold else "C:/Windows/Fonts/georgia.ttf"),
        "C:/Windows/Fonts/seguisym.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    )
    for name in candidates:
        if os.path.isfile(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


_GRADIENT_CACHE: dict[tuple[int, int], Image.Image] = {}


def _gradient(width: int, height: int) -> Image.Image:
    key = (width, height)
    cached = _GRADIENT_CACHE.get(key)
    if cached is not None:
        return cached.copy()
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(38 - 16 * t)
        g = int(22 - 10 * t)
        b = int(12 - 5 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse(
        [width * 0.08, height * 0.18, width * 0.92, height * 0.82],
        fill=(70, 42, 18, 50),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    _GRADIENT_CACHE[key] = img
    return img.copy()


def draw_brand_bars(img: Image.Image, fmt: dict) -> Image.Image:
    """Верх/низ под UI Instagram (safe zone), бренд-полосы."""
    if fmt["safe_top"] < 80:
        return img
    out = img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    top = fmt["safe_top"]
    bottom = fmt["safe_bottom"]
    draw.rectangle([0, 0, w, top - 8], fill=(16, 8, 4))
    draw.rectangle([0, h - bottom + 8, w, h], fill=(16, 8, 4))
    draw.line([(40, top - 10), (w - 40, top - 10)], fill=GOLD, width=3)
    draw.line([(40, h - bottom + 10), (w - 40, h - bottom + 10)], fill=GOLD, width=3)

    # крупный бренд — читается с телефона
    ft = _font(40 if w >= 1000 else 32, bold=True)
    title = "БИТВА ЗА ТЕРРИТОРИЮ"
    bb = draw.textbbox((0, 0), title, font=ft)
    tw = bb[2] - bb[0]
    draw.text(((w - tw) // 2, 72), title, fill=GOLD_LIGHT, font=ft)

    fs = _font(26 if w >= 1000 else 20)
    # две строки слогана — крупнее и читаемее
    line1 = "решаешь · качаешь"
    line2 = "захватываешь · развиваешься"
    for i, line in enumerate((line1, line2)):
        sb = draw.textbbox((0, 0), line, font=fs)
        sw = sb[2] - sb[0]
        draw.text(((w - sw) // 2, 122 + i * 32), line, fill=MUTED, font=fs)

    cta_font = _font(24 if w >= 1000 else 18)
    cta = "Ссылка в профиле · territory-battle"
    cb = draw.textbbox((0, 0), cta, font=cta_font)
    cw = cb[2] - cb[0]
    draw.text(((w - cw) // 2, h - bottom + 36), cta, fill=MUTED, font=cta_font)
    return out


def make_title_card(
    width: int,
    height: int,
    title: str,
    subtitle: str = "",
    *,
    progress: float = 1.0,
    badge: str = "",
    fmt: dict | None = None,
) -> Image.Image:
    img = _gradient(width, height)
    draw = ImageDraw.Draw(img)
    p = max(0.0, min(1.0, progress))
    fmt = fmt or {"safe_top": 40, "safe_bottom": 40}

    inset_x = 40
    inset_y_top = fmt["safe_top"] + 16
    inset_y_bot = fmt["safe_bottom"] + 16
    inset = int(10 + (1 - p) * 20)
    col = tuple(int(c * (0.55 + 0.45 * p)) for c in GOLD)
    draw.rectangle(
        [inset_x + inset, inset_y_top + inset, width - inset_x - inset - 1, height - inset_y_bot - inset - 1],
        outline=col,
        width=max(3, int(3 + 2 * p)),
    )

    # масштаб под Stories / Feed
    is_tall = height >= 1400
    title_size = 78 if is_tall else (64 if height >= 1000 else 48)
    sub_size = 36 if is_tall else (30 if height >= 1000 else 24)
    badge_size = 34 if is_tall else 28

    max_text_w = width - 100
    if badge and p > 0.35:
        fb = _font(badge_size, bold=True)
        bb = draw.textbbox((0, 0), badge, font=fb)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        bx = (width - bw) // 2
        by = inset_y_top + 40
        draw.rounded_rectangle(
            [bx - 22, by - 8, bx + bw + 22, by + bh + 10],
            radius=12,
            fill=(60, 36, 18),
            outline=GOLD,
            width=3,
        )
        draw.text((bx, by), badge, fill=GOLD_LIGHT, font=fb)

    ft = _font(title_size, bold=True)
    fs = _font(sub_size)
    lines = _wrap_text(title, ft, max_text_w, draw)
    line_h = draw.textbbox((0, 0), "Ay", font=ft)[3] + 12
    sub_line_h = draw.textbbox((0, 0), "Ay", font=fs)[3] + 10
    sub_lines = _wrap_text(subtitle, fs, max_text_w, draw) if subtitle else []
    block_h = line_h * len(lines) + (28 + sub_line_h * len(sub_lines) if sub_lines else 0)
    ty = int(height // 2 - block_h // 2 + (1 - p) * 36)

    for i, line in enumerate(lines):
        tw = draw.textbbox((0, 0), line, font=ft)[2]
        tx = (width - tw) // 2
        y = ty + i * line_h
        draw.text((tx + 3, y + 3), line, fill=(0, 0, 0), font=ft)
        title_col = tuple(int(c * (0.4 + 0.6 * p)) for c in GOLD_LIGHT)
        draw.text((tx, y), line, fill=title_col, font=ft)

    if sub_lines and p > 0.45:
        sp = (p - 0.45) / 0.55
        sy0 = ty + len(lines) * line_h + 22
        for j, sl in enumerate(sub_lines):
            sw = draw.textbbox((0, 0), sl, font=fs)[2]
            sx = (width - sw) // 2
            sub_col = tuple(int(c * sp) for c in MUTED)
            draw.text((sx, sy0 + j * sub_line_h), sl, fill=sub_col, font=fs)

    return draw_brand_bars(img, fmt) if fmt.get("safe_top", 0) >= 80 else img


def title_sequence(
    width: int,
    height: int,
    title: str,
    subtitle: str,
    fps: int,
    seconds: float,
    badge: str = "",
    fmt: dict | None = None,
    *,
    fade_in: float = 0.55,
    fade_out: float = 0.45,
) -> list[Image.Image]:
    """Титр: fade-in → hold → fade-out. Без резких появлений."""
    total = max(1, int(fps * seconds))
    fi = max(2, int(fps * fade_in))
    fo = max(2, int(fps * fade_out))
    hold_n = max(1, total - fi - fo)
    frames: list[Image.Image] = []
    black = Image.new("RGB", (width, height), (8, 4, 2))
    full = make_title_card(width, height, title, subtitle, progress=1.0, badge=badge, fmt=fmt)
    for i in range(fi):
        p = ease_in_out((i + 1) / fi)
        card = make_title_card(width, height, title, subtitle, progress=p, badge=badge, fmt=fmt)
        frames.append(Image.blend(black, card, p))
    frames.extend(hold(full, fps, hold_n / fps))
    for i in range(fo):
        p = 1.0 - ease_in_out((i + 1) / fo)
        frames.append(Image.blend(black, full, p))
    return frames


def flash_frame(width: int, height: int, color=(255, 236, 180)) -> Image.Image:
    """Устарело для монтажа — оставляем на случай отладки."""
    return Image.new("RGB", (width, height), color)


def overlay_hook(img: Image.Image, text: str, fmt: dict) -> Image.Image:
    """Простой баннер (legacy)."""
    return draw_popup(img, text, "", fmt, progress=1.0, position="top")


def draw_popup(
    img: Image.Image,
    title: str,
    subtitle: str,
    fmt: dict,
    *,
    progress: float,
    position: str = "top",
) -> Image.Image:
    """Небольшой всплывающий кадр поверх анимации.

    progress 0..1: появление → удержание → исчезновение (внутри жизни попапа).
    """
    p = max(0.0, min(1.0, progress))
    # 0..0.22 in, 0.22..0.78 hold, 0.78..1 out
    if p < 0.22:
        vis = ease_in_out(p / 0.22)
        slide = 1.0 - vis
    elif p > 0.78:
        vis = ease_in_out((1.0 - p) / 0.22)
        slide = 1.0 - vis
    else:
        vis = 1.0
        slide = 0.0
    if vis < 0.02:
        return img

    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = base.size
    title_font = _font(44 if h > 1400 else 34, bold=True)
    sub_font = _font(28 if h > 1400 else 22)
    pad_x, pad_y = 20, 12
    max_text_w = w - 100

    title_lines = _wrap_text(title, title_font, max_text_w, draw)
    sub_lines = _wrap_text(subtitle, sub_font, max_text_w, draw) if subtitle else []
    title_h = draw.textbbox((0, 0), "Ay", font=title_font)[3] + 4
    sub_h = draw.textbbox((0, 0), "Ay", font=sub_font)[3] + 2
    content_h = title_h * len(title_lines) + (8 + sub_h * len(sub_lines) if sub_lines else 0)
    box_h = content_h + pad_y * 2

    content_w = 0
    for ln in title_lines:
        content_w = max(content_w, draw.textbbox((0, 0), ln, font=title_font)[2])
    for ln in sub_lines:
        content_w = max(content_w, draw.textbbox((0, 0), ln, font=sub_font)[2])
    box_w = min(w - 64, content_w + pad_x * 2 + 8)

    x0 = (w - box_w) // 2
    if position == "bottom":
        y_base = h - fmt["safe_bottom"] - box_h - 36
        y0 = int(y_base + slide * 28)
    elif position == "mid":
        y_base = h // 2 - box_h // 2
        y0 = int(y_base + slide * 16)
    else:
        y_base = fmt["safe_top"] + 24
        y0 = int(y_base - slide * 28)
    # не выходим за safe-zone / края кадра
    y0 = max(fmt["safe_top"] + 8, min(y0, h - fmt["safe_bottom"] - box_h - 8))
    x0 = max(24, min(x0, w - box_w - 24))

    alpha = int(235 * vis)
    # тень под карточкой
    draw.rounded_rectangle(
        [x0 + 4, y0 + 5, x0 + box_w + 4, y0 + box_h + 5],
        radius=14,
        fill=(0, 0, 0, int(110 * vis)),
    )

    fill = (18, 10, 6, alpha)
    outline = (*GOLD, int(255 * vis))
    draw.rounded_rectangle(
        [x0, y0, x0 + box_w, y0 + box_h],
        radius=14,
        fill=fill,
        outline=outline,
        width=3,
    )
    # акцентная полоска слева
    draw.rounded_rectangle(
        [x0 + 4, y0 + 8, x0 + 10, y0 + box_h - 8],
        radius=3,
        fill=(*GOLD_LIGHT, int(255 * vis)),
    )

    ty = y0 + pad_y
    for ln in title_lines:
        lw = draw.textbbox((0, 0), ln, font=title_font)[2]
        tx = x0 + (box_w - lw) // 2
        draw.text((tx + 1, ty + 1), ln, fill=(0, 0, 0, int(180 * vis)), font=title_font)
        draw.text((tx, ty), ln, fill=(*GOLD_LIGHT, int(255 * vis)), font=title_font)
        ty += title_h
    if sub_lines:
        ty += 4
        for ln in sub_lines:
            lw = draw.textbbox((0, 0), ln, font=sub_font)[2]
            tx = x0 + (box_w - lw) // 2
            draw.text((tx, ty), ln, fill=(*MUTED, int(255 * vis)), font=sub_font)
            ty += sub_h

    out = Image.alpha_composite(base, overlay)
    return out.convert("RGB")


def apply_scene_popups(
    frames: list[Image.Image],
    popups: list[tuple],
    fps: int,
    fmt: dict,
) -> list[Image.Image]:
    """Накладывает несколько коротких всплывающих заголовков на таймлайн сцены."""
    if not frames or not popups:
        return frames
    n = len(frames)
    scene_dur = n / max(fps, 1)
    out: list[Image.Image] = []
    for i, fr in enumerate(frames):
        t = i / max(fps, 1)  # секунды от начала сцены
        current = fr
        for start_r, dur_s, title, subtitle, pos in popups:
            start_t = start_r * scene_dur
            if start_t <= t <= start_t + dur_s:
                local = (t - start_t) / max(dur_s, 0.01)
                current = draw_popup(current, title, subtitle, fmt, progress=local, position=pos)
        out.append(current)
    return out


def fade_overlay_hook(
    frames: list[Image.Image],
    text: str,
    fmt: dict,
    fps: int,
) -> list[Image.Image]:
    """Совместимость: один хук сверху, если нет SCENE_POPUPS."""
    return apply_scene_popups(
        frames,
        [(0.05, min(2.8, len(frames) / max(fps, 1) * 0.45), text, "", "top")],
        fps,
        fmt,
    )


def trim_to_content(im: Image.Image, bg_thresh: int = 42, pad: int = 10) -> Image.Image:
    """Больше не обрезаем — оставляем весь скриншот сцены целиком."""
    return im.convert("RGB")


def place_centered(
    content: Image.Image,
    canvas_w: int,
    canvas_h: int,
    fmt: dict,
    *,
    zoom: float = 1.0,
    fit_margin: float = 0.92,
    frame: bool = True,
) -> Image.Image:
    """Contain: весь контент помещается, без обрезки (fit_margin < 1 = запас)."""
    canvas = _gradient(canvas_w, canvas_h)
    # запас под бренд-полосы
    area_top = fmt["safe_top"] + 28
    area_bot = canvas_h - fmt["safe_bottom"] - 36
    area_h = max(120, area_bot - area_top)
    area_w = canvas_w - 64
    cw, ch = content.size
    fit = min(area_w / cw, area_h / ch) * fit_margin
    scale = fit * min(1.0, zoom)
    nw = max(1, int(cw * scale))
    nh = max(1, int(ch * scale))
    resized = content.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (canvas_w - nw) // 2
    y = area_top + (area_h - nh) // 2
    canvas.paste(resized, (x, y))
    if frame and nw > 8 and nh > 8:
        # единая золотая рамка на всех демо-слайдах (не зависит от CSS/скриншота)
        draw = ImageDraw.Draw(canvas)
        inset = 1
        draw.rounded_rectangle(
            [x + inset, y + inset, x + nw - 1 - inset, y + nh - 1 - inset],
            outline=GOLD,
            width=3,
            radius=max(6, min(14, nw // 40)),
        )
        draw.rounded_rectangle(
            [x + inset + 3, y + inset + 3, x + nw - 4 - inset, y + nh - 4 - inset],
            outline=(160, 120, 55),
            width=1,
            radius=max(4, min(12, nw // 45)),
        )
    return draw_brand_bars(canvas, fmt)


def ken_burns(
    frames: list[Image.Image],
    canvas_w: int,
    canvas_h: int,
    fmt: dict,
    *,
    fit_margin: float = 0.92,
) -> list[Image.Image]:
    """Лёгкий отъезд — картинка не обрезается."""
    n = len(frames)
    out = []
    for i, f in enumerate(frames):
        t = ease_in_out(i / max(n - 1, 1))
        zoom = 1.0 - 0.02 * t
        out.append(place_centered(f, canvas_w, canvas_h, fmt, zoom=zoom, fit_margin=fit_margin))
    return out


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def crossfade(a: Image.Image, b: Image.Image, steps: int) -> list[Image.Image]:
    """Плавный dissolve с ease — без рывков."""
    frames = []
    for i in range(1, steps + 1):
        t = ease_in_out(i / (steps + 1))
        frames.append(Image.blend(a.convert("RGB"), b.convert("RGB"), t))
    return frames


def fade_to_black(frame: Image.Image, steps: int) -> list[Image.Image]:
    black = Image.new("RGB", frame.size, (8, 4, 2))
    return crossfade(frame, black, steps)


def fade_from_black(frame: Image.Image, steps: int) -> list[Image.Image]:
    black = Image.new("RGB", frame.size, (8, 4, 2))
    return crossfade(black, frame, steps)


def hold(frame: Image.Image, fps: int, seconds: float) -> list[Image.Image]:
    return [frame.copy() for _ in range(max(1, int(fps * seconds)))]


def temporal_smooth(frames: list[Image.Image], amount: float = 0.28) -> list[Image.Image]:
    """Смешивает соседние кадры — убирает дёрганье UI-анимаций."""
    if len(frames) < 2:
        return frames
    # единый размер сцены (trim даёт плавающий crop)
    max_w = max(f.width for f in frames)
    max_h = max(f.height for f in frames)
    normalized: list[Image.Image] = []
    for f in frames:
        canvas = Image.new("RGB", (max_w, max_h), BG)
        canvas.paste(f, ((max_w - f.width) // 2, (max_h - f.height) // 2))
        normalized.append(canvas)
    out = [normalized[0]]
    prev = normalized[0]
    for cur in normalized[1:]:
        blended = Image.blend(prev, cur, 1.0 - amount)
        out.append(blended)
        prev = blended
    return out


def png_to_image(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGB")


def capture_scene(page, demo: str, duration: float, fps: int) -> list[Image.Image]:
    stage = page.locator(f'[data-demo="{demo}"]').first
    stage.scroll_into_view_if_needed()
    # чат: короткая пауза — иначе в буфер попадает хвост 1-го цикла + старт 2-го
    settle_ms = 350 if demo == "chat" else 900
    page.wait_for_timeout(settle_ms)
    frames: list[Image.Image] = []
    interval_ms = max(30, int(1000 / fps))
    n = max(1, int(duration * fps))
    t0 = time.time()
    for i in range(n):
        png = stage.screenshot(type="png")
        frames.append(trim_to_content(png_to_image(png), bg_thresh=42, pad=8))
        # держим реальный тайминг, чтобы анимация UI не «скакала»
        target = t0 + (i + 1) * (interval_ms / 1000.0)
        delay = target - time.time()
        if delay > 0.005:
            page.wait_for_timeout(int(delay * 1000))
    return frames  # без temporal blend — иначе двоение текста/иконок


def open_mp4(path: Path, fps: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    return imageio.get_writer(
        str(path),
        fps=fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
        ffmpeg_params=["-movflags", "+faststart", "-profile:v", "high", "-level", "4.1"],
    )


def write_frames(writer, frames) -> int:
    n = 0
    for fr in frames:
        writer.append_data(np.asarray(fr.convert("RGB")))
        n += 1
    return n


def write_hold(writer, frame: Image.Image, fps: int, seconds: float) -> int:
    n = max(1, int(fps * seconds))
    arr = np.asarray(frame.convert("RGB"))
    for _ in range(n):
        writer.append_data(arr)
    return n


def write_crossfade(writer, a: Image.Image, b: Image.Image, steps: int) -> Image.Image:
    """Пишет dissolve и возвращает последний кадр."""
    a_rgb = a.convert("RGB")
    b_rgb = b.convert("RGB")
    last = b_rgb
    for i in range(1, steps + 1):
        t = ease_in_out(i / (steps + 1))
        last = Image.blend(a_rgb, b_rgb, t)
        writer.append_data(np.asarray(last))
    return last


def speed_up(frames: list[Image.Image], factor: int) -> list[Image.Image]:
    """Ускорение: каждый N-й кадр (×2, ×3…)."""
    if factor <= 1 or not frames:
        return frames
    return frames[::factor]


def flash_burst(width: int, height: int, n: int = 3) -> list[Image.Image]:
    """Короткая вспышка / glitch-акцент."""
    frames = []
    for i in range(n):
        if i % 2 == 0:
            frames.append(Image.new("RGB", (width, height), (255, 248, 230)))
        else:
            frames.append(Image.new("RGB", (width, height), (40, 20, 10)))
    return frames


def slice_seconds(frames: list[Image.Image], fps: int, start_s: float, dur_s: float) -> list[Image.Image]:
    if not frames:
        return []
    a = int(start_s * fps)
    b = int((start_s + dur_s) * fps)
    chunk = frames[a:b]
    need = max(1, int(dur_s * fps))
    if not chunk:
        chunk = [frames[min(a, len(frames) - 1)]]
    while len(chunk) < need:
        chunk.append(chunk[-1])
    return chunk[:need]


def color_grade(im: Image.Image, mood: str) -> Image.Image:
    """science=синий, loot=золото/фиолет, battle=оранж."""
    out = im.convert("RGB")
    if mood == "science":
        out = ImageEnhance.Color(out).enhance(1.05)
        r, g, b = out.split()
        b = b.point(lambda x: min(255, int(x * 1.12)))
        r = r.point(lambda x: int(x * 0.92))
        out = Image.merge("RGB", (r, g, b))
        return ImageEnhance.Brightness(out).enhance(1.02)
    if mood == "loot":
        out = ImageEnhance.Color(out).enhance(1.18)
        return ImageEnhance.Brightness(out).enhance(1.05)
    if mood == "battle":
        out = ImageEnhance.Color(out).enhance(1.15)
        r, g, b = out.split()
        r = r.point(lambda x: min(255, int(x * 1.1)))
        b = b.point(lambda x: int(x * 0.88))
        out = Image.merge("RGB", (r, g, b))
        return ImageEnhance.Brightness(out).enhance(1.04)
    return out


def make_map_wake_frame(width: int, height: int, t: float, show_title: bool) -> Image.Image:
    """Стилизованное «пробуждение карты» (туман → регионы → замки)."""
    img = Image.new("RGB", (width, height), (8, 10, 18))
    draw = ImageDraw.Draw(img)
    # фон
    for y in range(height):
        u = y / max(height - 1, 1)
        draw.line([(0, y), (width, y)], fill=(int(10 + 18 * u), int(12 + 14 * u), int(22 + 20 * u)))

    # регионы (простые многоугольники)
    cx, cy = width // 2, height // 2 + 40
    regions = [
        [(-220, -180), (-40, -220), (20, -80), (-160, -40)],
        [(40, -200), (240, -160), (200, 20), (60, -40)],
        [(-200, 20), (-20, -20), (40, 160), (-180, 180)],
        [(20, 40), (200, 10), (240, 200), (40, 180)],
        [(-60, -40), (80, -20), (60, 100), (-40, 80)],
    ]
    reveal = ease_in_out(min(1.0, t / 0.75))
    for i, poly in enumerate(regions):
        pts = [(cx + int(x * (0.85 + 0.1 * reveal)), cy + int(y * (0.85 + 0.1 * reveal))) for x, y in poly]
        base = (40 + i * 18, 70 + i * 12, 110 + i * 8)
        col = tuple(int(c * (0.35 + 0.65 * reveal)) for c in base)
        draw.polygon(pts, fill=col, outline=(180, 160, 90) if reveal > 0.4 else (60, 70, 90))

    # замки
    if reveal > 0.45:
        castles = [(-120, -100), (140, -90), (-100, 100), (130, 120), (10, 20)]
        a = min(1.0, (reveal - 0.45) / 0.4)
        for ox, oy in castles:
            x, y = cx + ox, cy + oy
            draw.rectangle([x - 10, y - 18, x + 10, y + 10], fill=(int(160 * a), int(140 * a), int(70 * a)))
            draw.polygon([(x - 14, y - 18), (x, y - 34), (x + 14, y - 18)], fill=(int(200 * a), int(170 * a), int(80 * a)))

    # туман поверх (убывает)
    fog = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fog)
    fog_a = int(210 * (1.0 - ease_in_out(min(1.0, t / 0.85))))
    for i in range(14):
        y0 = int(i * height / 14)
        y1 = int((i + 1) * height / 14 + 20)
        fd.rectangle([0, y0, width, y1], fill=(30, 40, 55, max(0, fog_a - i * 4)))
    img = Image.alpha_composite(img.convert("RGBA"), fog).convert("RGB")
    draw = ImageDraw.Draw(img)

    if show_title:
        ft = _font(64 if height > 1400 else 48, bold=True)
        title = "БИТВА ЗА ТЕРРИТОРИЮ"
        lines = _wrap_text(title, ft, width - 80, draw)
        line_h = draw.textbbox((0, 0), "Ay", font=ft)[3] + 8
        ty = height // 2 - (line_h * len(lines)) // 2 - 80
        for i, ln in enumerate(lines):
            tw = draw.textbbox((0, 0), ln, font=ft)[2]
            # лёгкая тень
            draw.text(((width - tw) // 2 + 2, ty + i * line_h + 2), ln, fill=(0, 0, 0), font=ft)
            draw.text(((width - tw) // 2, ty + i * line_h), ln, fill=GOLD_LIGHT, font=ft)
    return img


def map_wake_sequence(width: int, height: int, fps: int, seconds: float = 4.0) -> list[Image.Image]:
    n = max(1, int(fps * seconds))
    frames = []
    for i in range(n):
        t = i / max(n - 1, 1)
        show_title = t >= 0.72  # ~с 3-й секунды при 4с
        frames.append(make_map_wake_frame(width, height, t, show_title))
    return frames


def phone_wipe_sequence(
    map_frame: Image.Image, width: int, height: int, fps: int, seconds: float = 2.0
) -> list[Image.Image]:
    """Карта сворачивается в «телефон»."""
    n = max(1, int(fps * seconds))
    frames = []
    phone_w, phone_h = int(width * 0.55), int(height * 0.62)
    for i in range(n):
        t = ease_in_out(i / max(n - 1, 1))
        canvas = _gradient(width, height)
        scale = 1.0 - 0.55 * t
        mw = max(40, int(width * scale))
        mh = max(40, int(height * scale))
        mini = map_frame.resize((mw, mh), Image.Resampling.LANCZOS)
        # рамка телефона появляется к концу
        if t > 0.35:
            px = (width - phone_w) // 2
            py = (height - phone_h) // 2 - 20
            draw = ImageDraw.Draw(canvas)
            glow = int(80 * ((t - 0.35) / 0.65))
            draw.rounded_rectangle(
                [px - 8, py - 8, px + phone_w + 8, py + phone_h + 8],
                radius=36,
                outline=(GOLD[0], GOLD[1], GOLD[2],),
                width=4,
            )
            draw.rounded_rectangle(
                [px, py, px + phone_w, py + phone_h],
                radius=28,
                fill=(12, 14, 22),
                outline=(90, 100, 120),
                width=3,
            )
            # экран
            inset = 18
            screen = mini.resize((phone_w - 2 * inset, phone_h - 2 * inset - 20), Image.Resampling.LANCZOS)
            canvas.paste(screen, (px + inset, py + inset + 10))
            if glow:
                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                od.ellipse(
                    [px - 40, py - 40, px + phone_w + 40, py + phone_h + 40],
                    outline=(212, 168, 75, glow),
                    width=6,
                )
                canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        else:
            canvas.paste(mini, ((width - mw) // 2, (height - mh) // 2))
        if t > 0.55:
            canvas = draw_popup(
                canvas, "Твой ход, командор", "", {"safe_top": 40, "safe_bottom": 40},
                progress=min(1.0, (t - 0.55) / 0.35), position="bottom",
            )
        frames.append(canvas)
    return frames


def write_demo_block(
    writer,
    raw_frames: list[Image.Image],
    fmt: dict,
    fps: int,
    seconds: float,
    *,
    popups: list | None = None,
    mood: str = "",
    start_s: float = 0.0,
    flash_on_end: bool = False,
    zoom_in: bool = False,
    stretch: bool = True,
    one_shot: bool = False,
    one_shot_src_s: float = 5.0,
    fit_margin: float = 0.90,
) -> tuple[int, Image.Image | None]:
    """Ken Burns + попапы + цветокор + запись. Возвращает (n, last)."""
    if not raw_frames:
        return 0, None
    need = max(1, int(fps * seconds))
    a = int(start_s * fps)
    if one_shot:
        # один проход демо (без повтора цикла) → растянуть до seconds
        take = max(8, int(one_shot_src_s * fps))
        chunk = raw_frames[a : a + take] or raw_frames[:take] or raw_frames[-1:]
    else:
        take = min(len(raw_frames), max(need // 2 if stretch else need, int(seconds * fps * 0.7)))
        chunk = raw_frames[a : a + take] or raw_frames[a : a + 1] or raw_frames[-1:]
    if stretch and len(chunk) > 1 and need > len(chunk):
        stretched = []
        for i in range(need):
            idx = int(i / max(need - 1, 1) * (len(chunk) - 1))
            stretched.append(chunk[idx])
        chunk = stretched
    elif len(chunk) < need:
        while len(chunk) < need:
            chunk.append(chunk[-1])
    else:
        chunk = chunk[:need]
    dressed = ken_burns(chunk, fmt["w"], fmt["h"], fmt, fit_margin=fit_margin)
    if zoom_in and dressed:
        # слабый зум без сильной обрезки UI
        zoomed = []
        nfr = len(dressed)
        for i, f in enumerate(dressed):
            t = ease_in_out(i / max(nfr - 1, 1))
            z = 1.0 + 0.035 * t
            w, h = f.size
            cw, ch = max(2, int(w / z)), max(2, int(h / z))
            left, top = (w - cw) // 2, (h - ch) // 2
            crop = f.crop((left, top, left + cw, top + ch)).resize((w, h), Image.Resampling.LANCZOS)
            zoomed.append(crop)
        dressed = zoomed
    if popups:
        dressed = apply_scene_popups(dressed, popups, fps, fmt)
    if len(dressed) > need:
        dressed = dressed[:need]
    while len(dressed) < need and dressed:
        dressed.append(dressed[-1])
    last = None
    n = 0
    for f in dressed:
        fr = color_grade(f, mood) if mood else f
        writer.append_data(np.asarray(fr.convert("RGB")))
        last = fr
        n += 1
    if flash_on_end and last is not None:
        flash = ImageEnhance.Brightness(last).enhance(1.25)
        writer.append_data(np.asarray(flash.convert("RGB")))
        n += 1
    return n, last


def write_micro_toast(
    writer, base: Image.Image, title: str, subtitle: str, fmt: dict, fps: int, seconds: float = 1.2
) -> int:
    """Короткая микро-награда поверх последнего кадра."""
    card = draw_popup(base.copy(), title, subtitle, fmt, progress=0.55, position="mid")
    return write_hold(writer, card, fps, seconds)


def write_rapid_cuts(
    writer,
    sources: list[tuple[list[Image.Image], str]],
    fmt: dict,
    fps: int,
    total_seconds: float,
    *,
    cut_len: float = 1.35,
    mood: str = "battle",
    popups: list | None = None,
) -> int:
    """Быстрая нарезка кусков по ~1–1.5 с из разных демо."""
    if not sources:
        return 0
    need = max(1, int(fps * total_seconds))
    cut_n = max(1, int(fps * cut_len))
    n = 0
    src_i = 0
    offset = 0.0
    frames_buf: list[Image.Image] = []
    while n + len(frames_buf) < need:
        raw, key = sources[src_i % len(sources)]
        src_i += 1
        if not raw:
            continue
        chunk = slice_seconds(raw, fps, offset % max(0.1, len(raw) / fps - 0.5), cut_len + 0.2)
        offset += cut_len * 1.7
        dressed = ken_burns(chunk[:cut_n], fmt["w"], fmt["h"], fmt)
        for f in dressed[:cut_n]:
            frames_buf.append(color_grade(f, mood) if mood else f)
            if len(frames_buf) >= need:
                break
        # вспышка между кусками
        if frames_buf and len(frames_buf) < need:
            frames_buf.append(ImageEnhance.Brightness(frames_buf[-1]).enhance(1.4))
    if popups and frames_buf:
        frames_buf = apply_scene_popups(frames_buf[:need], popups, fps, fmt)
    for f in frames_buf[:need]:
        writer.append_data(np.asarray(f.convert("RGB")))
        n += 1
    return n


def make_problem_card(width: int, height: int, fmt: dict) -> Image.Image:
    """Хук в стиле бренда: фон + еле заметные формулы."""
    img = _gradient(width, height)
    draw = ImageDraw.Draw(img)
    # золотая рамка как у титров
    inset_x, inset_y_top = 40, fmt.get("safe_top", 40) + 16
    inset_y_bot = fmt.get("safe_bottom", 40) + 16
    draw.rectangle(
        [inset_x, inset_y_top, width - inset_x - 1, height - inset_y_bot - 1],
        outline=GOLD, width=3,
    )
    # разбросанные формулы — еле заметный цвет
    faint = (68, 48, 32)
    f_dim = _font(26 if height > 1400 else 20)
    rng_positions = [
        (0.08, 0.22), (0.55, 0.20), (0.22, 0.28), (0.70, 0.26),
        (0.12, 0.38), (0.62, 0.36), (0.35, 0.42), (0.78, 0.40),
        (0.10, 0.52), (0.48, 0.50), (0.72, 0.54), (0.18, 0.62),
        (0.58, 0.60), (0.30, 0.70), (0.68, 0.68), (0.42, 0.78),
    ]
    for i, (px, py) in enumerate(rng_positions):
        s = MATH_WALLPAPER[i % len(MATH_WALLPAPER)]
        draw.text((int(width * px), int(height * py)), s, fill=faint, font=f_dim)

    ft = _font(62 if height > 1400 else 46, bold=True)
    lines = _wrap_text("Надоело просто решать задачи?", ft, width - 120, draw)
    line_h = draw.textbbox((0, 0), "Ay", font=ft)[3] + 12
    ty = height // 2 - (line_h * len(lines)) // 2
    for i, ln in enumerate(lines):
        tw = draw.textbbox((0, 0), ln, font=ft)[2]
        draw.text(((width - tw) // 2 + 2, ty + i * line_h + 2), ln, fill=(20, 10, 4), font=ft)
        draw.text(((width - tw) // 2, ty + i * line_h), ln, fill=GOLD_LIGHT, font=ft)
    fs = _font(28 if height > 1400 else 22)
    hint = "Есть способ интереснее"
    hw = draw.textbbox((0, 0), hint, font=fs)[2]
    draw.text(((width - hw) // 2, ty + len(lines) * line_h + 36), hint, fill=MUTED, font=fs)
    return img


def make_map_with_cities(width: int, height: int, t: float = 1.0, map_bg: Image.Image | None = None) -> Image.Image:
    """Фон заставки: карта + подписи городов (или кадр из демо capture)."""
    if map_bg is not None:
        canvas = place_centered(
            map_bg, width, height, {"safe_top": 40, "safe_bottom": 40},
            zoom=1.0 + 0.04 * t, frame=False,
        )
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle([0, 0, width, height], fill=(8, 6, 4, 110))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    else:
        canvas = make_map_wake_frame(width, height, min(1.0, 0.4 + 0.6 * t), show_title=False)
    draw = ImageDraw.Draw(canvas)
    fc = _font(20 if height > 1400 else 16, bold=True)
    positions = [
        (0.28, 0.38), (0.52, 0.36), (0.72, 0.40), (0.35, 0.52), (0.58, 0.50),
        (0.45, 0.62), (0.68, 0.58), (0.30, 0.68), (0.55, 0.70), (0.75, 0.65),
    ]
    a = ease_in_out(min(1.0, t))
    for i, name in enumerate(CITY_LABELS[: len(positions)]):
        px = int(width * positions[i][0])
        py = int(height * positions[i][1])
        col = (int(212 * a), int(180 * a), int(90 * a))
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=col)
        bb = draw.textbbox((0, 0), name, font=fc)
        draw.text((px - (bb[2] - bb[0]) // 2, py + 8), name, fill=col, font=fc)
    return canvas


def topics_brain_sequence(width: int, height: int, fps: int, seconds: float, fmt: dict) -> list[Image.Image]:
    """Блок «прокачивай мозг»: все генераторы (22), крупный шрифт на всю высоту."""
    n = max(1, int(fps * seconds))
    topics = list(SKILL_TOPICS)
    is_tall = height > 1400
    frames = []
    for i in range(n):
        t = i / max(n - 1, 1)
        img = _gradient(width, height)
        draw = ImageDraw.Draw(img)
        margin_x = 40 if is_tall else 28
        top = fmt.get("safe_top", 40) + (24 if is_tall else 12)
        bot = height - fmt.get("safe_bottom", 40) - (20 if is_tall else 12)
        draw.rectangle([margin_x, top, width - margin_x - 1, bot], outline=GOLD, width=3)

        fb = _font(26 if is_tall else 18, bold=True)
        badge = "ВСЕ ТЕМЫ"
        bb = draw.textbbox((0, 0), badge, font=fb)
        bw, bh = bb[2] - bb[0] + 28, bb[3] - bb[1] + 14
        bx = (width - bw) // 2
        by = top + 16
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, outline=GOLD, width=2)
        draw.text((bx + 14, by + 5), badge, fill=GOLD_LIGHT, font=fb)

        ft = _font(40 if is_tall else 28, bold=True)
        title = "Решай задачи - прокачивай мозг"
        lines = _wrap_text(title, ft, width - margin_x * 2 - 28, draw)
        line_h = draw.textbbox((0, 0), "Ay", font=ft)[3] + 6
        ty = by + bh + 16
        for j, ln in enumerate(lines):
            tw = draw.textbbox((0, 0), ln, font=ft)[2]
            draw.text(((width - tw) // 2, ty + j * line_h), ln, fill=GOLD_LIGHT, font=ft)

        fs = _font(22 if is_tall else 16)
        sub = f"{len(topics)} генераторов заданий"
        sw = draw.textbbox((0, 0), sub, font=fs)[2]
        draw.text(((width - sw) // 2, ty + len(lines) * line_h + 8), sub, fill=MUTED, font=fs)

        # сетка 2×11 — на всю доступную высоту, крупный шрифт
        cols = 2
        rows = (len(topics) + cols - 1) // cols
        gap_x = 14 if is_tall else 10
        col_w = (width - margin_x * 2 - 32 - gap_x) // cols
        list_top = ty + len(lines) * line_h + 28
        avail_h = max(240, bot - 14 - list_top)
        row_h = max(48 if is_tall else 34, avail_h // rows)
        # крупный шрифт: ~45–55% высоты строки
        font_sz = max(24, min(36 if is_tall else 26, int(row_h * 0.48)))
        list_font = _font(font_sz, bold=True)
        pad_x, pad_y = 10, max(6, int(row_h * 0.12))

        reveal_n = max(0, min(len(topics), int((t - 0.10) / 0.72 * len(topics) + 0.5)))
        for k in range(reveal_n):
            topic = topics[k]
            col = k % cols
            row = k // cols
            cx = margin_x + 18 + col * (col_w + gap_x)
            cy = list_top + row * row_h
            if cy + row_h > bot - 12:
                continue
            max_tw = col_w - pad_x * 2
            # ломаем по пробелам и по «/»
            soft = topic.replace("/", " / ")
            wrapped = _wrap_text(soft, list_font, max_tw, draw)
            if len(wrapped) > 2:
                # чуть уменьшить шрифт для длинных названий
                small = _font(max(18, font_sz - 4), bold=True)
                wrapped = _wrap_text(soft, small, max_tw, draw)[:2]
                use_font = small
            else:
                use_font = list_font
                # если одна слишком длинная «слово» — всё равно укоротить
                for wi, wl in enumerate(wrapped):
                    while draw.textbbox((0, 0), wl, font=use_font)[2] > max_tw and len(wl) > 5:
                        wl = wl[:-2] + "…"
                    wrapped[wi] = wl
            line_gap = 3
            text_h = 0
            for wl in wrapped:
                text_h += draw.textbbox((0, 0), "Ay", font=use_font)[3] + line_gap
            text_h -= line_gap
            box_h = min(row_h - 4, text_h + pad_y * 2)
            box_w = col_w
            lx = cx
            ly = cy + max(0, (row_h - box_h) // 2)
            draw.rounded_rectangle(
                [lx, ly, lx + box_w - 1, ly + box_h],
                radius=10, fill=(48, 30, 16), outline=GOLD, width=2,
            )
            ty_txt = ly + (box_h - text_h) // 2
            for wl in wrapped:
                ww = draw.textbbox((0, 0), wl, font=use_font)[2]
                draw.text((lx + (box_w - ww) // 2, ty_txt), wl, fill=GOLD_LIGHT, font=use_font)
                ty_txt += draw.textbbox((0, 0), "Ay", font=use_font)[3] + line_gap

        if fmt.get("safe_top", 0) >= 80:
            img = draw_brand_bars(img, fmt)
        frames.append(img)
    return frames


def title_over_map(
    width: int,
    height: int,
    fps: int,
    seconds: float,
    map_src: Image.Image | None,
    fmt: dict,
    *,
    hold_seconds: float = 3.0,
) -> list[Image.Image]:
    """Заставка: карта + яркое название проекта + холд."""
    anim_n = max(1, int(fps * seconds))
    hold_n = max(1, int(fps * hold_seconds))
    frames = []
    # появление
    for i in range(anim_n):
        t = i / max(anim_n - 1, 1)
        bg = make_map_with_cities(width, height, t=0.5 + 0.5 * t, map_bg=map_src)
        card = make_title_card(
            width, height, "Битва за территорию",
            "Математика как стратегическая игра",
            progress=min(1.0, t * 1.6), badge="ИГРА ДЛЯ УМА", fmt=fmt,
        )
        # к концу сильнее «карта → титр», название читается ярче
        blend = 0.45 + 0.50 * ease_in_out(t)
        mixed = Image.blend(bg, card, blend)
        # лёгкое усиление яркости/контраста на финале
        if t > 0.55:
            boost = 1.0 + 0.12 * ((t - 0.55) / 0.45)
            mixed = ImageEnhance.Brightness(ImageEnhance.Contrast(mixed).enhance(1.08)).enhance(boost)
        frames.append(mixed)
    # холд яркого названия
    if frames:
        last = frames[-1]
        bright = ImageEnhance.Brightness(ImageEnhance.Contrast(last).enhance(1.12)).enhance(1.08)
        frames.extend([bright] * hold_n)
    return frames


def write_chapter(
    writer, fmt: dict, fps: int, title: str, subtitle: str, seconds: float = 3.0, badge: str = ""
) -> int:
    seq = title_sequence(
        fmt["w"], fmt["h"], title, subtitle, fps, seconds,
        badge=badge, fmt=fmt, fade_in=0.4, fade_out=0.35,
    )
    return write_frames(writer, seq)


def _sec(s: float) -> float:
    """Замедление хронометража ~20%."""
    return s * TIME_SCALE


def compose_v5(
    writer,
    raw: dict[str, list[Image.Image]],
    fmt: dict,
    fps: int,
) -> int:
    """Обзорный ролик v5.1: без flash, темы отдельным блоком, темп медленнее."""
    W, H = fmt["w"], fmt["h"]
    n = 0

    task = raw.get("task") or []
    skills = raw.get("skills") or []
    cap = raw.get("capture") or []
    equip = raw.get("equip") or []
    item = raw.get("item") or []
    chest = raw.get("chest") or []
    pvp = raw.get("pvp") or []
    chat = raw.get("chat") or []

    map_still = cap[len(cap) // 3] if cap else None

    # --- 0. Хук (без flash после) ---
    hook = make_problem_card(W, H, fmt)
    n += write_hold(writer, hook, fps, _sec(2.5))

    # --- 1. Заставка с картой: яркое название + холд ---
    n += write_frames(
        writer,
        title_over_map(W, H, fps, _sec(4.0), map_still, fmt, hold_seconds=_sec(3.5)),
    )

    # --- 2. Задачи + прокачка персонажа ---
    n += write_chapter(
        writer, fmt, fps,
        "Решай задачи и прокачивай персонажа",
        "XP, уровень, характеристики",
        _sec(3.0), badge="01",
    )
    c, _ = write_demo_block(
        writer, task, fmt, fps, _sec(5.0),
        popups=SCENE_POPUPS.get("task"), mood="science", start_s=0.0, zoom_in=True,
    )
    n += c
    c, _ = write_demo_block(
        writer, skills, fmt, fps, _sec(4.0),
        popups=SCENE_POPUPS.get("skills"), mood="science", start_s=0.0,
    )
    n += c

    # --- 2.5 Темы / мозг: все 22 генератора ---
    n += write_frames(
        writer,
        topics_brain_sequence(W, H, fps, _sec(8.0), fmt),
    )

    # --- 3. Захват областей (без zoom-crop, больше запас по краям) ---
    n += write_chapter(
        writer, fmt, fps,
        "Решай задачи - захватывай области",
        "Карта · сила клана · стратегия",
        _sec(3.0), badge="02",
    )
    c, last = write_demo_block(
        writer, cap, fmt, fps, _sec(6.0),
        popups=[SCENE_POPUPS["capture"][0]], mood="battle", start_s=0.5,
        zoom_in=False, fit_margin=0.82,
    )
    n += c
    if last is not None:
        n += write_micro_toast(writer, last, "Территория захвачена!", "+25 к силе клана", fmt, fps, _sec(1.0))

    # --- 4. Улучшения ---
    n += write_chapter(
        writer, fmt, fps,
        "Улучшай героя",
        "Навыки · характеристики · снаряжение",
        _sec(3.0), badge="03",
    )
    c, _ = write_demo_block(
        writer, skills, fmt, fps, _sec(3.0),
        popups=SCENE_POPUPS.get("skills"), mood="loot", start_s=3.0, fit_margin=0.88,
    )
    n += c
    c, _ = write_demo_block(
        writer, equip, fmt, fps, _sec(3.5),
        popups=SCENE_POPUPS.get("equip"), mood="loot", start_s=0.0, fit_margin=0.86,
    )
    n += c
    loot_src = item or chest
    loot_key = "item" if item else "chest"
    c, _ = write_demo_block(
        writer, loot_src, fmt, fps, _sec(3.8),
        popups=SCENE_POPUPS.get(loot_key), mood="loot", start_s=0.35,
        # один проход покупки: без растягивания цикла
        one_shot=True, one_shot_src_s=5.2, stretch=False,
        zoom_in=False, fit_margin=0.86,
    )
    n += c

    # --- 5. PvP ---
    n += write_chapter(
        writer, fmt, fps,
        "Сразись на PvP-арене",
        "Дуэль один на один",
        _sec(3.0), badge="04",
    )
    c, _ = write_demo_block(
        writer, pvp, fmt, fps, _sec(5.0),
        popups=SCENE_POPUPS.get("pvp"), mood="battle", start_s=0.0,
        zoom_in=False, fit_margin=0.86,
    )
    n += c

    # --- 6. Коммуникация: короткий титр + быстрый чат ---
    n += write_chapter(
        writer, fmt, fps,
        "Общайся с кланом",
        "Чат, планы, совместные захваты",
        _sec(0.75), badge="05",
    )
    c, _ = write_demo_block(
        writer, chat, fmt, fps, _sec(1.9),
        popups=SCENE_POPUPS.get("chat"), mood="science",
        # один проход; берём середину (набор + отправка), без растягивания
        one_shot=True, one_shot_src_s=2.2, start_s=2.5, stretch=False,
        zoom_in=False, fit_margin=0.88,
    )
    n += c

    # --- 7. CTA ---
    cta = title_sequence(
        W, H,
        "Начни захват прямо сейчас",
        "Прокачай ум · захвати карту · победи с кланом",
        fps, _sec(3.5), badge="ИГРАЙ", fmt=fmt, fade_in=0.4, fade_out=0.2,
    )
    n += write_frames(writer, cta)
    del cta
    hold_base = make_title_card(
        W, H,
        "Начни захват прямо сейчас",
        "Ссылка в профиле · territory-battle",
        progress=1.0, badge="ИГРАЙ", fmt=fmt,
    )
    swipe = draw_popup(hold_base, "ЛИСТАЙ ВВЕРХ", "чтобы играть", fmt, progress=0.5, position="bottom")
    for i in range(int(fps * _sec(3.5))):
        pulse = 1.0 + 0.04 * math.sin(i / fps * math.pi * 1.6)
        writer.append_data(np.asarray(ImageEnhance.Brightness(swipe).enhance(pulse)))
        n += 1

    return n


def save_mp4(frames: list[Image.Image], path: Path, fps: int) -> None:
    writer = open_mp4(path, fps)
    try:
        write_frames(writer, frames)
    finally:
        writer.close()


def save_gif(frames: list[Image.Image], path: Path, fps: int, colors: int = 64) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    duration = int(1000 / fps)
    # уменьшаем для соцсетей
    scaled = []
    for f in frames:
        q = f
        if f.width > 540:
            nh = int(f.height * (540 / f.width))
            q = f.resize((540, nh), Image.Resampling.LANCZOS)
        scaled.append(q.convert("P", palette=Image.Palette.ADAPTIVE, colors=colors))
    scaled[0].save(
        path,
        save_all=True,
        append_images=scaled[1:],
        duration=duration,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Промо-ролик territory-battle для Instagram")
    ap.add_argument("--url", default="http://127.0.0.1:5000/territory-battle/rules")
    ap.add_argument(
        "--format",
        choices=list(FORMATS.keys()) + ["all"],
        default="stories",
        help="stories/reels (9:16), feed (1:1), feed45 (4:5) или all",
    )
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--fps", type=int, default=24, help="24 fps — кинематографичный ритм")
    ap.add_argument("--scenes", default=HIT_SCENES, help=f"По умолчанию хит: {HIT_SCENES}")
    ap.add_argument("--gif", action="store_true", help="Также сохранить сжатый GIF")
    ap.add_argument("--no-titles", action="store_true")
    args = ap.parse_args()

    wanted = {s.strip() for s in args.scenes.split(",") if s.strip()}
    scenes = [s for s in SCENES if not wanted or s[0] in wanted]
    if not scenes:
        print("No scenes", file=sys.stderr)
        return 1

    formats = [args.format]
    if args.format == "all":
        formats = ["stories", "feed"]

    raw_by_demo: dict[str, list[Image.Image]] = {}

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, channel="chrome")
        except Exception:
            browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1200, "height": 1000},
            device_scale_factor=1.25,
        )
        page = context.new_page()
        # замедление демо-таймингов (захват и др.) только для съёмки
        page.add_init_script("window.__TB_PROMO_SCALE__ = 1.85; window.__TB_PROMO_ONCE__ = true;")
        print(f"Open {args.url} ...")
        page.goto(args.url, wait_until="networkidle", timeout=120_000)
        page.add_style_tag(content=PROMO_CSS)
        # только стрелки/редкие символы без глифа в шрифтах; эмодзи оставляем
        page.evaluate(
            """() => {
              const walk = (root) => {
                const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
                const nodes = [];
                while (w.nextNode()) nodes.push(w.currentNode);
                nodes.forEach((n) => {
                  if (n.nodeValue && n.nodeValue.includes('→')) {
                    n.nodeValue = n.nodeValue.replace(/→/g, ' · ');
                  }
                });
              };
              walk(document.body);
            }"""
        )
        page.wait_for_timeout(600)

        for demo, hook, dur in scenes:
            print(f"  capture -> {demo} ({dur}s @ {args.fps}fps)")
            try:
                raw_by_demo[demo] = capture_scene(page, demo, dur, args.fps)
            except Exception as e:
                print(f"    skip: {e}")
        browser.close()

    if not raw_by_demo:
        print("Nothing captured", file=sys.stderr)
        return 1

    for fmt_name in formats:
        fmt = FORMATS[fmt_name]
        W, H = fmt["w"], fmt["h"]
        print(f"\nCompose v5 {fmt_name} ({fmt['label']}) {W}x{H}")
        out_mp4 = args.out_dir / f"territory_battle_{fmt_name}.mp4"
        writer = open_mp4(out_mp4, args.fps)
        frame_count = 0
        t0 = time.time()
        try:
            if args.no_titles:
                for demo, hook, _dur in scenes:
                    raw = raw_by_demo.get(demo)
                    if not raw:
                        continue
                    dressed = ken_burns(raw, W, H, fmt)
                    frame_count += write_frames(writer, dressed)
            else:
                frame_count = compose_v5(writer, raw_by_demo, fmt, args.fps)
        finally:
            writer.close()

        mb = out_mp4.stat().st_size / (1024 * 1024)
        dur_s = frame_count / args.fps
        print(f"Saving {frame_count} frames -> {out_mp4}")
        print(f"  v5 ready: {mb:.2f} MB · {dur_s:.1f}s · encode {time.time() - t0:.1f}s")

    print("\nv5.1: hook -> map -> tasks -> topics -> capture -> upgrades -> pvp -> chat -> CTA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
