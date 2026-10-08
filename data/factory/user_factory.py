"""用户数据工厂 — 动态生成随机用户测试数据。"""
from __future__ import annotations

import random
import string


def generate(**kwargs) -> dict:
    """生成随机用户数据

    可覆盖默认值: generate(username="custom", email="custom@test.com")
    """
    random_name = ''.join(random.choices(string.ascii_lowercase, k=8))
    data = {
        "username": f"user_{random_name}",
        "password": "Test@1234",
        "email": f"{random_name}@test.com",
    }
    data.update(kwargs)
    return data
