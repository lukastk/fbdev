"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/utils.ipynb.

# %% auto 0
__all__ = ['is_in_event_loop', 'await_multiple_events', 'await_any_event', 'AttrContainer', 'ReadonlyEvent', 'EventHandler',
           'EventCollection', 'StateHandler', 'StateView', 'StateCollection', 'TaskManager']

# %% ../nbs/api/utils.ipynb 4
import asyncio
from typing import Optional, Type, Union, Coroutine, List, Callable, Any, Tuple
from types import MappingProxyType
import copy
import traceback
import inspect

import fbdev

# %% ../nbs/api/utils.ipynb 6
def is_in_event_loop():
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False

# %% ../nbs/api/utils.ipynb 8
async def await_multiple_events(*events):
    try:
        event_await_tasks = []
        while not all([event.is_set() for event in events]): # In the off-chance that as asyncio.wait finishes, one of the events is cleared
            event_await_tasks.clear()
            for event in events:
                event_await_tasks.append(asyncio.create_task(event.wait()))
            await asyncio.wait(event_await_tasks)
    except asyncio.CancelledError:
        for task in event_await_tasks:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
        raise

# %% ../nbs/api/utils.ipynb 10
async def await_any_event(*events):
    try:
        event_await_tasks = [asyncio.create_task(event.wait()) for event in events]
        await asyncio.wait(event_await_tasks, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        for task in event_await_tasks:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
        raise

# %% ../nbs/api/utils.ipynb 13
class AttrContainer:
    def __init__(self, _attrs=None, obj_name="AttrContainer", dtype:Optional[Type]=None):
        self.idx = ()
        self._attrs = dict(_attrs) if _attrs is not None else {}
        self._obj_name = obj_name
        self._dtype = dtype
        
    def __getattr__(self, key):
        if key.startswith("__") and key.endswith("__"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}' (in {self._obj_name})")
        return self[key]
        
    def __getitem__(self, key):
        if key in self._attrs:
            return self._attrs[key]
        elif key.startswith("__") and key.endswith("__"):
            raise KeyError(f"'{type(self).__name__}' object has no key '{key}' (in {self._obj_name})")
        else:
            raise Exception(f"'{key}' does not exist (in {self._obj_name})")
        
    def _set(self, key, value):
        if self._dtype is not None and type(value) != self._dtype:
            raise TypeError(f"Value {value} is not of type {self._dtype} (in {self._obj_name}).")
        self._attrs[key] = value
        
    def keys(self):
        return self._attrs.keys()
    
    def values(self):
        return self._attrs.values()
    
    def items(self):
        return self._attrs.items()
    
    def as_readonly_dict(self):
        return MappingProxyType(self._attrs)
    
    def as_list(self):
        return list(self.values())
        
    def __iter__(self):
        return self._attrs.__iter__()
    
    def __contains__(self, key):
        return key in self._attrs

    def __len__(self):
        return self._attrs.__len__()
    
    def __str__(self):
        return f'{self._obj_name}: {", ".join([f"{k}: {v}" for k,v in self._attrs.items()])}'
    
    def copy(self):
        copy =  copy.copy(self)
        for key, value in self.items():
            if type(value) == AttrContainer:
                copy._set(key, value.copy())
        return copy

# %% ../nbs/api/utils.ipynb 15
class ReadonlyEvent:
    def __init__(self, event: asyncio.Event):
        self._event = event

    def is_set(self):
        return self._event.is_set()

    async def wait(self):
        await self._event.wait()

# %% ../nbs/api/utils.ipynb 17
class EventHandler:
    """Subscribable events"""
    def __init__(self, name):
        self._events = []
        self.name = name
    
    def subscribe(self):
        event = asyncio.Event()
        self._events.append(event)
        return event

    def _trigger(self):
        for event in self._events:
            event.set()
        self._events.clear()
        
    def __str__(self):
        return f"EventHandler(name='{self.name}')"
    
    def __repr__(self):
        return str(self)

# %% ../nbs/api/utils.ipynb 19
class EventCollection(AttrContainer):
    def __init__(self) -> None:
        super().__init__({}, obj_name="EventCollection")
    
    def _add_event(self, event_handler: EventHandler):
        self._set(event_handler.name, event_handler)

# %% ../nbs/api/utils.ipynb 21
class StateHandler:
    def __init__(self, name, current_state, state_vals=[True, False]):
        self.name = name
        state_vals = list(state_vals) # Can be enums
        self._state_vals = state_vals
        if len(state_vals) != len(set(state_vals)): raise ValueError("`state_vals` must have all unique elements.")
        if current_state not in state_vals: raise ValueError("`current_state` must be in `state_vals`.")
        self.__state_is_on = {state : asyncio.Event() for state in state_vals}
        self.__state_is_on[current_state].set()
        self.__state_is_off = {state : asyncio.Event() for state in state_vals}
        self._current_state = current_state
        for state in self.__state_is_off:
            if state != current_state: self.__state_is_off[state].set()
        
    def check(self, state):
        return self.__state_is_on[state].is_set()
    
    def get(self):
        return self._current_state
    
    def set(self, state):
        if state not in self._state_vals: raise ValueError(f"Invalid state: {state}. Possible states: {', '.join(self._state_vals)}")
        self._current_state = state
        for _state in self.__state_is_on:
            if _state == state:
                self.__state_is_on[_state].set()
                self.__state_is_off[_state].clear()
            else:
                self.__state_is_on[_state].clear()
                self.__state_is_off[_state].set()
            
    def wait(self, state, target_value=True):
        if target_value: return self.__state_is_on[state].wait()
        else: return self.__state_is_off[state].wait()
        
    async def __event_func(self, state, event):
        await state.wait()
        event.set()
      
    def get_state_event(self, state, target_value=True):
        if target_value: return ReadonlyEvent(self.__state_is_on[state])
        else: return ReadonlyEvent(self.__state_is_off[state])
        
    def get_state_toggle_event(self, state, target_value=True):
        event = asyncio.Event()
        if target_value: asyncio.create_task(self.__event_func(self.__state_is_on[state], event))
        else: asyncio.create_task(self.__event_func(self.__state_is_off[state], event))
        return event
    
    def __str__(self):
        return f"State {self.name}: {self._current_state}"
    
    def __repr__(self):
        return self.__str__()

# %% ../nbs/api/utils.ipynb 23
class StateView:
    def __init__(self, state_handler):
        self._state_handler: StateHandler = state_handler
        
    def check(self, state):
        return self._state_handler.check(state)
    
    def get(self):
        return self._state_handler._current_state
            
    def wait(self, state, state_value=True):
        return self._state_handler.wait(state, state_value)
      
    def get_state_event(self, state, state_value=True):
        return self._state_handler.get_state_event(state, state_value)
        
    def get_state_toggle_event(self, state, state_value=True):
        return self._state_handler.get_state_toggle_event(state, state_value)
    
    def __str__(self):
        return str(self._state_handler)
    
    def __repr__(self):
        return self.__str__()

# %% ../nbs/api/utils.ipynb 25
class StateCollection(AttrContainer):
    def __init__(self) -> None:
        super().__init__({}, obj_name="StateCollection")
    
    def _add_state(self, state_handler: StateHandler, readonly=False):
        self._set(f"_{state_handler.name}", state_handler)
        if readonly:
            self._set(f"{state_handler.name}", StateView(state_handler))
        else:
            self._set(state_handler.name, state_handler)

# %% ../nbs/api/utils.ipynb 27
class TaskManager:
    def __init__(self, host):
        self._host = host
        self._tasks = []
        self._cancelled_tasks = []
        self._monitoring_task = asyncio.create_task(self._monitor_tasks())
        self._callbacks: List[Callable[[asyncio.Task, Exception], None]] = []
        self._registered_exceptions = []
        self._exceptions_non_empty_condition = asyncio.Condition()
        self._tasks_non_empty_condition = asyncio.Condition()  # New condition for task management
        
    def create_task(self, coroutine:Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        self._tasks.append(task)
        async def _notify():
            async with self._tasks_non_empty_condition:
                self._tasks_non_empty_condition.notify_all()
        asyncio.create_task(_notify())
        return task
        
    async def _monitor_tasks(self):
        try:
            while True:
                await asyncio.sleep(0)
                async with self._tasks_non_empty_condition:
                    await self._tasks_non_empty_condition.wait_for(lambda: len(self._tasks) > 0) 
                done, pending = await asyncio.wait(self._tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        exception = task.exception()
                    except asyncio.CancelledError as e:
                        exception = e
                    if exception is not None:
                        async with self._exceptions_non_empty_condition:
                            self.submit_exception(task, exception, ())
                    self._tasks.remove(task)
        except asyncio.CancelledError: # This registers the task cancel exception as handled.
            pass
        except Exception as e:
            self.submit_exception(asyncio.current_task(), e, ())
                
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
        
    def submit_exception(self, task:asyncio.Task, exception:Exception, source_trace:Tuple[Any, ...]):
        self._registered_exceptions.append((task, exception, source_trace + (self._host,)))
        for callback in self._callbacks:
            callback(task, exception, source_trace + (self._host,))
        async def _notify():
            async with self._exceptions_non_empty_condition:
                self._exceptions_non_empty_condition.notify_all()
        asyncio.create_task(_notify())
            
    async def destroy(self):
        for task in self._tasks:
            await self.cancel_wait(task)
        self._monitoring_task.cancel()
        try: await self._monitoring_task
        except asyncio.CancelledError: pass
            
    def get_task_coro_qualnames(self):
        qualnames = [task.get_coro().__qualname__ for task in self._tasks]
        qualname_counts = {name : qualnames.count(name) for name in set(qualnames)}
        return qualname_counts
