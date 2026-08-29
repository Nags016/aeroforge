import sys
sys.path.insert(0, '/home/mr_nags/aeroforge')
from aeroforge_production import AeroForgeProduction

app = AeroForgeProduction()
app.run_deploy_pipeline('Fly from (0,0,2) to (15,10,3) using camera and depth to avoid dynamic obstacles with 2m clearance')