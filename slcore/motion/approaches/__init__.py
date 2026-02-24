"""Motion approach implementations.

This package contains concrete implementations of MotionApproach for
different motion planning algorithms.

Available approaches:
- DifferentialIKApproach: Wraps Isaac Lab's DifferentialIKController
"""

from slcore.motion.approaches.differential_ik import DifferentialIKApproach

__all__ = [
    "DifferentialIKApproach",
]
