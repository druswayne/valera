#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для генерации JSON файла с заданиями для босса

Генерирует:
- 500 заданий на вычисление выражений (повышенная сложность, скобки, степени)
- 500 заданий на решение уравнений (повышенная сложность, больше шагов)
- 500 заданий на НОД и НОК (включая текстовые задачи)
- 500 заданий на приведение дробей к новому знаменателю
- 500 заданий на сокращение дробей
- 500 текстовых задач на нахождение части от целого (доли) (включая многошаговые)
- 500 текстовых задач на нахождение целого по его части (доли) (включая многошаговые)
- 500 задач: какую часть составляет одно от другого (включая изменения количества)
- 500 задач на движение (разные сюжеты и вопросы)
- 500 заданий на упрощение выражений с переменной (со скобками и множителями)
- 500 текстовых задач: сумма/разность двух неизвестных и задачи "в k раз больше"
"""

import json
import random
import math
from typing import List, Dict, Tuple, Any, Optional

# Забавные названия для заданий
MATH_TITLES = [
    "Математический марафон",
    "Числовая головоломка",
    "Вычислительный вызов",
    "Арифметическая атака",
    "Числовой квест",
    "Математическая битва",
    "Вычислительный дуэль",
    "Числовая загадка",
    "Арифметический арсенал",
    "Математический микс",
    "Вычислительный взрыв",
    "Числовая миссия",
    "Арифметическая авантюра",
    "Математический марафон",
    "Числовая одиссея",
    "Вычислительный турнир",
    "Арифметический вызов",
    "Математическая миссия",
    "Числовая битва",
    "Вычислительный квест"
]

EXPRESSION_TITLES = [
    "Вычислительное приключение",
    "Арифметическая атака",
    "Числовая головоломка",
    "Вычислительный вызов",
    "Математический марафон",
    "Арифметический арсенал",
    "Числовая загадка",
    "Вычислительный дуэль",
    "Математическая битва",
    "Числовой квест"
]

EQUATION_TITLES = [
    "Уравнительный вызов",
    "Алгебраическая атака",
    "Уравнение-головоломка",
    "Математический детектив",
    "Алгебраический квест",
    "Уравнительный марафон",
    "Математическая загадка",
    "Алгебраический вызов",
    "Уравнение-приключение",
    "Математический поиск"
]

GCD_LCM_TITLES = [
    "Делительский вызов",
    "НОД-НОК головоломка",
    "Делительная атака",
    "Математический поиск делителей",
    "НОД-НОК квест",
    "Делительский марафон",
    "Математическая загадка делителей",
    "НОД-НОК вызов",
    "Делительное приключение",
    "Математический поиск общих делителей"
]

FRACTION_TITLES = [
    "Дробный вызов",
    "Фракционный квест",
    "Знаменательный марафон",
    "Дробная тренировка",
    "Преобразование дробей",
    "Дробная головоломка",
    "Знаменательный рывок",
    "Дробная миссия",
    "Фракционный турнир",
    "Дробный штурм"
]

REDUCE_FRACTION_TITLES = [
    "Сократи дробь",
    "Дроби без лишнего",
    "Несократимая победа",
    "Дробная чистка",
    "Сокращение в бой",
    "Фракционный минимум",
    "Дробный минимум",
    "Упростите дробь",
    "Сокращательный квест",
    "Дробное упрощение"
]

PART_OF_WHOLE_TITLES = [
    "Доли и части",
    "Найдите часть",
    "Задача на доли",
    "Часть от целого",
    "Дробная история",
    "Сколько осталось?",
    "Продажи по долям",
    "Доли в жизни",
    "Проценты без процентов",
    "Доля от количества"
]

WHOLE_FROM_PART_TITLES = [
    "Найди целое по части",
    "Сколько было всего?",
    "Целое и доля",
    "Задача на восстановление целого",
    "По части найти целое",
    "Доли наоборот",
    "Сколько было изначально?",
    "Целое по дроби",
    "Обратная задача на доли",
    "Найди первоначальное количество"
]

PART_FRACTION_TITLES = [
    "Какая это часть?",
    "Доля в виде дроби",
    "Часть от группы",
    "Найдите долю",
    "Какую часть составляют?",
    "Доли вокруг нас",
    "Доля без процентов",
    "Дробь из отношения",
    "Часть класса",
    "Доля группы"
]

MOTION_TITLES = [
    "Скорость, время, расстояние",
    "Движение в пути",
    "Встречное движение",
    "Движение вдогонку",
    "Движение по течению",
    "Движение против течения",
    "Маршрут и скорость",
    "Путешествие",
    "Движение и расстояния"
]

SIMPLIFY_X_TITLES = [
    "Упростите выражение",
    "Соберите подобные",
    "Алгебраическое упрощение",
    "Приведите подобные",
    "Упрощение с x",
    "Сложите коэффициенты",
    "Вынесите x",
    "Упрощение выражения",
    "Подобные слагаемые",
    "Алгебра: упрощение"
]

# Сводка тем по типам заданий (для вывода в генераторе)
TASK_THEMES = {
    "Вычисление выражений": EXPRESSION_TITLES,
    "Решение уравнений": EQUATION_TITLES,
    "НОД и НОК": GCD_LCM_TITLES,
    "Приведение дробей к знаменателю": FRACTION_TITLES,
    "Сокращение дробей": REDUCE_FRACTION_TITLES,
    "Часть от целого (доли)": PART_OF_WHOLE_TITLES,
    "Целое по части (доли)": WHOLE_FROM_PART_TITLES,
    "Какую часть составляет (доля)": PART_FRACTION_TITLES,
    "Задачи на движение": MOTION_TITLES,
    "Упрощение выражений с переменной": SIMPLIFY_X_TITLES,
    "Две неизвестные (сумма/разность, части)": MATH_TITLES,
}


def print_task_themes() -> None:
    """Выводит в консоль темы задач по типам."""
    print("=" * 60)
    print("ТЕМЫ ЗАДАЧ В ГЕНЕРАТОРЕ (по типам)")
    print("=" * 60)
    for task_type, themes in TASK_THEMES.items():
        themes_unique = list(dict.fromkeys(themes))
        print(f"\n{task_type}:")
        for t in themes_unique:
            print(f"  • {t}")
    print("\n" + "=" * 60)


def gcd(a: int, b: int) -> int:
    """Находит НОД двух чисел"""
    while b:
        a, b = b, a % b
    return abs(a)

def lcm(a: int, b: int) -> int:
    """Находит НОК двух чисел"""
    return abs(a * b) // gcd(a, b) if a and b else 0


def _rand_coprime_fraction(den_min: int, den_max: int) -> Tuple[int, int]:
    den = random.randint(den_min, den_max)
    num = random.randint(1, den - 1)
    attempts = 0
    while gcd(num, den) != 1 and attempts < 50:
        num = random.randint(1, den - 1)
        attempts += 1
    return num, den


def _pick_multiple(k: int, min_val: int, max_val: int) -> int:
    lo = (min_val + k - 1) // k
    hi = max_val // k
    if lo > hi:
        return k * max(1, lo)
    return k * random.randint(lo, hi)


def _strip_meta(task: Dict[str, Any]) -> Dict[str, Any]:
    """Удаляет служебные поля (мета-данные) перед записью в JSON."""
    out = dict(task)
    out.pop("_meta", None)
    return out


# Верхний индекс для степеней (для генератора «Вычисления» в битве за территорию)
SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def to_superscript(n: int) -> str:
    """Число в виде верхнего индекса (например, 2³⁵)."""
    return "".join(SUPERSCRIPT_DIGITS[int(d)] for d in str(n))


def _format_power(base_display: str, exp: int) -> Tuple[str, str]:
    """
    Возвращает (display, eval) для степени.
    display должен быть только со спецсимволами '²/³' (без '^'), eval всегда '**exp'.
    """
    if exp == 2:
        return f"{base_display}²", f"({base_display})**2"
    if exp == 3:
        return f"{base_display}³", f"({base_display})**3"
    # На текущий момент степени >3 не используем (для детей).
    # Если когда-нибудь понадобится, лучше расширить набор спец-символов,
    # а не вводить '^'.
    return f"{base_display}²", f"({base_display})**2"


def _format_power_territory(base_display: str, exp: int) -> Tuple[str, str]:
    """Степень для битвы за территорию: любой показатель в верхнем индексе (⁰¹²³⁴⁵⁶⁷⁸⁹)."""
    return f"{base_display}{to_superscript(exp)}", f"({base_display})**{exp}"


# Сложность для генератора «Вычисления»: (ops_min, ops_max) по уровню игрока
# Единая шкала для всех генераторов: 1 — одно действие, 2 — 2–3 действия, 3 — 4–7 действий
TERRITORY_COMPUTATIONS_OPS = {
    1: (1, 1),   # одно действие (например 5+3, 20:4)
    2: (2, 3),   # 2–3 действия
    3: (4, 7),   # 4–7 действий
}


def _safe_eval_int(expr: str) -> int:
    """
    Безопасно вычисляет арифметическое выражение (int результат).
    Поддержка: + - * / ** скобки. Деление только если даёт целое.
    """
    import ast

    def _eval(node: ast.AST) -> int:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = _eval(node.operand)
            return +v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0 or left % right != 0:
                    raise ValueError("Non-integer division")
                return left // right
            if isinstance(node.op, ast.Pow):
                if right < 0 or right > 6:
                    raise ValueError("Bad exponent")
                return left ** right
        raise ValueError("Unsupported expression")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree)

# Параметры сложности: (ops_min, ops_max, num_min, num_max, power_chance, paren_chance)
# Единая шкала: 1 — одно действие, 2 — 2–3 действия, 3 — 4–7 действий; результат — натуральное число
_EXPRESSION_DIFFICULTY = {
    1: (1, 1, 2, 20, 0.0, 0.0),   # одно действие, без степеней и скобок
    2: (2, 3, 2, 40, 0.1, 0.15),   # 2–3 действия
    3: (4, 7, 2, 60, 0.25, 0.4),   # 4–7 действий
}


def generate_expression_task(difficulty: int = 2) -> Dict[str, Any]:
    """Генерирует задание на вычисление выражения (со скобками и степенями).
    difficulty: 1 — лёгкий, 2 — средний, 3 — сложный."""
    params = _EXPRESSION_DIFFICULTY.get(difficulty, _EXPRESSION_DIFFICULTY[2])
    ops_min, ops_max, num_min, num_max, power_chance, paren_chance = params

    def _maybe_paren(s: str) -> str:
        return f"({s})" if random.random() < paren_chance else s

    # Собираем выражение "снизу-вверх", одновременно считая значение (только целые).
    max_attempts = 300
    for _ in range(max_attempts):
        ops_count = random.randint(ops_min, ops_max)
        # Начальные атомы
        atoms_display = [str(random.randint(num_min, num_max)) for _ in range(ops_count + 1)]
        atoms_eval = atoms_display[:]

        # Иногда превращаем часть атомов в степени
        for i in range(len(atoms_display)):
            if random.random() < power_chance:
                exp = random.choice([2, 3])
                disp, ev = _format_power(_maybe_paren(atoms_display[i]), exp)
                atoms_display[i] = disp
                atoms_eval[i] = ev

        display = atoms_display[0]
        ev = atoms_eval[0]

        # Важно: деление делаем только "точное", чтобы ответ был целым.
        for i in range(ops_count):
            pow_weight = 5 if difficulty == 1 else (10 if difficulty == 2 else 15)
            op = random.choices(
                population=["+", "-", "*", "/", "pow_wrap"],
                weights=[22, 20, 30, 18, pow_weight],
                k=1,
            )[0]

            next_disp = atoms_display[i + 1]
            next_ev = atoms_eval[i + 1]

            if op == "pow_wrap":
                # Оборачиваем текущую часть в степень
                exp = random.choice([2, 3])
                disp, ev2 = _format_power(_maybe_paren(display), exp)
                # Корректно: пересобираем как (ev)**exp
                display = disp
                ev = f"({ev})**{exp}"
                continue

            # Вставляем скобки для повышения сложности
            left_disp = _maybe_paren(display)
            right_disp = _maybe_paren(next_disp)
            left_ev = f"({ev})"
            right_ev = f"({next_ev})"

            if op == "+":
                display = f"{left_disp}+{right_disp}"
                ev = f"{left_ev}+{right_ev}"
            elif op == "-":
                display = f"{left_disp}-{right_disp}"
                ev = f"{left_ev}-{right_ev}"
            elif op == "*":
                display = f"{left_disp}·{right_disp}"
                ev = f"{left_ev}*{right_ev}"
            else:  # "/"
                display = f"{left_disp}:{right_disp}"
                ev = f"{left_ev}/{right_ev}"

        # Проверяем, что значение — натуральное и "разумного" размера
        try:
            result = _safe_eval_int(ev)
        except Exception:
            continue

        if result <= 0 or result > 1_000_000:
            continue

        title = random.choice(EXPRESSION_TITLES) + f" #{random.randint(1, 1000)}"
        description = (
            f"Найдите значение выражения {display}. "
            f"В ответ укажи просто число"
        )
        # Баллы зависят от размера дерева/операций и сложности
        base_points = 14 + difficulty * 2 + max(0, ops_count - 5) * 2
        points = base_points * 2
        return {
            "title": title,
            "description": description,
            "correct_answer": str(result),
            "points": points,
            "_meta": {"ev": ev, "display": display, "result": result, "ops": ops_count},
        }

    # Фоллбек (крайне редко)
    return generate_expression_task(difficulty=difficulty)


def generate_territory_computations(difficulty: int) -> Dict[str, Any]:
    """Генератор «Вычисления» для битвы за территорию.
    Выражения с +, -, *, :, скобками и степенью (степень в верхнем индексе).
    Степень считается за одно действие. Все действия дают натуральное число.
    difficulty 1: 1 действие; 2: 2–3 действия; 3: 4–7 действий.
    """
    params = TERRITORY_COMPUTATIONS_OPS.get(difficulty, TERRITORY_COMPUTATIONS_OPS[2])
    ops_min, ops_max = params
    num_min, num_max = 2, 25
    # Первый уровень — без скобок; на 2–3 уровнях скобки есть
    paren_chance = 0.0 if difficulty == 1 else (0.35 + (difficulty - 2) * 0.15)
    # Степень только со 2-го уровня сложности
    power_weight = 0 if difficulty == 1 else (8 + (difficulty - 2) * 4)  # 0 / 8 / 12

    def _maybe_paren(s: str) -> str:
        return f"({s})" if random.random() < paren_chance else s

    max_attempts = 400
    for _ in range(max_attempts):
        ops_count = random.randint(ops_min, ops_max)
        # Все действия — только в цикле ниже (каждое +, -, *, :, степень = 1 действие)
        atoms_display = [str(random.randint(num_min, num_max)) for _ in range(ops_count + 1)]
        atoms_eval = list(atoms_display)

        display = atoms_display[0]
        ev = atoms_eval[0]

        for i in range(ops_count):
            op = random.choices(
                population=["+", "-", "*", "/", "pow_wrap"],
                weights=[24, 22, 28, 16, power_weight],
                k=1,
            )[0]

            next_disp = atoms_display[i + 1]
            next_ev = atoms_eval[i + 1]

            if op == "pow_wrap":
                exp = random.randint(1, 4)
                disp, _ = _format_power_territory(_maybe_paren(display), exp)
                display = disp
                ev = f"({ev})**{exp}"
                continue

            left_disp = _maybe_paren(display)
            right_disp = _maybe_paren(next_disp)
            left_ev = f"({ev})"
            right_ev = f"({next_ev})"

            if op == "+":
                display = f"{left_disp}+{right_disp}"
                ev = f"{left_ev}+{right_ev}"
            elif op == "-":
                display = f"{left_disp}-{right_disp}"
                ev = f"{left_ev}-{right_ev}"
            elif op == "*":
                display = f"{left_disp}×{right_disp}"
                ev = f"{left_ev}*{right_ev}"
            else:
                display = f"{left_disp}:{right_disp}"
                ev = f"{left_ev}/{right_ev}"

        try:
            result = _safe_eval_int(ev)
        except Exception:
            continue

        if result <= 0 or result > 1_000_000:
            continue

        description = f"Найдите значение выражения: {display} = ? В ответ укажите одно число."
        base_points = 12 + difficulty * 2 + max(0, ops_count - 4)
        points = min(50, base_points * 2)
        return {
            "title": "Вычисления",
            "description": description,
            "correct_answer": str(result),
            "points": points,
        }

    # фоллбек — упрощённое задание
    return generate_territory_computations(min(difficulty, 2))


def generate_equation_task(difficulty: int = 3) -> Dict[str, Any]:
    """Генерирует линейное уравнение; решение x — натуральное число.
    difficulty 1: одно действие (x+a=b, x-a=b, a·x=b, x:a=b);
    2: 2–3 действия (например 2x+15=45, (x+5)-6=29);
    3: 4–7 действий (сложные схемы со скобками и делением).
    """
    max_attempts = 400
    for _ in range(max_attempts):
        x = random.randint(2, 250)

        # ——— Уровень 1: одно действие ———
        if difficulty == 1:
            pattern = random.choice(["L1_plus", "L1_minus", "L1_mult", "L1_div"])
            if pattern == "L1_plus":
                # x + a = b  →  x = b - a
                a = random.randint(1, 100)
                b = x + a
                equation = f"x+{a}={b}"
                points = 10
            elif pattern == "L1_minus":
                # x - a = b  →  x = a + b
                a = random.randint(1, min(80, x - 1))
                b = x - a
                equation = f"x-{a}={b}"
                points = 10
            elif pattern == "L1_mult":
                # a·x = b  →  x = b/a, b кратно a
                a = random.randint(2, 12)
                b = a * x
                equation = f"{a}·x={b}"
                points = 12
            else:  # L1_div
                # x : a = b  →  x = a*b
                a = random.randint(2, 15)
                b = x  # x = a*b, значит b = x/a — но x должно быть натуральным, значит x = a*b
                # делаем так: задаём b, тогда x = a*b
                b = random.randint(2, 30)
                x = a * b
                equation = f"x:{a}={b}"
                points = 12
            title = random.choice(EQUATION_TITLES) + f" #{random.randint(1, 1000)}"
            description = f"Найдите корень уравнения {equation}. В ответ укажи просто число"
            points *= 2
            return {
                "title": title,
                "description": description,
                "correct_answer": str(x),
                "points": points,
                "_meta": {"equation": equation, "x": x},
            }

        # ——— Уровень 2: 2–3 действия ———
        if difficulty == 2:
            pattern = random.choice(["L2_axb", "L2_axmb", "L2_xab", "L2_xamb", "L2_axpb", "L2_xpb"])
            if pattern == "L2_axb":
                # a·x + b = c  →  x = (c-b)/a
                a = random.randint(2, 12)
                b = random.randint(1, 80)
                c = a * x + b
                equation = f"{a}·x+{b}={c}"
                points = 16
            elif pattern == "L2_axmb":
                # a·x - b = c  →  x = (c+b)/a, c+b кратно a
                a = random.randint(2, 10)
                b = random.randint(1, 60)
                c = a * x - b
                if c <= 0:
                    continue
                equation = f"{a}·x-{b}={c}"
                points = 16
            elif pattern == "L2_xab":
                # (x + a) + b = c  →  x = c - a - b
                a = random.randint(1, 50)
                b = random.randint(1, 50)
                c = x + a + b
                equation = f"(x+{a})+{b}={c}"
                points = 14
            elif pattern == "L2_xamb":
                # (x + a) - b = c  →  x = c + b - a
                a = random.randint(1, 40)
                b = random.randint(1, 40)
                c = x + a - b
                if c <= 0:
                    continue
                equation = f"(x+{a})-{b}={c}"
                points = 14
            elif pattern == "L2_axpb":
                # a·(x + b) = c  →  x = c/a - b, c кратно a
                a = random.randint(2, 10)
                b = random.randint(1, 50)
                c = a * (x + b)
                equation = f"{a}·(x+{b})={c}"
                points = 18
            else:  # L2_xpb
                # (x + a) : b = c  →  x = c*b - a
                b = random.randint(2, 10)
                c = random.randint(2, 40)
                a = random.randint(0, 100)
                x = c * b - a
                if x < 1:
                    continue
                equation = f"(x+{a}):{b}={c}"
                points = 18
            title = random.choice(EQUATION_TITLES) + f" #{random.randint(1, 1000)}"
            description = f"Найдите корень уравнения {equation}. В ответ укажи просто число"
            points *= 2
            return {
                "title": title,
                "description": description,
                "correct_answer": str(x),
                "points": points,
                "_meta": {"equation": equation, "x": x},
            }

        # ——— Уровень 3: 4–7 действий ———
        pattern = random.choice(["p1", "p2", "p3", "p4", "p5"])

        if pattern == "p1":
            # ((a*x + b) : c) + d = e
            a = random.randint(2, 15)
            c = random.randint(2, 12)
            b = random.randint(0, 80)
            d = random.randint(1, 60)
            left_num = a * x + b
            if left_num % c != 0:
                b += (c - (left_num % c))
                left_num = a * x + b
            e = (left_num // c) + d
            equation = f"(( {a}·x+{b} ):{c})+{d}={e}".replace(" ", "")
            points = 22

        elif pattern == "p2":
            # a*(x+b) - c = d
            a = random.randint(2, 12)
            b = random.randint(1, 60)
            c = random.randint(1, 120)
            d = a * (x + b) - c
            if d <= 0:
                c = a * (x + b) - 1
                d = 1
            equation = f"{a}·(x+{b})-{c}={d}"
            points = 20

        elif pattern == "p3":
            # (x - a)*b + c = d
            a = random.randint(1, min(80, x - 1))
            b = random.randint(2, 12)
            c = random.randint(1, 120)
            d = (x - a) * b + c
            equation = f"(x-{a})·{b}+{c}={d}"
            points = 22

        elif pattern == "p4":
            # (a - x)*b + c = d  (следим, чтобы было натурально)
            b = random.randint(2, 10)
            a = random.randint(x + 1, x + 120)
            c = random.randint(1, 120)
            d = (a - x) * b + c
            equation = f"({a}-x)·{b}+{c}={d}"
            points = 24

        else:  # p5
            # ((x+a)*b - c) : d = e
            a = random.randint(1, 40)
            b = random.randint(2, 10)
            ddiv = random.randint(2, 10)
            c = random.randint(1, 120)
            temp = (x + a) * b - c
            if temp <= 0:
                c = (x + a) * b - 1
                temp = 1
            if temp % ddiv != 0:
                # корректируем c так, чтобы делилось
                r = temp % ddiv
                c -= r
                temp = (x + a) * b - c
                if temp <= 0 or temp % ddiv != 0:
                    continue
            e = temp // ddiv
            equation = f"((x+{a})·{b}-{c}):{ddiv}={e}"
            points = 26

        title = random.choice(EQUATION_TITLES) + f" #{random.randint(1, 1000)}"
        description = f"Найдите корень уравнения {equation}. В ответ укажи просто число"
        points *= 2

        # Внутренняя проверка (подстановка x в левую часть)
        try:
            left, right = equation.split("=", 1)
            left_eval = left.replace(":", "/").replace("·", "*")
            left_eval = left_eval.replace("x", str(x))
            right_val = int(right)
            lv = _safe_eval_int(left_eval)
            if lv != right_val:
                continue
        except Exception:
            continue

        return {
            "title": title,
            "description": description,
            "correct_answer": str(x),
            "points": points,
            "_meta": {"equation": equation, "x": x},
        }

    return generate_equation_task(difficulty)

def _generate_gcd_lcm_word_task() -> Dict[str, Any]:
    """Текстовые задачи на НОД/НОК (разные сюжеты)."""

    kind = random.choice(["gcd_crafts", "gcd_boxes", "gcd_ribbons", "lcm_steps", "lcm_bells", "lcm_schedule"])

    if kind.startswith("gcd"):
        # задача на "максимальное число одинаковых наборов"
        if kind == "gcd_crafts":
            a = random.randint(18, 90)
            b = random.randint(18, 96)
            c = random.randint(18, 108)
            # делаем числа "приятными": домножим на общий множитель
            k = random.randint(2, 6)
            a *= k
            b *= k
            c *= k
            ans = gcd(gcd(a, b), c)
            title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
            description = (
                f"Для изготовления поделок из природного материала использовали {a} желудей, {b} орехов и {c} сухих веточек. "
                f"Какое наибольшее число одинаковых поделок можно сделать, если в каждой поделке будет одинаковое количество "
                f"каждого вида материала? В ответ укажите только число"
            )
            points = 24
            return {"title": title, "description": description, "correct_answer": str(ans), "points": points * 2, "_meta": {"kind": kind, "a": a, "b": b, "c": c, "ans": ans}}

        if kind == "gcd_boxes":
            a = random.randint(24, 180)
            b = random.randint(24, 180)
            c = random.randint(24, 180)
            k = random.randint(2, 5)
            a *= k
            b *= k
            c *= k
            ans = gcd(gcd(a, b), c)
            title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
            description = (
                f"Есть {a} яблок, {b} груш и {c} апельсинов. Их хотят разложить в одинаковые наборы так, чтобы "
                f"каждый набор содержал одинаковое количество каждого фрукта и все фрукты были разложены. "
                f"Сколько наибольшее число наборов можно сделать? В ответ укажите только число"
            )
            points = 24
            return {"title": title, "description": description, "correct_answer": str(ans), "points": points * 2, "_meta": {"kind": kind, "a": a, "b": b, "c": c, "ans": ans}}

        # gcd_ribbons
        a = random.randint(30, 240)
        b = random.randint(30, 240)
        ans = gcd(a, b)
        title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
        description = (
            f"Есть две ленты длиной {a} см и {b} см. Их нужно разрезать на одинаковые по длине куски без остатка. "
            f"Какой наибольшей длины (в сантиметрах) могут быть куски? В ответ укажите только число"
        )
        points = 22
        return {"title": title, "description": description, "correct_answer": str(ans), "points": points * 2, "_meta": {"kind": kind, "a": a, "b": b, "ans": ans}}

    # LCM
    if kind == "lcm_steps":
        # шаги в сантиметрах, чтобы ответ был целым
        s1 = random.choice([50, 55, 60, 65, 70, 75, 80, 90])
        s2 = random.choice([40, 45, 50, 60, 72, 75, 84])
        s3 = random.choice([85, 90, 95, 100, 105, 110, 120])
        ans = lcm(lcm(s1, s2), s3)
        title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
        description = (
            f"Длина шага Вани равна {s1} см, Тани — {s2} см, а их папы — {s3} см. "
            f"Гуляя, все трое сделали целое число шагов. Какое наименьшее расстояние (в сантиметрах) они могли пройти? "
            f"В ответ укажите только число"
        )
        points = 26
        return {"title": title, "description": description, "correct_answer": str(ans), "points": points * 2, "_meta": {"kind": kind, "s1": s1, "s2": s2, "s3": s3, "ans": ans}}

    if kind == "lcm_bells":
        a = random.randint(6, 18)
        b = random.randint(8, 20)
        c = random.randint(10, 24)
        ans = lcm(lcm(a, b), c)
        title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
        description = (
            f"В школе три звонка звенят одновременно. Первый звенит каждые {a} минут, второй — каждые {b} минут, "
            f"третий — каждые {c} минут. Через сколько минут они снова прозвенят одновременно? В ответ укажите только число"
        )
        points = 24
        return {"title": title, "description": description, "correct_answer": str(ans), "points": points * 2, "_meta": {"kind": kind, "a": a, "b": b, "c": c, "ans": ans}}

    # lcm_schedule
    a = random.randint(7, 15)
    b = random.randint(9, 18)
    ans = lcm(a, b)
    title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
    description = (
        f"Автобус №1 отправляется каждые {a} минут, а автобус №2 — каждые {b} минут. "
        f"Сейчас они отправились одновременно. Через сколько минут они снова отправятся одновременно? "
        f"В ответ укажите только число"
    )
    points = 22
    return {"title": title, "description": description, "correct_answer": str(ans), "points": points * 2, "_meta": {"kind": kind, "a": a, "b": b, "ans": ans}}


def _lcm3(a: int, b: int, c: int) -> int:
    """НОК трёх чисел."""
    return lcm(lcm(a, b), c)


def _gcd3(a: int, b: int, c: int) -> int:
    """НОД трёх чисел."""
    return gcd(gcd(a, b), c)


def generate_territory_gcd_lcm_task(difficulty: int) -> Dict[str, Any]:
    """
    Генератор заданий «НОД и НОК» для битвы за территорию по уровням сложности.

    Уровень 1: два числа. НОД — числа до 50 (НОД ≠ 1). НОК — числа от 2 до 15.
    Уровень 2: два числа. НОД — числа от 50 до 100 (НОД ≠ 1). НОК — числа от 10 до 20.
    Уровень 3: три числа. НОД — числа от 10 до 100 (НОД ≠ 1). НОК — числа от 10 до 40.
    """
    difficulty = max(1, min(3, difficulty))
    task_kind = random.choice(['gcd', 'lcm'])

    if difficulty == 1:
        # Два числа. НОД: числа до 50, НОД ≠ 1. НОК: числа 2..15
        if task_kind == 'gcd':
            for _ in range(50):
                g = random.randint(2, 25)
                max_mult = 50 // g
                if max_mult < 2:
                    continue
                mults = [random.randint(2, max_mult) for _ in range(2)]
                if gcd(mults[0], mults[1]) != 1:
                    continue
                a, b = g * mults[0], g * mults[1]
                if a > 50 or b > 50 or a < 2 or b < 2:
                    continue
                result = gcd(a, b)
                desc = f"Найдите НОД({a}, {b}). В ответ укажите только число."
                break
            else:
                a, b = 12, 18
                result = gcd(a, b)
                desc = f"Найдите НОД({a}, {b}). В ответ укажите только число."
        else:
            a = random.randint(2, 15)
            b = random.randint(2, 15)
            if a == b:
                b = random.randint(2, 15)
                if a == b:
                    b = (a % 15) + 2 if a < 14 else 2
            result = lcm(a, b)
            desc = f"Найдите НОК({a}, {b}). В ответ укажите только число."
        title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
        points = 10
        return {
            "title": title,
            "description": desc,
            "correct_answer": str(result),
            "points": points,
            "_meta": {"kind": "territory_gcd_lcm", "difficulty": 1, "task_kind": task_kind},
        }

    if difficulty == 2:
        # Два числа. НОД: числа 50..100, НОД ≠ 1. НОК: числа 10..20
        if task_kind == 'gcd':
            for _ in range(50):
                g = random.randint(2, 50)
                lo = (50 + g - 1) // g
                hi = 100 // g
                if lo > hi or hi < 2:
                    continue
                m1 = random.randint(lo, hi)
                m2 = random.randint(lo, hi)
                if gcd(m1, m2) != 1:
                    continue
                a, b = g * m1, g * m2
                if a < 50 or b < 50 or a > 100 or b > 100:
                    continue
                result = gcd(a, b)
                desc = f"Найдите НОД({a}, {b}). В ответ укажите только число."
                break
            else:
                a, b = 56, 84
                result = gcd(a, b)
                desc = f"Найдите НОД({a}, {b}). В ответ укажите только число."
        else:
            a = random.randint(10, 20)
            b = random.randint(10, 20)
            if a == b:
                b = (a % 11) + 10 if a < 20 else 10
            result = lcm(a, b)
            desc = f"Найдите НОК({a}, {b}). В ответ укажите только число."
        title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
        points = 14
        return {
            "title": title,
            "description": desc,
            "correct_answer": str(result),
            "points": points,
            "_meta": {"kind": "territory_gcd_lcm", "difficulty": 2, "task_kind": task_kind},
        }

    # difficulty == 3: три числа. НОД: 10..100 (НОД ≠ 1). НОК: 10..40
    if task_kind == 'gcd':
        for _ in range(80):
            g = random.randint(2, 50)
            lo = max(1, (10 + g - 1) // g)
            hi = 100 // g
            if lo > hi or hi < 2:
                continue
            m1 = random.randint(lo, hi)
            m2 = random.randint(lo, hi)
            m3 = random.randint(lo, hi)
            if _gcd3(m1, m2, m3) != 1:
                continue
            a, b, c = g * m1, g * m2, g * m3
            if not (10 <= a <= 100 and 10 <= b <= 100 and 10 <= c <= 100):
                continue
            result = _gcd3(a, b, c)
            desc = f"Найдите НОД({a}, {b}, {c}). В ответ укажите только число."
            break
        else:
            a, b, c = 24, 36, 60
            result = _gcd3(a, b, c)
            desc = f"Найдите НОД({a}, {b}, {c}). В ответ укажите только число."
    else:
        a = random.randint(10, 40)
        b = random.randint(10, 40)
        c = random.randint(10, 40)
        result = _lcm3(a, b, c)
        desc = f"Найдите НОК({a}, {b}, {c}). В ответ укажите только число."
    title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"
    points = 18
    return {
        "title": title,
        "description": desc,
        "correct_answer": str(result),
        "points": points,
        "_meta": {"kind": "territory_gcd_lcm", "difficulty": 3, "task_kind": task_kind},
    }


def generate_gcd_lcm_task() -> Dict[str, Any]:
    """Генерирует задание на НОД/НОК (числовое или текстовое)."""
    # Добавляем текстовые задачи, чтобы максимизировать разнообразие
    if random.random() < 0.45:
        return _generate_gcd_lcm_word_task()

    task_type = random.choice(['gcd2', 'lcm2', 'gcd3', 'lcm3'])
    
    if task_type == 'gcd2':
        # НОД двух чисел
        # Генерируем два числа с общим делителем
        common_factor = random.randint(2, 20)
        a_mult = random.randint(2, 15)
        b_mult = random.randint(2, 15)
        a = common_factor * a_mult
        b = common_factor * b_mult
        
        # Добавляем случайные множители для усложнения
        if random.random() < 0.5:
            extra_factor = random.randint(2, 5)
            a *= extra_factor
            b *= extra_factor
        
        result = gcd(a, b)
        description = f"Найдите НОД({a}, {b}). В ответ укажи просто число"
        
        # Points зависят от размера чисел
        if max(a, b) < 100:
            points = 5
        elif max(a, b) < 500:
            points = 10
        else:
            points = 15
    
    elif task_type == 'lcm2':
        # НОК двух чисел
        a = random.randint(10, 100)
        b = random.randint(10, 100)
        result = lcm(a, b)
        description = f"Найдите НОК({a}, {b}). В ответ укажи просто число"
        
        if max(a, b) < 50:
            points = 6
        elif max(a, b) < 100:
            points = 11
        else:
            points = 16
    
    elif task_type == 'gcd3':
        # НОД трех чисел
        common_factor = random.randint(2, 15)
        a_mult = random.randint(2, 10)
        b_mult = random.randint(2, 10)
        c_mult = random.randint(2, 10)
        a = common_factor * a_mult
        b = common_factor * b_mult
        c = common_factor * c_mult
        
        # Добавляем случайные множители
        if random.random() < 0.5:
            extra_factor = random.randint(2, 4)
            a *= extra_factor
            b *= extra_factor
            c *= extra_factor
        
        result = gcd(gcd(a, b), c)
        description = f"Найдите НОД({a}, {b}, {c}). В ответ укажи просто число"
        
        if max(a, b, c) < 100:
            points = 10
        elif max(a, b, c) < 300:
            points = 15
        else:
            points = 20
    
    else:  # lcm3
        # НОК трех чисел
        a = random.randint(10, 50)
        b = random.randint(10, 50)
        c = random.randint(10, 50)
        result = lcm(lcm(a, b), c)
        description = f"Найдите НОК({a}, {b}, {c}). В ответ укажи просто число"
        
        if max(a, b, c) < 30:
            points = 11
        elif max(a, b, c) < 50:
            points = 16
        else:
            points = 21
    
    title = random.choice(GCD_LCM_TITLES) + f" #{random.randint(1, 1000)}"

    points *= 2
    return {
        "title": title,
        "description": description,
        "correct_answer": str(result),
        "points": points,
        "_meta": {"kind": "numeric", "task_type": task_type, "result": result},
    }

def generate_fraction_task() -> Dict[str, Any]:
    """Генерирует задание на приведение дроби к новому знаменателю"""
    # Базовая правильная дробь a/b
    b = random.randint(2, 20)
    a = random.randint(1, b - 1)
    # Чтобы ответ был однозначнее, стараемся брать несократимую дробь
    attempts = 0
    while gcd(a, b) != 1 and attempts < 20:
        a = random.randint(1, b - 1)
        attempts += 1

    k = random.randint(2, 12)
    new_den = b * k
    new_num = a * k

    title = random.choice(FRACTION_TITLES) + f" #{random.randint(1, 1000)}"
    description = (
        f"Приведите дробь {a}/{b} к дроби со знаменателем {new_den}. "
        f"В ответ укажите дробь в формате 1/2 без пробелов"
    )

    # Баллы от сложности (чем больше множитель/знаменатель, тем дороже)
    if new_den <= 60:
        points = 8
    elif new_den <= 150:
        points = 12
    else:
        points = 16

    points *= 2
    return {
        "title": title,
        "description": description,
        "correct_answer": f"{new_num}/{new_den}",
        "points": points,
        "_meta": {"a": a, "b": b, "k": k, "new_num": new_num, "new_den": new_den},
    }

def generate_reduce_fraction_task() -> Dict[str, Any]:
    """Генерирует задание на сокращение дроби (до несократимой)"""
    # Сначала берём несократимую дробь p/q, затем умножаем на k>1
    q = random.randint(2, 25)
    p = random.randint(1, q - 1)
    attempts = 0
    while gcd(p, q) != 1 and attempts < 30:
        p = random.randint(1, q - 1)
        attempts += 1

    k = random.randint(2, 15)
    a = p * k
    b = q * k

    title = random.choice(REDUCE_FRACTION_TITLES) + f" #{random.randint(1, 1000)}"
    description = (
        f"Сократите дробь {a}/{b}. "
        f"В ответ укажи несократимую дробь в формате 1/2 без пробелов"
    )

    if b <= 80:
        points = 8
    elif b <= 180:
        points = 12
    else:
        points = 16

    points *= 2
    return {
        "title": title,
        "description": description,
        "correct_answer": f"{p}/{q}",
        "points": points,
        "_meta": {"a": a, "b": b, "p": p, "q": q, "k": k},
    }


def _format_fraction_display(integer_part: int, numerator: int, denominator: int) -> str:
    """Форматирует дробь для отображения: целая часть, числитель, знаменатель (нормальный вид)."""
    if integer_part != 0 and numerator != 0:
        return f"{integer_part} {numerator}/{denominator}"
    if integer_part != 0:
        return str(integer_part)
    return f"{numerator}/{denominator}"


def _format_fraction_html(integer_part: int, numerator: int, denominator: int) -> str:
    """Вертикальное отображение дроби как на изображении: числитель над чертой, знаменатель под чертой; при смешанном числе — целая часть слева."""
    num = str(numerator)
    den = str(denominator)
    frac_inner = f'<span class="frac-num">{num}</span><span class="frac-line"></span><span class="frac-den">{den}</span>'
    if integer_part != 0 and numerator != 0:
        return f'<span class="mixed-frac"><span class="frac-int">{integer_part}</span><span class="frac">{frac_inner}</span></span>'
    if integer_part != 0:
        return f'<span class="frac-int-only">{integer_part}</span>'
    return f'<span class="frac">{frac_inner}</span>'


def generate_fraction_property_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Основное свойство дроби» для битвы за территорию.
    Задания: приведение к новому знаменателю и сокращение дроби.
    Ответ и отображение: целая часть, числитель, знаменатель (три поля).
    difficulty 1: приведение — знам. исходной 1-значный, новый 2-значный; сокращение — 2-значные.
    difficulty 2: приведение — знам. исходной 1-значный, новый 3-значный; сокращение — 2–3-значные.
    difficulty 3: приведение — знам. исходной 3-значный, новый 2-значный; сокращение — 3-значные.
    """
    task_type = random.choice(["to_denominator", "reduce"])
    points = 12 + difficulty * 4

    if task_type == "to_denominator":
        # Приведение дроби к новому знаменателю
        if difficulty == 1:
            # Исходная: знаменатель однозначный (2–9), новый — двузначный (10–99)
            b = random.randint(2, 9)
            # new_den = b * k, двузначный: 10..99
            k_min = max(2, (10 + b - 1) // b)
            k_max = 99 // b
            if k_max < k_min:
                k_max = k_min
            k = random.randint(k_min, max(k_min, k_max))
            new_den = b * k
        elif difficulty == 2:
            # Исходная: знаменатель однозначный, новый — трёхзначный (100–999)
            b = random.randint(2, 9)
            k_min = max(12, (100 + b - 1) // b)
            k_max = min(999 // b, 200)
            k = random.randint(k_min, max(k_min, k_max))
            new_den = b * k
        else:
            # difficulty 3: знаменатель исходной трёхзначный (100–999), новый — двузначный (10–99). b = new_den * k
            new_den = random.randint(10, 99)
            k_min = max(2, (100 + new_den - 1) // new_den)
            k_max = min(9, 999 // new_den)
            k = random.randint(k_min, max(k_min, k_max))
            b = new_den * k

        a = random.randint(1, b - 1)
        attempts = 0
        while gcd(a, b) != 1 and attempts < 30:
            a = random.randint(1, b - 1)
            attempts += 1
        new_num = a * k

        # Ответ — дробь с указанным знаменателем (числитель и знаменатель), т.е. new_num/new_den
        correct_answer = f"{new_num}|{new_den}"

        # Отображение исходной дроби вертикально (как на изображении)
        int_a = a // b
        num_a = a % b
        den_a = b
        frac_html = _format_fraction_html(int_a, num_a, den_a)
        description = (
            f"Приведите дробь {frac_html} к дроби со знаменателем {new_den}. "
            f"В ответ укажите числитель и знаменатель."
        )
        return {
            "title": "Основное свойство дроби",
            "description": description,
            "correct_answer": correct_answer,
            "points": points,
            "answer_type": "fraction",
            "_meta": {"a": a, "b": b, "new_num": new_num, "new_den": new_den},
        }

    # Сокращение дроби
    if difficulty == 1:
        # Двузначные числитель и знаменатель, сокращаемые
        q = random.randint(2, 25)
        p = random.randint(1, q - 1)
        attempts = 0
        while gcd(p, q) != 1 and attempts < 30:
            p = random.randint(1, q - 1)
            attempts += 1
        k = random.randint(2, 9)
        a = p * k
        b = q * k
        if a < 10 or b < 10:
            a, b = max(10, min(a, b)), max(a, b)
            if a > 99 or b > 99:
                b = min(99, max(a, b))
                a = min(99, min(a, b))
        while a < 10 or b < 10 or a > 99 or b > 99:
            q = random.randint(10, 50)
            p = random.randint(1, q - 1)
            while gcd(p, q) != 1:
                p = random.randint(1, q - 1)
            k = random.randint(2, 5)
            a = p * k
            b = q * k
    elif difficulty == 2:
        # Двузначные–трёхзначные
        q = random.randint(2, 50)
        p = random.randint(1, q - 1)
        attempts = 0
        while gcd(p, q) != 1 and attempts < 30:
            p = random.randint(1, q - 1)
            attempts += 1
        k = random.randint(2, 20)
        a = p * k
        b = q * k
        if a < 10:
            a = p * random.randint(3, 15)
            b = q * (a // p)
        if b < 10:
            b = q * random.randint(2, 15)
            a = p * (b // q)
        while a > 999 or b > 999:
            a = a // 2
            b = b // 2
    else:
        # difficulty 3: трёхзначные
        q = random.randint(20, 150)
        p = random.randint(1, q - 1)
        attempts = 0
        while gcd(p, q) != 1 and attempts < 50:
            p = random.randint(1, q - 1)
            attempts += 1
        k = random.randint(2, 8)
        a = p * k
        b = q * k
        while a < 100 or b < 100 or a > 999 or b > 999:
            q = random.randint(34, 333)
            p = random.randint(1, q - 1)
            while gcd(p, q) != 1:
                p = random.randint(1, q - 1)
            k = random.randint(2, 5)
            a = p * k
            b = q * k

    # Ответ — только числитель и знаменатель несократимой дроби p/q
    correct_answer = f"{p}|{q}"

    frac_html = _format_fraction_html(a // b, a % b, b)
    description = (
        f"Сократите дробь {frac_html}. "
        f"В ответ укажите числитель и знаменатель полученной несократимой дроби."
    )
    return {
        "title": "Основное свойство дроби",
        "description": description,
        "correct_answer": correct_answer,
        "points": points,
        "answer_type": "fraction",
        "_meta": {"a": a, "b": b, "p": p, "q": q},
    }


def generate_common_denominator_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Общий знаменатель»: две дроби, в ответ — две дроби с наименьшим общим знаменателем.
    Ответ: num1|den|num2|den (числитель первой, общий знам., числитель второй, общий знам.).
    difficulty 1: знаменатели взаимно простые, от 2 до 20.
    difficulty 2: знаменатели не взаимно простые, от 20 до 99.
    difficulty 3: знаменатели не взаимно простые, от 100 до 1000.
    """
    points = 14 + difficulty * 4
    max_attempts = 100
    for _ in range(max_attempts):
        if difficulty == 1:
            # Взаимно простые знаменатели, 2..20
            b = random.randint(2, 20)
            d = random.randint(2, 20)
            if gcd(b, d) != 1:
                continue
        elif difficulty == 2:
            # Не взаимно простые, 20..99
            b = random.randint(20, 99)
            d = random.randint(20, 99)
            if gcd(b, d) == 1:
                continue
        else:
            # Не взаимно простые, 100..1000
            b = random.randint(100, 1000)
            d = random.randint(100, 1000)
            if gcd(b, d) == 1:
                continue

        a = random.randint(1, b - 1)
        c = random.randint(1, d - 1)
        common_den = lcm(b, d)
        num1 = a * (common_den // b)
        num2 = c * (common_den // d)
        correct_answer = f"{num1}|{common_den}|{num2}|{common_den}"

        frac1_html = _format_fraction_html(a // b, a % b, b)
        frac2_html = _format_fraction_html(c // d, c % d, d)
        description = "Приведите к наименьшему общему знаменателю. В ответ укажите новые дроби в полях ниже."
        return {
            "title": "Общий знаменатель",
            "description": description,
            "correct_answer": correct_answer,
            "points": points,
            "answer_type": "common_denominator",
            "display_frac1": frac1_html,
            "display_frac2": frac2_html,
            "_meta": {"a": a, "b": b, "c": c, "d": d, "common_den": common_den, "num1": num1, "num2": num2},
        }
    # фоллбек
    return generate_common_denominator_task(min(difficulty, 2))


def generate_proper_improper_fraction_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Правильные/неправильные дроби».
    Два типа заданий наугад:
    1) Смешанное число (целая + правильная несократимая дробь) -> представить в виде неправильной дроби. Ответ: num|den.
    2) Неправильная несократимая дробь -> выделить целую и дробную часть (смешанное число). Ответ: int|num|den.
    Уровень 1: целая 1–10, числитель и знаменатель 1–20.
    Уровень 2: целая 11–20, числитель и знаменатель 21–50.
    Уровень 3: целая от 21, числитель и знаменатель от 51.
    """
    task_type = random.choice(["mixed_to_improper", "improper_to_mixed"])
    points = 12 + difficulty * 4

    if difficulty == 1:
        int_lo, int_hi = 1, 10
        den_lo, den_hi = 2, 20
    elif difficulty == 2:
        int_lo, int_hi = 11, 20
        den_lo, den_hi = 21, 50
    else:
        int_lo, int_hi = 21, 50
        den_lo, den_hi = 51, 120

    if task_type == "mixed_to_improper":
        # Смешанное число -> неправильная дробь
        int_part = random.randint(int_lo, int_hi)
        den = random.randint(den_lo, den_hi)
        num = random.randint(1, den - 1)
        attempts = 0
        while gcd(num, den) != 1 and attempts < 30:
            num = random.randint(1, den - 1)
            attempts += 1
        improper_num = int_part * den + num
        improper_den = den
        correct_answer = f"{improper_num}|{improper_den}"
        frac_html = _format_fraction_html(int_part, num, den)
        description = f"Представьте смешанное число {frac_html} в виде неправильной дроби."
        return {
            "title": "Правильные/неправильные дроби",
            "description": description,
            "correct_answer": correct_answer,
            "points": points,
            "answer_type": "fraction",
            "_meta": {"task_type": "mixed_to_improper", "int_part": int_part, "num": num, "den": den},
        }

    # improper_to_mixed: неправильная дробь -> смешанное число (num > den, дробь не целое число)
    for _ in range(100):
        den = random.randint(max(2, den_lo), den_hi - 1 if difficulty == 1 else den_hi)
        if den < 2:
            continue
        num_lo = den + 1
        num_hi = den_hi if difficulty <= 2 else den + 60
        num_hi = max(num_hi, num_lo)
        num = random.randint(num_lo, num_hi)
        if num % den == 0:
            continue
        attempts = 0
        while gcd(num, den) != 1 and attempts < 50:
            num = random.randint(num_lo, min(num_hi, den * 3))
            if num % den == 0:
                break
            attempts += 1
        if gcd(num, den) != 1 or num % den == 0:
            continue
        int_part = num // den
        rem_num = num % den
        rem_den = den
        correct_answer = f"{int_part}|{rem_num}|{rem_den}"
        frac_html = _format_fraction_html(0, num, den)
        description = "Выделите целую и дробную часть. Представьте неправильную дробь в виде смешанного числа."
        return {
            "title": "Правильные/неправильные дроби",
            "description": description,
            "correct_answer": correct_answer,
            "points": points,
            "answer_type": "mixed_fraction",
            "display_frac": frac_html,
            "_meta": {"task_type": "improper_to_mixed", "num": num, "den": den},
        }
    return generate_proper_improper_fraction_task(difficulty)


def _to_mixed_irreducible(num: int, den: int) -> Tuple[int, int, int]:
    """Привести дробь num/den к несократимому виду и выделить целую часть. Возвращает (целая, числитель, знаменатель)."""
    if den <= 0:
        den = 1
    g = gcd(num, den)
    num, den = num // g, den // g
    if den < 0:
        num, den = -num, -den
    int_part = num // den
    rem_num = num % den
    rem_den = den
    return int_part, rem_num, rem_den


def generate_add_sub_fractions_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Сложение и вычитание дробей» для битвы за территорию.
    Сумма или разность двух обыкновенных дробей. Разность — только положительная.
    Ответ: несократимая дробь с выделенной целой частью (int|num|den).
    1 уровень: одинаковые знаменатели (2–20).
    2 уровень: взаимно простые знаменатели (2–20).
    3 уровень: разные не взаимно простые знаменатели.
    """
    instruction = "Вычислите выражение выше. В ответе укажите несократимую дробь и выделите целую часть, если это возможно."
    points = 12 + difficulty * 4
    is_sum = random.choice([True, False])

    if difficulty == 1:
        # Одинаковые знаменатели
        b = random.randint(2, 20)
        d = b
        if is_sum:
            a = random.randint(1, max(1, b - 2))
            c = random.randint(1, max(1, b - 1 - a))
            num = a + c
        else:
            a = random.randint(2, b - 1)
            c = random.randint(1, a - 1)
            num = a - c
        den = b
    elif difficulty == 2:
        # Взаимно простые знаменатели (2–20)
        b = random.randint(2, 20)
        d = random.randint(2, 20)
        attempts = 0
        while gcd(b, d) != 1 and attempts < 50:
            b = random.randint(2, 20)
            d = random.randint(2, 20)
            attempts += 1
        if gcd(b, d) != 1:
            b, d = 4, 9  # гарантированно взаимно простые
        a = random.randint(1, b - 1)
        c = random.randint(1, d - 1)
        if is_sum:
            num = a * d + c * b
            den = b * d
        else:
            if a * d <= c * b:
                a, c = c, a
                b, d = d, b
            num = a * d - c * b
            den = b * d
    else:
        # Разные не взаимно простые знаменатели
        b = random.randint(2, 20)
        d = random.randint(2, 20)
        attempts = 0
        while (b == d or gcd(b, d) == 1) and attempts < 100:
            b = random.randint(2, 20)
            d = random.randint(2, 20)
            attempts += 1
        if b == d:
            b, d = 6, 9
        if gcd(b, d) == 1:
            b, d = 6, 10
        a = random.randint(1, b - 1)
        c = random.randint(1, d - 1)
        if is_sum:
            num = a * d + c * b
            den = b * d
        else:
            if a * d <= c * b:
                a, c = c, a
                b, d = d, b
            num = a * d - c * b
            den = b * d

    int_part, rem_num, rem_den = _to_mixed_irreducible(num, den)
    correct_answer = f"{int_part}|{rem_num}|{rem_den}"

    frac1_html = _format_fraction_html(0, a, b)
    frac2_html = _format_fraction_html(0, c, d)
    description = instruction

    return {
        "title": "Сложение и вычитание дробей",
        "description": description,
        "correct_answer": correct_answer,
        "points": points,
        "answer_type": "add_sub_fractions",
        "display_frac1": frac1_html,
        "display_frac2": frac2_html,
        "display_operator": "+" if is_sum else "−",
        "int_part_zero": (int_part == 0),
        "_meta": {"a": a, "b": b, "c": c, "d": d, "is_sum": is_sum},
    }


def generate_mul_div_fractions_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Умножение и деление дробей» для битвы за территорию.
    Умножение или деление двух обыкновенных дробей.
    Ответ: несократимая правильная дробь с целой частью, если есть (int|num|den).
    1 уровень: числители и знаменатели от 2 до 10.
    2 уровень: числители и знаменатели от 11 до 20.
    3 уровень: числители и знаменатели от 21 до 50.
    """
    instruction = "Вычислите выражение выше. В ответе укажите несократимую дробь и выделите целую часть, если это возможно."
    points = 12 + difficulty * 4
    is_mul = random.choice([True, False])

    if difficulty == 1:
        low, high = 2, 10
    elif difficulty == 2:
        low, high = 11, 20
    else:
        low, high = 21, 50

    a = random.randint(2, high)
    b = random.randint(2, high)
    c = random.randint(2, high)
    d = random.randint(2, high)

    if is_mul:
        num = a * c
        den = b * d
    else:
        # (a/b) : (c/d) = (a*d)/(b*c)
        num = a * d
        den = b * c

    if den <= 0:
        den = 1
    int_part, rem_num, rem_den = _to_mixed_irreducible(num, den)
    correct_answer = f"{int_part}|{rem_num}|{rem_den}"

    frac1_html = _format_fraction_html(0, a, b)
    frac2_html = _format_fraction_html(0, c, d)

    return {
        "title": "Умножение и деление дробей",
        "description": instruction,
        "correct_answer": correct_answer,
        "points": points,
        "answer_type": "add_sub_fractions",
        "display_frac1": frac1_html,
        "display_frac2": frac2_html,
        "display_operator": "×" if is_mul else "÷",
        "int_part_zero": (int_part == 0),
        "_meta": {"a": a, "b": b, "c": c, "d": d, "is_mul": is_mul},
    }


def generate_mixed_numbers_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Смешанные числа» для битвы за территорию.
    Сложение, вычитание, умножение или деление двух смешанных чисел.
    Смешанное число: целая часть + правильная дробь (числитель/знаменатель).
    Ответ: несократимая дробь с целой частью, если есть (int|num|den).
    1 уровень: знаменатели 2–10, целые части 0–2.
    2 уровень: знаменатели 11–20, целые части 0–4.
    3 уровень: знаменатели 21–50, целые части 0–6.
    """
    instruction = "Вычислите выражение выше. В ответе укажите несократимую дробь и выделите целую часть, если это возможно."
    points = 12 + difficulty * 4
    op = random.choice(["add", "sub", "mul", "div"])

    if difficulty == 1:
        den_lo, den_hi = 2, 10
        int_max = 2
    elif difficulty == 2:
        den_lo, den_hi = 11, 20
        int_max = 4
    else:
        den_lo, den_hi = 21, 50
        int_max = 6

    def one_mixed() -> Tuple[int, int, int]:
        b = random.randint(den_lo, den_hi)
        a = random.randint(1, b - 1)
        g = gcd(a, b)
        while g != 1 and b > 1:
            a = random.randint(1, b - 1)
            g = gcd(a, b)
        int_p = random.randint(0, int_max)
        return int_p, a, b

    i1, n1, d1 = one_mixed()
    i2, n2, d2 = one_mixed()

    # Неправильные дроби: num = int*den + num_proper
    num1 = i1 * d1 + n1
    num2 = i2 * d2 + n2

    if op == "add":
        res_num = num1 * d2 + num2 * d1
        res_den = d1 * d2
    elif op == "sub":
        if num1 * d2 < num2 * d1:
            num1, num2, d1, d2 = num2, num1, d2, d1
            i1, n1, i2, n2 = i2, n2, i1, n1
        res_num = num1 * d2 - num2 * d1
        res_den = d1 * d2
    elif op == "mul":
        res_num = num1 * num2
        res_den = d1 * d2
    else:  # div
        res_num = num1 * d2
        res_den = d1 * num2
        if res_den <= 0:
            res_den = 1

    if res_den <= 0:
        res_den = 1
    int_part, rem_num, rem_den = _to_mixed_irreducible(res_num, res_den)
    correct_answer = f"{int_part}|{rem_num}|{rem_den}"

    frac1_html = _format_fraction_html(i1, n1, d1)
    frac2_html = _format_fraction_html(i2, n2, d2)
    op_char = {"add": "+", "sub": "−", "mul": "×", "div": "÷"}[op]

    return {
        "title": "Смешанные числа",
        "description": instruction,
        "correct_answer": correct_answer,
        "points": points,
        "answer_type": "add_sub_fractions",
        "display_frac1": frac1_html,
        "display_frac2": frac2_html,
        "display_operator": op_char,
        "int_part_zero": (int_part == 0),
        "_meta": {"i1": i1, "n1": n1, "d1": d1, "i2": i2, "n2": n2, "d2": d2, "op": op},
    }


def generate_part_of_whole_word_task() -> Dict[str, Any]:
    """Усложнённые текстовые задачи на 'часть от целого' (в т.ч. многошаговые)."""

    variant = random.choice(["simple_part", "remaining_after_part", "price_change", "remove_from_fraction", "rectangle"])
    title = random.choice(PART_OF_WHOLE_TITLES) + f" #{random.randint(1, 1000)}"

    if variant == "simple_part":
        n, d = _rand_coprime_fraction(2, 10)
        total = _pick_multiple(d, 60, 3000)
        part = total * n // d
        unit = random.choice(["кг", "л", "шт.", "руб."])
        obj = random.choice(["яблок", "конфет", "сока", "денег"])
        description = (
            f"Дано {total} {unit} {obj}. Найдите {n}/{d} от этого количества. "
            f"В ответ укажите только число без единиц измерения"
        )
        points = 18
        return {"title": title, "description": description, "correct_answer": str(part), "points": points * 2, "_meta": {"variant": variant, "n": n, "d": d, "total": total, "ans": part}}

    if variant == "remaining_after_part":
        n, d = _rand_coprime_fraction(2, 10)
        total = _pick_multiple(d, 60, 3000)
        remaining = total * (d - n) // d
        unit = random.choice(["кг", "л", "шт.", "руб."])
        obj = random.choice(["овощей", "фруктов", "воды", "карандашей"])
        action = random.choice(["потратили", "продали", "израсходовали", "убрали"])
        description = (
            f"Было {total} {unit} {obj}. {action.capitalize()} {n}/{d} от всего количества. "
            f"Сколько осталось? В ответ укажите только число без единиц измерения"
        )
        points = 20
        return {"title": title, "description": description, "correct_answer": str(remaining), "points": points * 2, "_meta": {"variant": variant, "n": n, "d": d, "total": total, "ans": remaining}}

    if variant == "price_change":
        # Цена снизилась на n1/d1 от исходной, затем выросла на n2/d2 от новой
        n1, d1 = _rand_coprime_fraction(2, 10)
        n2, d2 = _rand_coprime_fraction(2, 10)
        # Чтобы всё было целым: price кратна d1, а после снижения кратна d2
        base = _pick_multiple(d1, 500, 30000)
        after_down = base * (d1 - n1) // d1
        # подгоняем base, чтобы after_down делился на d2
        attempts = 0
        while after_down % d2 != 0 and attempts < 200:
            base += d1
            after_down = base * (d1 - n1) // d1
            attempts += 1
        if after_down % d2 != 0:
            return generate_part_of_whole_word_task()
        after_up = after_down + (after_down * n2 // d2)
        description = (
            f"Стоимость товара снизилась на {n1}/{d1}, а затем подорожала на {n2}/{d2} от новой стоимости. "
            f"Найдите итоговую стоимость, если вначале товар стоил {base} руб. "
            f"В ответ укажите только число"
        )
        points = 24
        return {"title": title, "description": description, "correct_answer": str(after_up), "points": points * 2, "_meta": {"variant": variant, "n1": n1, "d1": d1, "n2": n2, "d2": d2, "base": base, "ans": after_up}}

    if variant == "remove_from_fraction":
        total = random.randint(60, 180)
        n, d = _rand_coprime_fraction(2, 10)
        total = _pick_multiple(d, max(60, total), 240)
        red = total * n // d
        removed = random.randint(1, min(20, red - 1))
        remaining = red - removed
        description = (
            f"В коробке {total} карандашей, {n}/{d} — красные. Убрали {removed} красных. "
            f"Сколько красных осталось? В ответ укажите только число"
        )
        points = 22
        return {"title": title, "description": description, "correct_answer": str(remaining), "points": points * 2, "_meta": {"variant": variant, "total": total, "n": n, "d": d, "removed": removed, "ans": remaining}}

    # rectangle
    width = _pick_multiple(7, 14, 350)  # чтобы дроби 4/7, 3/7 и т.п. давали целое
    n, d = random.choice([(4, 7), (5, 7), (3, 7), (2, 7)])
    length = width * n // d
    perim = 2 * (width + length)
    description = (
        f"Ширина прямоугольника {width} м, а длина составляет {n}/{d} его ширины. "
        f"Найдите периметр прямоугольника. В ответ укажите только число"
    )
    points = 24
    return {"title": title, "description": description, "correct_answer": str(perim), "points": points * 2, "_meta": {"variant": variant, "width": width, "n": n, "d": d, "ans": perim}}

def generate_whole_from_part_word_task() -> Dict[str, Any]:
    """Усложнённые задачи: найти исходное целое по части/результату."""

    variant = random.choice(["classic_part", "classic_remaining", "reverse_operations"])
    title = random.choice(WHOLE_FROM_PART_TITLES) + f" #{random.randint(1, 1000)}"

    if variant == "classic_part":
        n, d = _rand_coprime_fraction(2, 12)
        total = _pick_multiple(d, 80, 5000)
        part = total * n // d
        obj = random.choice(["яблок", "книг", "рублей", "карандашей"])
        action = random.choice(["продали", "потратили", "использовали", "убрали"])
        description = (
            f"Сначала было некоторое количество {obj}. Потом {action} {part}. "
            f"Это {n}/{d} от всего количества. Сколько было всего? "
            f"В ответ укажите только число"
        )
        points = 24
        return {"title": title, "description": description, "correct_answer": str(total), "points": points * 2, "_meta": {"variant": variant, "n": n, "d": d, "total": total, "part": part, "ans": total}}

    if variant == "classic_remaining":
        n, d = _rand_coprime_fraction(2, 12)
        total = _pick_multiple(d, 80, 5000)
        rem_num = d - n
        rem_den = d
        g = gcd(rem_num, rem_den)
        rem_num //= g
        rem_den //= g
        remaining = total * rem_num // rem_den
        obj = random.choice(["фруктов", "карандашей", "рублей", "книг"])
        description = (
            f"После изменений осталось {remaining} {obj}. Это {rem_num}/{rem_den} от всего количества. "
            f"Сколько было всего? В ответ укажите только число"
        )
        points = 26
        return {"title": title, "description": description, "correct_answer": str(total), "points": points * 2, "_meta": {"variant": variant, "rem_num": rem_num, "rem_den": rem_den, "remaining": remaining, "ans": total}}

    # reverse_operations (пример из запроса)
    # x*mul -> берём n/d -> получаем res
    mul = random.randint(2, 9)
    n, d = _rand_coprime_fraction(2, 10)
    # подбираем x, чтобы res был целым и "приятным"
    x = random.randint(10, 200)
    value = x * mul
    if (value * n) % d != 0:
        # корректируем x кратностью d
        x = _pick_multiple(d, 10, 300)
        value = x * mul
    res = value * n // d
    description = (
        f"Число умножили на {mul}, затем взяли {n}/{d} от результата и получили {res}. "
        f"Какое было число? В ответ укажите только число"
    )
    points = 28
    return {"title": title, "description": description, "correct_answer": str(x), "points": points * 2, "_meta": {"variant": variant, "mul": mul, "n": n, "d": d, "res": res, "ans": x}}

def generate_part_fraction_word_task() -> Dict[str, Any]:
    """Усложнённая задача: какую часть составляет одна группа от другой/от общего (ответ — несократимая дробь)."""
    def plural_ru(n: int, one: str, two: str, five: str) -> str:
        # one: 1 (книга), two: 2-4 (книги), five: 5+ (книг)
        n_abs = abs(n)
        n10 = n_abs % 10
        n100 = n_abs % 100
        if 11 <= n100 <= 14:
            return five
        if n10 == 1:
            return one
        if 2 <= n10 <= 4:
            return two
        return five

    contexts = [
        {
            "place": "В классе",
            "total_forms": ("ученик", "ученика", "учеников"),
            "cat1_forms": ("мальчик", "мальчика", "мальчиков"),
            "cat1_nom": "мальчики",
            "cat2_nom": "девочки",
        },
        {
            "place": "В коробке",
            "total_forms": ("конфета", "конфеты", "конфет"),
            "cat1_forms": ("шоколадная конфета", "шоколадные конфеты", "шоколадных конфет"),
            "cat1_nom": "шоколадные конфеты",
            "cat2_nom": "карамельные конфеты",
        },
        {
            "place": "В корзине",
            "total_forms": ("яблоко", "яблока", "яблок"),
            "cat1_forms": ("красное яблоко", "красных яблока", "красных яблок"),
            "cat1_nom": "красные яблоки",
            "cat2_nom": "зелёные яблоки",
        },
        {
            "place": "В библиотеке",
            "total_forms": ("книга", "книги", "книг"),
            "cat1_forms": ("учебник", "учебника", "учебников"),
            "cat1_nom": "учебники",
            "cat2_nom": "художественные книги",
        },
    ]

    ctx = random.choice(contexts)
    total0 = random.randint(20, 120)
    part10 = random.randint(1, total0 - 1)

    total_one, total_two, total_five = ctx["total_forms"]
    cat1_one, cat1_two, cat1_five = ctx["cat1_forms"]

    # Усложнение: возможны изменения (добавили/убрали) ТОЛЬКО первой категории,
    # чтобы условие было однозначным (и проверяемым).
    change = random.random() < 0.55
    delta = 0
    total = total0
    part1 = part10
    if change:
        # меняем только первую категорию и общий итог
        delta = random.randint(-min(10, part1 - 1), min(12, (total - part1) - 1))
        if delta == 0:
            delta = 1
        part1_new = part1 + delta
        total_new = total + delta
        if part1_new <= 0 or part1_new >= total_new:
            change = False
        else:
            part1, total = part1_new, total_new

    # 1) спрашиваем долю первой группы
    # 2) спрашиваем долю второй группы (оставшихся)
    ask_complement = random.random() < 0.4

    if ask_complement:
        asked_nom = ctx["cat2_nom"]
        asked_count = total - part1
        points = 14
    else:
        asked_nom = ctx["cat1_nom"]
        asked_count = part1
        points = 12

    g = gcd(asked_count, total)
    num = asked_count // g
    den = total // g

    title = random.choice(PART_FRACTION_TITLES) + f" #{random.randint(1, 1000)}"
    total_phrase = plural_ru(total0, total_one, total_two, total_five)
    part1_phrase0 = plural_ru(part10, cat1_one, cat1_two, cat1_five)
    if change:
        delta_abs = abs(delta)
        if delta > 0:
            change_sentence = f"Затем пришло ещё {delta_abs} {plural_ru(delta_abs, cat1_one, cat1_two, cat1_five)}."
        else:
            change_sentence = f"Затем ушло {delta_abs} {plural_ru(delta_abs, cat1_one, cat1_two, cat1_five)}."
        description = (
            f"{ctx['place']} было {total0} {total_phrase}, из них {part10} {part1_phrase0}. "
            f"{change_sentence} "
            f"Теперь всего стало {total} {plural_ru(total, total_one, total_two, total_five)}, "
            f"а {ctx['cat1_nom']} стало {part1}. "
            f"Какую часть всех {total_five} составляют {asked_nom}? "
            f"В ответ укажите несократимую дробь в формате 5/6 без пробелов"
        )
    else:
        description = (
            f"{ctx['place']} {total} {plural_ru(total, total_one, total_two, total_five)}, из них {part1} {plural_ru(part1, cat1_one, cat1_two, cat1_five)}. "
            f"Какую часть всех {total_five} составляют {asked_nom}? "
            f"В ответ укажите несократимую дробь в формате 5/6 без пробелов"
        )

    points *= 2
    return {
        "title": title,
        "description": description,
        "correct_answer": f"{num}/{den}",
        "points": points,
        "_meta": {"total": total, "asked_count": asked_count, "num": num, "den": den, "ask_complement": ask_complement, "changed": change, "delta": delta},
    }


def generate_territory_fraction_word_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Задачи на дроби» для битвы за территорию.
    Объединяет три типа: часть от целого (доли), целое по части (доли), какую часть составляет (доля).
    Ответ: число (для части от целого / целое по части) или несократимая дробь вида 5/6 (для «какую часть составляет»).
    """
    choice = random.choice(["part_of_whole", "whole_from_part", "part_fraction"])
    if choice == "part_of_whole":
        task = generate_part_of_whole_word_task()
    elif choice == "whole_from_part":
        task = generate_whole_from_part_word_task()
    else:
        task = generate_part_fraction_word_task()
    return {
        "title": "Задачи на дроби",
        "description": task["description"],
        "correct_answer": task["correct_answer"],
        "points": 12 + difficulty * 4,
        "_meta": task.get("_meta", {}),
    }


def generate_motion_task(motion_type: str) -> Dict:
    """Генерирует задачу на движение. Все входные данные и ответ — натуральные числа."""
    title = random.choice(MOTION_TITLES) + f" #{random.randint(1, 1000)}"

    def _pick_multiple(k: int, min_val: int, max_val: int) -> int:
        lo = (min_val + k - 1) // k
        hi = max_val // k
        if lo > hi:
            return k * max(1, lo)
        return k * random.randint(lo, hi)

    def _hours_word(n: int) -> str:
        # для текста, если нужно
        n10 = n % 10
        n100 = n % 100
        if 11 <= n100 <= 14:
            return "часов"
        if n10 == 1:
            return "час"
        if 2 <= n10 <= 4:
            return "часа"
        return "часов"

    # Встречное движение
    if motion_type == "meet":
        v1 = random.randint(20, 90)
        v2 = random.randint(20, 90)
        variant = random.random()
        if variant < 0.45:
            # Найти расстояние
            t = random.randint(1, 6)
            s = (v1 + v2) * t
            description = (
                f"Из двух пунктов навстречу друг другу одновременно выехали два автомобиля. "
                f"Скорость первого {v1} км/ч, скорость второго {v2} км/ч. "
                f"Сколько километров будет между пунктами, если они встретятся через {t} {_hours_word(t)}? "
                f"В ответ укажите только число"
            )
            correct_answer = str(s)
        elif variant < 0.8:
            # Найти время встречи
            sum_v = v1 + v2
            s = _pick_multiple(sum_v, 80, 1200)
            t = s // sum_v
            description = (
                f"Расстояние между двумя пунктами {s} км. "
                f"Навстречу друг другу одновременно выехали два автомобиля со скоростями {v1} км/ч и {v2} км/ч. "
                f"Через сколько часов они встретятся? В ответ укажите только число"
            )
            correct_answer = str(t)
        else:
            # Найти скорость второго по расстоянию/времени/скорости первого
            t = random.randint(2, 8)
            sum_v = v1 + v2
            s = sum_v * t
            description = (
                f"Два автомобиля выехали навстречу друг другу. Скорость первого {v1} км/ч. "
                f"Они встретились через {t} {_hours_word(t)}, а расстояние между пунктами равно {s} км. "
                f"Найдите скорость второго автомобиля (км/ч). В ответ укажите только число"
            )
            correct_answer = str(v2)
        points = 18

    # В противоположных направлениях (разъезжаются)
    elif motion_type == "opposite":
        v1 = random.randint(10, 80)
        v2 = random.randint(10, 80)
        variant = random.random()
        if variant < 0.55:
            t = random.randint(1, 6)
            dist = (v1 + v2) * t
            description = (
                f"Из пункта A одновременно в противоположных направлениях выехали два велосипедиста. "
                f"Скорость первого {v1} км/ч, скорость второго {v2} км/ч. "
                f"Какое расстояние будет между ними через {t} {_hours_word(t)}? В ответ укажите только число"
            )
            correct_answer = str(dist)
        elif variant < 0.85:
            sum_v = v1 + v2
            dist = _pick_multiple(sum_v, 40, 800)
            t = dist // sum_v
            description = (
                f"Из пункта A в противоположных направлениях выехали два велосипедиста со скоростями "
                f"{v1} км/ч и {v2} км/ч. Через сколько часов расстояние между ними станет {dist} км? "
                f"В ответ укажите только число"
            )
            correct_answer = str(t)
        else:
            # Найти скорость одного по расстоянию/времени/скорости другого
            t = random.randint(2, 7)
            dist = (v1 + v2) * t
            description = (
                f"Из пункта A одновременно в противоположных направлениях выехали два велосипедиста. "
                f"Скорость второго {v2} км/ч. Через {t} {_hours_word(t)} расстояние между ними стало {dist} км. "
                f"Найдите скорость первого велосипедиста (км/ч). В ответ укажите только число"
            )
            correct_answer = str(v1)
        points = 18

    # Вдогонку
    elif motion_type == "catchup":
        # Подбираем так, чтобы время догонялки было целым
        attempts = 0
        while True:
            v_slow = random.randint(6, 24)   # пеший/велосипедист
            v_fast = random.randint(v_slow + 6, v_slow + 60)
            delay = random.randint(1, 6)
            head_start = v_slow * delay
            rel = v_fast - v_slow
            if rel > 0 and head_start % rel == 0:
                t = head_start // rel
                if t > 0:
                    break
            attempts += 1
            if attempts > 200:
                # запасной простой вариант
                v_slow, v_fast, delay = 12, 36, 2
                head_start = v_slow * delay
                rel = v_fast - v_slow
                t = head_start // rel
                break

        variant = random.random()
        if variant < 0.45:
            description = (
                f"Из пункта A выехал велосипедист со скоростью {v_slow} км/ч. "
                f"Через {delay} {_hours_word(delay)} вслед за ним выехал мотоциклист со скоростью {v_fast} км/ч. "
                f"Через сколько часов после выезда мотоциклист догонит велосипедиста? В ответ укажите только число"
            )
            correct_answer = str(t)
        elif variant < 0.8:
            dist_to_catch = v_fast * t
            description = (
                f"Из пункта A выехал велосипедист со скоростью {v_slow} км/ч. "
                f"Через {delay} {_hours_word(delay)} вслед за ним выехал мотоциклист со скоростью {v_fast} км/ч. "
                f"Сколько километров проедет мотоциклист до момента, когда догонит велосипедиста? "
                f"В ответ укажите только число"
            )
            correct_answer = str(dist_to_catch)
        else:
            # Вариант: известно расстояние форы, найти время догонялки
            head_start = v_slow * delay
            description = (
                f"Мотоциклист едет со скоростью {v_fast} км/ч и догоняет велосипедиста со скоростью {v_slow} км/ч. "
                f"В момент старта мотоциклиста велосипедист был впереди на {head_start} км. "
                f"Через сколько часов мотоциклист догонит велосипедиста? В ответ укажите только число"
            )
            correct_answer = str(t)
        points = 20

    # По течению
    elif motion_type == "downstream":
        u = random.randint(1, 10)  # скорость течения
        v = random.randint(u + 5, u + 40)  # скорость лодки в стоячей воде
        t = random.randint(1, 6)
        v_down = v + u
        s = v_down * t

        variant = random.random()
        if variant < 0.5:
            description = (
                f"Скорость лодки в стоячей воде {v} км/ч, скорость течения {u} км/ч. "
                f"Лодка плыла по течению {t} {_hours_word(t)}. Какое расстояние (в км) она проплыла? "
                f"В ответ укажите только число"
            )
            correct_answer = str(s)
        else:
            # скорость в стоячей воде по известным s, t, u
            v_down_known = s // t
            v_still = v_down_known - u
            description = (
                f"Лодка плыла по течению {s} км за {t} {_hours_word(t)}. "
                f"Скорость течения {u} км/ч. Найдите скорость лодки в стоячей воде (км/ч). "
                f"В ответ укажите только число"
            )
            correct_answer = str(v_still)
        points = 22

    # Против течения
    elif motion_type == "upstream":
        u = random.randint(1, 10)
        v = random.randint(u + 6, u + 45)  # v > u обязательно
        t = random.randint(1, 6)
        v_up = v - u
        s = v_up * t

        variant = random.random()
        if variant < 0.5:
            description = (
                f"Скорость лодки в стоячей воде {v} км/ч, скорость течения {u} км/ч. "
                f"Лодка плыла против течения {t} {_hours_word(t)}. Какое расстояние (в км) она проплыла? "
                f"В ответ укажите только число"
            )
            correct_answer = str(s)
        else:
            v_up_known = s // t
            v_still = v_up_known + u
            description = (
                f"Лодка плыла против течения {s} км за {t} {_hours_word(t)}. "
                f"Скорость течения {u} км/ч. Найдите скорость лодки в стоячей воде (км/ч). "
                f"В ответ укажите только число"
            )
            correct_answer = str(v_still)
        points = 22

    else:
        # неизвестный тип
        return generate_motion_task(random.choice(["meet", "opposite", "catchup", "downstream", "upstream"]))

    # Гарантия натуральности ответа
    if not correct_answer.isdigit() or int(correct_answer) <= 0:
        return generate_motion_task(motion_type)

    points *= 2
    return {
        "title": title,
        "description": description,
        "correct_answer": correct_answer,
        "points": points,
        "_meta": {"motion_type": motion_type, "expected": int(correct_answer)},
    }


def generate_territory_motion_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Задачи на движение» для битвы за территорию.
    Использует те же типы задач, что и generate_motion_task; difficulty влияет на выбор типа:
    1 — встречное и в противоположных направлениях;
    2 — + вдогонку;
    3 — все типы (в т.ч. по течению / против течения).
    Ответ: одно число (текстовый ввод).
    """
    if difficulty == 1:
        motion_type = random.choice(["meet", "opposite"])
    elif difficulty == 2:
        motion_type = random.choice(["meet", "opposite", "catchup"])
    else:
        motion_type = random.choice(["meet", "opposite", "catchup", "downstream", "upstream"])
    task = generate_motion_task(motion_type)
    return {
        "title": "Задачи на движение",
        "description": task["description"],
        "correct_answer": task["correct_answer"],
        "points": 12 + difficulty * 4,
        "_meta": task.get("_meta", {}),
    }


def generate_simplify_x_expression_task() -> Dict[str, Any]:
    """
    Генерирует задание на упрощение выражения, состоящего только из одночленов с переменной x.

    Требования:
    - только переменная x (английская буква)
    - коэффициенты натуральные
    - при последовательном упрощении (слева направо) промежуточный коэффициент остаётся натуральным
    """
    # Усложнение: выражение содержит группы в скобках и множители.
    # ВАЖНО: это задания для детей, поэтому НЕ допускаем отрицательных одночленов
    # (никаких "-11y", "-3n" и т.п.). То есть внутри выражения используем только сложение
    # положительных одночленов (скобки и множители остаются).
    var = random.choice(list("xyzabcmnt"))  # разные латинские переменные

    def _term(c: int) -> str:
        return var if c == 1 else f"{c}{var}"

    max_attempts = 300
    for _ in range(max_attempts):
        group_count = random.randint(2, 4)
        total_coeff = 0
        expr_parts: List[str] = []

        for gi in range(group_count):
            mult = random.randint(2, 8) if random.random() < 0.8 else 1
            inner_terms = random.randint(2, 7)
            coeffs = [random.randint(1, 15) for _ in range(inner_terms)]
            inner_sum = sum(coeffs)

            inside = "+".join(_term(c) for c in coeffs)
            group_str = f"({inside})"  # всегда скобки для сложности
            piece = group_str if mult == 1 else f"{mult}{group_str}"

            if gi == 0:
                expr_parts.append(piece)
            else:
                expr_parts.append("+" + piece)

            total_coeff += mult * inner_sum

        if total_coeff <= 0 or total_coeff > 900:
            continue

        expression = "".join(expr_parts)
        simplified = var if total_coeff == 1 else f"{total_coeff}{var}"

        title = random.choice(SIMPLIFY_X_TITLES) + f" #{random.randint(1, 1000)}"
        description = (
            f"Упростите выражение {expression}. "
            f"В ответ укажите получившееся выражение, например 10{var} ({var} — английская буква). "
            f"Пишите без пробелов"
        )

        # Баллы от количества групп/длины
        if group_count <= 2:
            points = 24
        elif group_count <= 3:
            points = 28
        else:
            points = 32

        points *= 2
        return {
            "title": title,
            "description": description,
            "correct_answer": simplified,
            "points": points,
            "_meta": {"var": var, "total_coeff": total_coeff, "expression": expression},
        }

    return generate_simplify_x_expression_task()


def generate_two_unknowns_word_task() -> Dict[str, Any]:
    """
    Текстовые задачи на две неизвестные величины:
    1) сумма и разность (одна величина на D больше/дороже другой)
    2) задачи на части: одна величина в k раз больше другой, известна сумма
    3) задачи на части: одна величина в k раз больше другой, известна разность

    Ответ: одно натуральное число (обычно "большая/дорогая" величина).
    """

    title = random.choice(MATH_TITLES) + f" #{random.randint(1, 1000)}"
    variant = random.choice(["sum_diff_money", "sum_diff_generic", "ratio_sum", "ratio_diff"])

    # 1) Сумма и разность: x + y = T, x - y = D (x > y)
    if variant in ("sum_diff_money", "sum_diff_generic"):
        contexts = [
            {
                "kind": "money",
                "unit": "руб.",
                "items": [("бита", "мяч"), ("книга", "тетрадь"), ("ручка", "карандаш"), ("куртка", "шапка")],
            },
            {
                "kind": "length",
                "unit": "см",
                # элементы в родительном падеже (чтобы не склонять в шаблоне)
                "items": [("первой ленты", "второй ленты"), ("первого отрезка", "второго отрезка")],
            },
            {
                "kind": "weight",
                "unit": "кг",
                # также используем родительный падеж
                "items": [("большой тыквы", "маленькой тыквы"), ("первого мешка", "второго мешка")],
            },
            {
                "kind": "pages",
                "unit": "стр.",
                # предл. падеж: "в альбоме", "в тетради" и т.п.
                "items": [("в первой книге", "во второй книге"), ("в альбоме", "в тетради")],
            },
        ]

        ctx = random.choice(contexts)
        item_big, item_small = random.choice(ctx["items"])

        # Подбираем x,y так, чтобы (T ± D) были целыми и >0
        y = random.randint(5, 250)
        # D выбираем умеренно, чтобы формулировка была естественной
        d = random.randint(10, 220)
        x = y + d
        t = x + y

        # Ограничиваем размеры для "денежных" и "длина/вес"
        if ctx["unit"] == "руб." and t > 2000:
            scale = max(1, t // 2000 + 1)
            x //= scale
            y //= scale
            if y <= 0:
                y = 5
            x = y + d // scale if d // scale > 0 else y + 1
            t = x + y
            d = x - y

        ask_big = True  # чаще спрашиваем "большую/дорогую"
        if random.random() < 0.25:
            ask_big = False

        # Разность задаём как "меньше" (детям обычно понятнее "дешевле/короче/легче")
        if d <= 0:
            return generate_two_unknowns_word_task()

        ask_item = item_big if ask_big else item_small
        kind = ctx["kind"]
        unit = ctx["unit"]

        if kind == "money":
            # ВАЖНО: unit уже содержит точку ("руб."), поэтому не ставим "руб.." в конце предложения.
            description = (
                f"{item_big.capitalize()} и {item_small} стоят {t} {unit} "
                f"{item_small.capitalize()} на {d} {unit} дешевле {item_big}. "
                f"Сколько стоит {ask_item}? В ответ укажите только число"
            )
        elif kind == "length":
            description = (
                f"Сумма длин {item_big} и {item_small} равна {t} {unit}. "
                f"Длина {item_small} на {d} {unit} меньше длины {item_big}. "
                f"Чему равна длина {ask_item}? В ответ укажите только число"
            )
        elif kind == "weight":
            description = (
                f"Сумма масс {item_big} и {item_small} равна {t} {unit}. "
                f"Масса {item_small} на {d} {unit} меньше массы {item_big}. "
                f"Сколько весит {ask_item}? В ответ укажите только число"
            )
        else:  # pages
            description = (
                f"{item_big.capitalize()} и {item_small} вместе {t} {unit} "
                f"(здесь {unit} — это страницы). "
                f"{item_small.capitalize()} на {d} {unit} меньше, чем {item_big}. "
                f"Сколько {unit} {ask_item}? В ответ укажите только число"
            )

        ans = x if ask_big else y
        if ans <= 0:
            return generate_two_unknowns_word_task()

        points = 26
        return {
            "title": title,
            "description": description,
            "correct_answer": str(ans),
            "points": points * 2,
            "_meta": {"variant": variant, "x": x, "y": y, "t": t, "d": d, "ask_big": ask_big, "ans": ans},
        }

    # 2) Задачи на части: в k раз больше, известна сумма
    if variant == "ratio_sum":
        k = random.randint(2, 7)
        small = random.randint(3, 60)
        big = k * small
        total = big + small

        contexts = [
            {"what": "фруктов", "where_sg": "корзине", "where_pl": "корзинах"},
            {"what": "книг", "where_sg": "коробке", "where_pl": "коробках"},
            {"what": "карандашей", "where_sg": "пенале", "where_pl": "пеналах"},
            {"what": "конфет", "where_sg": "пакете", "where_pl": "пакетах"},
        ]
        ctx = random.choice(contexts)
        what = ctx["what"]
        where_sg = ctx["where_sg"]
        where_pl = ctx["where_pl"]
        description = (
            f"В одной {where_sg} в {k} раз больше {what}, чем в другой. "
            f"В двух {where_pl} {total} {what}. "
            f"Сколько {what} в большей {where_sg}? В ответ укажите только число"
        )
        ans = big
        points = 24
        return {
            "title": title,
            "description": description,
            "correct_answer": str(ans),
            "points": points * 2,
            "_meta": {"variant": variant, "k": k, "small": small, "big": big, "total": total, "ans": ans},
        }

    # 3) Задачи на части: в k раз больше, известна разность
    k = random.randint(2, 7)
    small = random.randint(3, 70)
    big = k * small
    diff = big - small

    contexts = [
        {"what": "фруктов", "where_sg": "корзине"},
        {"what": "марок", "where_sg": "альбоме"},
        {"what": "шариков", "where_sg": "коробке"},
        {"what": "орехов", "where_sg": "пакете"},
    ]
    ctx = random.choice(contexts)
    what = ctx["what"]
    where = ctx["where_sg"]
    description = (
        f"В одной {where} в {k} раз больше {what}, чем в другой. "
        f"В большей {where} на {diff} {what} больше. "
        f"Сколько {what} в большей {where}? В ответ укажите только число"
    )
    ans = big
    points = 26
    return {
        "title": title,
        "description": description,
        "correct_answer": str(ans),
        "points": points * 2,
        "_meta": {"variant": variant, "k": k, "small": small, "big": big, "diff": diff, "ans": ans},
    }


def _time_unit_word(n: int, unit: str) -> str:
    """Склонение единицы времени: unit in ('day', 'hour', 'min') -> день/дня/дней и т.п."""
    n_abs = abs(n)
    n10 = n_abs % 10
    n100 = n_abs % 100
    if 11 <= n100 <= 14:
        return {"day": "дней", "hour": "часов", "min": "минут"}[unit]
    if n10 == 1:
        return {"day": "день", "hour": "час", "min": "минуту"}[unit]
    if 2 <= n10 <= 4:
        return {"day": "дня", "hour": "часа", "min": "минуты"}[unit]
    return {"day": "дней", "hour": "часов", "min": "минут"}[unit]


# Шаблоны задач «Совместная работа» для 2–3 уровня сложности (трубы, бригады, насосы, мастер/ученик)
JOINT_WORK_TEMPLATES_L2 = [
    {
        "description": "Через первую трубу бассейн можно наполнить за 3 ч, через вторую — за 6 ч. Какую часть бассейна наполняют две трубы за 1 ч? В ответ укажите несократимую дробь в формате 5/6.",
        "correct_answer": "1/2",
    },
    {
        "description": "Через первую трубу можно наполнить бак за 4 мин, через вторую — за 12 мин. За сколько минут можно наполнить бак через две трубы? В ответ укажите только число (мин).",
        "correct_answer": "3",
    },
    {
        "description": "Одна бригада может выполнить работу за 6 дней, а другая — за 12 дней. За сколько дней две бригады выполнят ту же работу вместе? В ответ укажите только число (дней).",
        "correct_answer": "4",
    },
    {
        "description": "Через одну трубу резервуар наполняется за 30 ч, через другую — за 6 ч. Сколько времени займёт наполнение резервуара, если одновременно задействовать обе трубы? В ответ укажите только число (часов).",
        "correct_answer": "5",
    },
]

JOINT_WORK_TEMPLATES_L3 = [
    {
        "description": "Если использовать большой насос, то цистерна наполнится за 4 ч, а если маленький — за 16 ч. Какая часть цистерны будет заполнена, если оба насоса включить одновременно на 3 ч? В ответ укажите несократимую дробь в формате 5/6.",
        "correct_answer": "15/16",
    },
    {
        "description": "Мастер может обработать партию деталей за 5 ч, а его ученик — за 20 ч. Успеют ли они обработать партию деталей за 3 ч, если будут работать вместе? В ответ укажите да или нет.",
        "correct_answer": "нет",
    },
    {
        "description": "Через одну трубу бассейн наполняется водой за 6 ч, через другую — за 15 ч. Какая часть бассейна будет заполнена, если одновременно открыть краны на обеих трубах на 2 ч? В ответ укажите несократимую дробь в формате 5/6.",
        "correct_answer": "7/15",
    },
]


def generate_joint_work_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «Совместная работа» для битвы за территорию.
    Задачи на совместную работу: 2 или 3 исполнителя (бригады, трубы, комбайны, мастер и ученик).
    Вопрос: какую часть работы за 1 единицу времени выполняют вместе, или за сколько времени выполнят всю работу.
    Ответ: дробь вида num/den (часть за 1 ед. времени) или одно число (время).
    Для сложности 2 и 3 используются в том числе фиксированные шаблоны задач.
    """
    points = 12 + difficulty * 4

    # Для 2–3 уровня с вероятностью 50% выдаём шаблонную задачу
    if difficulty == 2 and JOINT_WORK_TEMPLATES_L2 and random.random() < 0.5:
        t = random.choice(JOINT_WORK_TEMPLATES_L2)
        return {
            "title": "Совместная работа",
            "description": t["description"],
            "correct_answer": t["correct_answer"],
            "points": points,
            "_meta": {"template": True, "difficulty": 2},
        }
    if difficulty == 3 and JOINT_WORK_TEMPLATES_L3 and random.random() < 0.5:
        t = random.choice(JOINT_WORK_TEMPLATES_L3)
        return {
            "title": "Совместная работа",
            "description": t["description"],
            "correct_answer": t["correct_answer"],
            "points": points,
            "_meta": {"template": True, "difficulty": 3},
        }

    num_workers = 2 if difficulty == 1 else random.choice([2, 3])
    ask_part = random.choice([True, False])  # True: часть за 1 ед.; False: за сколько времени вся работа

    # Контексты: object — винительный (отремонтировать что? дорогу), object_gen — родительный (часть чего? дороги)
    if num_workers == 2:
        contexts = [
            {"names": ["Первая бригада", "Вторая бригада"], "object": "дорогу", "object_gen": "дороги", "action": "отремонтировать", "action_plural": "отремонтируют", "unit": "day"},
            {"names": ["Первый комбайн", "Второй комбайн"], "object": "поле", "object_gen": "поля", "action": "обработать", "action_plural": "обработают", "unit": "hour"},
            {"names": ["Первая труба", "Вторая труба"], "object": "емкость", "object_gen": "емкости", "action": "наполнить водой", "action_plural": "наполнят водой", "unit": "min"},
            {"names": ["Первая труба", "Вторая труба"], "object": "бассейн", "object_gen": "бассейна", "action": "наполнить водой", "action_plural": "наполнят водой", "unit": "hour"},
            {"names": ["Мастер", "Ученик"], "object": "работу", "object_gen": "работы", "action": "выполнить", "action_plural": "выполнят", "unit": "hour"},
        ]
    else:
        contexts = [
            {"names": ["Первая труба", "Вторая труба", "Третья труба"], "object": "емкость", "object_gen": "емкости", "action": "наполнить водой", "action_singular": "наполняет водой", "action_plural": "наполнят водой", "unit": "min"},
            {"names": ["Первая труба", "Вторая труба", "Третья труба"], "object": "бассейн", "object_gen": "бассейна", "action": "наполнить водой", "action_singular": "наполняет водой", "action_plural": "наполнят водой", "unit": "hour"},
        ]

    ctx = random.choice(contexts)
    unit_key = ctx["unit"]
    unit_word = {"day": "дней", "hour": "ч", "min": "мин"}[unit_key]

    if num_workers == 2:
        if ask_part:
            # Любые целые t1, t2; часть = 1/t1 + 1/t2 = (t1+t2)/(t1*t2)
            if difficulty == 1:
                t1 = random.randint(2, 12)
                t2 = random.randint(2, 12)
            elif difficulty == 2:
                t1 = random.randint(3, 20)
                t2 = random.randint(3, 20)
            else:
                t1 = random.randint(4, 30)
                t2 = random.randint(4, 30)
            sum_rates_num = t1 + t2
            sum_rates_den = t1 * t2
            g = gcd(sum_rates_num, sum_rates_den)
            num = sum_rates_num // g
            den = sum_rates_den // g
            correct_answer = f"{num}/{den}"
            time_word_1 = _time_unit_word(t1, unit_key)
            time_word_2 = _time_unit_word(t2, unit_key)
            one_unit = "день" if unit_key == "day" else ("час" if unit_key == "hour" else "минуту")
            desc = (
                f"{ctx['names'][0]} может {ctx['action']} {ctx['object']} за {t1} {time_word_1}, "
                f"а {ctx['names'][1].lower()} — за {t2} {time_word_2}. "
                f"Какую часть {ctx['object_gen']} {ctx['action_plural']} за 1 {one_unit} при совместной работе? "
                f"В ответ укажите несократимую дробь в формате 5/6"
            )
        else:
            # Подбираем t1, t2 так, чтобы T = t1*t2/(t1+t2) было целым: T задаём, A = t1, B = A*T/(A-T)
            for _ in range(50):
                T = random.randint(2, 12) if difficulty == 1 else random.randint(2, 20)
                A = random.randint(T + 1, 3 * T + 10)
                if (A - T) <= 0:
                    continue
                if (A * T) % (A - T) != 0:
                    continue
                B = (A * T) // (A - T)
                if B <= 0 or B == A:
                    continue
                t1, t2 = A, B
                break
            else:
                t1, t2 = 6, 3  # 2 ч
            T = (t1 * t2) // (t1 + t2)
            correct_answer = str(T)
            time_word_1 = _time_unit_word(t1, unit_key)
            time_word_2 = _time_unit_word(t2, unit_key)
            desc = (
                f"{ctx['names'][0]} может {ctx['action']} {ctx['object']} за {t1} {time_word_1}, "
                f"{ctx['names'][1].lower()} — за {t2} {time_word_2}. "
                f"За какое время {ctx['action_plural']} {ctx['object']} при совместной работе? "
                f"В ответ укажите только число ({unit_word})"
            )
    else:
        # 3 workers
        if ask_part:
            if difficulty == 1:
                times = [random.randint(2, 8) for _ in range(3)]
            else:
                times = [random.randint(2, 15) for _ in range(3)]
            # rate = 1/t1 + 1/t2 + 1/t3 = (t2*t3 + t1*t3 + t1*t2) / (t1*t2*t3)
            t1, t2, t3 = times
            num_rate = t2 * t3 + t1 * t3 + t1 * t2
            den_rate = t1 * t2 * t3
            g = gcd(num_rate, den_rate)
            num = num_rate // g
            den = den_rate // g
            one_unit = "час" if unit_key == "hour" else "минуту"
            correct_answer = f"{num}/{den}"
            desc = (
                f"{ctx['names'][0]} {ctx['action_singular']} {ctx['object']} за {t1} {unit_word}, "
                f"{ctx['names'][1].lower()} — за {t2} {unit_word}, "
                f"{ctx['names'][2].lower()} — за {t3} {unit_word}. "
                f"Какую часть {ctx['object_gen']} {ctx['action_plural']} за 1 {one_unit} все три, работая одновременно? "
                f"В ответ укажите несократимую дробь в формате 5/6"
            )
        else:
            # Подбираем (t1,t2,t3) так, чтобы T = 1/(1/t1+1/t2+1/t3) было целым
            # T = t1*t2*t3 / (t1*t2 + t1*t3 + t2*t3)
            predefined_triples = [
                (6, 3, 2),   # 1/(1/6+1/3+1/2)=1, 6*3*2/(18+12+6)=36/36=1
                (10, 6, 15), # 1500/(60+150+90)=1500/300=5
                (2, 5, 10),  # 100/(10+20+50)=100/80 - no
                (2, 3, 6),   # 36/(6+12+18)=36/36=1
                (4, 6, 12),  # 288/(24+48+72)=288/144=2
                (3, 4, 6),   # 72/(12+18+24)=72/54 - no
                (6, 8, 12),  # 576/(48+72+96)=576/216 - no
                (5, 10, 10), # 500/(50+50+100)=500/200 - no
                (6, 10, 15), # 900/(60+90+150)=900/300=3
            ]
            for _ in range(30):
                if difficulty == 1 and predefined_triples:
                    t1, t2, t3 = random.choice(predefined_triples[:4])
                else:
                    t1 = random.randint(2, 12)
                    t2 = random.randint(2, 12)
                    t3 = random.randint(2, 12)
                s = t1 * t2 + t1 * t3 + t2 * t3
                if s == 0:
                    continue
                T_num = t1 * t2 * t3
                if T_num % s != 0:
                    continue
                T = T_num // s
                if T >= 1:
                    break
            else:
                t1, t2, t3 = 6, 3, 2
                T = 1
            correct_answer = str(T)
            desc = (
                f"{ctx['names'][0]} {ctx['action_singular']} {ctx['object']} за {t1} {unit_word}, "
                f"{ctx['names'][1].lower()} — за {t2} {unit_word}, "
                f"{ctx['names'][2].lower()} — за {t3} {unit_word}. "
                f"За какое время {ctx['action_plural']} {ctx['object']}, если одновременно задействовать все три? "
                f"В ответ укажите только число ({unit_word})"
            )

    return {
        "title": "Совместная работа",
        "description": desc,
        "correct_answer": correct_answer,
        "points": points,
        "_meta": {"num_workers": num_workers, "ask_part": ask_part},
    }


def generate_territory_two_unknowns_task(difficulty: int) -> Dict[str, Any]:
    """Генератор «сумма/разность и части» для битвы за территорию.
    Использует алгоритм двух неизвестных: сумма и разность, задачи на части (в k раз больше, сумма/разность).
    Ответ: одно натуральное число.
    """
    task = generate_two_unknowns_word_task()
    return {
        "title": "сумма/разность и части",
        "description": task["description"],
        "correct_answer": task["correct_answer"],
        "points": 12 + difficulty * 4,
        "_meta": task.get("_meta", {}),
    }


def verify_task(task: Dict[str, Any], task_type: str) -> bool:
    """Проверяет правильность ответа и согласованность условия максимально надёжно."""
    try:
        meta = task.get("_meta", {})

        if task_type == "expression":
            ev = meta.get("ev")
            if not isinstance(ev, str):
                return False
            result = _safe_eval_int(ev)
            return result > 0 and task.get("correct_answer") == str(result) and "выражения" in task.get("description", "")
        
        elif task_type == "equation":
            equation = meta.get("equation")
            if not isinstance(equation, str):
                return False
            x = int(task["correct_answer"])
            left, right = equation.split("=", 1)
            left_eval = left.replace(":", "/").replace("·", "*").replace("x", str(x))
            lv = _safe_eval_int(left_eval)
            rv = int(right)
            return lv == rv and "уравнения" in task.get("description", "")
        
        elif task_type == "gcd_lcm":
            kind = meta.get("kind")
            if kind == "numeric":
                # Числовой вариант: доверяем meta.result
                result = int(meta.get("result"))
                return task.get("correct_answer") == str(result) and ("НОД" in task.get("description", "") or "НОК" in task.get("description", ""))
            # Текстовые: мета содержит ans
            ans = meta.get("ans")
            if ans is None:
                return False
            return task.get("correct_answer") == str(int(ans))

        elif task_type == "fraction":
            new_num = meta.get("new_num")
            new_den = meta.get("new_den")
            if not isinstance(new_num, int) or not isinstance(new_den, int) or new_den <= 0:
                return False
            return task.get("correct_answer") == f"{new_num}/{new_den}" and "знаменателем" in task.get("description", "")

        elif task_type == "reduce_fraction":
            p = meta.get("p")
            q = meta.get("q")
            a = meta.get("a")
            b = meta.get("b")
            if not all(isinstance(x, int) for x in [p, q, a, b]) or q <= 0 or b <= 0:
                return False
            if gcd(p, q) != 1:
                return False
            if a * q != b * p:
                return False
            return task.get("correct_answer") == f"{p}/{q}" and "Сократите дробь" in task.get("description", "")

        elif task_type == "part_word":
            ans = meta.get("ans")
            if ans is None:
                return False
            return task.get("correct_answer") == str(int(ans)) and isinstance(task.get("description"), str)

        elif task_type == "whole_from_part_word":
            ans = meta.get("ans")
            if ans is None:
                return False
            return task.get("correct_answer") == str(int(ans)) and "Сколько" in task.get("description", "")

        elif task_type == "part_fraction_word":
            num = meta.get("num")
            den = meta.get("den")
            if not isinstance(num, int) or not isinstance(den, int) or den <= 0:
                return False
            if gcd(num, den) != 1:
                return False
            return task.get("correct_answer") == f"{num}/{den}"

        elif task_type == "motion":
            ca = task.get("correct_answer", "")
            if not isinstance(ca, str) or not ca.isdigit() or int(ca) <= 0:
                return False
            expected = meta.get("expected")
            if not isinstance(expected, int) or expected <= 0:
                return False
            return ca == str(expected) and isinstance(task.get("description"), str)

        elif task_type == "simplify_x":
            var = meta.get("var")
            total_coeff = meta.get("total_coeff")
            if not isinstance(var, str) or not isinstance(total_coeff, int) or total_coeff <= 0:
                return False
            expected = var if total_coeff == 1 else f"{total_coeff}{var}"
            return task.get("correct_answer") == expected and task.get("description", "").startswith("Упростите выражение ")

        elif task_type == "two_unknowns_word":
            ans = meta.get("ans")
            if ans is None:
                return False
            ca = task.get("correct_answer")
            if ca != str(int(ans)):
                return False
            desc = task.get("description", "")
            if not isinstance(desc, str) or len(desc) < 20:
                return False
            # Минимальные маркеры: есть "В ответ укажите только число"
            return "В ответ укажите только число" in desc
    except Exception as e:
        # Ошибка при проверке - считаем задание неверным
        return False
    return False

def main():
    """Генерирует JSON файл с заданиями"""
    tasks = []
    per_type = 500

    print_task_themes()
    print()

    print("Генерация заданий на вычисление выражений...")
    for i in range(per_type):
        task = generate_expression_task()
        # Проверяем правильность
        if verify_task(task, "expression"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+1}/{per_type} создано")
        else:
            # Если не прошло проверку, генерируем заново
            attempts = 0
            while not verify_task(task, "expression") and attempts < 10:
                task = generate_expression_task()
                attempts += 1
            if verify_task(task, "expression"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+1}/{per_type} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+1}/{per_type}")
    
    print("\nГенерация заданий на решение уравнений...")
    for i in range(per_type):
        task = generate_equation_task()
        # Проверяем правильность
        if verify_task(task, "equation"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type+1}/{per_type*10} создано")
        else:
            # Если не прошло проверку, генерируем заново
            attempts = 0
            while not verify_task(task, "equation") and attempts < 10:
                task = generate_equation_task()
                attempts += 1
            if verify_task(task, "equation"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type+1}/{per_type*10}")
    
    print("\nГенерация заданий на НОД и НОК...")
    for i in range(per_type):
        task = generate_gcd_lcm_task()
        # Проверяем правильность
        if verify_task(task, "gcd_lcm"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*2+1}/{per_type*10} создано")
        else:
            # Если не прошло проверку, генерируем заново
            attempts = 0
            while not verify_task(task, "gcd_lcm") and attempts < 10:
                task = generate_gcd_lcm_task()
                attempts += 1
            if verify_task(task, "gcd_lcm"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*2+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*2+1}/{per_type*10}")

    print("\nГенерация заданий на дроби (приведение к знаменателю)...")
    for i in range(per_type):
        task = generate_fraction_task()
        if verify_task(task, "fraction"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*3+1}/{per_type*10} создано")
        else:
            attempts = 0
            while not verify_task(task, "fraction") and attempts < 10:
                task = generate_fraction_task()
                attempts += 1
            if verify_task(task, "fraction"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*3+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*3+1}/{per_type*10}")

    print("\nГенерация заданий на дроби (сокращение)...")
    for i in range(per_type):
        task = generate_reduce_fraction_task()
        if verify_task(task, "reduce_fraction"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*4+1}/{per_type*10} создано")
        else:
            attempts = 0
            while not verify_task(task, "reduce_fraction") and attempts < 10:
                task = generate_reduce_fraction_task()
                attempts += 1
            if verify_task(task, "reduce_fraction"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*4+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*4+1}/{per_type*10}")

    print("\nГенерация текстовых задач на доли (часть от целого)...")
    for i in range(per_type):
        task = generate_part_of_whole_word_task()
        if verify_task(task, "part_word"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*5+1}/{per_type*10} создано")
        else:
            attempts = 0
            while not verify_task(task, "part_word") and attempts < 10:
                task = generate_part_of_whole_word_task()
                attempts += 1
            if verify_task(task, "part_word"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*5+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*5+1}/{per_type*10}")

    print("\nГенерация текстовых задач на доли (найти целое по части)...")
    for i in range(per_type):
        task = generate_whole_from_part_word_task()
        if verify_task(task, "whole_from_part_word"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*6+1}/{per_type*10} создано")
        else:
            attempts = 0
            while not verify_task(task, "whole_from_part_word") and attempts < 10:
                task = generate_whole_from_part_word_task()
                attempts += 1
            if verify_task(task, "whole_from_part_word"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*6+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*6+1}/{per_type*10}")

    print("\nГенерация задач на долю (какую часть составляет группа)...")
    for i in range(per_type):
        task = generate_part_fraction_word_task()
        if verify_task(task, "part_fraction_word"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*7+1}/{per_type*10} создано")
        else:
            attempts = 0
            while not verify_task(task, "part_fraction_word") and attempts < 10:
                task = generate_part_fraction_word_task()
                attempts += 1
            if verify_task(task, "part_fraction_word"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*7+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*7+1}/{per_type*10}")

    print("\nГенерация задач на движение...")
    # Ровно 500 задач: по 100 каждого вида
    motion_types = (["meet"] * 100) + (["opposite"] * 100) + (["catchup"] * 100) + (["downstream"] * 100) + (["upstream"] * 100)
    random.shuffle(motion_types)
    for i in range(per_type):
        task = generate_motion_task(motion_types[i])
        if verify_task(task, "motion"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*8+1}/{per_type*10} создано")
        else:
            attempts = 0
            while not verify_task(task, "motion") and attempts < 10:
                task = generate_motion_task(motion_types[i])
                attempts += 1
            if verify_task(task, "motion"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*8+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*8+1}/{per_type*10}")

    print("\nГенерация заданий на упрощение выражений с x...")
    for i in range(per_type):
        task = generate_simplify_x_expression_task()
        if verify_task(task, "simplify_x"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*9+1}/{per_type*10} создано")
        else:
            attempts = 0
            while not verify_task(task, "simplify_x") and attempts < 10:
                task = generate_simplify_x_expression_task()
                attempts += 1
            if verify_task(task, "simplify_x"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*9+1}/{per_type*10} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*9+1}/{per_type*10}")

    print("\nГенерация текстовых задач на две неизвестные (сумма/разность, части)...")
    for i in range(per_type):
        task = generate_two_unknowns_word_task()
        if verify_task(task, "two_unknowns_word"):
            tasks.append(_strip_meta(task))
            print(f"  [OK] Задание {i+per_type*10+1}/{per_type*11} создано")
        else:
            attempts = 0
            while not verify_task(task, "two_unknowns_word") and attempts < 10:
                task = generate_two_unknowns_word_task()
                attempts += 1
            if verify_task(task, "two_unknowns_word"):
                tasks.append(_strip_meta(task))
                print(f"  [OK] Задание {i+per_type*10+1}/{per_type*11} создано (после {attempts+1} попыток)")
            else:
                print(f"  [ERROR] Ошибка при создании задания {i+per_type*10+1}/{per_type*11}")
    
    # Сохраняем в JSON
    output = {
        "tasks": tasks
    }
    
    filename = "boss_tasks.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Создано {len(tasks)} заданий")
    print(f"[OK] Файл сохранен: {filename}")
    
    # Статистика
    expected_total = per_type * 11
    if len(tasks) != expected_total:
        print(f"[WARN] Ожидалось {expected_total} заданий, фактически {len(tasks)}")

    # Счётчики задаём по этапам генерации (так надёжнее любых эвристик по тексту)
    expression_count = per_type
    equation_count = per_type
    gcd_lcm_count = per_type
    fraction_count = per_type
    reduce_fraction_count = per_type
    part_word_count = per_type
    whole_from_part_count = per_type
    part_fraction_count = per_type
    motion_count = per_type
    simplify_x_count = per_type
    two_unknowns_count = per_type
    
    print(f"\nСтатистика:")
    print(f"  - Выражения: {expression_count}")
    print(f"  - Уравнения: {equation_count}")
    print(f"  - НОД/НОК: {gcd_lcm_count}")
    print(f"  - Дроби: {fraction_count}")
    print(f"  - Сокращение дробей: {reduce_fraction_count}")
    print(f"  - Текстовые задачи на доли: {part_word_count}")
    print(f"  - Найти целое по части: {whole_from_part_count}")
    print(f"  - Доля как дробь: {part_fraction_count}")
    print(f"  - Задачи на движение: {motion_count}")
    print(f"  - Упрощение выражений с x: {simplify_x_count}")
    print(f"  - Две неизвестные (текстовые): {two_unknowns_count}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Генератор заданий для босса (JSON)')
    parser.add_argument('--show-themes', action='store_true', help='Показать темы задач по типам и выйти')
    args = parser.parse_args()
    if args.show_themes:
        print_task_themes()
    else:
        main()
