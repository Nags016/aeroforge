import sys
sys.path.insert(0, '/home/mr_nags/aeroforge')
from autonomous_deploy import AutonomousDeploymentAgent

agent = AutonomousDeploymentAgent()
state = agent.run_full_pipeline('Fly from (0,0,2) to (10,10,2) avoiding obstacles')
print(f'Final stage: {state.stage}')
print(f'Deployment package: {state.deployment_package}')