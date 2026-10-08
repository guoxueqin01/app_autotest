"""代码生成器常量定义。

包含三大部分：
1. UNIFIED_TYPES: 三大平台的原生控件 -> 统一元素类型（Android / iOS / HarmonyOS）
2. UNIFIED_ATTR_MAP: 三大平台属性键 -> 统一字段名（resource_id / text / content_desc / class ...）
3. TYPE_TO_ACTION / TYPE_TO_MODEL: 生成 Page 语义化方法 + Model 字段时使用的映射
"""
from __future__ import annotations

from typing import Dict, List

# ================================================================
# 1. 元素类型（细化：新增 image/scroll_view/navigation_bar/tab/progress/slider/label）
# ================================================================
UNIFIED_TYPES: Dict[str, List[str]] = {
    "button": [
        # Android
        "Button", "Button2",
        # iOS (XCUITest identifier / class chain)
        "XCUIElementButton", "XCUIElementTypeButton",
        # HarmonyOS (uitest dump)
        "Button", "CustomButton",
    ],
    "text": [
        "TextView", "StaticText", "Text",
        "UILabel", "XCUIElementTypeStaticText",
        "Text", "StaticText",
    ],
    "input": [
        "EditText",
        "UITextField", "XCUIElementTypeTextField", "XCUIElementTypeSecureTextField",
        "TextInput", "Edit",
    ],
    "password_input": [
        "XCUIElementTypeSecureTextField",
    ],
    "image": [
        "ImageView", "Image",
        "UIImageView", "XCUIElementTypeImage",
        "Image", "Picture",
    ],
    "checkbox": [
        "CheckBox",
        "XCUIElementTypeCheckBox",
    ],
    "switch": [
        "Switch",
        "UISwitch", "XCUIElementTypeSwitch",
        "Toggle", "ToggleSwitch",
    ],
    "radio": [
        "RadioButton",
        "XCUIElementTypeRadio",
        "Radio", "RadioCheckBox",
    ],
    "list": [
        "RecyclerView", "ListView", "CollectionView", "ScrollView", "Table",
        "UITableView", "UICollectionView", "XCUIElementTypeTable",
        "List", "Recycler",
    ],
    "scroll_view": [
        "ScrollView", "HorizontalScrollView",
        "UIScrollView", "XCUIElementTypeScrollView",
        "Scroll",
    ],
    "list_item": [
        "ListItem", "Cell", "FrameLayout",
        "UITableViewCell", "UICollectionViewCell",
        "ListItem",
    ],
    "tab": [
        "TabItem", "TabView",
        "UITabButton", "XCUIElementTypeTab",
        "Tab", "Tabs",
    ],
    "navigation_bar": [
        "ActionBar", "Toolbar",
        "UINavigationBar", "XCUIElementTypeNavigationBar",
        "Navigation", "TitleBar",
    ],
    "progress": [
        "ProgressBar", "ProgressBarHorizontal",
        "UIActivityIndicatorView", "XCUIElementTypeActivityIndicator",
        "Loading", "Progress",
    ],
    "slider": [
        "SeekBar",
        "UISlider", "XCUIElementTypeSlider",
        "Slider",
    ],
    "spinner": [
        "Spinner", "AutoCompleteTextView",
        "UIPickerView", "XCUIElementTypePicker",
        "Picker", "Select",
    ],
    "label": [
        "Label", "Title",
        "UILabel",
    ],
    "dialog": [
        "Window", "Dialog", "PopupWindow",
        "UIAlertController", "XCUIElementTypeSheet",
        "Dialog", "Popup", "Alert",
    ],
    "date_picker": [
        "DatePicker", "TimePicker",
        "UIDatePicker", "XCUIElementTypeDatePicker",
        "DatePicker",
    ],
    "container": [
        "LinearLayout", "RelativeLayout", "ConstraintLayout",
        "UIStackView",
        "Stack", "StackPanel",
    ],
}

# ================================================================
# 2. 属性映射 — 三大平台的属性键 -> 统一字段名
# ================================================================
# 输入属性键 (dump 后 xml/json 里出现的)  ->  统一字段名
UNIFIED_ATTR_MAP: Dict[str, str] = {
    # Android (uiautomator2 / dumpsys window)
    "resource-id": "resource_id",
    "text": "text",
    "content-desc": "content_desc",
    "class": "raw_class",
    "package": "package",
    "checkable": "checkable",
    "checked": "checked",
    "clickable": "clickable",
    "enabled": "enabled",
    "focusable": "focusable",
    "focused": "focused",
    "scrollable": "scrollable",
    "selected": "selected",
    "visible-to-user": "visible_to_user",
    "bounds": "bounds",
    # iOS (WDA / source json)
    "identifier": "resource_id",
    "name": "resource_id",
    "label": "text",
    "value": "text",
    "type": "raw_class",
    "traits": "traits",
    # HarmonyOS (uitest dump)
    "id": "resource_id",
    "description": "content_desc",
    "help": "content_desc",
    "role": "raw_class",
}

# ================================================================
# 3. 语义化方法生成 — 不同类型对应 Page Object 里生成的方法
# ================================================================
TYPE_TO_ACTION: Dict[str, str] = {
    "button": "tap",
    "checkbox": "check",
    "switch": "check",
    "radio": "check",
    "input": "input_text",
    "password_input": "input_password",
    "text": "get_text",
    "label": "get_text",
    "image": "tap",
    "list_item": "tap",
    "list": "scroll_to",
    "scroll_view": "scroll",
    "tab": "tap",
    "navigation_bar": "tap",
    "progress": "wait_disappear",
    "slider": "set_slider",
    "spinner": "select_item",
    "date_picker": "select_date",
    "dialog": "dismiss",
    "container": "is_displayed",
}

# ================================================================
# 4. Model 字段生成 — 类型 -> Python 类型 & 默认值
# ================================================================
TYPE_TO_MODEL_FIELD: Dict[str, tuple] = {
    "button": ("bool", False),       # 是否点击
    "checkbox": ("bool", False),     # 目标状态
    "switch": ("bool", False),
    "radio": ("bool", False),
    "input": ("str", ""),
    "password_input": ("str", ""),
    "text": ("str", ""),
    "label": ("str", ""),
    "image": ("str", ""),
    "list": ("str", ""),
    "list_item": ("str", ""),
    "scroll_view": ("str", ""),
    "tab": ("str", ""),
    "navigation_bar": ("str", ""),
    "progress": ("bool", False),
    "slider": ("float", 0.5),
    "spinner": ("str", ""),
    "date_picker": ("str", ""),
    "dialog": ("bool", False),
    "container": ("bool", True),
}

# ================================================================
# 5. 中文命名词表 — 用于生成 display_name 与语义字段
# ================================================================
CN_LABEL_MAP: Dict[str, str] = {
    "login": "登录", "register": "注册", "password": "密码", "username": "用户名",
    "phone": "手机号", "email": "邮箱", "submit": "提交", "cancel": "取消",
    "confirm": "确认", "save": "保存", "delete": "删除", "edit": "编辑",
    "add": "添加", "search": "搜索", "share": "分享", "settings": "设置",
    "profile": "个人中心", "home": "首页", "tab_home": "首页Tab",
    "tab_message": "消息Tab", "tab_me": "我的Tab",
    "loading": "加载中", "toast": "提示", "error": "错误", "success": "成功",
    "upload": "上传", "download": "下载", "next": "下一步", "previous": "上一步",
    "finish": "完成", "skip": "跳过", "retry": "重试", "back": "返回",
    "close": "关闭", "open": "打开", "view": "查看", "buy": "购买",
    "pay": "支付", "cart": "购物车", "coupon": "优惠券",
}

# ================================================================
# 6. 平台列表
# ================================================================
SUPPORTED_PLATFORMS = ("android", "ios", "harmony")

# ================================================================
# 7. 定位器类型优先级 — 用于生成 fallback 链
# ================================================================
LOCATOR_TYPE_PRIORITY = ["resource_id", "text", "desc", "class_text", "xpath", "image"]
