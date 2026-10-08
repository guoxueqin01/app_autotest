"""LoginPage — login screen page object."""
from __future__ import annotations

from pages.base_page import BasePage

try:
    import allure  # type: ignore
except ImportError:
    from pages.base_page import allure


@allure.feature("登录功能")
@allure.story("用户登录")
class LoginPage(BasePage):
    """登录页面对象"""

    page_name = "登录页"
    PACKAGE = "com.example.app"
    ACTIVITY = ".MainActivity"

    # Locators — semantic so they translate to all platforms
    USERNAME_INPUT = {"id": "username"}
    PASSWORD_INPUT = {"id": "password"}
    LOGIN_BUTTON = "登录"
    REMEMBER_SWITCH = {"desc": "记住我"}
    ERROR_MESSAGE = {"id": "error_msg"}

    # --- Navigation ---

    def open(self) -> None:
        super().open()
        self.wait_for_page_loaded()

    def wait_for_page_loaded(self) -> None:
        self.wait_for_visible(self.USERNAME_INPUT)
        self.wait_for_visible(self.PASSWORD_INPUT)
        self.wait_for_visible(self.LOGIN_BUTTON)

    # --- Actions ---

    @allure.step("输入用户名: {username}")
    def fill_username(self, username: str) -> "LoginPage":
        self.fill(self.USERNAME_INPUT, username)
        return self

    @allure.step("输入密码")
    def fill_password(self, password: str) -> "LoginPage":
        self.fill(self.PASSWORD_INPUT, password)
        return self

    @allure.step("点击登录")
    def click_login(self) -> "LoginPage":
        self.tap(self.LOGIN_BUTTON)
        return self

    @allure.step("执行登录: {username}")
    def login(self, username: str, password: str, remember: bool = False) -> "LoginPage":
        self.fill_username(username)
        self.fill_password(password)
        if remember:
            self.tap(self.REMEMBER_SWITCH)
        self.click_login()
        return self

    # --- Assertions ---

    @allure.step("验证登录成功")
    def should_login_success(self) -> None:
        self.assert_visible("首页")

    @allure.step("验证登录失败: {expected_error}")
    def should_show_error(self, expected_error: str) -> None:
        self.assert_visible(self.ERROR_MESSAGE)
        self.assert_text_contains(self.ERROR_MESSAGE, expected_error)
