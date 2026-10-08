"""HomePage — 首页操作页面对象 (从 profile 拆出)。"""
from __future__ import annotations

from pages.base_page import BasePage

try:
    import allure  # type: ignore
except ImportError:
    from pages.base_page import allure


@allure.feature("首页功能")
@allure.story("首页操作")
class HomePage(BasePage):
    """首页页面对象"""

    page_name = "首页"
    PACKAGE = "com.example.app"
    ACTIVITY = ".MainActivity"

    SEARCH_ENTRY = "搜索"
    PROFILE_ENTRY = "我的"
    LOGOUT_BUTTON = "退出登录"
    CONFIRM_BUTTON = "确认"

    def wait_for_page_loaded(self) -> None:
        self.wait_for_text("首页")

    @allure.step("点击搜索入口")
    def go_search(self) -> None:
        self.tap(self.SEARCH_ENTRY)

    @allure.step("打开个人中心")
    def go_profile(self) -> None:
        self.tap(self.PROFILE_ENTRY)

    @allure.step("退出登录")
    def logout(self) -> None:
        self.tap(self.PROFILE_ENTRY)
        self.tap(self.LOGOUT_BUTTON)
        self.tap(self.CONFIRM_BUTTON)
