# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict

_coder3_state: Dict[int, Dict] = {}


def set_state(chat_id: int, **kwargs):
    bucket = _coder3_state.setdefault(chat_id, {})
    bucket.update(kwargs)
    return bucket


def get_state(chat_id: int) -> Dict:
    return _coder3_state.get(chat_id, {})


def clear_state(chat_id: int):
    _coder3_state.pop(chat_id, None)
