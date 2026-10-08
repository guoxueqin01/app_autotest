"""搜索测试 — 跨平台通用。"""
from __future__ import annotations

import pytest

from pages.base_page import allure


@allure.epic("AtomX 框架示例")
@allure.feature("搜索功能")
class TestSearch:

    @allure.story("关键词搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("搜索关键词: {keyword}")
    @pytest.mark.smoke
    @pytest.mark.search
    @pytest.mark.parametrize("keyword", ["手机", "电脑", "耳机", "键盘", "鼠标"])
    def test_search_keyword(self, app, keyword):
        """参数化搜索测试"""
        with allure.step("点击搜索入口"):
            app.find("搜索").tap()

        with allure.step(f"输入搜索词: {keyword}"):
            app.find({"id": "search_box"}).input_text(keyword)

        with allure.step("点击搜索按钮"):
            app.find("搜索").tap()

        with allure.step("验证搜索结果"):
            app.assert_.exists("搜索结果")

        with allure.step("附加搜索结果截图"):
            screenshot = app.driver.screenshot()
            allure.attach(screenshot, name=f"搜索结果_{keyword}",
                          attachment_type=allure.attachment_type.PNG)
