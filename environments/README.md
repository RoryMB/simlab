# Environment Management

This directory organizes **two separate** uv-managed virtual environments.

## Quick Setup

For new users after cloning the repository:

```bash
cd environments/isaacsim && ./setup.sh && cd ../..
cd environments/madsci && ./setup.sh && cd ../..
```

Commands to individually manage each environment:

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
