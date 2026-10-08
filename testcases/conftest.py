"""Testcase-level conftest: shared fixtures for app tests."""
from __future__ import annotations

from typing import Any

import pytest

from atomx import AtomX
from pages.login import LoginPage
from pages.order import OrderDetailPage, OrderListPage
from pages.profile import ProfilePage
from pages.home import HomePage


@pytest.fixture
def login_page(app: AtomX) -> LoginPage:
    return LoginPage(app)


@pytest.fixture
def order_list_page(app: AtomX) -> OrderListPage:
    return OrderListPage(app)


@pytest.fixture
def order_detail_page(app: AtomX) -> OrderDetailPage:
    return OrderDetailPage(app)


@pytest.fixture
def profile_page(app: AtomX) -> ProfilePage:
    return ProfilePage(app)


@pytest.fixture
def home_page(app: AtomX) -> HomePage:
    return HomePage(app)


# ==================== Data fixtures ====================

@pytest.fixture(scope="session")
def data_provider():
    """Session 级数据提供者"""
    from atomx.infra.data.provider import DataProvider
    return DataProvider()


@pytest.fixture(scope="function")
def test_data(request: Any, data_provider):
    """Function 级测试数据 — 用例标记 @pytest.mark.data("login_data.yaml") 自动加载"""
    marker = request.node.get_closest_marker("data")
    if marker:
        filename = marker.args[0]
        key = marker.kwargs.get("key")
        return data_provider.load(filename, key)
    return None
