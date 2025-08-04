# 6-DOF Coordinate System Support

The prototyping robot system now supports both 6-DOF joint angles and Cartesian coordinates for robot positioning.

## Supported Coordinate Systems

### 1. Joint Angles (Default)
- **Format**: `[j1, j2, j3, j4, j5, j6]` in radians
- **Description**: Direct joint angle control for 6-DOF UR5e robot
- **Example**: `[0.0, -1.57, 0.0, -1.57, 0.0, 0.0]`
- **Joint Limits**: 
  - Base, Shoulder, Wrist joints: ±2π radians
  - Elbow: ±π radians

### 2. Cartesian Coordinates
- **Format**: `[x, y, z, rx, ry, rz]` in meters and radians
- **Description**: End-effector pose in Cartesian space
- **Example**: `[0.5, 0.2, 0.8, 0.0, 0.0, 1.57]`

## Configuration

### Workcell Configuration
The `workcell.yaml` file now uses 6-DOF joint angles by default:

```yaml
locations:
- location_name: location_1
  lookup:
    sim_robot_1:
    - 0.0      # Base joint
    - -1.57    # Shoulder lift
    - 0.0      # Elbow
    - -1.57    # Wrist 1
    - 0.0      # Wrist 2
    - 0.0      # Wrist 3
```

### Robot Node Configuration
Start the robot node with coordinate system preference:

```bash
# Use joint angles (default)
python sim_robot.py --coordinate_type joint_angles

# Use Cartesian coordinates
python sim_robot.py --coordinate_type cartesian
```

## Available Actions

### Enhanced Transfer Action
```python
transfer(
    source=location_1,
    target=location_2,
    coordinate_type="joint_angles",  # or "cartesian"
    auto_detect_coordinates=True     # automatically detect coordinate type
)
```

### New Movement Actions
```python
# Joint angle movement
movej(joints=[0.0, -1.57, 0.0, -1.57, 0.0, 0.0])

# Linear movement (Cartesian)
movel(target=[0.5, 0.2, 0.8, 0.0, 0.0, 1.57])

# Get current pose
get_pose()  # Returns end-effector Cartesian pose
```

## Automatic Coordinate Detection

The system can automatically detect coordinate types based on value ranges:
- Values > 10: Likely Cartesian coordinates (meters/mm)
- Values ≤ 10: Likely joint angles (radians)

## Legacy Support

The system maintains backward compatibility:
- 4-element arrays are converted to 6-DOF using legacy mapping
- Old workflows continue to work with automatic conversion

## Implementation Details

### Kinematics
- **Forward Kinematics**: Converts joint angles to end-effector pose
- **Inverse Kinematics**: Converts Cartesian pose to joint angles (simplified)
- **Joint Validation**: Ensures all joint angles are within UR5e limits

### Isaac Sim Integration
- Enhanced validation for joint angle ranges
- Better error reporting for invalid commands
- Support for pose queries

## Usage Examples

### Using Joint Angles
```yaml
# In workcell.yaml
lookup:
  sim_robot_1: [0.785, -1.2, -0.5, -1.8, 0.0, 0.0]
```

### Using Cartesian Coordinates
```python
# In workflow action
movel(target=[0.4, 0.3, 0.6, 0.0, 1.57, 0.0])
```

### Mixed Usage
```python
# Auto-detect coordinate system
transfer(
    source=joint_angle_location,
    target=cartesian_location,
    auto_detect_coordinates=True
)
```