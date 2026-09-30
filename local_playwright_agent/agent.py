"""On-demand TestHub Playwright runner.

The process is launched by the ``testhub-runner://`` URL protocol, claims exactly
one job, uploads its artifacts, releases Playwright, and exits.
"""

import argparse
import asyncio
import hashlib
import ipaddress
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

if getattr(sys, 'frozen', False):
    if platform.system() == 'Darwin':
        bundled_browsers = Path.home() / 'Library' / 'Application Support' / 'TestHubRunner' / 'ms-playwright'
    else:
        bundled_browsers = Path(sys.executable).resolve().parent / 'ms-playwright'
    if bundled_browsers.exists():
        os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(bundled_browsers))

from playwright.async_api import async_playwright


try:
    from local_playwright_agent.step_runtime import (RUNNER_VERSION, CAPABILITY, EXTENDED_ACTIONS, PAGE_ASSERTIONS,
        prepare_contract, playwright_locator, execute_playwright_extension, resolve_timeout_ms)
except ImportError:  # PyInstaller and direct script launch
    from step_runtime import (RUNNER_VERSION, CAPABILITY, EXTENDED_ACTIONS, PAGE_ASSERTIONS,
        prepare_contract, playwright_locator, execute_playwright_extension, resolve_timeout_ms)

USER_AGENT = f'TestHub-Local-Runner/{RUNNER_VERSION}'
LOGGER = logging.getLogger('testhub_runner')


def _config_path():
    if platform.system() == 'Darwin':
        return Path.home() / 'Library' / 'Application Support' / 'TestHubRunner' / 'config.json'
    base = os.environ.get('LOCALAPPDATA') or str(Path.home() / '.config')
    return Path(base) / 'TestHubRunner' / 'config.json'


def _log_path():
    return _config_path().parent / 'runner.log'


def _setup_logging():
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=2, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    return path


def _show_macos_error(message):
    if platform.system() != 'Darwin':
        return
    script = (
        'on run argv\n'
        'display alert "TestHub Runner 启动失败" message (item 1 of argv) '
        'as critical buttons {"知道了"} default button "知道了"\n'
        'end run'
    )
    try:
        subprocess.run(
            ['osascript', '-e', script, str(message)],
            check=False,
            timeout=30,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _load_allowed_origin():
    configured = os.environ.get('TESTHUB_SERVER_ORIGIN', '').rstrip('/')
    if configured:
        return configured
    path = _config_path()
    if path.exists():
        return str(json.loads(path.read_text(encoding='utf-8-sig')).get('server_origin', '')).rstrip('/')
    return ''


def _origin(url):
    parsed = urlparse(url)
    return f'{parsed.scheme}://{parsed.netloc}'.rstrip('/')


def _is_allowed_server_url(url):
    """Allow HTTP only for loopback/private-network development servers."""
    parsed = urlparse(url)
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {'', '/'}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return False
    if parsed.scheme == 'https':
        return True
    if parsed.scheme != 'http':
        return False

    hostname = parsed.hostname.lower().rstrip('.')
    if hostname == 'localhost' or hostname.endswith('.local'):
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or address.is_private


def _parse_launch_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'testhub-runner' or parsed.netloc != 'execute':
        raise ValueError('无效的 TestHub Runner 启动链接')
    params = parse_qs(parsed.query)
    claim_url = params.get('claim_url', [''])[0]
    launch_code = params.get('code', [''])[0]
    if not claim_url or not launch_code:
        raise ValueError('启动链接缺少 claim_url 或 code')

    allowed_origin = _load_allowed_origin()
    if not allowed_origin:
        raise ValueError(f'尚未配置 TestHub 服务地址，请检查 {_config_path()}')
    if _origin(claim_url).lower() != allowed_origin.lower():
        raise ValueError('启动链接的服务器与本机配置不一致，已拒绝领取任务')
    if not _is_allowed_server_url(_origin(claim_url)):
        raise ValueError('HTTP 仅允许 localhost、.local 主机名或局域网私有 IP；公网服务必须使用 HTTPS')
    return claim_url, launch_code


class JobClient:
    def __init__(self, claim_url, launch_code):
        self.claim_url = claim_url
        self.launch_code = launch_code
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.job = None

    def claim(self):
        response = self.session.post(
            self.claim_url,
            json={'launch_code': self.launch_code, 'protocol_version': 3, 'capabilities': [CAPABILITY]},
            timeout=30,
        )
        if not response.ok:
            LOGGER.error('领取任务失败: HTTP %s %s', response.status_code, response.text[:1000])
        response.raise_for_status()
        self.job = response.json()
        claim_origin = _origin(self.claim_url)
        for name, url in self.job.get('urls', {}).items():
            parsed = urlparse(url)
            if _origin(url).lower() != claim_origin.lower():
                corrected = f'{claim_origin}{parsed.path}'
                if parsed.query:
                    corrected = f'{corrected}?{parsed.query}'
                LOGGER.warning('修正任务地址 %s: %s -> %s', name, url, corrected)
                self.job['urls'][name] = corrected
        self.session.headers.update({'Authorization': f"Bearer {self.job['upload_token']}"})
        return self.job

    def event(self, event_type, **data):
        payload = {'type': event_type, 'timestamp': time.time(), **data}
        try:
            response = self.session.post(self.job['urls']['events'], json=payload, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f'事件上传失败，将继续执行: {exc}', file=sys.stderr)

    def download_asset(self, asset, destination):
        url = f"{self.job['urls']['files']}{asset['id']}/"
        with self.session.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            digest = hashlib.sha256()
            with destination.open('wb') as output:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        digest.update(chunk)
                        output.write(chunk)
        if asset.get('sha256') and digest.hexdigest() != asset['sha256']:
            destination.unlink(missing_ok=True)
            raise ValueError(f"测试文件校验失败: {asset['name']}")

    def artifact(self, path, artifact_type):
        with path.open('rb') as file_handle:
            response = self.session.post(
                self.job['urls']['artifacts'],
                data={'artifact_type': artifact_type},
                files={'file': (path.name, file_handle, 'application/octet-stream')},
                timeout=300,
            )
        response.raise_for_status()
        return response.json()

    def complete(self, success, duration, step_results, error_message='', row_results=None, case_results=None):
        response = self.session.post(
            self.job['urls']['complete'],
            json={
                'success': success,
                'duration': duration,
                'step_results': step_results,
                'error_message': error_message,
                **({'row_results': row_results} if row_results is not None else {}),
                **({'case_results': case_results} if case_results is not None else {}),
            },
            timeout=30,
        )
        response.raise_for_status()


_locator = playwright_locator


async def _execute_step(page_ref, context, step, asset_paths, variables=None):
    variables = variables if variables is not None else {}
    step = {**step, **prepare_contract(step, variables)}
    action = step['action_type']
    wait_time = int(step.get('wait_time') or 1000)
    element = step.get('element')

    if action == 'wait':
        await asyncio.sleep(wait_time / 1000)
        return page_ref, f'等待 {wait_time}ms 完成'
    if action == 'screenshot':
        return page_ref, '页面截图完成'
    if action == 'switchTab':
        deadline = time.monotonic() + wait_time / 1000
        while len(context.pages) <= 1 and time.monotonic() < deadline:
            await asyncio.sleep(0.2)
        pages = context.pages
        requested = step.get('input_value', '')
        index = int(requested) if str(requested).isdigit() else len(pages) - 1
        page_ref = pages[index]
        await page_ref.bring_to_front()
        return page_ref, f'切换到标签页 {index}'

    if action == 'assert' and step['assert_type'] in PAGE_ASSERTIONS:
        message = await execute_playwright_extension(
            page_ref, None, step, variables, resolve_timeout_ms())
        return page_ref, message

    if not element:
        raise ValueError(f'操作 {action} 缺少元素定位器')
    locator = _locator(page_ref, element)
    timeout = resolve_timeout_ms(element, wait_time)
    force = bool(element.get('force_action', False))

    if action in EXTENDED_ACTIONS:
        message = await execute_playwright_extension(page_ref, locator, step, variables, timeout, force)
        return page_ref, message

    if action == 'click':
        await locator.click(timeout=timeout, force=force)
    elif action == 'fill':
        await locator.fill(str(step.get('input_value', '')), timeout=timeout, force=force)
    elif action == 'waitFor':
        await locator.wait_for(state='visible', timeout=timeout)
    elif action == 'waitForEnabled':
        await locator.click(timeout=timeout, trial=True)
    elif action == 'hover':
        await locator.hover(timeout=timeout, force=force)
    elif action == 'scroll':
        await locator.scroll_into_view_if_needed(timeout=timeout)
    elif action == 'uploadFile':
        paths = [str(asset_paths[asset_id]) for asset_id in step.get('file_asset_ids', [])]
        if not paths:
            raise ValueError('上传步骤没有测试文件')
        input_type = (await locator.get_attribute('type') or '').lower()
        if input_type == 'file':
            await locator.set_input_files(paths, timeout=timeout)
        else:
            async with page_ref.expect_file_chooser(timeout=timeout) as chooser_info:
                await locator.click(timeout=timeout, force=force)
            await (await chooser_info.value).set_files(paths)
    else:
        raise ValueError(f'本机执行器暂不支持操作: {action}')
    return page_ref, f'{action} 执行成功'


class _DataRowClient:
    """Reuse the same upload token, but defer batch completion until every row finishes."""
    def __init__(self, client, iteration, results):
        self.client = client
        self.index = iteration['data_index']
        self.results = results
        payload = dict(client.job['payload'])
        payload.pop('iterations', None)
        payload['steps'] = iteration['steps']
        self.job = {**client.job, 'payload': payload}

    def event(self, event_type, **data):
        self.client.event(event_type, **data, data_index=self.index)

    def download_asset(self, asset, destination):
        self.client.download_asset(asset, destination)

    def artifact(self, path, artifact_type):
        named = path.with_name(f'row-{self.index}-{path.name}')
        import shutil
        shutil.copy2(path, named)
        self.client.artifact(named, artifact_type)

    def complete(self, success, duration, step_results, error_message=''):
        result = {'data_index': self.index, 'success': success, 'duration': duration,
                  'step_results': step_results, 'error_message': error_message}
        self.results.append(result)
        self.client.event('row_finished', **result)


class _SuiteCaseClient:
    def __init__(self, client, item, results):
        self.client = client
        self.execution_id = item['execution_id']
        self.results = results
        self.job = {**client.job, 'payload': item['payload']}

    def event(self, event_type, **data):
        self.client.event(event_type, **data, execution_id=self.execution_id)

    def download_asset(self, asset, destination):
        self.client.download_asset(asset, destination)

    def artifact(self, path, artifact_type):
        import shutil
        named = path.with_name(f'execution-{self.execution_id}-{path.name}')
        shutil.copy2(path, named)
        self.client.artifact(named, artifact_type)

    def complete(self, success, duration, step_results, error_message=''):
        result = {'execution_id': self.execution_id, 'success': success, 'duration': duration,
                  'step_results': step_results, 'error_message': error_message}
        self.results.append(result)
        self.client.event('case_finished', **result)


async def _run_job(client, work_dir):
    payload = client.job['payload']
    if payload.get('suite_items'):
        started = time.monotonic()
        results = []
        for item in payload['suite_items']:
            case_dir = work_dir / f"execution-{item['execution_id']}"
            case_dir.mkdir()
            case_client = _SuiteCaseClient(client, item, results)
            try:
                await _run_job(case_client, case_dir)
            except Exception as exc:
                if not any(result['execution_id'] == item['execution_id'] for result in results):
                    case_client.complete(False, 0, [], str(exc))
                LOGGER.exception('套件用例执行或附件回传失败')
        success = all(result['success'] for result in results)
        client.complete(success, round(time.monotonic() - started, 3), [],
                        '' if success else '套件中部分用例执行失败', case_results=results)
        return success
    if payload.get('iterations'):
        started = time.monotonic()
        results = []
        for iteration in payload['iterations']:
            row_dir = work_dir / f"row-{iteration['data_index']}"
            row_dir.mkdir()
            row_client = _DataRowClient(client, iteration, results)
            try:
                await _run_job(row_client, row_dir)
            except Exception as exc:
                if not any(item['data_index'] == iteration['data_index'] for item in results):
                    row_client.complete(False, 0, [], str(exc))
                LOGGER.exception('数据行执行或附件回传失败')
        success = all(item['success'] for item in results)
        client.complete(success, round(time.monotonic() - started, 3), [],
                        '' if success else '部分数据行执行失败', row_results=results)
        return success
    asset_paths = {}
    assets_dir = work_dir / 'assets'
    assets_dir.mkdir()
    for asset in payload.get('assets', []):
        suffix = Path(asset['name']).suffix
        destination = assets_dir / f"{asset['id']}{suffix}"
        client.download_asset(asset, destination)
        asset_paths[asset['id']] = destination

    browser_name = payload.get('browser', 'chrome')
    browser_engine = 'firefox' if browser_name == 'firefox' else 'webkit' if browser_name in {'safari', 'webkit'} else 'chromium'
    trace_path = work_dir / 'trace.zip'
    step_results = []
    started = time.monotonic()
    success = False
    error_message = ''

    playwright = browser = context = None
    try:
        playwright = await async_playwright().start()
        browser = await getattr(playwright, browser_engine).launch(headless=bool(payload.get('headless', False)))
        context = await browser.new_context()
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()
        base_url = payload['case'].get('base_url')
        if base_url:
            await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)

        client.event('started', case_name=payload['case']['name'])
        variables = {}  # Fresh for every case/data row.
        steps = payload.get('steps', [])
        for step_index, step in enumerate(steps):
            step_started = time.monotonic()
            try:
                page, message = await _execute_step(page, context, step, asset_paths, variables)
                if step['action_type'] == 'screenshot':
                    screenshot = work_dir / f"step-{step['step_number']}.png"
                    await page.screenshot(path=str(screenshot), full_page=True)
                    client.artifact(screenshot, 'screenshot')
                result = {
                    'step_number': step['step_number'],
                    'action_type': step['action_type'],
                    'description': step.get('description', ''),
                    'success': True,
                    'message': message,
                    'duration': round(time.monotonic() - step_started, 3),
                }
                step_results.append(result)
                client.event('step_finished', **result)
                if (payload['case'].get('global_wait_enabled')
                        and step_index < len(steps) - 1):
                    await asyncio.sleep(int(payload['case'].get('global_wait_time') or 1000) / 1000)
            except Exception as exc:
                error_message = f"步骤 {step['step_number']} 执行失败: {exc}"
                result = {
                    'step_number': step['step_number'],
                    'action_type': step['action_type'],
                    'description': step.get('description', ''),
                    'success': False,
                    'error': str(exc),
                    'duration': round(time.monotonic() - step_started, 3),
                }
                step_results.append(result)
                client.event('step_finished', **result)
                screenshot = work_dir / f"failure-step-{step['step_number']}.png"
                await page.screenshot(path=str(screenshot), full_page=True)
                client.artifact(screenshot, 'screenshot')
                break
        else:
            success = True
    except Exception as exc:
        error_message = str(exc)
        client.event('runner_error', error=error_message)
    finally:
        if context:
            try:
                await context.tracing.stop(path=str(trace_path))
            except Exception as exc:
                client.event('trace_error', error=str(exc))
            try:
                await context.close()
            except Exception as exc:
                print(f'关闭 BrowserContext 失败: {exc}', file=sys.stderr)
        if browser:
            try:
                await browser.close()
            except Exception as exc:
                print(f'关闭 Browser 失败: {exc}', file=sys.stderr)
        if playwright:
            try:
                await playwright.stop()
            except Exception as exc:
                print(f'停止 Playwright 失败: {exc}', file=sys.stderr)

    duration = round(time.monotonic() - started, 3)
    client.complete(success, duration, step_results, error_message)
    if trace_path.exists():
        try:
            client.artifact(trace_path, 'playwright_trace')
        except Exception:
            LOGGER.exception('执行结果已回传，但 Trace 上传失败')
            recovery_dir = _config_path().parent / 'pending-artifacts' / str(client.job['job_id'])
            recovery_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(trace_path, recovery_dir / 'trace.zip')
            _show_macos_error(f'执行结果已回传，但 Trace 上传失败。文件已保留：{recovery_dir / "trace.zip"}')
    return success


def main():
    log_path = _setup_logging()
    LOGGER.info('Runner 已由系统唤起，版本=%s', RUNNER_VERSION)
    parser = argparse.ArgumentParser(description='TestHub 本机 Playwright 执行器')
    parser.add_argument('--version', action='version', version=USER_AGENT)
    parser.add_argument('launch_url', nargs='?', help='testhub-runner:// 启动链接')
    args, extras = parser.parse_known_args()
    launch_url = args.launch_url
    if not launch_url or not launch_url.startswith('testhub-runner://'):
        launch_url = next((arg for arg in extras if arg.startswith('testhub-runner://')), '')
    if not launch_url:
        message = '没有收到执行链接，请从 TestHub 网页点击“本机执行”。'
        LOGGER.error(message)
        _show_macos_error(f'{message}\n\n日志：{log_path}')
        return 2

    try:
        claim_url, launch_code = _parse_launch_url(launch_url)
        LOGGER.info('启动链接校验通过，领取地址=%s', claim_url)
        client = JobClient(claim_url, launch_code)
        job = client.claim()
        LOGGER.info('开始执行任务 job_id=%s', job['job_id'])
        with tempfile.TemporaryDirectory(prefix='testhub-runner-') as directory:
            success = asyncio.run(_run_job(client, Path(directory)))
        LOGGER.info('任务执行完成，success=%s，资源已释放', success)
        return 0 if success else 1
    except Exception as exc:
        LOGGER.exception('TestHub Runner 执行失败: %s', exc)
        _show_macos_error(f'{exc}\n\n请运行安装包里的“诊断 TestHub Runner.command”，或查看日志：\n{log_path}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
