# -*- coding: utf-8 -*-
"""
A股Sentinel Pro Backend - 全局初始化

此模块在任何其他导入之前执行，确保TQDM进度条被彻底禁用
"""

import os
import sys

# ============================================================================
# 彻底禁用 TQDM 进度条（解决 Tushare SDK 的 58 步骤问题）
# ============================================================================

# 设置环境变量
os.environ['TQDM_DISABLE'] = '1'
os.environ['TQDM_MININTERVAL'] = '999999'
os.environ['TQDM_MINITERS'] = '999999'

# 创建完全静默的tqdm类
class _SilentTqdm:
    """完全静默的tqdm替代类"""
    def __init__(self, iterable=None, *args, **kwargs):
        self.iterable = iterable if iterable is not None else []
        self.disable = True
        self.n = 0
        self.total = None
        self._instances = {}

    def __iter__(self):
        return iter(self.iterable)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, n=1, *args, **kwargs):
        self.n += n
        return self

    def close(self):
        pass

    def set_description(self, desc=None, *args, **kwargs):
        pass

    def refresh(self, *args, **kwargs):
        pass

    def write(self, s, file=None, end='\n', *args, **kwargs):
        pass

    def iter(self):
        return self.iterable

    def reset(self, total=None):
        pass

    @property
    def format_dict(self):
        return {}

    @staticmethod
    def range(*args, **kwargs):
        return _SilentTqdm(range(*args))

    @staticmethod
    def auto(*args, **kwargs):
        return _SilentTqdm(*args, **kwargs)


# 在模块导入之前替换tqdm
_fake_tqdm_module = type('Module', (), {
    'tqdm': _SilentTqdm,
    'trange': lambda *a, **k: _SilentTqdm(range(*a)),
    'tqdm_gui': _SilentTqdm,
    'tqdm_notebook': _SilentTqdm,
    'autonotebook': lambda *a, **k: None,
    'auto': _SilentTqdm,
    'gui': _SilentTqdm,
    'notebook': _SilentTqdm,
    '__version__': '0.0.0'
})()

sys.modules['tqdm'] = _fake_tqdm_module
sys.modules['tqdm.gui'] = type('Module', (), {'tqdm': _SilentTqdm})()
sys.modules['tqdm.auto'] = type('Module', (), {'tqdm': _SilentTqdm, 'auto': _SilentTqdm})()
sys.modules['tqdm.notebook'] = type('Module', (), {'tqdm': _SilentTqdm})()

print("[INIT] TQDM进度条已全局禁用")
