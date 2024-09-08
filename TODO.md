# TODO

## Feautures

- [ ] Running .py files as components

### Minor features

- [ ] Running modes
  - DAG mode: First checks if the graph is a DAG, and then also enforces that all components can only be run once.
- [ ] Way for a component to send a stop signal to the whole graph (in case, for example, a data validator component fails or something).
  
### Major features

- [ ] Serialisation
- [ ] Orchestrators
  - Right now the net is set up as a dance between Node and CompositeComponent. Eventually, it might be a good idea for this to instead be done by an orchestrator (that you can customise by subclassing). I'm not sure yet where any information about what nodes should be run in separate threads, processes or remotely. It could be in the graph, but I suppose it would be fairly simple to have a dictionary that points node addresses to a `NodeSettings` class, and subnets to `SubNetSettings`. `NetSettings` would be for the whole net.
  - Perhaps orchestrators are the right tool to enforce things like DAG mode.
- [ ] Detect when a net is blocked
- [ ] mermaid user interface thingie
- [ ] Logging
  - In the `Logging` class, you can have a way to get a `Context`. So `TaskManager` can be passed a specific context instance from the logger. That way,
  any logs submitted by the task manager will have the correct metadata, without the taskmanager having to know anything about its host.
  - Need to log warnings when any resource is __del___-ed without being destroyed.

### Feature ideas

- [ ] Can have a list of remote compute available in a config file (their SSH addresses etc), similar to .env files.

### Components

- [ ] TerminalComponentFactory. Turn terminal commands into components.

### Executors

- [X] BatchExecutor
- [ ] CLIExecutor
- [ ] RESTExecutor
  - Set up a net and expose it via a REST API
- [ ] CLIServerExecutor
  - Name will probably change, but the idea is to set up a RESTExecutor locally, that you can communicate with using the command line.

## Refactor

- [ ] Add type hints for attributes like this: `self.config_input_edges: Dict[str, Edge] = {}`
- [ ] `Node.address` should be in `NodeSpec`

### Major refactors

- [ ] Take out the flow runtime out of `fbdev` (call it `fbruntime` or `fbcore`). `fbdev` will be the 'development' part of the fbX universe (similar to `nbdev` vs `fastcore`).

## Bugs

## Documentation

- [ ] Docstrings for everything
- [ ] Example code for everything

## Tests

- [ ] Tests that exceptions are raised properly