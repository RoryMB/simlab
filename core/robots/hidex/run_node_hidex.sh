#!/bin/bash
set -a; source ../../madsci/config/.env; set +a
NODE_URL=http://127.0.0.1:8024/ python ./sim_hidex_rest_node.py \
    --node_definition ./sim_hidex_1.node.yaml \
    --zmq_server tcp://localhost:5561
