# TODO

## Features

- [ ] Running .py files as components

### Minor features

- [ ] DAGraphComponentFactory
- [ ] An option in GraphComponentFactory to only allow each node to run once
- [ ] Way for a component to send a stop signal to the whole graph (in case, for example, a data validator component fails or something).
- [ ] Need to update graph.ReadOnlyGraph

### Major features

- [ ] FSMRuntime
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
- [ ] Component memory
- [ ] PacketRegistry
- [ ] Node policies (similar to KAS). Specifies when a node should restart, be destroyed etc. Also where it should be run.

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

- [ ] 'ComponentFactory' to 'ComponentTemplate'
- [ ] Change `Executor` to `Runtime`
- [ ] Add type hints for attributes like this: `self.config_input_edges: Dict[str, Edge] = {}`
- [ ] `Node.address` should be in `NodeSpec`
- [ ] Make `export_tests.py` also run `nbdev_clean` on `test_nbs`.
- [ ] Add `from __future__ import annotations` to all submodules, and replace string annotations.
- [ ] The `Packet` constructor should give a warning if one is instantiated outside of a PacketRegistry (perhaps you have to pass some kind of flag to do it).
- [ ] `NodeError` should take address as an argument and print it out when raised.

- [ ] Add a Lock/Condition to edges, so that it is possible to guarantee that a packet can move. The below code would be improved if that was possible.
    It would avoid packets existing in a limbo state between ports and edges.
  ```python
  async def _handle_graph_in_port(self, graph_port:InputPort, edge:Edge):
      edge_non_full = edge.states.full.get_state_event(False)
      packet = None
      try:
          while True:
              packet = await graph_port.receive()
              await edge_non_full.wait()
              edge._load(packet)
              packet = None
              await asyncio.sleep(0)
  ```

- [ ] See if you can reduce coupling using dependency injection. For example the below code in `Node` tightly couples it with `PacketRegistry`:
  ```python
  def initialise(self):
      if self.is_net: self._packet_registry = PacketRegistry()
      self._packet_handler = PacketHandler(registry=self._get_packet_registry(), parent_node=self)
  ```
  One reason why coupling is high is that AddressableMixins have references to their parents. The main reason I do this is because this enables me to dynamically retrieve the address
  based on its set of ancestors. Alternatively, the addresses of nodes and edges are just set upon instantiation.

### Major refactors

- [ ] Take out the flow runtime out of `fbdev` (call it `fbruntime` or `fbcore`). `fbdev` will be the 'development' part of the fbX universe (similar to `nbdev` vs `fastcore`).

## Bugs

- [ ] Only allow for `_[a-zA-Z0-9_]+` for node and edge ids.

## Documentation

- [ ] Docstrings for everything
- [ ] Example code for everything

## Tests

- [ ] Tests that exceptions are raised properly
- [ ] Check that PacketActivities are added properly in PacketRegistry