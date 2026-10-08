"""iOS 专属搜索场景。"""
from __future__ import annotations

import pytest

from pages.base_page import allure


@pytest.mark.ios
@pytest.mark.search
class TestIOSSearch:
    """iOS 专属搜索场景"""

    @pytest.mark.regression
    @allure.feature("搜索功能")
    @allure.story("搜索历史")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("iOS 搜索历史记录")
    def test_search_history(self, app):
        """iOS 专属搜索历史验证"""
        with allure.step("点击搜索"):
            app.find("搜索").tap()
        with allure.step("点击历史记录"):
            app.find("历史记录").tap()
        with allure.step("验证最近搜索"):
            app.assert_.exists("最近搜索")
