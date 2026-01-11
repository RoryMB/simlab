#!/bin/bash
set -a; source ../../madsci/config/.env; set +a
NODE_URL=http://127.0.0.1:8019/ python ./sim_ot2_rest_node.py \
    --node_definition ./sim_ot2_1.node.yaml \
    --zmq_server tcp://localhost:5556
