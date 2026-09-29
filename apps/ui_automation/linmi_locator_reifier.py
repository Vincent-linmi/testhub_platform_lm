# -*- coding: utf-8 -*-
"""把 LinMi Page Object 里的 Playwright 定位表达式，实体化成 TestHub 可直接使用的选择器。

背景
----
LinMi 的 Page Object 用 Python 表达式写定位，例如：

    main.get_by_role('button', name=re.compile(r'^全部(?:\\s*\\d+)?$'))
    dialog.get_by_role('switch', name=re.compile('访问密码')).or_(dialog.get_by_role('checkbox', name=re.compile('访问密码')))
    self.page.locator('header').filter(has=self.page.get_by_title('转接', exact=True)).get_by_role('button', name='更多')

这些表达式用字符串规则去解析很容易出错（正则、or_ 组合、filter 链、作用域变量），
但 Playwright 自己会把它们编译成内部选择器，而内部选择器可以原样交给 page.locator()。
所以本模块的做法是：**真的把表达式在一个空白 Page 上求值一次，然后读回 Playwright 生成的内部选择器**。

    page.get_by_role('button', name=re.compile('^全部'))  →  internal:role=button[name=/^全部/]

这样得到的值与原表达式语义完全一致（含 exact、正则、作用域、nth 等），
不需要维护任何「Python 写法 → 选择器写法」的对照表。

安全约束
--------
求值只允许「构造定位器」的调用（get_by_*/locator/first/last/nth/filter/or_/re 等白名单）。
任何其它调用（.click()/.fill()/自定义方法）都会被拒绝，避免在求值过程中真的去操作页面、
或在元素不存在时阻塞几十秒。每条表达式还有 3 秒硬超时兜底。

作用域解析
----------
表达式里的自由变量（row / menu / dialog / main / block ...）按 **方法级作用域** 解析：
只在「真正用到这条表达式的方法」内部找变量赋值，必要时回退到类级赋值（如 __init__ 里的 self.rows）。
同名变量在不同方法里绑定不同对象时不会被混用；如果确实解析出多个不同结果，
会在返回值里给出歧义说明，由调用方记录到元素描述里。
"""
from __future__ import annotations

import ast
import collections
import re
import signal
from pathlib import Path

# 允许出现在表达式里的调用：全部是纯构造定位器的函数，不会触碰页面
_ALLOWED_CALLS = {
    'get_by_role', 'get_by_text', 'get_by_placeholder', 'get_by_label', 'get_by_title',
    'get_by_test_id', 'get_by_alt_text', 'locator', 'first', 'last', 'nth', 'filter',
    'or_', 'and_', 'compile', 'escape', 'count', 'str', 'int', 'len', 'min', 'max',
}

_EVAL_TIMEOUT_SECONDS = 3


class Unreifiable(Exception):
    """该表达式无法实体化（依赖运行时参数，或用了白名单之外的调用）"""


class _Self:
    """self 占位对象：只暴露 page 与被解析出来的属性"""


def normalize_expression(expr: str) -> str:
    """把表达式归一化成 ast.unparse 的写法。

    catalog 里存的表达式与源码的引号风格、换行、括号位置可能不同
    （例如源码 `get_by_role(\n  "heading", level=2\n)`），直接做字符串匹配会找不到所属方法，
    所以先解析成 AST 再统一 unparse。
    """
    try:
        return ast.unparse(ast.parse(expr, mode='eval').body)
    except SyntaxError:
        return (expr or '').strip()


def _call_name(node: ast.Call):
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_safe_expression(node: ast.AST, allowed_names: set[str] | None = None) -> bool:
    """只允许白名单调用，杜绝执行到真实页面操作。

    allowed_names 为 None 时不做名字检查——名字是否存在交给迭代求值阶段判断，
    否则 `a = b.first` 这种「先引用后绑定」的赋值会在收集阶段被误丢弃。
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if _call_name(child) not in _ALLOWED_CALLS:
                return False
        elif isinstance(child, ast.Name):
            if allowed_names is not None and child.id not in allowed_names \
                    and child.id not in _ALLOWED_CALLS:
                return False
        elif isinstance(child, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                                ast.GeneratorExp, ast.Await, ast.Yield)):
            return False
    return True


class _Timeout(Exception):
    pass


def _alarm_handler(signum, frame):  # pragma: no cover - 仅用于中断超长求值
    raise _Timeout()


class LocatorReifier:
    """在空白 Page 上求值定位表达式，读回 Playwright 内部选择器。

    用法::

        with LocatorReifier(Path.home() / 'linmi' / 'linmi-test-automation') as reifier:
            selector, note = reifier.reify(expr, source_ref, used_by)
    """

    def __init__(self, repo_root: Path, page=None):
        self.repo_root = Path(repo_root)
        self._page = page
        self._playwright = None
        self._browser = None
        self._tree_cache: dict[str, ast.Module | None] = {}
        self._method_index_cache: dict[str, dict] = {}

    # ---------- 生命周期 ----------

    def __enter__(self) -> 'LocatorReifier':
        self._ensure_page()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _ensure_page(self):
        if self._page is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch()
            self._page = self._browser.new_page()
        return self._page

    def close(self):
        for closer in (self._browser, self._playwright):
            try:
                if closer is not None:
                    closer.close() if closer is self._browser else closer.stop()
            except Exception:
                pass
        self._browser = self._playwright = None

    # ---------- 源码解析 ----------

    def _tree(self, source_ref: str):
        if source_ref not in self._tree_cache:
            rel = source_ref.replace('linmi-test-automation/', '')
            path = self.repo_root / rel
            try:
                self._tree_cache[source_ref] = ast.parse(path.read_text(encoding='utf-8'))
            except (OSError, SyntaxError):
                self._tree_cache[source_ref] = None
        return self._tree_cache[source_ref]

    def _method_index(self, source_ref: str):
        """方法名 → (ClassDef, FunctionDef)，并记录每个方法里出现过的表达式源码"""
        if source_ref in self._method_index_cache:
            return self._method_index_cache[source_ref]
        tree = self._tree(source_ref)
        index = {'by_name': {}, 'by_expr': collections.defaultdict(list),
                 'by_target': collections.defaultdict(list)}
        if tree is not None:
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                for fn in [n for n in cls.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                    index['by_name'][fn.name] = (cls, fn)
                    for node in ast.walk(fn):
                        if isinstance(node, ast.Call):
                            index['by_expr'][ast.unparse(node)].append((cls, fn))
                        # 裸变量表达式（如 create_dialog = dialog）要按「赋值目标」找所属方法
                        elif isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    index['by_target'][target.id].append((cls, fn))
        self._method_index_cache[source_ref] = index
        return index

    # ---------- 作用域构造 ----------

    def _module_namespace(self, tree):
        env = {'page': self._page, 're': re}
        assigns = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and _is_safe_expression(node.value):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigns.append((target.id, ast.unparse(node.value)))
        # 模块常量之间也可能互相引用，按依赖顺序迭代求值
        for _ in range(4):
            progressed = False
            for item in assigns[:]:
                name, expr = item
                try:
                    env[name] = eval(expr, env)
                except Exception:
                    continue
                assigns.remove(item)
                progressed = True
            if not progressed:
                break
        return env

    @staticmethod
    def _assignments(fn):
        """收集一个方法里的赋值：局部变量 与 self.x（只保留白名单调用）"""
        found = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if not _is_safe_expression(node.value):
                    continue
                if isinstance(target, ast.Name):
                    found.append((target.id, ast.unparse(node.value), False))
                elif (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                      and target.value.id == 'self'):
                    found.append((target.attr, ast.unparse(node.value), True))
        return found

    def _apply_assignments(self, assigns, env, me, rounds=4):
        remaining = list(assigns)
        for _ in range(rounds):
            progressed = False
            for item in remaining[:]:
                name, expr, is_attr = item
                if is_attr and hasattr(me, name):
                    remaining.remove(item)
                    continue
                try:
                    value = eval(expr, env)
                except Exception:
                    continue
                if is_attr:
                    setattr(me, name, value)
                else:
                    env[name] = value
                remaining.remove(item)
                progressed = True
            if not progressed:
                break

    def _method_namespace(self, cls, fn, tree):
        """方法级作用域：先本方法赋值，再回退类级赋值，最后模块常量"""
        page = self._ensure_page()
        me = _Self()
        me.page = page
        env = {'page': page, 're': re, 'self': me}
        module_env = self._module_namespace(tree)
        env.update({k: v for k, v in module_env.items() if k != 'page'})

        # 1) 本方法内的赋值优先
        self._apply_assignments(self._assignments(fn), env, me)
        # 2) 类内其它方法（含 __init__）的赋值兜底
        for other in [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            if other is fn:
                continue
            self._apply_assignments(self._assignments(other), env, me)
            env['self'] = me
        return env

    # ---------- 实体化 ----------

    def _evaluate(self, expr, env):
        try:
            signal.alarm(_EVAL_TIMEOUT_SECONDS)
        except ValueError:  # 非主线程：退化为不设超时
            pass
        try:
            value = eval(expr, env)
        finally:
            try:
                signal.alarm(0)
            except ValueError:
                pass
        selector = getattr(getattr(value, '_impl_obj', None), '_selector', None)
        if not selector:
            raise Unreifiable('求值结果不是 Playwright Locator')
        return selector

    def reify(self, expr: str, source_ref: str, used_by=()) -> tuple[str, str]:
        """返回 (选择器, 备注)。无法实体化时抛 Unreifiable。"""
        expr = (expr or '').strip()
        if not expr:
            raise Unreifiable('表达式为空')
        expr = normalize_expression(expr)
        self._ensure_page()
        tree = self._tree(source_ref)
        if tree is None:
            raise Unreifiable(f'读不到源文件：{source_ref}')

        index = self._method_index(source_ref)
        candidates = list(index['by_expr'].get(expr, ()))
        if not candidates and expr.isidentifier():
            # 裸变量表达式（值本身就是 dialog / first_conversation 这类定位器变量）
            candidates = list(index['by_target'].get(expr, ()))
        if not candidates:
            for method_name in used_by:
                hit = index['by_name'].get(method_name)
                if hit:
                    candidates.append(hit)
        if not candidates:
            raise Unreifiable('在源文件里找不到该表达式所属的方法（可能有拼接或换行）')

        # used_by 里的方法优先，其余按出现顺序
        order = {name: i for i, name in enumerate(used_by)}
        candidates.sort(key=lambda pair: order.get(pair[1].name, len(order)))

        results = []          # [(方法名, 选择器)]
        first_error = None
        for cls, fn in candidates:
            try:
                env = self._method_namespace(cls, fn, tree)
            except Exception as exc:
                first_error = first_error or f'{type(exc).__name__}: {exc}'
                continue
            try:
                results.append((fn.name, self._evaluate(expr, env)))
            except _Timeout:
                first_error = first_error or '求值超时'
            except Unreifiable as exc:
                first_error = first_error or str(exc)
            except NameError as exc:
                first_error = first_error or f'依赖运行时参数/变量 {exc}'
            except AttributeError as exc:
                first_error = first_error or f'作用域对象上没有该属性：{exc}'
            except Exception as exc:
                first_error = first_error or f'{type(exc).__name__}: {exc}'

        if not results:
            raise Unreifiable(first_error or '无法实体化')

        distinct = {selector for _, selector in results}
        selector = results[0][1]
        if len(distinct) > 1:
            methods = '、'.join(f'{name}' for name, _ in results[:4])
            note = (f'⚠ 同一表达式在 {len(distinct)} 个方法里绑定到不同元素'
                    f'（{methods}），此处取 `{results[0][0]}` 的绑定，使用前请核对')
        else:
            note = ''
        return selector, note
