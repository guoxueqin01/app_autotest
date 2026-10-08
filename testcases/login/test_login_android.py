"""Android 专属登录场景 — 手势密码等。"""
from __future__ import annotations

import pytest

from pages.base_page import allure


@pytest.mark.android
@pytest.mark.login
class TestAndroidLogin:
    """Android 专属登录场景"""

    @pytest.mark.regression
    @allure.feature("登录功能")
    @allure.story("手势密码")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("手势密码登录")
    def test_gesture_password(self, app):
        """Android 独有: 手势密码"""
        with allure.step("点击手势密码"):
            app.find("手势密码").tap()
        with allure.step("验证手势密码结果"):
            app.assert_.exists("验证成功")
