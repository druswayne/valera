# -*- coding: utf-8 -*-
"""
Фильтр ненормативной лексики по списку из ban.txt.
Используется в чатах: клан, администратор, PvP арена, поиск клана.
"""
import os
import re

_BAN_FILE = os.path.join(os.path.dirname(__file__), 'ban.txt')
_regex_patterns = []
_literal_words = []
_loaded = False


def _load_ban_list():
    global _regex_patterns, _literal_words, _loaded
    if _loaded:
        return
    _loaded = True
    if not os.path.isfile(_BAN_FILE):
        return
    regex_meta = set(r'\[]()*+?{}|^$.')
    with open(_BAN_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Пробуем скомпилировать как regex
            try:
                if any(c in line for c in regex_meta) or '\\' in line:
                    p = re.compile(line, re.IGNORECASE | re.UNICODE)
                    _regex_patterns.append(p)
                else:
                    _literal_words.append(line)
            except re.error:
                _literal_words.append(line)
    # Сначала заменяем длинные слова, чтобы "блядь" не превратилась в "*дь" после "бля"
    _literal_words.sort(key=len, reverse=True)


def filter_chat_text(text):
    """
    Заменяет в тексте все вхождения слов/паттернов из ban.txt:
    каждая буква матерного слова заменяется на '*', например сука -> ****.
    Возвращает отфильтрованную строку.
    """
    if not text:
        return text
    _load_ban_list()
    result = text
    for p in _regex_patterns:
        result = p.sub(lambda m: '*' * len(m.group(0)), result)
    for word in _literal_words:
        if len(word) == 0:
            continue
        replacement = '*' * len(word)
        result = re.sub(re.escape(word), replacement, result, flags=re.IGNORECASE)
    return result
