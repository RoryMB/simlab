# Run from simlab project root

python tools/orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/prism && python run_sim.py" \
    --gateway-cmd "source activate-madsci.sh && python -m slcore.gateway.rest_gateway --num-envs 1 --robot-types ot2,pf400,sealer,peeler,thermocycler,hidex" \
    --madsci-cmd "./tools/run_madsci.sh projects/prism" \
    --workflow-cmd "source activate-madsci.sh && cd projects/prism && python run_workflow.py workflow.yaml" \
    --timeout 240
