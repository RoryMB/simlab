# Environment Management

This directory organizes **two separate** uv-managed virtual environments.

## Quick Setup

For new users after cloning the repository:

```bash
cd environments/isaacsim && ./setup.sh && cd ../..
cd environments/madsci && ./setup.sh && cd ../..
```

If you wish to personally manage each environment, the steps of `setup.sh` are explain here:

```bash
# In `environments/isaacsim` or `environments/madsci`

# Create the virtual environment (only once)
# NOTE: isaacsim requires Python 3.10: `uv venv -p python@3.10`
uv venv

# Activate the newly created environment
source .venv/bin/activate

# Only necessary if/when you modify the `requirements.in` file
./compile.sh

# Install dependencies, and update dependencies after running `./compile.sh`
./sync.sh

# Deactivate the environment
deactivate
```

## Usage

### Running Scripts

Typically you'll run scripts simultaneously in separate terminals:

**Terminal 1**
```bash
./activate-isaacsim.sh
python src/isaacsim/your_simulation_script.py
```

**Terminal 2**
```bash
./activate-madsci.sh
python src/madsci/your_orchestration_script.py
```

## For Developers

### Adding Dependencies

1. **Edit the requirements.in file**: `environments/{isaacsim,madsci}/requirements.in`

2. **Recompile the lockfile:** `./compile.sh`

3. **Update the virtual environment:** `./sync.sh`

4. **Commit the changes:** Commit both the updated `.in` file and the generated `.txt` lockfile to git.

### Upgrading Dependencies

- To upgrade all packages, run the command in `./compile.sh` with `--upgrade` appended.

- To upgrade specific packages, run the command in `./compile.sh` with `--upgrade-package package-name` appended.

## Isaac Sim Local Assets Pack

For up-to-date instructions, visit `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_faq.html#isaac-sim-setup-assets-content-pack`

1. Download the **Isaac Sim Assets** pack from `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/download.html`.
2. Edit `environments/isaacsim/.venv/lib/python3.10/site-packages/isaacsim/apps/isaacsim.exp.base.kit`.
3. Add the settings below to the end of the file:

```
# Remember to replace `{VERSION}` with the version of Isaac Sim you have (e.g., 4.5)

[settings]
persistent.isaac.asset_root.default = "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}"
exts."isaacsim.asset.browser".folders = [
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Robots",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/People",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/IsaacLab",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Props",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Environments",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Materials",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Samples",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Sensors",
]

# The lines below are optional. It is recommended to use the Content Browser instead.
exts."isaacsim.asset.browser".folders = [
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Robots",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/People",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/IsaacLab",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Props",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Environments",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Materials",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Samples",
    "/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}/Isaac/Sensors",
]
```

You can also use the following option for `isaac-sim.sh` usage:
```
./isaac-sim.sh --/persistent/isaac/asset_root/default="/home/<username>/isaacsim_assets/Assets/Isaac/{VERSION}"
```
**Remember to replace `{VERSION}` with the version of Isaac Sim you have (e.g., 4.5).**
