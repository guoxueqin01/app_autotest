"""OrderDetailPage — page object for order detail screen."""
from __future__ import annotations

from pages.base_page import BasePage


class OrderDetailPage(BasePage):
    PACKAGE = "com.example.app"
    ACTIVITY = ".OrderDetailActivity"

    ORDER_ID_LABEL = {"id": "order_id"}
    ORDER_TOTAL = {"id": "order_total"}
    STATUS_BADGE = {"id": "order_status"}
    CANCEL_BUTTON = {"text": "取消订单"}
    PAY_BUTTON = {"text": "立即支付"}
    BACK_BUTTON = {"desc": "返回"}

    def wait_for_page_loaded(self) -> None:
        self.wait_for_visible(self.ORDER_ID_LABEL)

    def get_order_id(self) -> str:
        return self.get_text(self.ORDER_ID_LABEL)

    def get_order_total(self) -> str:
        return self.get_text(self.ORDER_TOTAL)

    def get_status(self) -> str:
        return self.get_text(self.STATUS_BADGE)

    def click_cancel(self) -> None:
        self.tap(self.CANCEL_BUTTON)

    def click_pay(self) -> None:
        self.tap(self.PAY_BUTTON)

    def go_back(self) -> None:
        self.tap(self.BACK_BUTTON)

    def assert_status(self, expected: str) -> None:
        self.assert_text_equals(self.STATUS_BADGE, expected)
