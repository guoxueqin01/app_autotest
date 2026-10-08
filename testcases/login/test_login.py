"""Cross-platform login testcases."""
from __future__ import annotations

import pytest

try:
    import allure  # type: ignore
except ImportError:
    allure = None  # type: ignore

from models.login import LoginPageData
from pages.base_page import allure as _allure
from utils.data_loader import load_cases_as


DATA_FILE = "data/yaml/login_data.yaml"
CASES = load_cases_as(DATA_FILE, LoginPageData)
IDS = [c.case for c in CASES]


@_allure.epic("AtomX 框架示例")
@_allure.feature("登录功能")
@_allure.story("正常登录流程")
class TestLogin:

    @pytest.mark.smoke
    @pytest.mark.login
    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_login(self, app, login_page, case: LoginPageData):
        """三平台通用登录流程"""
        _allure.dynamic.title(f"登录: {case.case}")
        with _allure.step("启动应用"):
            app.start_app("com.example.app", ".MainActivity")

        with _allure.step("等待登录页加载"):
            login_page.wait_for_page_loaded()

        with _allure.step(f"执行登录: {case.username}"):
            login_page.login(case.username, case.password, remember=case.remember)

        with _allure.step("验证结果"):
            if case.expected_error:
                login_page.should_show_error(case.expected_error)
            else:
                login_page.should_login_success()
