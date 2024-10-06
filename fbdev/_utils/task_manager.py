"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/utils/task_manager.ipynb.

# %% ../../nbs/api/utils/task_manager.ipynb 4
from __future__ import annotations
import asyncio
from typing import Coroutine, List, Callable, Any, Tuple
import traceback
import inspect

import fbdev

# %% auto 0
__all__ = ['TaskManager']

# %% ../../nbs/api/utils/task_manager.ipynb 6
class TaskManager:
    def __init__(self, host):
        self._host = host
        self._tasks = []
        self._cancelled_tasks = []
        self._monitoring_tasks = []
        self._callbacks: List[Callable[[asyncio.Task, Exception], None]] = []
        self._registered_exceptions = []
        self._exceptions_non_empty_condition = asyncio.Condition()
        self._tasks_non_empty_condition = asyncio.Condition()  # New condition for task management
        
    def create_task(self, coroutine:Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        self._tasks.append(task)
        monitor_task = asyncio.create_task(self._monitor_task_exceptions(task))
        self._monitoring_tasks.append(monitor_task)
        return task
                
    async def _monitor_task_exceptions(self, task):
        try:
            await task
        except asyncio.CancelledError as e:
            # We presume any cancellation was done on purpose.
            # TaskManager.is_cancelled checks whether a given task was cancelled by the current task manager, but it cannot tell whether the task's cancellation was due to a parent task's cancellation.
            pass
        except Exception as e:
            self.submit_exception(task, (e, ), ())
        self._tasks.remove(task)
                
    async def wait_for_exceptions(self):
        try:
            async with self._exceptions_non_empty_condition:
                await self._exceptions_non_empty_condition.wait_for(lambda: len(self._registered_exceptions) > 0)
        except asyncio.CancelledError: pass
                
    def exception_occured(self): return len(self._registered_exceptions) > 0
    
    def get_exceptions(self):
        return list(self._registered_exceptions)
                
    def cancel(self, task, msg=None):
        if task not in self._tasks:
            raise ValueError(f"Task {task} is not in the task manager.")
        if task in self._cancelled_tasks:
            raise ValueError(f"Task {task} is already cancelled.")
        task.cancel(msg)
        current_frame = inspect.currentframe()
        caller_name = current_frame.f_back.f_code.co_name #TODO potentially use for logging
        self._cancelled_tasks.append(task)
        
    async def cancel_wait(self, task, msg=None):
        self.cancel(task, msg)
        try:
            await asyncio.wait_for(task, timeout=None) 
        except asyncio.CancelledError:
            pass  # Task was cancelled successfully
        
    async def stop(self):
        for task in self._tasks:
            await self.cancel_wait(task)
        
    def is_cancelled(self, task:asyncio.Task):
        return task in self._cancelled_tasks
                
    def subscribe(self, callback: Callable[[asyncio.Task, Exception, Tuple[Any, ...]], None]):
        self._callbacks.append(callback)
        
    def submit_exception(self, task:asyncio.Task, exceptions:Tuple[Exception, ...], source_trace:Tuple[Any, ...]):
        self._registered_exceptions.append((task, exceptions, source_trace + (str(self._host),)))
        for callback in self._callbacks:
            callback(task, exceptions, source_trace + (str(self._host),))
        async def _notify():
            async with self._exceptions_non_empty_condition:
                self._exceptions_non_empty_condition.notify_all()
        asyncio.create_task(_notify())
            
    async def destroy(self):
        for task in self._tasks:
            await self.cancel_wait(task)
        for monitor_task in self._monitoring_tasks:
            monitor_task.cancel()
            try: await monitor_task
            except asyncio.CancelledError: pass
            
    def get_task_coro_qualnames(self):
        qualnames = [task.get_coro().__qualname__ for task in self._tasks]
        qualname_counts = {name : qualnames.count(name) for name in set(qualnames)}
        return qualname_counts
    
    async def exec_coros(self, *coros: List[Coroutine], print_all_exceptions=True, sequentially=False):
        """Run a coroutine and monitor for exceptions in the coroutine, as well as
        any exceptions that occurs in the task manager. Therefore, for it to work
        as expected, the coroutine must be starting tasks using self.create_task(),
        or tasks that are created by task managers linked to this task manager.
        """
        results = []
        async def all_coros():
            if sequentially:
                for coro in coros: await coro
            else:
                _tasks = [asyncio.create_task(coro) for coro in coros]
                await asyncio.gather(*_tasks)
                for task in _tasks: results.append(task.result())
        task = asyncio.create_task(all_coros())
        monitor_task = asyncio.create_task(self.wait_for_exceptions())
        await asyncio.wait([task, monitor_task], return_when=asyncio.FIRST_COMPLETED)
        exception_data = self.get_exceptions()
        if task.done():
            try: await task
            except Exception as e: exception_data.append((task, (e,), ()))
        if not monitor_task.done():
            monitor_task.cancel()
        
        if print_all_exceptions:
            for i, (task, exceptions, source_trace) in enumerate(exception_data):
                if len(exceptions) != len(source_trace):
                    raise RuntimeError("Mismatch in `exceptions` and `source_trace` length.")
                print(f"Exception chain {i+1}:")
                for j, (e, source) in enumerate(zip(exceptions, source_trace)):
                    print(f"    Exception {j+1} ({e.__class__.__name__}):")
                    print(f"        Source:", source)
                    print(f"        Message: {e}")
                    print(f"        Traceback:")
                    traceback_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__)).strip()
                    traceback_str = "\n".join([f"            {line}" for line in traceback_str.split("\n")])
                    print(traceback_str)
                    
        
        if exception_data:
            _, _exceptions, _ = exception_data[0]
            raise _exceptions[0]
        
        if len(results) == 1: return results[0]
        else: return results
    
