"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/03_concurrent/02_subprocess_node_launcher.ipynb.

# %% ../../nbs/api/03_concurrent/02_subprocess_node_launcher.ipynb 4
from __future__ import annotations
import asyncio
from typing import Tuple
from multiprocessing.connection import Listener

import fbdev
from .._utils import TaskManager
from ..graph.graph_spec import NodeSpec
from ..graph.net import BaseNode, Node
from .remote import RemoteController, ProxyNodeMediator

# %% auto 0
__all__ = ['node', 'remote', 'task_manager', 'node_created', 'close_connection_event', 'subprocess_node_worker']

# %% ../../nbs/api/03_concurrent/02_subprocess_node_launcher.ipynb 5
node: BaseNode = None
remote: RemoteController = None
task_manager: TaskManager = None
node_created: asyncio.Event = None
close_connection_event: asyncio.Event = None

# %% ../../nbs/api/03_concurrent/02_subprocess_node_launcher.ipynb 6
async def _create_node(node_spec:NodeSpec):
    global node
    node = Node(node_spec, None)
    node.task_manager.subscribe(_handle_remote_node_exception)
    proxy_node_mediator = ProxyNodeMediator('main', remote, task_manager, node)
    node_created.set()
    
async def _await_node_created():
    await node_created.wait()
    
def _handle_remote_node_exception(task:asyncio.Task, exception:Exception, source_trace:Tuple, tracebacks:Tuple[str, ...]):
    remote.sync_do('main', 'submit_exception_from_remote', str(task), exception, source_trace, tracebacks)
    
async def _close_connection():
    await remote.await_empty() # This is so that the DO_SUCCESSFUL has time to be sent back
    close_connection_event.set()

# %% ../../nbs/api/03_concurrent/02_subprocess_node_launcher.ipynb 7
def subprocess_node_worker(port_num:int, authkey:bytes):
    asyncio.run(_async_subprocess_node_worker(port_num, authkey))

async def _async_subprocess_node_worker(port_num:int, authkey:bytes):
    global remote, task_manager, node_created, close_connection_event
    node_created = asyncio.Event()
    close_connection_event = asyncio.Event()
    listener = Listener(('localhost', port_num), authkey=authkey)
    with listener.accept() as conn:
        task_manager = TaskManager('remote_node_task_manager')
        task_manager.subscribe(_handle_remote_node_exception)
        remote = RemoteController(conn, task_manager)
        remote.add_routine('main', 'create_node', _create_node)
        remote.add_routine('main', 'await_node_created', _await_node_created)
        remote.add_routine('main', 'close_connection', _close_connection)
        remote.send_ready()
        await remote.await_ready()
        await node_created.wait()
        await close_connection_event.wait()
        await task_manager.destroy()
