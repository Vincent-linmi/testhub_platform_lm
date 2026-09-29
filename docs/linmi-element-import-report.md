# LinMi UI 元素导入报告

- 元素索引：`/Users/vincent/linmi/catalog/ui_element-index.jsonl`
- 页面清单：`/Users/vincent/linmi/catalog/ui_surface-index.jsonl`
- 目标项目：`linmi-dev`
- 元素总数：634，其中可直接执行 548，待人工确认 86
- 实体化成功：546，字符串规则：2
- 本次运行新转正（原为待确认）：0
- 本次运行修正定位值：0

## 待人工确认的元素（定位值由方法参数决定）

| 页面 | 元素 | 原始表达式 | 原因 |
| --- | --- | --- | --- |
| 渠道管理 | button-button | `self.page.get_by_role('button', name=action, exact=True)` | 定位值由方法参数/运行时变量 `action` 决定，没有静态等价的定位值 |
| 渠道管理 | button-main | `self.page.get_by_role('main').get_by_role('button', name=category, exa` | 定位值由方法参数/运行时变量 `category` 决定，没有静态等价的定位值 |
| 渠道管理 | button-操作 | `row.get_by_role('button', name='操作', exact=True)` | 定位值由方法参数/运行时变量 `row` 决定，没有静态等价的定位值 |
| 渠道管理 | button-连接 {channel} | `self.page.get_by_role('button', name=f'连接 {channel}', exact=True)` | 定位值由方法参数/运行时变量 `channel` 决定，没有静态等价的定位值 |
| 渠道管理 | text-name | `self.page.get_by_text(name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 会话分享页 | avatar | `dialog.get_by_role('img', name=contact_name, exact=True)` | 定位值由方法参数/运行时变量 `dialog` 决定，没有静态等价的定位值 |
| 会话分享页 | name | `dialog.get_by_text(contact_name, exact=True)` | 定位值由方法参数/运行时变量 `dialog` 决定，没有静态等价的定位值 |
| 会话工作台 | button-button | `self.page.get_by_role('button', name=member_name, exact=True)` | 定位值由方法参数/运行时变量 `member_name` 决定，没有静态等价的定位值 |
| 会话工作台 | css-xpath=ancestor::div[contains(@class, | `message.locator("xpath=ancestor::div[contains(@class,'overflow-y-auto'` | 定位值由方法参数/运行时变量 `message` 决定，没有静态等价的定位值 |
| 会话工作台 | tab-tab | `self.page.get_by_role('tab', name=status, exact=True)` | 定位值由方法参数/运行时变量 `status` 决定，没有静态等价的定位值 |
| 会话工作台 | text-action | `self.page.get_by_text(action, exact=True)` | 定位值由方法参数/运行时变量 `action` 决定，没有静态等价的定位值 |
| 会话工作台 | text-member_name | `panel.get_by_text(member_name, exact=True)` | 定位值由方法参数/运行时变量 `member_name` 决定，没有静态等价的定位值 |
| 会话工作台 | text-name | `self.page.get_by_text(name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 会话工作台 | text-re.compile(f'接待人由\\s*{re.escape(previous)}\\s*变更为\\s*{re.escape(member_name)}') | `self.page.get_by_text(re.compile(f'接待人由\\s*{re.escape(previous)}\\s*变更` | 定位值由方法参数/运行时变量 `previous` 决定，没有静态等价的定位值 |
| 会话工作台 | text-section | `self.page.get_by_text(section, exact=True)` | 表达式把定位器当作参数传给了 Playwright 调用，需按具体参数实例化 |
| 会话工作台 | text-text | `self.page.get_by_text(text, exact=True)` | 定位值由方法参数/运行时变量 `text` 决定，没有静态等价的定位值 |
| 客户管理 | button-button | `self.page.get_by_role('button', name=action, exact=True)` | 定位值由方法参数/运行时变量 `action` 决定，没有静态等价的定位值 |
| 客户管理 | button-操作 | `row.get_by_role('button', name='操作', exact=True)` | 定位值由方法参数/运行时变量 `row` 决定，没有静态等价的定位值 |
| 客户管理 | option-option | `self.page.get_by_role('option', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 客户管理 | text-{action} 功能待接入 | `self.page.get_by_text(f'{action} 功能待接入', exact=True)` | 定位值由方法参数/运行时变量 `action` 决定，没有静态等价的定位值 |
| 客户管理 | text-name | `self.page.get_by_text(name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-客服 | button-button | `self.page.get_by_role('button', name=period, exact=True)` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 数据-客服 | option-option | `self.page.get_by_role('option', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-客户 | button-button | `self.page.get_by_role('button', name=period, exact=True)` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 数据-客户 | option-option | `self.page.get_by_role('option', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-会话 | button-button | `self.page.get_by_role('button', name=period, exact=True)` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 数据-会话 | option-option | `self.page.get_by_role('option', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-会话 | text-metric | `self.page.get_by_text(metric, exact=True)` | 定位值由方法参数/运行时变量 `metric` 决定，没有静态等价的定位值 |
| 数据-消息 | button-button | `self.page.get_by_role('button', name=period, exact=True)` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 数据-消息 | option-option | `self.page.get_by_role('option', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-在线时长 | button-button | `self.page.get_by_role('button', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-在线时长 | text-metric | `self.page.get_by_text(metric, exact=True)` | 定位值由方法参数/运行时变量 `metric` 决定，没有静态等价的定位值 |
| 数据-概览 | button-button | `self.page.get_by_role('button', name=period, exact=True)` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 数据-概览 | css-.report-granularity-select | `card.locator('.report-granularity-select')` | 定位值由方法参数/运行时变量 `card` 决定，没有静态等价的定位值 |
| 数据-概览 | css-xpath=ancestor::section[1] | `self.page.get_by_role('heading', name=name, exact=True).locator('xpath` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-概览 | heading-heading | `self.page.get_by_role('heading', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-概览 | option-.el-select__popper:visible | `self.page.locator('.el-select__popper:visible').get_by_role('option', ` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 数据-概览 | option-option | `self.page.get_by_role('option', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-概览 | text-metric | `self.page.get_by_text(metric, exact=True)` | 定位值由方法参数/运行时变量 `metric` 决定，没有静态等价的定位值 |
| 数据-响应 | button-button | `self.page.get_by_role('button', name=period, exact=True)` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 数据-响应 | option-option | `self.page.get_by_role('option', name=name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 数据-响应 | text-metric | `self.page.get_by_text(metric, exact=True)` | 定位值由方法参数/运行时变量 `metric` 决定，没有静态等价的定位值 |
| 推广账户 | button-button | `self.page.get_by_role('button', name=direction, exact=True)` | 定位值由方法参数/运行时变量 `direction` 决定，没有静态等价的定位值 |
| 推广账户 | button-main | `self.page.get_by_role('main').get_by_role('button', name=name, exact=T` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 组织设置-账户 | button-main | `self.page.get_by_role('main').get_by_role('button', name=name, exact=T` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 组织设置-账户 | button-操作 | `row.get_by_role('button', name='操作', exact=True)` | 定位值由方法参数/运行时变量 `row` 决定，没有静态等价的定位值 |
| 组织设置-账户 | text-name | `self.page.get_by_text(name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 个人设置-资料 | text-status | `self.page.get_by_text(status, exact=True)` | 定位值由方法参数/运行时变量 `status` 决定，没有静态等价的定位值 |
| 工作区设置-会话分享 | action_button | `row.get_by_role('button', name=re.compile('(更多|操作)'))` | 定位值由方法参数/运行时变量 `row` 决定，没有静态等价的定位值 |
| 工作区设置-会话分享 | cell-cell | `row.get_by_role('cell')` | 定位值由方法参数/运行时变量 `row` 决定，没有静态等价的定位值 |
| 工作区设置-会话分享 | css-cell | `rows.nth(index).get_by_role('cell').nth(0).locator('span.truncate')` | 定位值由方法参数/运行时变量 `index` 决定，没有静态等价的定位值 |
| 工作区设置-会话分享 | text-contact_name | `self.page.get_by_text(contact_name, exact=True)` | 定位值由方法参数/运行时变量 `contact_name` 决定，没有静态等价的定位值 |
| 工作区设置-会话分享 | text-created_at | `self.page.get_by_text(created_at, exact=True)` | 定位值由方法参数/运行时变量 `created_at` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | button-.el-popper:visible | `self.page.locator('.el-popper:visible').get_by_role('button', name=nam` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | button-.settings-select-popper:visible | `self.page.locator('.settings-select-popper:visible').get_by_role('butt` | 定位值由方法参数/运行时变量 `dataset` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | button-listitem | `self.page.get_by_role('listitem').filter(has=self.page.get_by_text(nam` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | button-main | `self.page.get_by_role('main').get_by_role('button', name=name, exact=T` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | cell-cell | `row.get_by_role('cell', name=member_role, exact=True)` | 定位值由方法参数/运行时变量 `member_role` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | css-.assignment-fallback-member--warning | `self.assignment_fallback_card().locator('.assignment-fallback-member--` | 定位值依赖实例属性 `assignment_fallback_card`（由方法参数决定），没有静态等价的定位值 |
| 工作区设置-常规 | css-xpath=../../.. | `self.stage_name_input(name).locator('xpath=../../..')` | 定位值依赖实例属性 `stage_name_input`（由方法参数决定），没有静态等价的定位值 |
| 工作区设置-常规 | css-xpath=ancestor::div[contains(concat( | `switch.locator("xpath=ancestor::div[contains(concat(' ', normalize-spa` | 定位值由方法参数/运行时变量 `switch` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | radio-radio | `self.page.get_by_role('radio', name=re.compile(f'^{re.escape(scope)}')` | 定位值由方法参数/运行时变量 `scope` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | text-.settings-dialog__panel | `self.page.locator('.settings-dialog__panel').get_by_text(message, exac` | 定位值由方法参数/运行时变量 `message` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | text-name | `self.page.get_by_text(name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 工作区设置-常规 | text-switch_name | `self.page.get_by_text(switch_name, exact=True)` | 定位值由方法参数/运行时变量 `switch_name` 决定，没有静态等价的定位值 |
| 工作区设置-用量 | button-button | `self.page.get_by_role('button', name=period, exact=True)` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 工作区设置-用量 | button-main | `self.page.get_by_role('main').get_by_role('button', name=resource, exa` | 定位值由方法参数/运行时变量 `resource` 决定，没有静态等价的定位值 |
| 工具-形式发票 | button-button | `self.invoice_row(number).get_by_role('button', name=number, exact=True` | 定位值依赖实例属性 `invoice_row`（由方法参数决定），没有静态等价的定位值 |
| 工具-形式发票 | button-main | `self.page.get_by_role('main').get_by_role('button', name=name, exact=T` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 工具-形式发票 | button-删除此行 | `self.invoice_item(index).get_by_role('button', name='删除此行', exact=True` | 定位值依赖实例属性 `invoice_item`（由方法参数决定），没有静态等价的定位值 |
| 工具-形式发票 | button-操作 | `row.get_by_role('button', name='操作', exact=True)` | 定位值由方法参数/运行时变量 `row` 决定，没有静态等价的定位值 |
| 工具-形式发票 | css-.settings-dialog__panel | `self.page.locator('.settings-dialog__panel').locator('label').filter(h` | 定位值由方法参数/运行时变量 `label` 决定，没有静态等价的定位值 |
| 工具-形式发票 | option-.el-select__popper:visible | `self.page.locator('.el-select__popper:visible').get_by_role('option', ` | 定位值由方法参数/运行时变量 `period` 决定，没有静态等价的定位值 |
| 工具-形式发票 | spinbutton-spinbutton | `item.get_by_role('spinbutton', name='数量', exact=True)` | 定位值由方法参数/运行时变量 `item` 决定，没有静态等价的定位值 |
| 工具-形式发票 | text-main | `self.page.get_by_role('main').get_by_text(label, exact=True)` | 定位值由方法参数/运行时变量 `label` 决定，没有静态等价的定位值 |
| 工具-形式发票 | text-message | `self.page.get_by_text(message, exact=True)` | 定位值由方法参数/运行时变量 `message` 决定，没有静态等价的定位值 |
| 工具-形式发票 | text-name | `self.page.get_by_text(name, exact=True)` | 定位值由方法参数/运行时变量 `name` 决定，没有静态等价的定位值 |
| 工具-形式发票 | text-number | `self.page.get_by_text(number, exact=True)` | 定位值由方法参数/运行时变量 `number` 决定，没有静态等价的定位值 |
| 工具-形式发票 | text-preset | `panel.get_by_text(preset, exact=True)` | 定位值由方法参数/运行时变量 `preset` 决定，没有静态等价的定位值 |
| 工具-形式发票 | text-确定删除单据 {number} 吗？ | `confirm.get_by_text(f'确定删除单据 {number} 吗？', exact=True)` | 定位值由方法参数/运行时变量 `number` 决定，没有静态等价的定位值 |
| 工具-形式发票 | textbox-品牌 | `item.get_by_role('textbox', name='品牌', exact=True)` | 定位值由方法参数/运行时变量 `item` 决定，没有静态等价的定位值 |
| 工具-形式发票 | textbox-商品描述 | `item.get_by_role('textbox', name='商品描述', exact=True)` | 定位值由方法参数/运行时变量 `item` 决定，没有静态等价的定位值 |
| 全局导航（跨页面） | button-button | `main.get_by_role('button', name=entry, exact=True)` | 定位值由方法参数/运行时变量 `entry` 决定，没有静态等价的定位值 |
| 全局导航（跨页面） | heading-heading | `self.page.get_by_role('heading', name=expected_heading, exact=True)` | 定位值由方法参数/运行时变量 `expected_heading` 决定，没有静态等价的定位值 |
| 全局导航（跨页面） | link-link | `main.get_by_role('link', name=entry, exact=True)` | 定位值由方法参数/运行时变量 `entry` 决定，没有静态等价的定位值 |
| 全局导航（跨页面） | text-status | `self.page.get_by_text(status, exact=True)` | 定位值由方法参数/运行时变量 `status` 决定，没有静态等价的定位值 |

## 值被修正的元素（原值与实体化结果语义不等价）

无

## 同名变量跨方法绑定不同（已取首个绑定，使用前请核对）

- 会话工作台 / heading-heading：⚠ 同一表达式在 2 个方法里绑定到不同元素（open_first_mine、open_first_direct_conversation、open_first_unassigned、first_outbound_preview_name），此处取 `open_first_mine` 的绑定，使用前请核对

## 页面对象

只关联「可直接执行」的元素；待人工确认的动态模板不关联（其定位值依赖方法参数，
且值为原始 Python 表达式，会让 generate_code 生成语法错误的代码）。

| 页面对象 | 页面 | 元素数 | 结果 |
| --- | --- | --- | --- |
| ChannelPage | 渠道管理 | 28 | 新建 |
| ChatSharePage | 会话分享页 | 25 | 新建 |
| ConversationPage | 会话工作台 | 72 | 新建 |
| ContactsPage | 客户管理 | 34 | 新建 |
| DataAgentsPage | 数据-客服 | 12 | 新建 |
| DataContactsPage | 数据-客户 | 8 | 新建 |
| DataConversationsPage | 数据-会话 | 10 | 新建 |
| DataMessagesPage | 数据-消息 | 8 | 新建 |
| DataOnlineDurationPage | 数据-在线时长 | 7 | 新建 |
| DataOverviewPage | 数据-概览 | 11 | 新建 |
| DataResponsePage | 数据-响应 | 12 | 新建 |
| GettingStartedPage | 新手引导页 | 6 | 新建 |
| LoginPage | 登录页 | 13 | 新建 |
| RegistrationPage | 注册页 | 11 | 新建 |
| NotificationsPage | 通知中心 | 6 | 新建 |
| PromotionPage | 推广账户 | 23 | 新建 |
| OrganizationSettingsPage | 组织设置-账户 | 23 | 新建 |
| PersonalSettingsPage | 个人设置-资料 | 20 | 新建 |
| ChatShareManagementPage | 工作区设置-会话分享 | 21 | 新建 |
| WorkspaceSettingsPage | 工作区设置-常规 | 137 | 新建 |
| WorkspaceUsagePage | 工作区设置-用量 | 4 | 新建 |
| ToolsPage | 工具-形式发票 | 53 | 新建 |
| Navigation | 全局导航（跨页面） | 4 | 新建 |

## 已知执行链路限制（本次未修改平台代码）

| 定位策略 | test_executor.py（套件执行） | playwright_engine.py（单条运行/MCP） |
| --- | --- | --- |
| CSS | 原样 `page.locator(值)` ✅ | 原样 `page.locator(值)` ✅ |
| role / placeholder / label / title / test-id | 原样透传 ✅ | 会再包一层 `get_by_xxx(值)` ❌ |
| text | 拼成 `text=值` ❌ | `get_by_text(值)` ❌ |
| XPath | 拼成 `xpath=值` ❌ | 拼成 `xpath=值` ❌ |

本命令统一存 CSS，正是为了避开上表差异。

另外 `playwright_engine.py` 的 CSS/XPath 分支里有：

```python
if any(keyword in locator_value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):
```

由于是子串判断，`login`、`blacklist`、`listitem` 这类值也会命中，
从而被强行追加 `>> visible=true` 与 `.first`，
断言「元素隐藏」或「匹配多个」的场景会失效，建议改成按选择器引擎前缀精确判断。

## 会被上述子串判断误伤的元素

以下元素的定位值包含 `dropdown` / `el-select` / `:has(` / `li`，
在 `playwright_engine.py` 里会被追加 `>> visible=true` 与 `.first`：

| 页面 | 元素 | 命中关键词 | 定位值 |
| --- | --- | --- | --- |
| 会话分享页 | first_group_conversation | :has( | `internal:role=main >> article:has(use[*|href="#sub-team"]) >> nth=0` |
| 会话分享页 | first_group_conversation_name | :has( | `internal:role=main >> article:has(use[*|href="#sub-team"]) >> nth=0 >> internal:` |
| 会话工作台 | css-.el-select__wrapper | el-select | `.chat-create-view-dialog >> .chat-view-scope-select >> .el-select__wrapper` |
| 会话工作台 | css-button.blacklist-confirm-ok | li | `button.blacklist-confirm-ok` |
| 会话工作台 | css-link[rel= | li | `link[rel="icon"]` |
| 会话工作台 | css-p.line-through | li | `internal:role=main >> [data-message-id] >> nth=0 >> p.line-through` |
| 会话工作台 | css-use[*|href= | li | `use[*|href="#chat-status-sent"], use[*|href="#chat-status-delivered"]` |
| 全局导航（跨页面） | link-link | li | `main.get_by_role('link', name=entry, exact=True)` |
| 客户管理 | css-.customer-create-drawer .el-select | el-select | `.customer-create-drawer .el-select` |
| 客户管理 | css-.el-select | el-select | `.chat-popover:visible >> nth=0 >> .el-select` |
| 客户管理 | css-.el-select__popper:visible | el-select | `.el-select__popper:visible` |
| 客户管理 | option-.el-select__popper:visible | el-select | `.el-select__popper:visible >> internal:role=option[name="接待成员"s]` |
| 工作区设置-常规 | button-listitem | li | `self.page.get_by_role('listitem').filter(has=self.page.get_by_text(name, exact=T` |
| 工作区设置-常规 | css-xpath=ancestor::div[contains(concat( | li | `switch.locator("xpath=ancestor::div[contains(concat(' ', normalize-space(@class)` |
| 工作区设置-常规 | listitem-listitem | li | `internal:role=listitem` |
| 工具-形式发票 | button-.divert-link-dialog | li | `.divert-link-dialog >> internal:role=button[name="创建"s]` |
| 工具-形式发票 | button-保存 | li | `.divert-link-dialog:visible >> internal:role=button[name="保存"s]` |
| 工具-形式发票 | css-.divert-link-dialog | li | `.divert-link-dialog` |
| 工具-形式发票 | css-.divert-link-dialog:visible | li | `.divert-link-dialog:visible` |
| 工具-形式发票 | css-.el-select__popper:visible | el-select | `.el-select__popper:visible` |
| 工具-形式发票 | option-.el-select__popper:visible | el-select | `self.page.locator('.el-select__popper:visible').get_by_role('option', name=perio` |
| 工具-形式发票 | placeholder-输入备注（仅内部可见） | li | `.divert-link-dialog:visible >> internal:attr=[placeholder="输入备注（仅内部可见）"s]` |
| 数据-会话 | css-main | el-select | `internal:role=main >> .el-select` |
| 数据-响应 | css-main | el-select | `internal:role=main >> .el-select` |
| 数据-客户 | css-main | el-select | `internal:role=main >> .el-select` |
| 数据-客服 | css-main | el-select | `internal:role=main >> .el-select` |
| 数据-概览 | css-.el-select__popper:visible | el-select | `.el-select__popper:visible` |
| 数据-概览 | css-main | el-select | `internal:role=main >> .el-select` |
| 数据-概览 | option-.el-select__popper:visible | el-select | `self.page.locator('.el-select__popper:visible').get_by_role('option', name=perio` |
| 数据-消息 | css-main | el-select | `internal:role=main >> .el-select` |

## 回滚

元素与页面对象都能按项目整体删掉（导入命令本身幂等，重复执行只更新不重复建）：

```bash
# 只删页面对象与关联，保留元素
python manage.py shell -c "from apps.ui_automation.models import PageObject; print(PageObject.objects.filter(project__name='linmi-dev').delete())"

# 删掉整批元素（含分组）
python manage.py shell -c "from apps.ui_automation.models import Element, ElementGroup; print(Element.objects.filter(project__name='linmi-dev').delete()); print(ElementGroup.objects.filter(project__name='linmi-dev').delete())"
```

单独删除某一条元素或页面对象，直接在「UI 自动化 → 元素管理 / 页面对象」界面操作即可。
