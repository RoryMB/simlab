#!/bin/bash
set -a; source ../../madsci/config/.env; set +a
NODE_URL=http://127.0.0.1:8018/ python ./sim_ur5e_rest_node.py \
    --node_definition ./sim_ur5e_1.node.yaml \
    --zmq_server tcp://localhost:5555
