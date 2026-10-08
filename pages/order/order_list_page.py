"""OrderListPage — page object with list/table row operations."""
from __future__ import annotations

from atomx.engine.control.element import Element, ElementNotFoundError
from pages.base_page import BasePage


class OrderListPage(BasePage):
    """Order list page with list row helpers."""

    PACKAGE = "com.example.app"
    ACTIVITY = ".OrderListActivity"

    LIST_CONTAINER = {"class": "list"}
    LIST_ITEM = {"class": "list_item"}

    SEARCH_INPUT = {"id": "search_input"}
    SEARCH_BUTTON = {"id": "search_btn"}

    ITEM_TITLE = {"id": "item_title"}
    ITEM_STATUS = {"id": "item_status"}
    ITEM_DETAIL_BUTTON = {"text": "详情"}
    ITEM_EDIT_BUTTON = {"text": "编辑"}
    ITEM_DELETE_BUTTON = {"text": "删除"}

    LOAD_MORE_TEXT = "加载更多"
    NO_MORE_TEXT = "没有更多了"

    def wait_for_page_loaded(self) -> None:
        self.wait_for_visible(self.LIST_CONTAINER)

    # --- Row operations ---

    def get_row_count(self) -> int:
        return len(self.find_all(self.LIST_ITEM))

    def get_row(self, row_index: int = 0) -> Element:
        items = self.find_all(self.LIST_ITEM)
        if row_index >= len(items):
            raise IndexError(f"Row index out of range: {row_index} (only {len(items)} rows)")
        return items[row_index]

    def get_row_title(self, row_index: int = 0) -> str:
        return self.get_row(row_index).find(self.ITEM_TITLE).text

    def get_row_status(self, row_index: int = 0) -> str:
        return self.get_row(row_index).find(self.ITEM_STATUS).text

    def click_row_action(self, row_index: int, action: str) -> None:
        action_map = {
            "detail": self.ITEM_DETAIL_BUTTON,
            "edit": self.ITEM_EDIT_BUTTON,
            "delete": self.ITEM_DELETE_BUTTON,
        }
        locator = action_map.get(action)
        if not locator:
            raise ValueError(f"Unsupported action: {action}")
        self.get_row(row_index).find(locator).tap()

    def find_row_by_title(self, title: str) -> int:
        count = self.get_row_count()
        for i in range(count):
            if self.get_row_title(i) == title:
                return i
        return -1

    def scroll_to_row(self, row_index: int) -> None:
        while self.get_row_count() <= row_index:
            self.swipe("up")

    def pull_refresh(self) -> None:
        self.app.swipe("down")
        self.wait_for_page_loaded()

    # --- Search ---

    def search(self, keyword: str) -> None:
        self.fill(self.SEARCH_INPUT, keyword)
        self.tap(self.SEARCH_BUTTON)
        self.wait_for_page_loaded()

    # --- Assertions ---

    def assert_row_count(self, count: int) -> None:
        self.assert_count(self.LIST_ITEM, count)

    def assert_no_more(self) -> None:
        self.assert_visible(self.NO_MORE_TEXT)
