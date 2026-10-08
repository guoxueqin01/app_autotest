"""iOS 专属登录场景 — Face ID 授权等。"""
from __future__ import annotations

import pytest

from pages.base_page import allure


@pytest.mark.ios
@pytest.mark.login
class TestIOSLogin:
    """iOS 专属登录场景"""

    @pytest.mark.smoke
    @allure.feature("登录功能")
    @allure.story("Face ID 授权")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("Face ID 授权登录")
    def test_face_id_auth(self, app):
        """iOS 独有: Face ID 授权"""
        with allure.step("点击 Face ID"):
            app.find("Face ID").tap()
        with allure.step("验证授权结果"):
            app.assert_.exists("已验证")
