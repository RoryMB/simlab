#!/bin/bash
NODE_URL=http://127.0.0.1:8018/ python modules/sim_ur5e.py \
    --node_definition node_definitions/sim_ur5e_1.node.yaml \
    --zmq_server tcp://localhost:5555
