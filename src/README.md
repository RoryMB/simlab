## Step-by-Step Instructions

### Step 1: Start Isaac Sim

**Terminal 1:**
```bash
./activate-isaacsim.sh
cd src/isaacsim/
python run.py
```

### Step 2: Start MADSci Services

**Terminal 2 (after Isaac Sim loads):**
```bash
cd src/madsci/
./run.sh
```

### Step 3: Start Robot Node

**Terminal 3:**
```bash
./activate-madsci.sh
cd src/madsci/
./run_node.sh
```

### Step 4: Submit Workflow

**Terminal 4 (after robot node connects):**
```bash
./activate-madsci.sh
cd src/
python run_workflow.py
```

**Expected Workflow Execution:**
1. Creates virtual plate and places it at `location_1`
2. Isaac Sim robot moves to source coordinates `[100, 100, 0, 0]`
3. Simulates picking up the plate
4. Isaac Sim robot moves to target coordinates `[200, 200, 0, 0]`
5. Simulates placing the plate
6. Workflow completes with status: "succeeded"

## Technical Details

### ZMQ Communication

The integration uses ZMQ REQ-REP pattern:
- **Server (Isaac Sim)**: Binds to `tcp://*:5555`
- **Client (MADSci Node)**: Connects to `tcp://localhost:5555`

**Supported Commands:**
```json
{"action": "move_joints", "joint_angles": [0, -1.57, 0, -1.57, 0, 0]}
{"action": "get_joints"}
```

### Coordinate Mapping

Location coordinates are converted to joint angles:
- `location_1`: `[100, 100, 0, 0]` → Joint angles for source position
- `location_2`: `[200, 200, 0, 0]` → Joint angles for target position

The mapping uses simplified inverse kinematics in `SimRobotInterface.location_to_joint_angles()`.

### MADSci Integration

The robot node integrates with MADSci through:
- **Actions**: `transfer` action for plate movement
- **Resources**: Virtual gripper and plate management
- **State Updates**: Periodic joint position reporting
- **Events**: Distributed logging of robot operations
