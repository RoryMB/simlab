#!/bin/bash
NODE_NODE_URL=http://127.0.0.1:8008/ python modules/sim_robot.py \
    --node_definition node_definitions/sim_robot_1.node.yaml \
    --zmq_server tcp://localhost:5555
