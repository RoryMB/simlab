# MADSci Project Template

This template provides a standalone MADSci configuration for a simlab project.

## Setup

1. Copy this entire `madsci/` directory into your project:
   ```bash
   cp -r projects/template/madsci projects/my-project/madsci
   ```

2. Configure your workcell in `config/workcell.yaml`:
   - Uncomment and add the nodes (robots) your project uses
   - Node URLs correspond to the REST servers started by `run_node_*.sh` scripts

3. Define locations in `config/managers/location.manager.yaml`:
   - Add locations relevant to your lab layout
   - Specify joint positions for each robot that can access each location

4. Optionally customize resource templates in `config/managers/resource.manager.yaml`

## Running

Start the MADSci services:
```bash
cd projects/my-project/madsci
./run_madsci.sh
```

Or via the orchestrator:
```bash
python tools/orchestrate.py \
    --madsci-cmd "cd projects/my-project/madsci && ./run_madsci.sh" \
    ...
```

## Files

| File | Purpose | Customize? |
|------|---------|------------|
| `compose.yaml` | Docker service definitions | Rarely |
| `run_madsci.sh` | Convenience script to start/stop services | No |
| `config/.env` | Manager paths and URLs | No |
| `config/workcell.yaml` | Which nodes are in this workcell | Yes |
| `config/managers/location.manager.yaml` | Lab locations and robot positions | Yes |
| `config/managers/resource.manager.yaml` | Resource templates | Sometimes |
| `config/managers/*.manager.yaml` | Other managers (data, event, experiment) | No |
| `config/lab.*.yaml` | Lab manager configs | No |

## Runtime Data

The `.madsci/` directory (created at runtime) contains:
- Logs from each manager
- Workflow execution history
- Datapoints from experiments

This directory is gitignored by default.

## Robot Nodes

Robot nodes (in `slcore/robots/`) require MADSci server URLs from the `.env` file.
Source your project's `.env` before running any node script:

```bash
# Load project's MADSci environment, then run node
set -a; source projects/my-project/madsci/config/.env; set +a
cd slcore/robots/ur5e && ./run_node_ur5e.sh
```

Or combine into a single command:
```bash
(set -a; source projects/my-project/madsci/config/.env; set +a; cd slcore/robots/ur5e && ./run_node_ur5e.sh)
```
