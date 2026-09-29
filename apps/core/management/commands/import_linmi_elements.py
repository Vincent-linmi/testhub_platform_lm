# -*- coding: utf-8 -*-
"""
Django管理命令：把 LinMi UI 元素索引导入 TestHub 元素库

数据来源：~/linmi/catalog/ui_element-index.jsonl
（由 linmi-test-automation 的 Page Object 机器抽取，每条记录含真实 locator 表达式）
页面对象结构来源：~/linmi/catalog/ui_surface-index.jsonl（surface → page_class / route / module）

用法：
    python manage.py import_linmi_elements --dry-run      # 预览，不写库
    python manage.py import_linmi_elements                # 导入（幂等：重复执行=更新）
    python manage.py import_linmi_elements --no-reify     # 不启用浏览器实体化，只用字符串规则
    python manage.py import_linmi_elements --no-page-objects
    python manage.py import_linmi_elements --report docs/linmi-element-import-report.md

定位值怎么来的（两条路径，优先第一条）
--------------------------------------
1) **实体化（默认）**：把表达式真的在一个空白 Page 上求值一次，读回 Playwright 自己生成的
   内部选择器（`locator._impl_obj._selector`）。正则、or_ 组合、filter 链、作用域变量
   （row/dialog/main…）都能无损表达，且与原表达式语义完全一致：

       main.get_by_role('button', name=re.compile('^全部'))  → internal:role=main >> internal:role=button[name=/^全部/]
       dialog.get_by_role('switch', name=re.compile('访问密码')).or_(dialog.get_by_role('checkbox', ...))
                                                            → internal:role=dialog >> nth=-1 >> internal:role=switch[name=/访问密码/] >> internal:or="..."

   实现见 apps/ui_automation/linmi_locator_reifier.py（含白名单求值与 3 秒超时，
   不会在求值过程中真的操作页面）。

2) **字符串规则（--no-reify 或实体化失败时）**：覆盖普通写法；正则/or_/作用域变量会失败。

仍无法转换的（定位值由方法参数决定，例如 `name=action`、`get_by_text(status)`）会照旧导入，
但标记 validation_status=PENDING 并把原因写进 validation_message，方便在「元素管理」里筛选后人工处理。
这类记录是「模板」而不是可执行元素，因此 is_enabled=False。

为什么全部存成 CSS 策略
----------------------
TestHub 有两条执行链路——
  apps/ui_automation/test_executor.py      （测试套件执行）
  apps/ui_automation/playwright_engine.py  （单条用例运行 / MCP）
两者对 locator_strategy 的映射表并不一致，例如 text 策略在前者会拼成 `text=值`、
在后者会调用 `get_by_text(值)`。唯一在两边都是「原样交给 page.locator()」的策略是 css，
所以统一存 CSS，值本身是完整的 Playwright 选择器串（含 internal:xxx 引擎前缀），
原始定位语义记录在 description 里。

页面对象
--------
按 ui_surface-index.jsonl 的 page_class 建 23 个 PageObject（如 ChannelPage），
url_pattern 取 route，元素按所属 surface 关联为属性（method_name 由元素名转成合法标识符），
并调用模型的 generate_code('python') 生成模板代码。
"""
import ast
import json
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ui_automation.linmi_locator_reifier import LocatorReifier, Unreifiable
from apps.ui_automation.models import (
    Element, ElementGroup, LocatorStrategy, PageObject, PageObjectElement, UiProject,
)

DEFAULT_SOURCE = Path.home() / 'linmi' / 'catalog' / 'ui_element-index.jsonl'
DEFAULT_SURFACE_INDEX = Path.home() / 'linmi' / 'catalog' / 'ui_surface-index.jsonl'
DEFAULT_LINMI_REPO = Path.home() / 'linmi' / 'linmi-test-automation'
DEFAULT_PROJECT = 'linmi-dev'
DEFAULT_BASE_URL = 'https://dev.linmi.com'

# surface → 中文页面名（ElementGroup 名 + Element.page）
SURFACE_LABELS = {
    'web:navigation': '全局导航（跨页面）',
    'web:/login#login_page': '登录页',
    'web:/login#registration_page': '注册页',
    'web:/getting-started': '新手引导页',
    'web:/chat#conversation_page': '会话工作台',
    'web:/chat#chat_share_page': '会话分享页',
    'web:/channel': '渠道管理',
    'web:/contacts': '客户管理',
    'web:/promotion/account': '推广账户',
    'web:/tools/proforma': '工具-形式发票',
    'web:/data/overview': '数据-概览',
    'web:/data/contacts': '数据-客户',
    'web:/data/conversations': '数据-会话',
    'web:/data/messages': '数据-消息',
    'web:/data/agents': '数据-客服',
    'web:/data/response': '数据-响应',
    'web:/data/onlineDuration': '数据-在线时长',
    'web:/notifications': '通知中心',
    'web:/settings/workspace/general': '工作区设置-常规',
    'web:/settings/workspace/chatShares': '工作区设置-会话分享',
    'web:/settings/workspace/usage': '工作区设置-用量',
    'web:/settings/org/account': '组织设置-账户',
    'web:/settings/personal/profile': '个人设置-资料',
}

# 抽取器给的 kind → TestHub 的 element_type
KIND_TO_TYPE = {
    'button': 'BUTTON',
    'link': 'LINK',
    'input': 'INPUT',
    'textbox': 'INPUT',
    'placeholder': 'INPUT',
    'spinbutton': 'INPUT',
    'select': 'DROPDOWN',
    'combobox': 'DROPDOWN',
    'option': 'DROPDOWN',
    'menu': 'DROPDOWN',
    'checkbox': 'CHECKBOX',
    'switch': 'CHECKBOX',
    'toggle': 'CHECKBOX',
    'radio': 'RADIO',
    'dialog': 'MODAL',
    'table': 'TABLE',
    'columnheader': 'TABLE',
    'row': 'TABLE',
    'cell': 'TABLE',
    'form': 'FORM',
    'image': 'IMAGE',
    'heading': 'TEXT',
    'text': 'TEXT',
    'title': 'TEXT',
    'state': 'TEXT',
    'article': 'TEXT',
    'css': 'CONTAINER',
    'control': 'CONTAINER',
    'container': 'CONTAINER',
    'main': 'CONTAINER',
    'tab': 'CONTAINER',
    'listitem': 'CONTAINER',
}

# 被当作 CSS 标签作用域使用的裸标识符
TAG_SCOPES = {
    'main', 'header', 'footer', 'body', 'article', 'aside', 'nav', 'section',
    'form', 'dialog', 'table', 'tr', 'ul', 'ol', 'li', 'div', 'span', 'p',
}

# page.locator('xpath=...') 这类自带引擎前缀的值 → 策略
ENGINE_PREFIX_STRATEGY = {
    'css': 'CSS',
    'xpath': 'XPath',
    'text': 'text',
    'role': 'role',
    'id': 'ID',
    'label': 'label',
    'placeholder': 'placeholder',
    'title': 'title',
    'testid': 'test-id',
}


class Unconvertible(Exception):
    """该 locator 表达式无法自动转换，需要在元素管理里人工确认"""


def _split_chain(expr):
    """按顶层 '.' 拆调用链。

    self.page.locator('.x').get_by_role('button', name='登录')
      -> ['self', 'page', "locator('.x')", "get_by_role('button', name='登录')"]
    """
    tokens, buf = [], []
    depth, quote, escaped = 0, None, False
    for ch in expr:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if quote:
            buf.append(ch)
            if ch == '\\':
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in '"\'':
            quote = ch
            buf.append(ch)
            continue
        if ch in '([{':
            depth += 1
            buf.append(ch)
            continue
        if ch in ')]}':
            depth -= 1
            buf.append(ch)
            continue
        if ch == '.' and depth == 0:
            tokens.append(''.join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    tail = ''.join(buf).strip()
    if tail:
        tokens.append(tail)
    return tokens


def _parse_call(token):
    """解析单个调用，参数必须是字面量，否则抛 Unconvertible。"""
    name, sep, rest = token.partition('(')
    if not sep or not rest.endswith(')'):
        return None
    try:
        node = ast.parse('_f(' + rest, mode='eval').body
    except SyntaxError:
        return None
    if not isinstance(node, ast.Call):
        return None

    args = []
    for a in node.args:
        if isinstance(a, ast.Constant) and isinstance(a.value, (str, int, float, bool)):
            args.append(a.value)
        else:
            raise Unconvertible('定位参数不是字面量（变量/函数调用），需人工确认')
    kwargs = {}
    for kw in node.keywords:
        if kw.arg is None or not isinstance(kw.value, ast.Constant):
            raise Unconvertible('关键字参数不是字面量，需人工确认')
        kwargs[kw.arg] = kw.value.value
    return name.strip(), args, kwargs


def _quote(value, exact=False):
    """对齐 Playwright 的 escapeForAttributeSelector / escapeForTextSelector：
    exact=True → "值"；否则 → "值"i（大小写不敏感）"""
    v = str(value).replace('\\', '\\\\').replace('"', '\\"')
    return f'"{v}"' if exact else f'"{v}"i'


def _strategy_of_raw(value):
    """locator('xpath=//div') 这类带引擎前缀的值，推断策略"""
    prefix = value.split('=', 1)[0].strip().lower() if '=' in value.split(' ')[0] else ''
    return ENGINE_PREFIX_STRATEGY.get(prefix, 'CSS')


def convert_locator(expr):
    """把 Playwright Python 表达式转成 (strategy, value)。

    无法转换时抛 Unconvertible。
    """
    raw = expr.strip()
    nth = None

    # 尾部 .first / .last / .nth(n) → nth= 后缀
    m = re.search(r'\.(first|last|nth\(\s*\d+\s*\))$', raw)
    if m:
        suffix = m.group(1)
        raw = raw[:m.start()]
        if suffix == 'first':
            nth = 0
        elif suffix == 'last':
            nth = -1
        else:
            nth = int(re.search(r'\d+', suffix).group())

    parts, strategy, scope = [], None, None
    for token in _split_chain(raw):
        if '(' not in token:
            if token in ('self', 'page'):
                continue
            if token in TAG_SCOPES:
                scope = token
                continue
            raise Unconvertible(f'作用域变量 `{token}` 无法解析（需人工补全）')

        parsed = _parse_call(token)
        if not parsed:
            raise Unconvertible(f'无法解析的调用：{token}')
        name, args, kwargs = parsed
        exact = bool(kwargs.get('exact', False))

        if name == 'locator':
            if not args:
                raise Unconvertible('locator() 没有参数')
            value = str(args[0])
            parts.append(value)
            strategy = _strategy_of_raw(value)
        elif name == 'get_by_role':
            if not args:
                raise Unconvertible('get_by_role() 没有 role 参数')
            sel = f'internal:role={args[0]}'
            if kwargs.get('name') is not None:
                sel += f'[name={_quote(kwargs["name"], exact)}]'
            parts.append(sel)
            strategy = 'role'
        elif name == 'get_by_placeholder':
            parts.append(f'internal:attr=[placeholder={_quote(args[0], exact)}]')
            strategy = 'placeholder'
        elif name == 'get_by_text':
            parts.append(f'internal:text={_quote(args[0], exact)}')
            strategy = 'text'
        elif name == 'get_by_label':
            parts.append(f'internal:label={_quote(args[0], exact)}')
            strategy = 'label'
        elif name == 'get_by_title':
            parts.append(f'internal:title={_quote(args[0], exact)}')
            strategy = 'title'
        elif name == 'get_by_alt_text':
            parts.append(f'internal:attr=[alt={_quote(args[0], exact)}]')
            strategy = 'CSS'
        elif name == 'get_by_test_id':
            parts.append(f'internal:testid=[data-testid={_quote(args[0], True)}]')
            strategy = 'test-id'
        else:
            raise Unconvertible(f'不支持的调用：{name}()')

    if not parts:
        raise Unconvertible('表达式里没有可用的定位调用')
    if scope:
        parts.insert(0, scope)

    selector = ' >> '.join(parts)
    if nth is not None:
        selector += f' >> nth={nth}'
    return (strategy or 'CSS'), selector


def _readable(selector):
    """把 Playwright 生成的 \\uXXXX 转义还原成原字符，便于在元素管理里阅读"""
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), selector)


def _canonical(selector):
    """归一化用于「语义是否等价」比较：去掉精确匹配后缀 s、还原转义"""
    text = _readable(selector or '')
    text = re.sub(r'"s(?=[\]\s>]|$)', '"', text)
    return text.strip()


def _double_quote_literals(selector):
    """把 CSS / XPath 段里的单引号字符串换成双引号。

    PageObject.generate_code() 用单引号包裹定位值且不做转义，
    值里出现单引号（如 `xpath=...[@role='switch']`、`[class*='row']`）会生成语法错误的 Python。
    CSS 与 XPath 都允许双引号字符串，这里做等价改写；单引号串内部含双引号时跳过不改。
    internal: 段由 Playwright 生成，本身就是双引号，不需要处理。
    """
    segments = []
    for segment in (selector or '').split(' >> '):
        if not segment.lstrip().startswith('internal:'):
            segment = re.sub(r"'([^'\"\n]*)'", r'"\1"', segment)
        segments.append(segment)
    return ' >> '.join(segments)


def _semantically_same(old, new):
    return _canonical(old) == _canonical(new)


def _pending_reason(rule_message, reify_error):
    """给待人工确认的元素生成一句人能看懂的原因。

    实体化的报错更具体（能指出是哪个方法参数），优先用它，但要把
    Playwright 内部的 TypeError 之类翻译掉，避免报告里出现看不懂的堆栈。
    """
    error = reify_error or ''
    m = re.search(r"name '(\w+)' is not defined", error)
    if m:
        return f'定位值由方法参数/运行时变量 `{m.group(1)}` 决定，没有静态等价的定位值'
    m = re.search(r"_Self' object has no attribute '(\w+)'", error)
    if m:
        return f'定位值依赖实例属性 `{m.group(1)}`（由方法参数决定），没有静态等价的定位值'
    if 'is not JSON serializable' in error:
        return '表达式把定位器当作参数传给了 Playwright 调用，需按具体参数实例化'
    if '求值超时' in error:
        return '求值超时（表达式可能触发了页面操作），需人工确认'
    return rule_message or error or '无法自动转换'


def _identifier(name, used):
    """元素名 → 合法且不重复的属性/方法名"""
    base = re.sub(r'[^0-9A-Za-z_\u4e00-\u9fff]+', '_', name or '').strip('_') or 'element'
    if base[0].isdigit():
        base = '_' + base
    base = base[:90]
    candidate, index = base, 2
    while candidate in used:
        candidate = f'{base}_{index}'
        index += 1
    return candidate


def load_surface_index(path):
    """surface key → {page_class, route, module}"""
    result = {}
    if not path.exists():
        return result
    with path.open(encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            attrs = record.get('attrs') or {}
            key = record.get('key') or attrs.get('key')
            if not key:
                continue
            result[key] = {
                'page_class': attrs.get('page_class') or '',
                'route': attrs.get('route') or '',
                'module': attrs.get('module') or '',
            }
    return result


class Command(BaseCommand):
    help = '把 LinMi UI 元素索引导入 TestHub 元素库（幂等，可重复执行）'

    def add_arguments(self, parser):
        parser.add_argument('--source', default=str(DEFAULT_SOURCE),
                            help=f'元素索引 jsonl 路径（默认 {DEFAULT_SOURCE}）')
        parser.add_argument('--surface-index', default=str(DEFAULT_SURFACE_INDEX),
                            help=f'页面清单 jsonl 路径（默认 {DEFAULT_SURFACE_INDEX}）')
        parser.add_argument('--linmi-repo', default=str(DEFAULT_LINMI_REPO),
                            help=f'LinMi 仓库根目录，用于实体化时读源码（默认 {DEFAULT_LINMI_REPO}）')
        parser.add_argument('--project', default=DEFAULT_PROJECT, help='TestHub 项目名（不存在则创建）')
        parser.add_argument('--base-url', default=None,
                            help=f'项目基础地址（仅在新建项目时使用，默认 {DEFAULT_BASE_URL}）')
        parser.add_argument('--user', default=None, help='创建人用户名（默认第一个超级用户）')
        parser.add_argument('--dry-run', action='store_true', help='只预览，不写数据库')
        parser.add_argument('--no-reify', dest='reify', action='store_false',
                            help='关闭浏览器实体化，只用字符串规则转换')
        parser.add_argument('--no-page-objects', dest='page_objects', action='store_false',
                            help='不创建/更新页面对象')
        parser.add_argument('--report', default=None, help='把导入报告写到指定 Markdown 文件')

    # ---------- 转换 ----------

    def _convert(self, records, reifier):
        """逐条转换。reifier 为 None 时只用字符串规则。返回 (items, stats)"""
        items = []
        stats = {'reified': 0, 'reified_from_pending': 0, 'rule': 0, 'pending': 0, 'notes': []}

        for rec in records:
            attrs = rec.get('attrs') or {}
            surface = attrs.get('surface') or 'unknown'
            expr = attrs.get('locator') or ''
            item = {
                'name': attrs.get('element') or rec.get('title') or rec.get('key'),
                'surface': surface,
                'page_label': SURFACE_LABELS.get(surface, surface),
                'kind': attrs.get('kind') or '',
                'element_type': KIND_TO_TYPE.get(attrs.get('kind'), 'CONTAINER'),
                'component': attrs.get('owner_class') or '',
                'expr': expr,
                'ref': (rec.get('source') or {}).get('ref', ''),
                'used_by': attrs.get('used_by') or [],
                'aliases': rec.get('aliases') or [],
                'confidence': rec.get('confidence') or '',
                'note': '',
            }

            # 1) 实体化
            if reifier is not None and expr:
                try:
                    selector, note = reifier.reify(expr, item['ref'], item['used_by'])
                    item.update(value=_double_quote_literals(_readable(selector)), semantic='实体化',
                                status='VALID', message='', origin='reify')
                    item['note'] = note
                    stats['reified'] += 1
                    if note:
                        stats['notes'].append((item['page_label'], item['name'], note))
                    items.append(item)
                    continue
                except Unreifiable as exc:
                    item['reify_error'] = str(exc)
                except Exception as exc:            # 兜底，不让单条脏数据中断
                    item['reify_error'] = f'{type(exc).__name__}: {exc}'

            # 2) 字符串规则
            try:
                semantic, value = convert_locator(expr)
                item.update(value=value, semantic=semantic, status='VALID', message='')
                item['origin'] = 'rule'
                stats['rule'] += 1
            except Unconvertible as exc:
                item.update(value=expr, semantic='未识别', status='PENDING', message=str(exc))
                item['origin'] = 'pending'
                stats['pending'] += 1
            except Exception as exc:
                item.update(value=expr, semantic='未识别', status='PENDING',
                            message=f'{type(exc).__name__}: {exc}')
                item['origin'] = 'pending'
                stats['pending'] += 1
            if item['origin'] == 'pending':
                item['message'] = _pending_reason(item.get('message'), item.get('reify_error'))
            items.append(item)

        return items, stats

    # ---------- 页面对象 ----------

    def _import_page_objects(self, project, surface_index, creator, dry_run):
        """按 surface 建/更新 PageObject，并把该页元素关联为属性

        只关联 validation_status=VALID 的元素：PENDING 的定位值由方法参数决定，
        本身不可执行，而且值是原始 Python 表达式（含单引号），
        会让 PageObject.generate_code() 生成出语法错误的代码。
        """
        elements_by_page = {}
        for element in Element.objects.filter(
                project=project, validation_status='VALID').order_by('order', 'name'):
            elements_by_page.setdefault(element.page, []).append(element)

        created = updated = linked = removed = 0
        report = []
        for surface_key, meta in sorted(surface_index.items()):
            page_class = meta['page_class']
            label = SURFACE_LABELS.get(surface_key, surface_key)
            elements = elements_by_page.get(label) or []
            if not page_class or not elements:
                continue
            if dry_run:
                report.append((page_class, label, len(elements), 'dry-run'))
                continue

            page_object, is_new = PageObject.objects.update_or_create(
                project=project, name=page_class,
                defaults={
                    'class_name': page_class,
                    'url_pattern': meta.get('route') or '',
                    'description': f"LinMi 页面：{label}\n来源：{meta.get('module')}",
                    'created_by': creator,
                },
            )
            created += int(is_new)
            updated += int(not is_new)
            report.append((page_class, label, len(elements), '新建' if is_new else '更新'))

            used, keep = set(), set()
            for order, element in enumerate(elements):
                method_name = _identifier(element.name, used)
                used.add(method_name)
                keep.add(method_name)
                PageObjectElement.objects.update_or_create(
                    page_object=page_object, method_name=method_name,
                    defaults={'element': element, 'is_property': True, 'order': order},
                )
                linked += 1
            stale = page_object.page_object_elements.exclude(method_name__in=keep)
            removed += stale.count()
            stale.delete()

            page_object.template_code = page_object.generate_code('python')
            page_object.save(update_fields=['template_code'])

        return {'created': created, 'updated': updated, 'linked': linked,
                'removed': removed, 'pages': report}

    # ---------- 报告 ----------

    def _write_report(self, path, context):
        lines = ['# LinMi UI 元素导入报告', '']
        lines.append(f"- 元素索引：`{context['source']}`")
        lines.append(f"- 页面清单：`{context['surface_index']}`")
        lines.append(f"- 目标项目：`{context['project']}`")
        lines.append(f"- 元素总数：{context['total']}，其中可直接执行 "
                     f"{context['valid']}，待人工确认 {context['pending']}")
        lines.append(f"- 实体化成功：{context['reified']}，字符串规则：{context['rule']}")
        lines.append(f"- 本次运行新转正（原为待确认）：{context['promoted']}")
        lines.append(f"- 本次运行修正定位值：{len(context['changed'])}")
        lines.append('')

        lines += ['## 待人工确认的元素（定位值由方法参数决定）', '']
        if context['pending_items']:
            lines += ['| 页面 | 元素 | 原始表达式 | 原因 |', '| --- | --- | --- | --- |']
            for page, name, expr, message in context['pending_items']:
                lines.append(f"| {page} | {name} | `{expr[:70]}` | {message[:80]} |")
        else:
            lines.append('无')
        lines += ['']

        lines += ['## 值被修正的元素（原值与实体化结果语义不等价）', '']
        if context['changed']:
            lines += ['| 页面 | 元素 | 原值 | 新值 |', '| --- | --- | --- | --- |']
            for page, name, old, new in context['changed']:
                lines.append(f"| {page} | {name} | `{old[:70]}` | `{new[:70]}` |")
        else:
            lines.append('无')
        lines += ['']

        lines += ['## 同名变量跨方法绑定不同（已取首个绑定，使用前请核对）', '']
        if context['notes']:
            for page, name, note in context['notes']:
                lines.append(f"- {page} / {name}：{note}")
        else:
            lines.append('无')
        lines += ['']

        lines += ['## 页面对象', '',
                  '只关联「可直接执行」的元素；待人工确认的动态模板不关联（其定位值依赖方法参数，',
                  '且值为原始 Python 表达式，会让 generate_code 生成语法错误的代码）。', '',
                  '| 页面对象 | 页面 | 元素数 | 结果 |', '| --- | --- | --- | --- |']
        for page_class, label, count, result in context['pages']:
            lines.append(f"| {page_class} | {label} | {count} | {result} |")
        lines += ['']

        lines += ['## 已知执行链路限制（本次未修改平台代码）', '',
                  '| 定位策略 | test_executor.py（套件执行） | playwright_engine.py（单条运行/MCP） |',
                  '| --- | --- | --- |',
                  '| CSS | 原样 `page.locator(值)` ✅ | 原样 `page.locator(值)` ✅ |',
                  '| role / placeholder / label / title / test-id | 原样透传 ✅ | 会再包一层 `get_by_xxx(值)` ❌ |',
                  '| text | 拼成 `text=值` ❌ | `get_by_text(值)` ❌ |',
                  '| XPath | 拼成 `xpath=值` ❌ | 拼成 `xpath=值` ❌ |',
                  '',
                  '本命令统一存 CSS，正是为了避开上表差异。',
                  '',
                  '另外 `playwright_engine.py` 的 CSS/XPath 分支里有：',
                  '',
                  '```python',
                  "if any(keyword in locator_value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):",
                  '```',
                  '',
                  "由于是子串判断，`login`、`blacklist`、`listitem` 这类值也会命中，",
                  '从而被强行追加 `>> visible=true` 与 `.first`，',
                  '断言「元素隐藏」或「匹配多个」的场景会失效，建议改成按选择器引擎前缀精确判断。',
                  '']

        lines += ['## 会被上述子串判断误伤的元素', '',
                  '以下元素的定位值包含 `dropdown` / `el-select` / `:has(` / `li`，',
                  '在 `playwright_engine.py` 里会被追加 `>> visible=true` 与 `.first`：', '']
        if context['risky']:
            lines += ['| 页面 | 元素 | 命中关键词 | 定位值 |', '| --- | --- | --- | --- |']
            for page, name, value, hits in context['risky']:
                lines.append(f"| {page} | {name} | {hits} | `{value[:80]}` |")
        else:
            lines.append('无')
        lines += ['']

        lines += ['## 回滚', '',
                  '元素与页面对象都能按项目整体删掉（导入命令本身幂等，重复执行只更新不重复建）：', '',
                  '```bash',
                  '# 只删页面对象与关联，保留元素',
                  "python manage.py shell -c \"from apps.ui_automation.models import PageObject; "
                  "print(PageObject.objects.filter(project__name='linmi-dev').delete())\"",
                  '',
                  '# 删掉整批元素（含分组）',
                  "python manage.py shell -c \"from apps.ui_automation.models import Element, ElementGroup; "
                  "print(Element.objects.filter(project__name='linmi-dev').delete()); "
                  "print(ElementGroup.objects.filter(project__name='linmi-dev').delete())\"",
                  '```',
                  '',
                  '单独删除某一条元素或页面对象，直接在「UI 自动化 → 元素管理 / 页面对象」界面操作即可。',
                  '']
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text('\n'.join(lines), encoding='utf-8')

    # ---------- 主流程 ----------

    def handle(self, *args, **options):
        source = Path(options['source']).expanduser()
        dry_run = options['dry_run']

        if not source.exists():
            self.stderr.write(self.style.ERROR(f'找不到元素索引文件：{source}'))
            return

        records = []
        with source.open(encoding='utf-8') as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    self.stderr.write(f'第 {lineno} 行 JSON 解析失败，已跳过：{exc}')

        self.stdout.write(f'读取 {source}：{len(records)} 条元素记录')

        reifier = None
        if options['reify']:
            reifier = LocatorReifier(Path(options['linmi_repo']).expanduser())
            reifier.__enter__()
            self.stdout.write('已启用浏览器实体化（读源码解析作用域变量）')
        try:
            items, stats = self._convert(records, reifier)
        finally:
            if reifier is not None:
                reifier.close()

        converted = [i for i in items if i['status'] == 'VALID']
        pending = [i for i in items if i['status'] == 'PENDING']

        by_semantic = {}
        for item in items:
            by_semantic[item['semantic']] = by_semantic.get(item['semantic'], 0) + 1
        surfaces = {}
        for item in items:
            surfaces[item['page_label']] = surfaces.get(item['page_label'], 0) + 1

        self.stdout.write('')
        self.stdout.write(f"可直接执行（VALID）  ：{len(converted)} 条")
        self.stdout.write(f"待人工确认（PENDING）：{len(pending)} 条")
        self.stdout.write(f"实体化成功：{stats['reified']} 条；字符串规则：{stats['rule']} 条")
        self.stdout.write(f"按转换方式：{dict(sorted(by_semantic.items(), key=lambda kv: -kv[1]))}")
        self.stdout.write('按页面分组：')
        for label, count in sorted(surfaces.items(), key=lambda kv: -kv[1]):
            self.stdout.write(f'  {count:>4}  {label}')

        if pending:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'待人工确认的 {len(pending)} 条（原因）：'))
            reasons = {}
            for item in pending:
                reasons.setdefault(item['message'], []).append(item['name'])
            for reason, names in sorted(reasons.items(), key=lambda kv: -len(kv[1])):
                self.stdout.write(f'  {len(names):>4} 条  {reason[:90]}')
                self.stdout.write(f'        例：{", ".join(names[:3])}')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('--dry-run：未写入数据库'))
            return

        user_model = get_user_model()
        creator = None
        if options['user']:
            creator = user_model.objects.filter(username=options['user']).first()
        if creator is None:
            creator = user_model.objects.filter(is_superuser=True).order_by('id').first()

        strategies = {s.name.lower(): s for s in LocatorStrategy.objects.all()}
        if not strategies:
            self.stderr.write(self.style.ERROR(
                '定位策略表为空，请先执行：python manage.py init_locator_strategies'))
            return

        created = updated = 0
        promoted = 0
        changed = []
        missing_strategy = set()

        with transaction.atomic():
            project = UiProject.objects.filter(name=options['project']).first()
            if project is None:
                project = UiProject.objects.create(
                    name=options['project'],
                    base_url=options['base_url'] or DEFAULT_BASE_URL,
                    description='LinMi 项目（元素由 import_linmi_elements 从 '
                                'linmi-test-automation 的 Page Object 导入）',
                    owner=creator,
                )
            # 元素列表接口只返回「自己是 owner 或团队成员」的项目，这里确保能看到
            if creator is not None:
                project.members.add(creator)
            if options['base_url'] and project.base_url != options['base_url']:
                project.base_url = options['base_url']
                project.save(update_fields=['base_url'])

            existing = {(e.page, e.name): e for e in Element.objects.filter(project=project)}
            group_cache = {}

            def get_group(label, surface):
                if label not in group_cache:
                    group, _ = ElementGroup.objects.get_or_create(
                        project=project, name=label,
                        defaults={'description': f'LinMi 页面：{surface}'},
                    )
                    group_cache[label] = group
                return group_cache[label]

            for order, item in enumerate(items):
                strategy = strategies.get('css')
                if strategy is None:
                    missing_strategy.add('CSS')
                    continue

                # 已存在且语义等价 → 保留原值，避免只差一个精确后缀就整批改写
                value = item['value']
                previous = existing.get((item['page_label'], item['name']))
                if previous is not None and item['status'] == 'VALID' \
                        and previous.validation_status == 'VALID' \
                        and _semantically_same(previous.locator_value, value):
                    value = previous.locator_value
                elif previous is not None and item['status'] == 'VALID' \
                        and previous.validation_status == 'PENDING':
                    promoted += 1
                elif previous is not None and item['status'] == 'VALID' \
                        and not _semantically_same(previous.locator_value, value):
                    changed.append((item['page_label'], item['name'],
                                    previous.locator_value, value))

                description = '\n'.join(filter(None, [
                    f"定位语义：{item['semantic']}（TestHub 统一存 CSS，值为完整 Playwright 选择器）",
                    f"来源：{item['ref']}" + (f"（{item['component']}）" if item['component'] else ''),
                    f"原始表达式：{item['expr']}",
                    item['note'],
                    f"别名：{', '.join(map(str, item['aliases']))}" if item['aliases'] else '',
                    f"被 {len(item['used_by'])} 个页面方法引用" if item['used_by'] else '',
                    f"抽取置信度：{item['confidence']}" if item['confidence'] else '',
                    '⚠ 该元素定位值依赖方法参数，不能直接执行，需按具体参数建实例'
                    if item['status'] == 'PENDING' else '',
                ]))

                _, was_created = Element.objects.update_or_create(
                    project=project,
                    page=item['page_label'],
                    name=item['name'],
                    defaults={
                        'group': get_group(item['page_label'], item['surface']),
                        'description': description,
                        'element_type': item['element_type'],
                        'locator_strategy': strategy,
                        'locator_value': value[:500],
                        'component_name': item['component'][:100],
                        'order': order,
                        'validation_status': item['status'],
                        'validation_message': item['message'][:500],
                        'created_by': creator,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)

            page_stats = None
            if options['page_objects']:
                surface_index = load_surface_index(Path(options['surface_index']).expanduser())
                if not surface_index:
                    self.stdout.write(self.style.WARNING(
                        f'页面清单为空或不存在：{options["surface_index"]}，跳过页面对象'))
                else:
                    page_stats = self._import_page_objects(project, surface_index, creator, dry_run)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'导入完成：项目「{project.name}」（id={project.id}，base_url={project.base_url}）'))
        self.stdout.write(self.style.SUCCESS(
            f'新建元素 {created} 条，更新元素 {updated} 条，页面分组 {len(group_cache)} 个'))
        self.stdout.write(f'其中：待确认转正 {promoted} 条，值被修正 {len(changed)} 条')
        if page_stats:
            self.stdout.write(self.style.SUCCESS(
                f"页面对象：新建 {page_stats['created']}，更新 {page_stats['updated']}，"
                f"元素关联 {page_stats['linked']}，清理失效关联 {page_stats['removed']}"))
        if missing_strategy:
            self.stdout.write(self.style.WARNING(
                f'定位策略表里缺这些策略，已回退为 CSS：{sorted(missing_strategy)}'))

        risky = []
        for element in Element.objects.filter(project=project):
            value = (element.locator_value or '').lower()
            hits = [kw for kw in ('dropdown', 'el-select', ':has(', 'li') if kw in value]
            if hits:
                risky.append((element.page, element.name, element.locator_value, '、'.join(hits)))

        if options['report']:
            self._write_report(options['report'], {
                'risky': risky,
                'source': source,
                'surface_index': options['surface_index'],
                'project': project.name,
                'total': len(items),
                'valid': len(converted),
                'pending': len(pending),
                'reified': stats['reified'],
                'rule': stats['rule'],
                'promoted': promoted,
                'pending_items': [(i['page_label'], i['name'], i['expr'], i['message'])
                                  for i in pending],
                'changed': changed,
                'notes': stats['notes'],
                'pages': page_stats['pages'] if page_stats else [],
            })
            self.stdout.write(f"报告已写入：{options['report']}")

        self.stdout.write('在「UI 自动化 → 元素管理 / 页面对象」里选择项目即可看到。')
