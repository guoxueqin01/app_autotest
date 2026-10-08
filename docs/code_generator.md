# AtomX 代码生成器方案

> 目标：把 UI 树扫描、元素分析、流程建模、配置合并和代码渲染串成一套可落地、可人工干预、可跨平台复用的代码生成体系。

---

## 1. 设计目标

### 1.1 需要解决的问题

代码生成器不只是“扫描页面、生成 Page Object”，它要覆盖完整链路：

1. **自动探测页面结构与元素**
2. **识别元素类型与交互意图**
3. **推导单页多步骤 / 多页多步骤流程**
4. **生成可人工修改的配置文件**
5. **支持自动配置 + 人工配置合并**
6. **渲染 Page Object、Models、Test Flow、测试用例**

### 1.2 设计原则

- **平台差异下沉**：生成器输出统一语义，运行时由 LocatorAdapter 翻译到 Android / iOS / HarmonyOS
- **配置优先**：先生成配置，再生成代码，方便人工修正和版本管理
- **自动化与人工协同**：自动探测不是最终答案，允许人工覆盖和增补
- **可增量生成**：支持只生成页面、只生成流程、只生成用例
- **可追溯**：配置中保留来源、置信度、生成时间、原始属性

---

## 2. 适用范围

### 2.1 覆盖范围

- Android / iOS / HarmonyOS 三平台
- 单页面操作、单页面多步骤、多页面多步骤
- 列表 / 表格行操作
- checkbox / radio 模板化
- 输入、选择、点击、断言、弹窗处理、条件分支

### 2.2 不覆盖范围

- 复杂业务编排 DSL
- 可视化低代码 IDE
- 跨端性能回归专项分析

---

## 3. 总体架构

```text
┌──────────────────────────────────────────────────────────────┐
│                         输入层                                │
│  UI Tree / 运行时截图 / 人工配置 / 历史执行结果                │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. Detector                                                    │
│    - 平台探测 / 元素归一化 / 属性标准化 / 置信度估算          │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Analyzer                                                    │
│    - 元素分类 / 角色识别 / 交互识别 / 列表识别 / 弹窗识别    │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. FlowBuilder                                                  │
│    - 单页流程 / 跨页流程 / 条件分支 / 状态跳转                │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. ConfigResolver                                               │
│    - 自动配置 + 人工配置合并 / 继承 / 冲突处理                │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. CodeGenerator                                                  │
│    - 渲染 Page Object / Models / Test Flow / Data Provider     │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
        pages/  models/  testcases/  data/
```

---

## 4. 平台兼容性设计

### 4.1 统一语义层

生成器对外只输出统一语义，不暴露平台原始 class。

统一语义类型：

- `button`
- `input`
- `textarea`
- `checkbox`
- `radio`
- `text`
- `list`
- `list_item`
- `dialog`
- `container`
- `action`

统一语义属性：

- `text`
- `id`
- `desc`
- `class`
- `clickable`
- `enabled`
- `checked`
- `visible`
- `role`
- `bounds`
- `parent`
- `confidence`
- `source`

### 4.2 平台映射表

| 统一类型 | Android | iOS | HarmonyOS |
|---|---|---|---|
| button | Button | Button | Button |
| input | EditText | TextField | TextInput |
| textarea | EditText | TextView | TextInput |
| checkbox | CheckBox | Switch | Toggle |
| radio | RadioButton | RadioButton | Radio |
| text | TextView | StaticText | Text |
| list | RecyclerView | CollectionView | List |
| list_item | RecyclerView | Cell | ListItem |
| dialog | AlertDialog | Alert | Dialog |

### 4.3 定位器翻译

生成器只生成统一语义定位器：

```python
{"text": "登录", "class": "button"}
{"id": "username", "class": "input"}
```

运行时由 LocatorAdapter 负责翻译：

- `class: "button"` -> Android `Button` / iOS `Button` / Harmony `Button`
- `class: "checkbox"` -> Android `CheckBox` / iOS `Switch` / Harmony `Toggle`
- `class: "input"` -> Android `EditText` / iOS `TextField` / Harmony `TextInput`

### 4.4 平台差异归一化

Detector 需要处理以下差异：

1. **UI 树格式差异**
   - Android：XML
   - iOS：XML / JSON
   - HarmonyOS：JSON -> XML

2. **属性名差异**
   - Android：`text` / `resource-id` / `content-desc` / `class`
   - iOS：`label` / `name` / `help` / `type`
   - Harmony：`text` / `id` / `description` / `type`

3. **坐标格式差异**
   - Android：`[x1,y1][x2,y2]`
   - iOS：`{x,y,width,height}`
   - Harmony：JSON rect / bounds

4. **元素命名差异**
   - iOS 常见语义标签
   - Android 常见资源 ID
   - Harmony 常见 accessibilityId

---

## 5. 输出配置模型

> 配置结构参照 `web_quality_ui_playwright/` 的自动生成配置风格：文件头放页面元信息，下面直接是容器/弹窗/页面流程 key，每个 key 下放 `cascade_fields` 或 `steps`。

### 5.1 配置文件命名规则

每个页面默认只保留一份通用配置文件，不按平台拆三份配置：

- `xx_auto_config.yaml`：检测器自动生成的配置，作为默认输入
- `xx_manual_config.yaml`：人工修正后的配置，用于覆盖自动配置中的错误、补充步骤、补充断言

示例：

```text
config/detect_config/
├── login_auto_config.yaml
├── login_manual_config.yaml
├── order_list_auto_config.yaml
└── order_list_manual_config.yaml
```

### 5.2 平台差异处理规则

默认使用**同一份配置承载多平台**，只有配置字段内部做平台覆盖：

- `platform: all` 表示三平台通用
- 如果页面有平台差异，就在元素里写 `platforms` 标记适用范围
- 如果元素相同但定位器不同，就在元素里写 `locator_overrides`
- 只有页面本身是平台独占功能时，才单独拆出平台配置文件

### 5.3 App 架构识别规则

生成器要识别 App 架构 / 技术栈，但不要把生成器拆成多套实现。  
统一生成器内部通过 `app_architecture` 选择探测与定位器生成策略。

建议规则：

- `app_architecture` 只影响 **探测器** 和 **定位器生成**
- 不影响统一的配置模型
- 不影响 Page Object / Models 的最终输出结构

可识别的架构类型：

- `native`：原生 App
- `react_native`：React Native
- `flutter`：Flutter
- `webview`：WebView / H5 容器
- `hybrid`：混合架构

示例：

```yaml
page_name: login
platform: all
app_architecture: native
url_path: /login

platform_info:
  android:
    package: com.example.app
    activity: .MainActivity
  ios:
    bundle_id: com.example.app
    app: 示例App
  harmony:
    bundle_name: com.example.app
    ability: EntryAbility
```

若同一套 App 在不同平台使用不同技术栈，可按平台写：

```yaml
app_architecture:
  android: react_native
  ios: flutter
  harmony: native
```

#### 5.3.1 架构差异影响范围

架构差异只允许影响以下 3 点：

1. **UI 树解析方式**
   - Android 原生 XML
   - iOS / HarmonyOS XML 或 JSON
   - React Native / Flutter 语义节点
   - WebView DOM 树

2. **元素属性映射**
   - 原生控件属性
   - accessibility 属性
   - testID / semantics / role

3. **定位器生成优先级**
   - 原生 Android 优先 `resource-id`
   - React Native 优先 `testID` 或 `text`
   - Flutter 优先 semantics / 文本 / 语义节点
   - WebView 优先 CSS / role

### 5.4 配置文件总体结构

```yaml
page_name: login
platform: all
url_path: /login
created_at: "2026-09-23 10:00:00"
platform_info:
  android:
    package: com.example.app
    activity: .MainActivity
  ios:
    bundle_id: com.example.app
    app: 示例App
  harmony:
    bundle_name: com.example.app
    ability: EntryAbility

login:
  button_name: 登录
  cascade_fields:
  - const_name: USERNAME_INPUT
    element_type: input
    label: 用户名
    selector: text:用户名
    locator:
      text: 用户名
      class: input
    locator_overrides:
      android: 'com.example.app:id/username'
      ios: 'username'
      harmony: 'username'
    options: []
    trigger_option: ''
    cascade_result_elements: []
  - const_name: PASSWORD_INPUT
    element_type: input
    label: 密码
    selector: text:密码
    locator:
      text: 密码
      class: input
    locator_overrides:
      android: 'com.example.app:id/password'
      ios: 'password'
      harmony: 'password'
    options: []
    trigger_option: ''
    cascade_result_elements: []
  - const_name: AGREEMENT_CHECKBOX
    element_type: checkbox
    label: 我已阅读并同意协议
    selector: text:我已阅读并同意协议
    locator:
      text: 我已阅读并同意协议
      class: checkbox
    locator_overrides:
      android: 'com.example.app:id/agreement_checkbox'
      ios: 'agreement_checkbox'
      harmony: 'agreement_checkbox'
    options: []
    trigger_option: ''
    cascade_result_elements: []
  - const_name: LOGIN_BUTTON
    element_type: button
    label: 登录
    selector: text:登录
    locator:
      text: 登录
      class: button
    locator_overrides:
      android: 'com.example.app:id/btn_login'
      ios: 'loginButton'
      harmony: 'btn_login'
    options: []
    trigger_option: ''
    cascade_result_elements: []

login_flow:
  button_name: 登录流程
  steps:
    - step_name: open_login_page
      action: open
      page: login
    - step_name: input_username
      action: fill
      element: USERNAME_INPUT
      value: "${username}"
    - step_name: input_password
      action: fill
      element: PASSWORD_INPUT
      value: "${password}"
    - step_name: check_agreement
      action: check
      element: AGREEMENT_CHECKBOX
    - step_name: tap_login
      action: tap
      element: LOGIN_BUTTON
    - step_name: verify_home
      action: assert_exists
      element: HOME_TITLE
```

### 5.5 部分元素平台差异时如何生成配置

如果一个页面三平台中只有部分元素不一样，仍然生成**同一份配置文件**，不要拆成三份。  
差异元素统一放在同一个 `cascade_fields` 里，用 `platforms` 标记元素适用范围：

- 三平台都有：不写 `platforms`，默认视为 `all`
- 某平台独有：写 `platforms: [ios]`
- 某平台不同：保留同一个 `const_name`，使用 `locator_overrides` 覆盖

示例：

```yaml
page_name: login
platform: all
url_path: /login

login:
  button_name: 登录
  cascade_fields:
  - const_name: USERNAME_INPUT
    element_type: input
    label: 用户名
    selector: text:用户名
    locator:
      text: 用户名
      class: input
    locator_overrides:
      android: 'com.example.app:id/username'
      ios: 'username'
      harmony: 'username'
    options: []
    trigger_option: ''
    cascade_result_elements: []
  - const_name: FACEID_LOGIN_BUTTON
    element_type: button
    label: Face ID 登录
    selector: text:Face ID
    locator:
      text: Face ID
      class: button
    platforms: [ios]
    options: []
    trigger_option: ''
    cascade_result_elements: []
  - const_name: FINGERPRINT_LOGIN_BUTTON
    element_type: button
    label: 指纹登录
    selector: text:指纹
    locator:
      text: 指纹
      class: button
    platforms: [android, harmony]
    options: []
    trigger_option: ''
    cascade_result_elements: []
  - const_name: AGREEMENT_CHECKBOX
    element_type: checkbox
    label: 我已阅读并同意协议
    selector: text:我已阅读并同意协议
    locator:
      text: 我已阅读并同意协议
      class: checkbox
    locator_overrides:
      android: 'com.example.app:id/agreement_checkbox'
      ios: 'agreement_checkbox'
      harmony: 'agreement_checkbox'
    options: []
    trigger_option: ''
    cascade_result_elements: []
```

规则解释：

1. **共有元素**：正常生成，不写 `platforms`
2. **单平台元素**：加 `platforms: [android|ios|harmony]`
3. **多平台差异定位器**：保留一个元素，用 `locator_overrides` 覆盖
4. **流程步骤**：如果步骤只适用于某平台，也在步骤上写 `platforms`

### 5.6 运行时读取规则

探测器 / 生成器读取配置时，必须遵守一条硬规则：

- **不要直接把 `locator_overrides` 当作定位器使用**
- **必须先知道当前平台，再只读取当前平台的值**

建议的解析顺序：

1. 读取 `platform`
2. 如果存在 `locator_overrides[current_platform]`，使用它
3. 否则回退到 `locator`
4. 再回退到默认语义定位器
5. 若仍失败，再走 fallback 定位器

示例伪代码：

```python
def get_locator(element: dict, platform: str):
    overrides = element.get("locator_overrides", {}) or {}
    if platform in overrides:
        return overrides[platform]
    return element.get("locator")
```

示例：当 `platform=android` 时，只读取：

```yaml
locator_overrides:
  android: 'com.example.app:id/username'
```

不会读取 iOS / HarmonyOS 的覆盖值。

### 5.7 人工配置覆盖示例

`login_manual_config.yaml` 只写需要人工修正、补充或覆盖的内容，未出现的字段继续沿用 `login_auto_config.yaml`。

```yaml
page_name: login
platform: all
url_path: /login

login:
  button_name: 登录
  cascade_fields:
  - const_name: USERNAME_INPUT
    element_type: input
    label: 用户名
    selector: text:用户名
    locator:
      text: 用户名
      class: input
    locator_overrides:
      android: 'com.example.app:id/username'
      ios: 'username'
      harmony: 'username'
    options: []
    trigger_option: ''
    cascade_result_elements: []
  - const_name: LOGIN_BUTTON
    element_type: button
    label: 登录
    selector: text:登录
    locator:
      text: 登录
      class: button
    locator_overrides:
      android: 'com.example.app:id/btn_login'
      ios: 'loginButton'
      harmony: 'btn_login'
    options: []
    trigger_option: ''
    cascade_result_elements: []

login_flow:
  button_name: 登录流程
  steps:
    - step_name: open_login_page
      action: open
      page: login
    - step_name: input_username
      action: fill
      element: USERNAME_INPUT
      value: "${username}"
    - step_name: input_password
      action: fill
      element: PASSWORD_INPUT
      value: "${password}"
    - step_name: check_agreement
      action: check
      element: AGREEMENT_CHECKBOX
    - step_name: tap_login
      action: tap
      element: LOGIN_BUTTON
    - step_name: verify_home
      action: assert_exists
      element: HOME_TITLE
```

---

## 6. 核心模块设计

### 6.1 Detector

职责：

1. 读取 UI 树
2. 读取平台信息
3. 归一化属性
4. 归一化坐标
5. 提取上下文文本
6. 生成分层页面结构
7. 执行交互级联探测
8. 生成统一元素模型
9. 估算置信度

关键能力：

- 平台原始属性到统一语义属性的映射
- bounds 跨平台解析
- 可见性、可点击、可编辑属性归一化
- 对相似元素做去重与聚类
- 输出置信度，方便人工审核

需要补齐的能力：

1. **上下文提取器**
   - 父级文本
   - 前后兄弟文本
   - label / placeholder / aria-label
   - 包装容器文本
   - 列表行上下文

2. **分层页面扫描**
   - 主页面区域
   - 搜索 / 筛选区域
   - 列表 / 表格区域
   - 弹窗 / 抽屉区域
   - 列表行区域

3. **交互级联探测**
   - 对 trigger 元素执行 click / fill / select
   - 探测新增元素
   - 探测不可见变可见元素
   - 探测列表 / 表格行数变化
   - 支持链式级联，限制最大深度

4. **弹窗 / 抽屉探测**
   - 按钮触发容器识别
   - 弹窗内元素扫描
   - 抽屉内元素扫描
   - 下拉菜单扫描

5. **会话 / 登录态恢复**
   - 登录态失效检测
   - 页面丢失恢复
   - 启动后状态恢复
   - 重新登录后继续探测

输出：

```json
{
  "page": "login",
  "platform": "android",
  "elements": [
    {
      "text": "登录",
      "id": "btn_login",
      "desc": "",
      "class": "button",
      "clickable": true,
      "enabled": true,
      "checked": false,
      "visible": true,
      "role": "button",
      "bounds": [10, 20, 100, 40],
      "parent": "container",
      "confidence": 0.96,
      "source": "auto"
    }
  ]
}
```

### 6.2 Analyzer

职责：

1. 元素分类
2. 角色识别
3. 业务语义推断
4. 列表识别
5. 弹窗识别
6. 控件组合识别
7. 元素命名生成
8. 元素去重与聚类

需要补齐的能力：

1. **细粒度元素类型**
   - input / password / number / date / time / file / upload
   - select / multi_select / select_search / cascader / tree_select
   - checkbox / checkbox_group / radio / radio_group / switch
   - button / submit / search_button / reset_button / confirm_button
   - pagination / pagination_item / pagination_options
   - table / list / list_item / row / cell
   - toast / alert / notification / empty / loading

2. **命名生成策略**
   - 中文文本转英文 key
   - 拼音兜底
   - 翻译缓存
   - 重名去重
   - 动态 id 过滤
   - 无语义元素降级命名

3. **唯一性判断**
   - id 唯一性
   - text 唯一性
   - desc 唯一性
   - locator 组合唯一性
   - 同一容器内重复元素去重

4. **字段类型推断**
   - str / bool / int / float
   - List[str] / Dict
   - 必填字段识别
   - 只读字段识别

示例规则：

- 输入框 + 登录按钮 -> 登录页
- 列表 + 多项操作 -> 列表页
- checkbox 组 -> 多选项页
- radio 组 -> 单选页
- 弹窗容器 + 确认按钮 -> dialog flow

### 6.3 FlowBuilder

职责：

1. 识别单页多步骤
2. 识别跨页跳转
3. 推断动作顺序
4. 标记等待条件
5. 标记断言点
6. 标记条件分支

#### 6.3.1 单页面多步骤

场景示例：

1. 输入用户名
2. 输入密码
3. 勾选协议
4. 点击登录
5. 等待跳转
6. 检查首页

#### 6.3.2 多页面多步骤

场景示例：

1. 登录页
2. 首页
3. 订单列表
4. 订单详情
5. 提交订单

#### 6.3.3 条件分支

- 登录失败 -> 错误提示页
- 点击提交 -> 成功页 / 校验失败页

### 6.4 ConfigResolver

职责：

1. 合并自动配置
2. 合并人工配置
3. 处理继承关系
4. 处理覆盖规则
5. 标记冲突字段

合并优先级：

1. 人工配置
2. 自动探测结果
3. 默认模板

### 6.5 CodeGenerator

职责：

1. 根据配置生成 Page Object
2. 根据配置生成 Models
3. 根据流程生成测试用例
4. 生成数据驱动文件
5. 输出增量变更说明

---

## 7. 生成策略

### 7.1 生成级别

建议支持 4 级生成：

1. **element-only**
   - 只生成页面元素与定位器

2. **page-only**
   - 生成 Page Object + Models

3. **flow-only**
   - 生成测试流程

4. **full**
   - 生成页面、模型、流程、数据文件

### 7.2 生成模式

- **auto**：全自动探测生成
- **semi**：自动探测 + 人工配置覆盖
- **manual**：只消费人工配置
- **merge**：自动 + 人工合并后再生成

---

## 8. 输出文件结构

```text
generated/
├── pages/
│   ├── login_page.py
│   └── order_list_page.py
├── models/
│   ├── login_models.py
│   └── order_list_models.py
├── flows/
│   ├── login_flow.py
│   └── order_flow.py
└── data/
    ├── login_data.yaml
    └── order_data.yaml
```

建议主工程结构保持不变：

```text
pages/
models/
testcases/
data/
script/generator/
```

生成结果可以写入：

- `generated/`：生成缓存与预览
- `pages/`：正式 Page Object
- `models/`：正式 Models
- `data/`：正式测试数据
- `testcases/`：正式测试用例

---

## 9. 配置生成与人工配置闭环

### 9.1 流程

1. 自动探测页面
2. 生成 `config/pages/{page}.yaml`
3. 人工检查并修改配置
4. 重新运行生成器
5. 生成器读取人工配置并覆盖自动结果
6. 渲染最终代码

### 9.2 人工配置能力

人工配置要支持：

- 修改元素命名
- 修改定位器优先级
- 增加备用定位器
- 修改等待时间
- 增加断言
- 删除误识别元素
- 补充流程步骤
- 调整动作顺序

---

## 10. 模板生成规则

### 10.1 Page Object

每个 Page 类包含：

1. 元素定位器
2. 元素操作方法
3. 列表 / 表格行操作方法
4. checkbox / radio 模板化方法
5. 页面断言方法
6. 页面跳转方法

### 10.2 Models

每个 Page 对应一个 dataclass：

- 文本输入字段
- 选择字段
- 状态字段
- 断言字段

### 10.3 Test Flow

每个流程生成：

- 步骤方法
- 成功路径
- 失败路径
- 数据驱动入口

---

## 11. 质量控制

### 11.1 置信度分级

- **high**：> 0.9，可直接生成
- **medium**：0.7 ~ 0.9，建议人工确认
- **low**：< 0.7，需要人工修正

### 11.2 自动校验

生成前要检查：

- 是否有关键元素缺失
- 是否有重复定位器
- 是否有不可点击元素被识别为按钮
- 是否有列表元素但没有行模板
- 是否有流程缺页或缺步骤

### 11.3 冲突处理

- 自动配置与人工配置冲突时，以人工配置为准
- 但必须在输出日志中记录冲突字段

---

## 12. 可执行接口设计

### 12.1 命令行接口

建议提供以下命令：

```bash
# 生成页面配置
python -m script.generator.cli detect --page login --platform android

# 生成页面代码
python -m script.generator.cli generate --page login

# 生成流程代码
python -m script.generator.cli generate-flow --flow login_flow

# 全量生成
python -m script.generator.cli generate-all
```

### 12.2 配置输入

```bash
python -m script.generator.cli detect \
  --platform android \
  --page login \
  --package com.example.app \
  --activity .MainActivity
```

---

## 13. 平台兼容实现建议

### 13.1 抽象层

- `Detector` 不直接写死平台 class
- `Analyzer` 只识别统一语义
- `FlowBuilder` 不关心平台
- 平台差异只出现在：
  - UI 树解析
  - 属性映射
  - 坐标解析
  - 平台命令层

### 13.2 平台适配表

统一属性映射表建议单点维护：

```python
UNIFIED_ATTR_MAP = {
    "android": {
        "text": "text",
        "id": "resource-id",
        "desc": "content-desc",
        "class": "class",
        "clickable": "clickable",
        "enabled": "enabled",
        "checked": "checked",
    },
    "ios": {
        "text": "label",
        "id": "name",
        "desc": "help",
        "class": "type",
        "clickable": "clickable",
        "enabled": "enabled",
    },
    "harmony": {
        "text": "text",
        "id": "id",
        "desc": "description",
        "class": "type",
        "clickable": "clickable",
        "enabled": "enabled",
    },
}
```

---

## 14. 与主方案的关系

主方案继续保留：

- 框架总览
- 驱动层
- LocatorAdapter
- Page Object / Models 总则
- pytest + Allure 集成

代码生成器独立文档负责：

- 配置模型
- 自动探测
- 人工配置
- 流程建模
- 生成策略
- 跨平台兼容细节
- 增量生成与冲突处理

---

## 15. 推荐落地顺序

### Phase 1：基础闭环
- Detector
- Analyzer
- ConfigResolver
- Page Object / Models 生成

### Phase 2：流程能力
- 单页面多步骤
- 多页面多步骤
- 条件分支

### Phase 3：质量增强
- 置信度
- 冲突提示
- 人工配置覆盖
- 生成前校验

### Phase 4：平台增强
- 平台属性映射扩展
- 更多控件类型
- 更精细的列表 / 表格识别



---

## 16. 对标 web_quality_ui_playwright 的补齐计划

对比 `web_quality_ui_playwright/script/generator`，当前 App 代码生成器方案还需要补齐以下能力。

### 16.1 生成闭环差距

当前方案已经具备：

- UI 树扫描
- 元素分析
- 配置生成
- 人工配置覆盖
- Page Object / Models / Flow 生成思路

仍需补齐：

1. **级联探测闭环**
   - 对 trigger 元素执行 click / fill / select
   - 记录交互前后的 UI 差异
   - 识别新增元素、可见性变化、列表行数变化
   - 支持链式级联，限制最大深度

2. **上下文提取能力**
   - 父级文本
   - 前后兄弟文本
   - label / placeholder / aria-label
   - wrapper 文本
   - 行内上下文

3. **分层扫描模型**
   - 主页面
   - 搜索区 / 筛选区
   - 列表区 / 表格区
   - 弹窗 / 抽屉
   - 列表行 / 表格行

4. **弹窗 / 抽屉 / 菜单探测**
   - 按钮触发容器
   - 弹窗内元素
   - 抽屉内元素
   - 下拉菜单项

### 16.2 元素识别差距

当前元素类型偏基础，后续需要扩展为细粒度类型：

- `input` / `password` / `number` / `date` / `time` / `file` / `upload`
- `select` / `multi_select` / `select_search` / `cascader` / `tree_select`
- `checkbox` / `checkbox_group` / `radio` / `radio_group` / `switch`
- `button` / `submit` / `search_button` / `reset_button` / `confirm_button`
- `pagination` / `pagination_item` / `pagination_options`
- `table` / `list` / `list_item` / `row` / `cell`
- `toast` / `alert` / `notification` / `empty` / `loading`

### 16.3 命名与稳定性差距

需要补齐：

1. **命名生成器**
   - 中文转英文 key
   - 拼音兜底
   - 翻译缓存
   - 重名去重
   - 无语义元素降级命名

2. **唯一性判断**
   - id 唯一性
   - text 唯一性
   - desc 唯一性
   - locator 组合唯一性
   - 同容器内重复元素去重

3. **字段类型推断**
   - str / bool / int / float
   - List[str] / Dict
   - 必填字段识别
   - 只读字段识别

### 16.4 模板与动作库差距

Web 侧已有组件动作类，如 Select Actions、InputNumber Actions。App 侧也建议补充：

1. **组件动作库**
   - InputActions
   - SelectActions
   - DatePickerActions
   - SwitchActions
   - RadioActions
   - UploadActions
   - PaginationActions

2. **模板拆分**
   - `base_page.jinja2`
   - `page_object.jinja2`
   - `page_table_object.jinja2`
   - `model.jinja2`
   - `test_flow.jinja2`

3. **行级模板**
   - 列表行按钮
   - 列表行输入
   - 列表行选择
   - 列表行 checkbox / radio
   - 行内菜单项

### 16.5 配置合并差距

需要把当前“人工配置覆盖”补成完整规则：

1. 合并优先级
   - 人工配置 > 自动配置 > 默认模板

2. 覆盖粒度
   - 页面级覆盖
   - 容器级覆盖
   - 元素级覆盖
   - 定位器覆盖
   - 步骤级覆盖

3. 冲突处理
   - 同名字段冲突时人工配置优先
   - 冲突写入生成日志
   - 人工新增字段自动追加
   - 人工删除字段可跳过自动补回

### 16.6 会话与稳定性差距

App 场景必须补齐：

1. **登录态管理**
   - 登录态检查
   - 登录态过期恢复
   - 自动重新登录
   - 登录后回到探测页面

2. **页面状态恢复**
   - App 被切后台后恢复
   - 页面白屏恢复
   - 弹窗遮挡恢复
   - 权限弹窗处理

3. **探测失败恢复**
   - trigger 不可见时跳过
   - locator 失效时降级
   - 配置缺失时生成 warning
   - 页面跳转异常时回退

### 16.7 CLI 差距

当前 CLI 需要补齐批量和细粒度能力：

```bash
# 单页探测
python -m script.generator.cli detect --page login

# 单页生成配置
python -m script.generator.cli detect-config --page login

# 只探测弹窗
python -m script.generator.cli detect-modal --page login --button 编辑

# 只生成代码
python -m script.generator.cli generate-code --page login

# 批量探测页面
python -m script.generator.cli detect-batch --config config/pages.yaml

# 生成全量产物
python -m script.generator.cli generate-all
```

### 16.8 推荐补齐顺序

1. **P0：生成闭环最小可用**
   - 分层扫描
   - 上下文提取
   - 命名生成
   - 基础配置生成

2. **P1：级联与人工配置**
   - trigger 交互探测
   - 级联结果写回
   - 人工配置合并

3. **P2：复杂结构**
   - 弹窗 / 抽屉
   - 列表 / 表格行
   - checkbox / radio 模板化

4. **P3：稳定性增强**
   - 会话恢复
   - 页面恢复
   - 冲突日志
   - 生成前校验

---

## 17. 可落地规格清单

> 本清单用于把“能力补齐计划”转成实现前可验收的规格项。P0 表示最小可运行，P1 表示人工配置闭环，P2 表示复杂页面能力，P3 表示稳定性和规模化能力。

### 17.1 元素上下文提取规格

**目标**：在扫描到元素时，统一生成可读、可定位、可去重的上下文信息。

**输出字段**：

```yaml
element_context:
  raw_text: "用户名"
  parent_text: "登录账号"
  pre_sibling_text: ""
  next_sibling_text: ""
  label_text: "用户名"
  placeholder: "请输入用户名"
  desc_text: ""
  wrapper_text: ""
  container_text: "登录"
  row_text: ""
  is_required: true
  is_unique: true
  source: auto
```

**实现规则**：

1. 上下文优先级：`label_text` > `parent_text` > `pre_sibling_text` > `placeholder` > `raw_text`。
2. 同一容器内 `raw_text` 重复时，必须追加索引或上下文前缀。
3. 列表行内元素必须记录 `row_text` 或 `row_index`。
4. 弹窗内元素必须记录 `dialog_title`。
5. 上下文不能替代唯一定位器，只能作为命名和校验依据。

### 17.2 元素类型识别规则表

**目标**：把元素从粗类型扩展成可生成动作和断言的细类型。

| 元素类型 | 识别依据 | 默认动作 | 字段类型 | 断言方式 |
|---|---|---|---|---|
| input | 可编辑文本框 | fill | str | has_text |
| password | password input / secure input | fill | str | is_editable |
| number | numeric / number input | fill | float | get_value |
| checkbox | checkable + multiple | check/uncheck | bool | is_checked |
| radio | checkable + single group | select | str/bool | is_checked |
| switch | toggle 控件 | toggle | bool | is_checked |
| select | 点击打开选项列表 | select_option | str | selected_text |
| multi_select | 可多选选项 | select_options | List[str] | selected_texts |
| date_picker | 日期选择入口 | open/select_date | str | selected_text |
| button | clickable 且无输入属性 | tap | - | is_clickable |
| list | 滚动容器且多行重复 | scroll/click_item | List | count |
| dialog | overlay/container | close/confirm | - | is_visible |
| text | 非交互文本 | - | str | has_text |

**实现规则**：

1. 每个元素必须输出 `element_type`。
2. 每个元素必须输出 `method_name`。
3. 每个交互元素必须输出至少一个动作。
4. 每个展示元素必须输出至少一个断言。
5. 类型识别失败时必须输出 `unknown`，并记录 warning。

### 17.3 分层扫描规格

**目标**：按页面区域扫描，而不是直接铺平所有 UI 节点。

**区域模型**：

```yaml
page_regions:
  - name: page_root
    type: page
    children:
      - name: search_area
        type: form
      - name: list_area
        type: list
      - name: toolbar_area
        type: action_bar
```

**扫描顺序**：

1. 页面根容器。
2. 顶部导航 / Tab / 工具栏。
3. 搜索区 / 筛选区。
4. 列表区 / 表格区。
5. 行内区域。
6. 按钮触发的弹窗 / 抽屉 / 菜单。

**跳过规则**：

- 不可见元素跳过。
- 重复装饰元素跳过。
- 非交互 icon 节点跳过。
- 动态生成时间戳 id 跳过。
- 已被父级复合组件覆盖的子元素跳过。

### 17.4 交互级联探测规格

**目标**：识别点击、输入、选择后产生的新元素和新状态。

**探测动作**：

- `click`
- `fill`
- `select_option`
- `check`
- `uncheck`
- `scroll`

**级联判据**：

1. **新增元素**：交互后 UI 树出现新的稳定元素。
2. **可见性变化**：原本不可见元素变为可见。
3. **容器变化**：新增弹窗、抽屉、下拉菜单。
4. **列表变化**：列表行数、空状态、loading、pagination 发生变化。
5. **页面跳转**：当前页面 key 发生变化。

**限制规则**：

- 默认最大级联深度：3。
- 每个 trigger 默认只探测一次。
- 失败不阻断整体探测，只记录 warning。
- 触发危险动作的按钮默认跳过，例如删除、支付、提交。

### 17.5 场景与流程配置规格

**目标**：支持单页面多步骤和多页面多步骤。

```yaml
scenario:
  name: create_user
  steps:
    - step_name: open_user_page
      action: open_page
      page: user_list
    - step_name: click_create
      action: tap
      element: CREATE_BUTTON
    - step_name: fill_username
      action: fill
      page: create_user
      element: USERNAME_INPUT
      value: "${username}"
    - step_name: submit
      action: tap
      element: SUBMIT_BUTTON
    - step_name: verify_toast
      action: assert_exists
      element: SUCCESS_TOAST
```

**步骤字段**：

```yaml
step_name: unique_step_key
action: open_page | tap | fill | check | select_option | assert_exists | wait | close
page: page_key
element: CONST_NAME
value: value_or_placeholder
platforms: [android, ios, harmony]
wait_after: 1.0
retry: 1
assert:
  element: TARGET_ELEMENT
  type: visible | text | exists
```

### 17.6 自动配置与人工配置合并规格

**目标**：人工配置稳定生效，自动配置可重复生成。

**合并优先级**：

1. `xx_manual_config.yaml`
2. `xx_auto_config.yaml`
3. 默认模板

**覆盖粒度**：

- 页面级：`page_name`、`app_architecture`、`platform_info`
- 容器级：`button_name`、`modal_title`、`container_key`
- 元素级：`const_name`、`element_type`、`label`
- 定位器级：`locator`、`locator_overrides`
- 步骤级：`steps[]`

**冲突规则**：

- 同名字段：人工配置覆盖自动配置。
- 人工新增字段：保留并追加。
- 自动新增字段：保留，除非人工配置存在 `exclude_elements`。
- 删除元素：人工配置写入 `exclude_elements`。
- 冲突必须写入生成日志。

### 17.7 模板与动作库规格

**目标**：模板只负责渲染，不承载复杂探测逻辑。

**模板拆分**：

| 模板 | 输出内容 |
|---|---|
| base_page.jinja2 | 基础定位、点击、输入、等待、断言、截图 |
| page_object.jinja2 | 页面元素常量、操作方法、导航方法 |
| page_table_object.jinja2 | 列表行、表格行、行内控件操作 |
| model.jinja2 | dataclass 数据模型 |
| test_flow.jinja2 | 多步骤流程测试用例 |

**动作库接口**：

```python
class InputActions:
    def fill(...)
    def clear(...)

class SelectActions:
    def open(...)
    def select_by_text(...)

class DatePickerActions:
    def open(...)
    def select_date(...)

class SwitchActions:
    def toggle(...)
    def set_checked(...)

class RowActions:
    def get_row(...)
    def click_in_row(...)
    def check_in_row(...)
```

### 17.8 稳定性与恢复规格

**目标**：避免探测过程被会话、弹窗、页面跳转阻断。

**必须支持**：

- 登录态检查。
- 登录失败恢复。
- 登录后回到目标页面。
- 全局弹窗关闭。
- 权限弹窗处理。
- 页面白屏恢复。
- 元素不可见时跳过。
- locator 失效时降级。
- 重复 locator 检测。
- 动态 id 过滤。

### 17.9 生成前校验规格

**生成前必须检查**：

1. 是否存在未命名元素。
2. 是否存在重复 `const_name`。
3. 是否存在空定位器。
4. 是否存在缺失 platform 覆盖。
5. 是否存在步骤引用不存在的 element。
6. 是否存在页面引用不存在的 page。
7. 是否存在冲突字段。
8. 是否存在低置信度元素未人工确认。

### 17.10 P0/P1/P2/P3 验收清单

**P0：最小可运行**

- [ ] Detector 可扫描 Android / iOS / HarmonyOS UI 树
- [ ] LocatorAdapter 可翻译统一语义定位器
- [ ] Analyzer 可生成 `element_type`、`const_name`、`method_name`
- [ ] 可输出 `xx_auto_config.yaml`
- [ ] 可生成基础 Page Object
- [ ] 可生成基础 Models

**P1：人工配置闭环**

- [ ] 支持 `xx_manual_config.yaml`
- [ ] 支持人工定位器覆盖
- [ ] 支持人工新增步骤
- [ ] 支持人工删除误识别元素
- [ ] 冲突写入日志
- [ ] 支持只生成配置

**P2：复杂页面能力**

- [ ] 支持弹窗 / 抽屉探测
- [ ] 支持列表 / 表格行探测
- [ ] 支持行内按钮
- [ ] 支持行内输入
- [ ] 支持 checkbox / radio 模板化
- [ ] 支持单页多步骤
- [ ] 支持多页多步骤

**P3：稳定性增强**

- [ ] 支持登录态恢复
- [ ] 支持全局弹窗处理
- [ ] 支持页面跳转恢复
- [ ] 支持 locator 降级链
- [ ] 支持重复元素去重
- [ ] 支持生成前校验
- [ ] 支持批量页面探测

---

## 18. 代码生成器代码框架

> 这一章给出最小可运行代码框架，供后续实现参考。实际落地时可以按平台拆成 Android / iOS / HarmonyOS 的 Detector 适配器，但核心模型保持统一。

### 18.1 代码目录结构

```text
script/generator/
├── __init__.py
├── cli.py
├── comm.py
├── config/
│   ├── default_config.yaml
│   └── detect_config/
├── core/
│   ├── constants.py
│   ├── detector.py
│   ├── context_extractor.py
│   ├── analyzer.py
│   ├── locator_builder.py
│   ├── config_builder.py
│   ├── config_resolver.py
│   ├── flow_builder.py
│   └── code_generator.py
└── templates/
    ├── base_page.jinja2
    ├── page_object.jinja2
    ├── page_table_object.jinja2
    ├── model.jinja2
    └── test_flow.jinja2
```

### 18.2 核心模型定义

建议先把统一模型定义清楚，后续 Detector / Analyzer / Generator 都依赖它。

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ElementContext:
    raw_text: str = ""
    parent_text: str = ""
    pre_sibling_text: str = ""
    next_sibling_text: str = ""
    label_text: str = ""
    placeholder: str = ""
    desc_text: str = ""
    wrapper_text: str = ""
    container_text: str = ""
    row_text: str = ""
    is_required: bool = False
    is_unique: bool = False
    source: str = "auto"

@dataclass
class Element:
    const_name: str = ""
    element_type: str = "text"
    label: str = ""
    locator: Dict[str, Any] = field(default_factory=dict)
    locator_overrides: Dict[str, Any] = field(default_factory=dict)
    action: str = ""
    method_name: str = ""
    assert_method_name: str = ""
    field_type: str = ""
    raw_name: str = ""
    confidence: float = 0.0
    source: str = "auto"
    platforms: List[str] = field(default_factory=list)
    context: Optional[ElementContext] = None

@dataclass
class PageConfig:
    page_name: str = ""
    platform: str = "all"
    app_architecture: str = "native"
    url_path: str = ""
    platform_info: Dict[str, Any] = field(default_factory=dict)
    elements: List[Element] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
```

### 18.3 代码框架示意

```python
# script/generator/core/detector.py
class Detector:
    def scan_page(self, driver, page_name: str, platform: str, app_architecture: str = "native") -> PageConfig:
        """扫描 UI 树，输出统一元素模型。"""
        raw_tree = self._dump_ui_tree(driver, platform)
        raw_nodes = self._parse_tree(raw_tree, platform)
        elements = [self._normalize_node(node, platform, app_architecture) for node in raw_nodes]
        elements = self._extract_context(elements)
        return PageConfig(
            page_name=page_name,
            platform=platform,
            app_architecture=app_architecture,
            elements=elements,
        )

    def _dump_ui_tree(self, driver, platform: str) -> str:
        raise NotImplementedError

    def _parse_tree(self, raw_tree: str, platform: str):
        raise NotImplementedError

    def _normalize_node(self, node, platform: str, app_architecture: str) -> Element:
        raise NotImplementedError

    def _extract_context(self, elements: List[Element]):
        raise NotImplementedError
```

```python
# script/generator/core/analyzer.py
class Analyzer:
    def analyze(self, page_config: PageConfig) -> PageConfig:
        for elem in page_config.elements:
            elem.element_type = self._identify_type(elem)
            elem.const_name = self._gen_const_name(elem)
            elem.method_name = self._gen_method_name(elem)
            elem.assert_method_name = self._gen_assert_method(elem)
            elem.field_type = self._infer_field_type(elem)
            elem.action = self._infer_action(elem)
        return page_config

    def _identify_type(self, elem: Element) -> str:
        raise NotImplementedError

    def _gen_const_name(self, elem: Element) -> str:
        raise NotImplementedError

    def _gen_method_name(self, elem: Element) -> str:
        raise NotImplementedError
```

```python
# script/generator/core/locator_builder.py
class LocatorBuilder:
    def build_locator(self, elem: Element, platform: str) -> Dict[str, Any]:
        """按平台和覆盖规则生成最终 locator。"""
        if platform in elem.locator_overrides:
            return elem.locator_overrides[platform]
        return elem.locator

    def build_fallback_chain(self, elem: Element, platform: str) -> List[Dict[str, Any]]:
        return [self.build_locator(elem, platform), elem.locator]
```

```python
# script/generator/core/config_builder.py
class ConfigBuilder:
    def to_yaml_dict(self, page_config: PageConfig) -> Dict[str, Any]:
        return {
            "page_name": page_config.page_name,
            "platform": page_config.platform,
            "app_architecture": page_config.app_architecture,
            "url_path": page_config.url_path,
            page_config.page_name: {
                "cascade_fields": [self._dump_element(e) for e in page_config.elements],
                "steps": page_config.steps,
            },
        }

    def save_auto_config(self, page_config: PageConfig, output_path):
        data = self.to_yaml_dict(page_config)
        save_yaml(output_path, data)

    def _dump_element(self, elem: Element) -> Dict[str, Any]:
        raise NotImplementedError
```

```python
# script/generator/core/config_resolver.py
class ConfigResolver:
    def merge(self, auto_config: Dict[str, Any], manual_config: Dict[str, Any]) -> Dict[str, Any]:
        return self._deep_merge(auto_config, manual_config, manual_wins=True)

    def _deep_merge(self, auto, manual, manual_wins=True):
        raise NotImplementedError
```

```python
# script/generator/core/flow_builder.py
class FlowBuilder:
    def build_flow(self, page_config: PageConfig, scenario_name: str) -> List[Dict[str, Any]]:
        return [
            {
                "step_name": "open_page",
                "action": "open_page",
                "page": page_config.page_name,
            },
        ]
```

```python
# script/generator/core/code_generator.py
class CodeGenerator:
    def generate(self, page_config: PageConfig, output_dir):
        page = self._render_page_object(page_config)
        model = self._render_model(page_config)
        flow = self._render_flow(page_config)
        save_text(output_dir / f"{page_config.page_name}_page.py", page)
        save_text(output_dir / f"{page_config.page_name}_models.py", model)
        save_text(output_dir / f"{page_config.page_name}_flow.py", flow)

    def _render_page_object(self, page_config: PageConfig) -> str:
        raise NotImplementedError

    def _render_model(self, page_config: PageConfig) -> str:
        raise NotImplementedError

    def _render_flow(self, page_config: PageConfig) -> str:
        raise NotImplementedError
```

```python
# script/generator/cli.py
def detect(args):
    detector = Detector()
    analyzer = Analyzer()
    config_builder = ConfigBuilder()

    page_config = detector.scan_page(driver=args.driver, page_name=args.page, platform=args.platform, app_architecture=args.architecture)
    page_config = analyzer.analyze(page_config)
    config_builder.save_auto_config(page_config, args.output)

def generate_code(args):
    page_config = load_page_config(args.config)
    generator = CodeGenerator()
    generator.generate(page_config, args.output_dir)
```

### 18.4 具体代码实现示例

以下示例展示一个“登录页”的最小生成链路。

```python
def run_login_example(platform="android"):
    driver = create_driver(platform)
    detector = Detector()
    analyzer = Analyzer()
    resolver = ConfigResolver()
    builder = ConfigBuilder()
    generator = CodeGenerator()

    page_config = detector.scan_page(driver=driver, page_name="login", platform=platform)
    page_config = analyzer.analyze(page_config)

    auto_config = builder.to_yaml_dict(page_config)
    manual_config = load_yaml("config/detect_config/login_manual_config.yaml")
    merged_config = resolver.merge(auto_config, manual_config)

    builder.save_auto_config(page_config, "config/detect_config/login_auto_config.yaml")
    generator.generate(page_config, "generated/pages")
```

### 18.5 渲染模板示例

#### Page Object 模板要点

```jinja2
class {{ class_name }}Page(BasePage):
    {% for elem in input_elements %}
    {{ elem.const_name }} = {{ elem.locator }}  # {{ elem.label }}
    {% endfor %}
    {% for elem in button_elements %}
    {{ elem.const_name }} = {{ elem.locator }}  # {{ elem.label }}
    {% endfor %}

    @allure.step("打开{{ class_name }}页面")
    def open(self):
        self.navigate(self.URI_PATH)
        self.wait_for_page_loaded()

    {% for elem in input_elements %}
    @allure.step("填写{{ elem.label }}")
    def fill_{{ elem.const_name | lower }}(self, value: str):
        self.fill(self.{{ elem.const_name }}, value)
    {% endfor %}

    {% for elem in button_elements %}
    @allure.step("点击{{ elem.label }}")
    def tap_{{ elem.const_name | lower }}(self):
        self.click(self.{{ elem.const_name }})
    {% endfor %}
```

#### Model 模板要点

```jinja2
from dataclasses import dataclass
from typing import List

@dataclass
class {{ class_name }}Data:
{% for elem in data_fields %}
    {{ elem.const_name | lower }}: {{ elem.field_type }}  # {{ elem.label }}
{% endfor %}
```

#### Flow 模板要点

```jinja2
import allure

@allure.feature("{{ flow_name }}")
def test_{{ flow_name }}(app):
    page = {{ class_name }}Page(app.driver)
{% for step in steps %}
    page.{{ step.method_name }}({% if step.value %}"{{ step.value }}"{% endif %})
{% endfor %}
```

### 18.6 最小执行流程

```bash
# 1. 探测页面配置
python -m script.generator.cli detect --page login --platform android --output config/detect_config/login_auto_config.yaml

# 2. 人工修正配置
# 编辑 config/detect_config/login_manual_config.yaml

# 3. 合并配置并生成代码
python -m script.generator.cli generate-code --page login --output-dir generated/pages
```

### 18.7 输出示例

生成后的 Page Object 必须继承 `BasePage`，并由 `BasePage` 统一提供：
- 初始化 `app` / `driver` / `platform`
- 延迟初始化 `logger`
- 导航、等待、定位、点击、输入、勾选、断言
- 滚动、截图、返回等通用能力

#### BasePage 示例

```python
from utils.logger import get_logger


class BasePage:
    def __init__(self, app):
        self.app = app
        self.driver = app.driver
        self.platform = app.platform
        self._logger = None
        self.page_name = self.__class__.__name__.replace("_", " ").lower()

    @property
    def logger(self):
        if not self._logger:
            self._logger = get_logger(__name__)
        return self._logger

    def navigate(self, url_path: str):
        self.logger.info(f"打开页面: {url_path}")
        self.app.open_url(url_path)

    def wait_for_page_loaded(self, timeout: float = 10.0):
        self.logger.info("等待页面加载完成")
        self.app.wait_idle(timeout=timeout)

    def find(self, locator):
        self.logger.info(f"定位元素: {locator}")
        return self.app.find(locator)

    def fill(self, locator, text: str):
        self.logger.info(f"输入文本: {text[:20]}")
        self.find(locator).send_keys(text)

    def click(self, locator):
        self.logger.info(f"点击元素: {locator}")
        self.find(locator).click()

    def check(self, locator):
        self.logger.info(f"勾选元素: {locator}")
        self.find(locator).check()

    def uncheck(self, locator):
        self.logger.info(f"取消勾选: {locator}")
        self.find(locator).uncheck()

    def assert_exists(self, locator):
        self.logger.info(f"断言元素存在: {locator}")
        assert self.find(locator).exists()

    def scroll_to(self, locator):
        self.logger.info(f"滚动到元素: {locator}")
        self.app.scroll_to(locator)

    def screenshot(self, name: str = "page"):
        self.logger.info(f"截图: {name}")
        return self.app.screenshot(name=name)

    def back(self):
        self.logger.info("返回上一页")
        self.app.back()
```

#### Page Object 示例

生成后的 Page Object 骨架应至少包含：
- 页面元信息
- 定位器常量
- 基础页面方法
- 输入/点击/勾选/断言方法
- 列表/弹窗等通用操作模板

```python
from utils.logger import get_logger


class LoginPage(BasePage):
    URI_PATH = "/login"

    # 统一语义定位器
    USERNAME_INPUT = {"text": "用户名", "class": "input"}
    PASSWORD_INPUT = {"text": "密码", "class": "input"}
    AGREEMENT_CHECKBOX = {"text": "我已阅读并同意协议", "class": "checkbox"}
    LOGIN_BUTTON = {"text": "登录", "class": "button"}

    # 平台覆盖定位器
    LOCATOR_OVERRIDES = {
        "USERNAME_INPUT": {
            "android": "com.example.app:id/username",
            "ios": "username",
            "harmony": "username",
        },
        "PASSWORD_INPUT": {
            "android": "com.example.app:id/password",
            "ios": "password",
            "harmony": "password",
        },
        "LOGIN_BUTTON": {
            "android": "com.example.app:id/btn_login",
            "ios": "loginButton",
            "harmony": "btn_login",
        },
    }

    def __init__(self, app):
        super().__init__(app)
        self._logger = None
        self.page_name = "login"

    @property
    def logger(self):
        """延迟获取 logger，确保测试框架初始化完成后再使用。"""
        if not self._logger:
            self._logger = get_logger(__name__)
        return self._logger

    def open(self):
        self.logger.info("打开登录页")
        self.navigate(self.URI_PATH)
        self.wait_for_page_loaded()

    def get_locator(self, const_name):
        overrides = self.LOCATOR_OVERRIDES.get(const_name, {})
        if self.platform in overrides:
            self.logger.info(f"使用平台定位器: {self.platform}, {const_name}")
            return overrides[self.platform]
        self.logger.info(f"使用统一语义定位器: {const_name}")
        return getattr(self, const_name)

    def fill_username(self, value: str):
        self.logger.info(f"填写用户名: {value}")
        self.fill(self.get_locator("USERNAME_INPUT"), value)

    def fill_password(self, value: str):
        self.logger.info("填写密码")
        self.fill(self.get_locator("PASSWORD_INPUT"), value)

    def check_agreement(self):
        self.logger.info("勾选协议")
        self.check(self.get_locator("AGREEMENT_CHECKBOX"))

    def tap_login(self):
        self.logger.info("点击登录")
        self.click(self.get_locator("LOGIN_BUTTON"))

    def assert_username_visible(self):
        self.logger.info("断言用户名输入框可见")
        self.assert_exists(self.get_locator("USERNAME_INPUT"))
```

> 说明：
> - `self.platform` 由运行时驱动注入，保证只读取当前平台 locator
> - `LOCATOR_OVERRIDES` 只作映射表，不能直接交给驱动执行
> - `self.logger` 延迟初始化，避免在测试框架准备阶段过早绑定日志上下文
> - Page Object 内的关键步骤都要打日志，便于 pytest / Allure 追踪执行过程

生成后的 Model 骨架应包含页面数据契约、默认值和字段注释。

```python
from dataclasses import dataclass


@dataclass
class LoginData:
    username: str = ""
    password: str = ""
    agree_terms: bool = False
```

> 建议：
> - `dataclass` 字段名使用业务语义
> - 注释保留中文标签
> - 字段顺序与页面流程顺序一致

如果页面上存在列表/弹窗/分页等复杂结构，Page Object 里应额外生成模板化方法，例如：

```python
class OrderListPage(BasePage):
    LIST_CONTAINER = {"class": "list"}
    LIST_ITEM = {"class": "list_item"}

    def get_row_by_text(self, text: str):
        return self.find_in_list(self.LIST_CONTAINER, self.LIST_ITEM, text)

    def click_row(self, text: str):
        self.click(self.get_row_by_text(text))

    def toggle_checkbox_by_name(self, row_text: str, checked: bool = True):
        self.toggle_checkbox(self.get_row_by_text(row_text), "checkbox", checked)

    def select_radio_by_name(self, row_text: str, option_text: str):
        self.select_radio(self.get_row_by_text(row_text), option_text)
```

生成后的 Flow 骨架大致如下：

```python
import allure
from pages.login_page import LoginPage
from models.login_models import LoginData


@allure.feature("登录")
def test_login(app):
    data = LoginData(username="tester", password="123456", agree_terms=True)
    page = LoginPage(app)
    page.open()
    page.fill_username(data.username)
    page.fill_password(data.password)
    page.check_agreement()
    page.tap_login()
```

---

## 19. 实现导向最终方案

> 这一章把前面所有设计、规格和代码框架收敛成一套可实现、可验收、可落地的最终方案。实现时优先完成 P0，再逐步补齐 P1/P2。

### 19.1 平台解析层

目标是先把三平台 UI 树解析成统一节点模型，后续所有分析都只依赖统一模型。

#### Android

解析输入：
- `uiautomator dump`
- XML 文本
- 节点属性：`text` / `resource-id` / `content-desc` / `class` / `clickable` / `bounds`

输出统一模型：
- `text`
- `id`
- `desc`
- `class`
- `bounds`
- `clickable`
- `visible`

实现重点：
- 解析 `[x1,y1][x2,y2]`
- 过滤重复包装容器
- 过滤空 class 节点
- 对 `EditText` / `Button` / `CheckBox` / `RadioButton` 做强类型识别

#### iOS

解析输入：
- WDA dump JSON / XML
- 节点属性：`label` / `name` / `help` / `type` / `visible` / `enabled` / `rect`

输出统一模型：
- `text` = `label`
- `id` = `name`
- `desc` = `help`
- `class` = `type`
- `bounds` = `rect`

实现重点：
- 兼容 JSON 和 XML 两种 dump 格式
- 支持 `rect: {x,y,width,height}`
- 对 `Button` / `Switch` / `TextField` 做强类型识别
- 处理重复 accessibility id

#### HarmonyOS

解析输入：
- `hdc` 或系统接口 dump
- JSON / XML
- 节点属性：`text` / `id` / `description` / `type` / `bounds`

输出统一模型：
- `text`
- `id`
- `desc`
- `class`
- `bounds`

实现重点：
- 归一化 JSON bounds
- 处理组件容器嵌套
- 兼容部分系统组件缺少 `type` 的情况

### 19.2 统一节点模型

所有平台最终必须落到同一结构：

```python
@dataclass
class UnifiedNode:
    tag: str
    text: str
    id: str
    desc: str
    class_name: str
    role: str
    clickable: bool
    enabled: bool
    checked: bool
    visible: bool
    bounds: tuple
    parent: Optional['UnifiedNode'] = None
    children: List['UnifiedNode'] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
```

### 19.3 细粒度元素类型体系

为了覆盖复杂页面，元素类型不再只停留在粗分类，而是采用实现导向的细粒度类型：

#### 基础交互

- `button`
- `text_button`
- `input`
- `password`
- `number`
- `checkbox`
- `radio`
- `switch`
- `select`
- `multi_select`
- `date_picker`
- `time_picker`

#### 展示类

- `text`
- `image`
- `icon`
- `badge`
- `tag`

#### 结构类

- `list`
- `list_item`
- `table`
- `row`
- `cell`
- `card`
- `container`

#### 反馈类

- `toast`
- `alert`
- `dialog`
- `drawer`
- `menu`
- `empty`
- `loading`

#### 导航类

- `pagination`
- `pagination_item`
- `tab`
- `tab_item`
- `back_button`
- `search_button`
- `reset_button`
- `submit_button`

#### 实现要求

每个类型都必须明确：
- 默认动作
- 默认断言
- 默认字段类型
- 默认 locator 策略

### 19.4 元素定位与命名策略

#### Locator 生成顺序

1. 稳定 ID
2. 稳定 role / class
3. 稳定文本
4. 组合 locator
5. fallback locator

#### 命名规则

1. 中文优先转英文 key
2. 若无法翻译，则使用拼音兜底
3. 动态 id 过滤，禁止以数字、时间戳、哈希为主 key
4. 同名元素加后缀：`_2` / `_3`
5. 容器元素必须带区域名前缀，例如 `SEARCH_INPUT`、`ROW_ACTION_BUTTON`

#### 唯一性规则

- `id` 唯一性优先
- `text` 唯一性次之
- 同容器内重复文本必须追加上下文
- 同一列表行内按钮必须使用模板化方法，不允许生成多个重复常量

### 19.5 级联探测实现方案

#### 探测触发器

仅对以下元素进行交互探测：

- `button`
- `text_button`
- `select`
- `multi_select`
- `checkbox`
- `radio`
- `switch`
- `list_item`

#### 判据

1. 新增稳定节点
2. 不可见变可见
3. 弹窗 / 抽屉 / 菜单出现
4. 列表行数变化
5. 页面跳转
6. 出现 toast / alert

#### 回溯策略

- 每次交互后记录原始页面 key
- 若识别为弹窗，优先点击关闭 / 返回
- 若识别为跳转，尝试回跳
- 若无法恢复，终止当前分支并记录 warning

#### 风险控制

默认跳过：
- 删除
- 支付
- 提交
- 确认
- 取消
- 退出

### 19.6 配置合并方案

配置分为两层：

- `auto_config.yaml`
- `manual_config.yaml`

#### 合并原则

1. `manual` 覆盖 `auto`
2. 元素级合并以 `const_name` 为准
3. 步骤级合并以 `step_name` 为准
4. 未显式删除的 `auto` 字段保留
5. 若人工配置只写了差异字段，则只覆盖差异字段
6. 若出现字段冲突，输出 merge log

#### 合并示例

- 自动配置生成了完整元素列表
- 人工配置只修改了定位器和 label
- 生成器只输出合并后的最小变更
- 冲突字段优先人工配置

### 19.7 组件动作库方案

生成 Page Object 时，不仅生成常量，还要生成动作方法。

#### 动作库分类

- `InputActions`
- `SelectActions`
- `CheckboxActions`
- `RadioActions`
- `SwitchActions`
- `DatePickerActions`
- `PaginationActions`
- `ListActions`
- `DialogActions`
- `DrawerActions`

#### 生成规则

- 输入框生成 `fill_*`
- 选择器生成 `select_*`
- checkbox 生成 `check_*` / `uncheck_*`
- 按钮生成 `tap_*`
- 列表生成 `click_item_*`
- 弹窗生成 `close_*` / `confirm_*`
- 文本生成 `assert_*`

### 19.8 模板生成方案

模板要覆盖五类输出：

#### 1. BasePage

- 页面初始化
- 打开页面
- 等待条件
- 统一日志
- 失败截图

#### 2. Page Object

- 定位器常量
- 业务动作
- 断言方法
- 列表/弹窗/表格动作
- 平台覆盖 locator 读取逻辑

#### 3. Model

- dataclass
- 数据校验
- 默认值
- 注释说明

#### 4. Test Flow

- 正常流程
- 异常流程
- 条件分支
- 步骤级 allure step

#### 5. Data

- YAML 数据
- 数据工厂
- 数据驱动输入

### 19.9 端到端执行闭环

最小闭环必须支持：

1. 连接设备
2. 打开目标页面
3. 扫描 UI 树
4. 解析平台节点
5. 生成统一元素模型
6. 分析元素类型
7. 生成自动配置
8. 读取人工配置
9. 合并配置
10. 渲染模板
11. 输出 Page / Model / Flow / Data
12. 生成校验结果

### 19.10 实现优先级

#### P0：最小可运行

- 平台解析层
- 统一节点模型
- 元素类型识别
- 基础 locator 生成
- auto config 输出
- 单页生成

#### P1：人工闭环

- manual config
- merge
- 命名规则
- 基础 Page Object
- 基础 Model

#### P2：复杂页面

- 级联探测
- 弹窗/抽屉
- 列表/表格
- 组件动作库
- 多页流程

#### P3：稳定性

- 去重
- 重试
- fallback
- merge log
- 异常恢复

### 19.11 验收标准

完成实现后，必须能完成以下场景：

1. 扫描登录页并生成配置
2. 合并人工修正配置
3. 生成 Page Object
4. 生成 Model
5. 生成单页多步骤流程
6. 生成多页面流程
7. 能处理 iOS / Android / HarmonyOS 的定位差异
8. 能处理列表行操作
9. 能处理弹窗触发的二级页面
10. 能输出可执行 pytest 测试

---

## 20. 结论

代码生成器应该被设计成：

> **探测 → 分析 → 建模 → 配置 → 生成** 的完整闭环

而不是单纯的 UI 树扫描器。

只有补齐配置生成、人工配置、流程建模和跨平台兼容后，它才能接近真实可落地的自动化生成能力。
