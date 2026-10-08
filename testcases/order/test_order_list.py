"""订单列表测试。"""
from __future__ import annotations

import pytest

from pages.base_page import allure
from models.order import OrderListPageData
from utils.data_loader import load_cases_as


DATA_FILE = "data/yaml/order_data.yaml"
CASES = load_cases_as(DATA_FILE, OrderListPageData)


@allure.epic("AtomX 框架示例")
@allure.feature("订单功能")
@allure.story("订单列表")
class TestOrderList:

    @pytest.mark.parametrize("case", CASES, ids=[c.case for c in CASES])
    @pytest.mark.smoke
    def test_order_list(self, app, order_list_page, case: OrderListPageData):
        """订单列表测试"""
        with allure.step("打开订单列表"):
            order_list_page.open()
            order_list_page.wait_for_page_loaded()

        if case.keyword:
            with allure.step(f"搜索: {case.keyword}"):
                order_list_page.search(case.keyword)
        else:
            with allure.step("等待加载完成"):
                order_list_page.wait_for_page_loaded()

        with allure.step(f"验证行数: {case.expected_rows}"):
            order_list_page.assert_row_count(case.expected_rows)
