"""个人中心测试。"""
from __future__ import annotations

from pages.base_page import allure


@allure.epic("AtomX 框架示例")
@allure.feature("个人中心")
@allure.story("用户资料")
class TestProfile:

    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("个人中心加载验证")
    def test_profile_load(self, app, profile_page):
        """个人中心加载测试"""
        with allure.step("打开个人中心"):
            profile_page.open()
            profile_page.wait_for_page_loaded()
        with allure.step("验证昵称存在"):
            nickname = profile_page.get_nickname()
            assert nickname, "昵称不应为空"
