"""订单详情测试。"""
from __future__ import annotations

import pytest

from pages.base_page import allure


@allure.epic("AtomX 框架示例")
@allure.feature("订单功能")
@allure.story("订单详情")
class TestOrderDetail:

    @pytest.mark.regression
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("订单详情状态验证")
    def test_order_detail_status(self, app, order_detail_page):
        """订单详情状态测试"""
        with allure.step("打开订单详情"):
            order_detail_page.open()
            order_detail_page.wait_for_page_loaded()
        with allure.step("获取状态"):
            status = order_detail_page.get_status()
        with allure.step(f"验证状态: {status}"):
            order_detail_page.assert_status(status)
