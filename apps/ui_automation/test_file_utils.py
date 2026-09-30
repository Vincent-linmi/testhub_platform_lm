"""Helpers for exposing stored test files to browser automation engines."""

import os
import shutil
import tempfile
from contextlib import ExitStack, contextmanager


@contextmanager
def materialized_test_file(asset):
    """Yield a local absolute path for a TestFileAsset, including remote storages."""
    if not asset or not asset.file:
        raise ValueError('上传文件步骤未配置测试文件')

    try:
        local_path = asset.file.path
    except (AttributeError, NotImplementedError):
        local_path = None

    if local_path and os.path.isfile(local_path):
        yield os.path.abspath(local_path)
        return

    suffix = os.path.splitext(asset.name or '')[1]
    temp_dir = tempfile.mkdtemp(prefix='testhub-ui-upload-')
    temp_path = os.path.join(temp_dir, f'asset{suffix}')
    try:
        with asset.file.open('rb') as source, open(temp_path, 'wb') as target:
            shutil.copyfileobj(source, target)
        yield temp_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@contextmanager
def materialized_test_files(assets):
    """Yield local absolute paths for all selected TestFileAsset objects."""
    assets = list(assets or [])
    if not assets:
        raise ValueError('上传文件步骤未配置测试文件')

    with ExitStack() as stack:
        yield [
            stack.enter_context(materialized_test_file(asset))
            for asset in assets
        ]


def get_step_file_assets(step):
    """Return selected files in stable order, with legacy single-file fallback."""
    cached = getattr(step, '_upload_file_assets', None)
    if cached is not None:
        assets = list(cached)
    else:
        prefetched = getattr(step, '_prefetched_objects_cache', {}).get('file_assets')
        assets = list(prefetched) if prefetched is not None else list(step.file_assets.all())

    if not assets and getattr(step, 'file_asset', None):
        assets = [step.file_asset]
    order = getattr(step, 'file_asset_order', None) or []
    if order:
        positions = {int(asset_id): index for index, asset_id in enumerate(order)}
        assets.sort(key=lambda asset: positions.get(asset.id, len(positions)))
    return assets
