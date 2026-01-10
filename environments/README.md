# Environment Management

This directory organizes **three separate** uv-managed virtual environments.

## Quick Setup

For new users after cloning the repository:

```bash
cd environments/isaacsim && ./setup.sh && cd ../..
cd environments/madsci && ./setup.sh && cd ../..
cd environments/usd && ./setup.sh && cd ../..
```

If you wish to personally manage each environment, the steps of `setup.sh` are explain here:

```bash
# In `environments/isaacsim` or `environments/madsci`

# Create the virtual environment (only once)
# NOTE: isaacsim requires a specific version of Python: `uv venv -p python@3.11`
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

Isaac Sim requires accepting the EULA and a lengthy startup on first run after installing/updating the isaacsim packages.
```bash
./activate-isaacsim.sh
isaacsim
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

## USD Command-Line Tools

The USD environment provides command-line utilities for inspecting, validating, and comparing USD (Universal Scene Description) files used for robot assets and simulation scenes.

### Available Tools

- **usdcat**: Print the ASCII representation of a USD file
- **usdtree**: Display the scene hierarchy as a tree structure
- **usddiff**: Compare two USD files and show differences
- **usdchecker**: Validate USD files for errors and compliance

### Installation

The USD tools are built from source (Pixar's OpenUSD v24.11) and installed to `environments/usd/usd-install/`.

**To set up the USD environment:**

```bash
cd environments/usd
./setup.sh
```

The setup script:
1. Creates a uv-managed virtual environment
2. Installs `usd-core` Python package (provides `pxr` module)
3. Installs `cmake>=3.24` in the virtual environment
4. Clones OpenUSD v24.11 from GitHub
5. Builds USD from source with minimal dependencies (no imaging, MaterialX, examples, or tutorials)
6. Installs binaries to `usd-install/bin/` and Python libraries to `usd-install/lib/python/`

**Build time:** ~20-40 minutes depending on system

### Replicating the USD Build

If you need to rebuild USD or set up on a new system:

```bash
cd environments/usd

# Clone OpenUSD repository (v24.11)
git clone --depth 1 --branch v24.11 https://github.com/PixarAnimationStudios/OpenUSD.git usd-source

# Activate the virtual environment with CMake 4.2.1
source .venv/bin/activate

# Build USD from source (minimal build, no imaging/MaterialX)
python3 usd-source/build_scripts/build_usd.py \
    --build-variant release \
    --no-imaging \
    --no-examples \
    --no-tutorials \
    --no-materialx \
    usd-install

# The build will install to usd-install/ directory
# Binaries: usd-install/bin/
# Python libs: usd-install/lib/python/
```

**Build options used:**
- `--build-variant release`: Optimized release build
- `--no-imaging`: Skip imaging libraries (Ptex, OpenVDB, OpenImageIO, etc.)
- `--no-examples`: Skip example code
- `--no-tutorials`: Skip tutorial code
- `--no-materialx`: Skip MaterialX support (would require libXt-dev system package)

### Usage

Activate the environment and use the tools:

```bash
# From project root
source activate-usd.sh

# Display scene hierarchy
usdtree assets/robots/Brooks/PF400/PF400.usd

# Search for specific prims
usdtree assets/robots/Brooks/PF400/PF400.usd | grep -i "pointer"

# View full USD file contents
usdcat assets/robots/Brooks/PF400/PF400.usd

# Compare old and new assets
usddiff assets/temp/robots/pf400.usda assets/robots/Brooks/PF400/PF400.usd

# Validate a USD file
usdchecker assets/robots/Brooks/PF400/PF400.usd
```

### Directory Structure

```
environments/usd/
├── .venv/                    # uv-managed Python virtual environment
│   └── bin/
│       ├── python3           # Python 3.12
│       └── cmake             # CMake 4.2.1
├── usd-source/               # OpenUSD v24.11 source code
├── usd-install/              # USD installation directory
│   ├── bin/                  # Command-line tools
│   │   ├── usdcat
│   │   ├── usdtree
│   │   ├── usddiff
│   │   └── usdchecker
│   ├── lib/
│   │   └── python/           # USD Python libraries (pxr module)
│   └── build/                # Build artifacts
├── requirements.in           # uv dependency file (usd-core, cmake)
├── requirements.txt          # Locked dependencies
├── setup.sh                  # Initial setup script
├── compile.sh                # Compile requirements.in → requirements.txt
└── sync.sh                   # Install from requirements.txt
```

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
