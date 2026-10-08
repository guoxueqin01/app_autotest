"""ProfilePage — user profile page object."""
from __future__ import annotations

from pages.base_page import BasePage

try:
    import allure  # type: ignore
except ImportError:
    from pages.base_page import allure


@allure.feature("个人中心")
@allure.story("用户资料")
class ProfilePage(BasePage):
    """个人中心页面对象"""

    page_name = "个人中心"
    PACKAGE = "com.example.app"
    ACTIVITY = ".ProfileActivity"

    AVATAR = {"id": "avatar"}
    NICKNAME = {"id": "nickname"}
    SETTINGS_BUTTON = {"desc": "设置"}
    LOGOUT_BUTTON = {"text": "退出登录"}

    def wait_for_page_loaded(self) -> None:
        self.wait_for_visible(self.NICKNAME)

    def get_nickname(self) -> str:
        return self.get_text(self.NICKNAME)

    @allure.step("打开设置")
    def open_settings(self) -> None:
        self.tap(self.SETTINGS_BUTTON)

    @allure.step("退出登录")
    def logout(self) -> None:
        self.tap(self.LOGOUT_BUTTON)

    @allure.step("验证昵称")
    def assert_nickname(self, expected: str) -> None:
        self.assert_text_equals(self.NICKNAME, expected)
