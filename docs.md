# SimLab
SimLab defines an organizational system for operating factory-scale automated scientific laboratories.

This document contains:
- Descriptions for currently supported resources
- Documentation for available laboratory actions
- An introduction to SimLab program design
- Example programs

# Resources

A SimLab resource is one of three `variants`:
- Agent: Active parts of SimLab that can receive and respond to commands
- Material: Equipment manipulated by agents to perform experiments
- Location: A world-space defined location for placing materials

Each resource also has a collection of `features`, defined in Python as a dictionary.
SimLab programs may not request specific resources, and instead request resources that match a `feature` template.
This is to allow a submitted program to allocate resources at run-time based on availability.

Agent resources also support a collection of actions, which are described in more detail in the Actions section.

Here is the set of resources that we currently support.

## ur5e
A Universal agents UR5e arm.
### Features
- `variant` (`str`) - The string 'agent'
- `model` (`str`) - The string 'ur5e'
### Supported Actions
- move_close
- move_to
- grab
- release

## platecrane_sciclops
### Features
- `variant` (`str`) - The string 'agent'
- `model` (`str`) - The string 'platecrane_sciclops'
- `plate_stack_position` (`pose`) - The world-space pose of the plate stack attached to the agent
- `plate_transfer_position` (`pose`) - The world-space pose of the plate transfer station attached to the agent
### Supported Actions
- move_close
- move_to
- grab
- release

## ot2
### Features
- `variant` (`str`) - The string 'agent'
- `model` (`str`) - The string 'ot2'
- `deck_position` (`pose`) - The world-space pose of a plate holding deck attached to the agent
### Supported Actions
- move_close
- move_to
- grab
- release

## microplate
### Features
- `variant` (`str`) - The string 'material'
- `model` (`str`) - The string 'microplate'

# Actions
## move_close(target)
> Safely move to the gripper to a position above the `target` location.
>
> `target` (`pose`) - Pose information for the location

## move_to(target)
> Move to the gripper to a `target` location.
> Should only be performed after a `move_close` command.
>
> `target` (`pose`) - Pose information for the location

## grab()
> Grab the object at the gripper's current location.
> Should only be performed after a `move_to` for this location, to ensure the intended object will be grabbed.
> Should always be followed by a `move_close` for this location, to safely back away from the grab location.

## release()
> Release the currently held object at the gripper's current location.
> Should only be performed after a `move_to` for this location, to ensure the drop location is correct.
> Should always be followed by a `move_close` for this location, to safely back off from the drop location.

## home()
> Sends the agent to its home location.

# SimLab Programs

SimLab programs are composed of 3 parts:
- Resource requests
- Nodes (operations)
- Edges (links between Nodes)

We frequently shorten these to R, N, and E.

```
R:
    features: dict[str, Any]

N:
    name: str
    cmd: tuple[R, list[Any]]

E:
    edge: tuple[N, N]
```

Each program defines a directed acyclic graph (DAG) of execution. A resource list is used to request all necessary agents, materials, and locations from the laboratory to ensure the experiment will be able to execute. The nodes define what commands are sent to each agent resource, and the edges define the order in which these commands will be executed.

A SimLab program is therefore 3 lists: a list of resources, a list of nodes, and a list of edges.

Nodes support 4 possible activities: locking, unlocking, commands, and sleep. We recommend only setting one of these on any particular Node for clarity. However, if multiple activities are provided on a single node, the order of execution is as such:
- lock
- command
- sleep
- unlock

# Examples

```python
arm1 = R({
    'variant': 'agent',
    'model': 'ur5e',
})
arm2 = R({
    'variant': 'agent',
    'model': 'pf400',
})
r_list = [arm1, arm2]
n_list = [
    N('0', locks=[(arm1, 'key_a'),]),
    N('1', cmd=(arm1, ['moveto', 'home',])),
    N('2', cmd=(arm2, ['grab',])),
    N('3', cmd=(arm1, ['release',])),
    N('4', unlocks=[(arm1, 'key_a'),]),
    N('5', locks=[(arm2, 'key_b'),]),
    N('6', cmd=(arm2, ['moveto', 'work',])),
    N('7', cmd=(arm2, ['grab',])),
    N('8', cmd=(arm1, ['release',])),
    N('9', unlocks=[(arm2, 'key_b'),]),
]
```
