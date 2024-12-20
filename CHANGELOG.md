# Changelog



## [0.0.5] - 2024-12-20
 
### Fixed

- Fixed NodeProcess.gather_outputs



## [0.0.4] - 2024-12-20
 
### Added

- Can now put packets into the `NodeProcess` ports without awaiting (as long as you're in the event loop).
- `NodeProcess.gather_outputs`. Convenient way to gather outputs.
- `PortCollection.iter_input_ports` and `PortCollection.iter_output_ports`

### Changed

### Fixed

- Bug caused `ExecComponent` to start two `_pre_execute` tasks when starting
- Packet locations weren't updated in `PacketRegistry.register_move` before
- Removing edges and nodes from `GraphSpec`s now works.



## [0.0.3] - 2024-10-06

Besides extensive refactoring, the main addition is `fbdev.concurrent.remote`, which allows for launching nodes in separate subprocesses.


## [0.0.2] - 2024-09-30

### Changed

Rewrite of the whole codebase.


## [0.0.1] - 2024-09-17

Initial release. Working prototype, with which it should be possible to developed
flow-based apps in Python.
