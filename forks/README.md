# Patches

Unified diff patches applied to third-party packages during `setup-madsci.sh`.

## opentrons.patch

Adds simulation support to opentrons 8.5.1 by replacing the hardware controller with a ZMQ-based simulation backend that communicates with Isaac Sim.

**Modified files:**
- `hardware_control/api.py` - Uses SimulationController instead of real hardware Controller

**New files:**
- `hardware_control/backends/simulation_controller.py` - ZMQ-based simulation backend
- `hardware_control/simulation/__init__.py` - Package exports
- `hardware_control/simulation/zmq_client.py` - ZMQ REQ-REP client for Isaac Sim communication
- `hardware_control/simulation/axis_mapper.py` - Maps OT2 axes to simulation joint coordinates

## opentrons_shared_data.patch

Fixes numpy 2.0 compatibility in opentrons_shared_data 8.5.1. The upstream package uses `numpy.trapz` which was renamed to `numpy.trapezoid` in numpy 2.0.

## Regenerating patches

If you need to update the opentrons patch (e.g., for a new opentrons version):

```bash
# Download upstream version
pip download opentrons==X.X.X -d /tmp/upstream --no-deps
unzip /tmp/upstream/opentrons-*.whl -d /tmp/upstream_extracted

# Make modifications to /tmp/upstream_extracted/opentrons/...

# Generate patch
diff -ruN /tmp/upstream_extracted/opentrons path/to/modified/opentrons > forks/opentrons.patch

# Fix paths for -p0 application from site-packages
sed -i 's|/tmp/upstream_extracted/||g' forks/opentrons.patch
sed -i 's|path/to/modified/||g' forks/opentrons.patch
```
