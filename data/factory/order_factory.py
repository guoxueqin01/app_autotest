"""订单数据工厂 — 动态生成随机订单测试数据。"""
from __future__ import annotations

import random
import string


def generate(**kwargs) -> dict:
    """生成随机订单数据"""
    order_id = ''.join(random.choices(string.digits, k=10))
    data = {
        "order_id": f"ORD{order_id}",
        "amount": round(random.uniform(10.0, 9999.0), 2),
        "status": random.choice(["待支付", "已支付", "已发货", "已完成", "已取消"]),
    }
    data.update(kwargs)
    return data
