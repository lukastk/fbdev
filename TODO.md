# TODO

## Priority

- [ ] Detect when a net is blocked
- [ ] BatchExecutor stops when net is blocked
- [x] Allow for single-run components

## Features

- [x] Running .py files as components

### Minor features

- [ ] DAGraphComponentFactory
- [ ] Way for a component to send a stop signal to the whole graph (in case, for example, a data validator component fails or something).
- [ ] Consider adding unsent messages to a queue, so that they don't get lost.

### Major features

- [ ] FSMRuntime
- [ ] Serialisation
- [ ] Orchestrators
  - Right now the net is set up as a dance between Node and CompositeComponent. Eventually, it might be a good idea for this to instead be done by an orchestrator (that you can customise by subclassing). I'm not sure yet where any information about what nodes should be run in separate threads, processes or remotely. It could be in the graph, but I suppose it would be fairly simple to have a dictionary that points node addresses to a `NodeSettings` class, and subnets to `SubNetSettings`. `NetSettings` would be for the whole net.
  - Perhaps orchestrators are the right tool to enforce things like DAG mode.
- [ ] Logging
  - In the `Logging` class, you can have a way to get a `Context`. So `TaskManager` can be passed a specific context instance from the logger. That way,
  any logs submitted by the task manager will have the correct metadata, without the taskmanager having to know anything about its host.
  - Need to log warnings when any resource is __del___-ed without being destroyed.
- [ ] Component memory
- [x] PacketRegistry
- [ ] Node policies (similar to Kubernetes). Specifies when a node should restart, be destroyed etc. Also where it should be run.
- [ ] Need a better way to deal with Component options (the ones defined in the class body). Once I do I need to update the `component_options` argument in `FuncComponentFactory.get_component`.

### Feature ideas

- [ ] Can have a list of remote compute available in a config file (their SSH addresses etc), similar to .env files.

### Components

- [ ] TerminalComponentFactory. Turn terminal commands into components.

### Runtimes

- [X] BatchExecutor
- [ ] CLIExecutor
- [ ] RESTExecutor
  - Set up a net and expose it via a REST API
- [ ] CLIServerExecutor
  - Name will probably change, but the idea is to set up a RESTExecutor locally, that you can communicate with using the command line.

## Refactor

- [ ] 'ComponentFactory' to 'ComponentTemplate'
- [x] Change `Executor` to `Runtime`
- [x] Add type hints for attributes like this: `self.config_input_edges: Dict[str, Edge] = {}`
- [x] Make `export_tests.py` also run `nbdev_clean` on `test_nbs`.
- [x] Add `from __future__ import annotations` to all submodules, and replace string annotations.

- [ ] The below code in the constructor of `Port` should be in a separate `ComponentPort` instead. And `is_blocked` should not be a property of Ports but of `ComponentPort`.
```python
        if self._is_input_port:
            self.get = self._get
            self.get_and_consume = self._get_and_consume
        else:
            self.put = self._put
            self.put_value = self._put_value
```

### Major refactors

- [ ] Take out the flow runtime out of `fbdev` (call it `fbruntime` or `fbcore`). `fbdev` will be the 'development' part of the fbX universe (similar to `nbdev` vs `fastcore`).

## Bugs

- [x] Only allow for `_[a-zA-Z0-9_]+` for node and edge ids.

## Documentation

- [ ] Docstrings for everything
- [ ] Example code for everything

## Tests

- [ ] Tests that exceptions are raised properly
- [ ] Check that PacketActivities are added properly in PacketRegistry