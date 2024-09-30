"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/dev_utils.ipynb.

# %% auto 0
__all__ = ['method_from_py_file']

# %% ../nbs/api/dev_utils.ipynb 4
import asyncio
from pathlib import Path
import pickle
import functools
import inspect
from typing import Callable

import fbdev
from ._utils import get_function_from_py_file
from .complib import ExecComponent
from .runtime import BatchExecutor

# %% ../nbs/api/dev_utils.ipynb 6
def method_from_py_file(file_path:Callable):
    def decorator(orig_func):
        args = list(inspect.signature(orig_func).parameters.keys())
        is_async = inspect.iscoroutinefunction(orig_func)
        new_func = get_function_from_py_file(file_path, func_name=orig_func.__name__, args=args, is_async=is_async)
        if is_async:
            @functools.wraps(orig_func)
            async def wrapped_method(*args, **kwargs):
                await new_func(*args, **kwargs)
                await orig_func(*args, **kwargs)
        else:
            @functools.wraps(orig_func)
            def wrapped_method(*args, **kwargs):
                new_func(*args, **kwargs)
                orig_func(*args, **kwargs)
        return wrapped_method
    return decorator
