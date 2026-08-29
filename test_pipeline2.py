import sys
sys.path.insert(0, '/home/mr_nags/aeroforge')
from autonomous_deploy import AutonomousDeploymentAgent

agent = AutonomousDeploymentAgent()
state = agent.run_full_pipeline('Fly from (0,0,2) to (20,15,3) using camera and depth to avoid dynamic obstacles with 2.5m clearance, minimize energy and time')
print(f'Final stage: {state.stage}')
print(f'Deployment package: {state.deployment_package}')