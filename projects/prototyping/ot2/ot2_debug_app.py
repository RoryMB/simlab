"""OT-2 Movement Debug Application"""

from pathlib import Path
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.workflow_types import WorkflowDefinition

def main():
    """Run the OT-2 movement debug test"""
    
    print("=" * 60)
    print("OT-2 MOVEMENT DEBUG TEST APPLICATION")
    print("=" * 60)
    
    # Protocol and workflow paths
    protocol_path = Path(__file__).parent / "ot2_movement_debug.py"
    workflow_path = Path(__file__).parent / "ot2_debug_workflow.yaml"
    
    if not protocol_path.exists():
        print(f"ERROR: Protocol not found at {protocol_path}")
        return 1
        
    if not workflow_path.exists():
        print(f"ERROR: Workflow not found at {workflow_path}")
        return 1
    
    try:
        print("\\nInitializing MADSci client...")
        # Initialize client
        client = WorkcellClient(workcell_server_url="http://localhost:8015")
        
        print("\\nLoading workflow...")
        # Load workflow definition
        workflow = WorkflowDefinition.from_yaml(workflow_path)
        
        print("\\nSubmitting movement debug workflow...")
        print(f"Protocol: {protocol_path}")
        print(f"Workflow: {workflow_path}")
        
        # Submit workflow
        result = client.submit_workflow(
            workflow=workflow,
            parameters={
                "protocol_path": str(protocol_path)
            },
            await_completion=True
        )
        
        print(f"\\nWorkflow completed!")
        print(f"Status: {result.status.description}")
        print(f"Result: {result}")
        
        print("\\n" + "=" * 60)
        print("DEBUG TEST INSTRUCTIONS:")
        print("1. Check the Isaac Sim console for [ZMQ_OT2_SERVER] debug messages")
        print("2. If you see ZMQ messages, the connection is working")  
        print("3. If you see no ZMQ messages, the connection failed")
        print("4. Watch the simulated OT-2 robot in Isaac Sim for movement")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\\nERROR: Workflow execution failed")
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        
        import traceback
        print(f"\\nFull traceback:")
        traceback.print_exc()
        
        return 1

if __name__ == "__main__":
    main()