# MADSci Project Template

This template provides a standalone MADSci configuration for a simlab project.

## Setup

1. Copy this entire `madsci/` directory into your project:
   ```bash
   cp -r projects/_template/madsci projects/my-project/madsci
   ```

2. Configure your workcell in `config/workcell.yaml`:
   - Add the nodes (robots) your project uses
   - Node URLs use path-based routing through the REST Gateway

3. Define locations in `config/managers/location.manager.yaml`:
   - Add locations relevant to your lab layout
   - Specify joint positions for each robot that can access each location

4. Optionally customize resource templates in `config/managers/resource.manager.yaml`

## Running

Start the full system via the orchestrator:
```bash
python tools/orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/my-project && python run.py" \
    --gateway-cmd "source activate-madsci.sh && python -m slcore.gateway.rest_gateway --num-envs 1 --robot-types pf400,peeler,thermocycler" \
    --madsci-cmd "cd projects/my-project/madsci && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/my-project && python run_workflow.py workflow.yaml"
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
