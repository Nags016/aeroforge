import sys
sys.path.insert(0, '/home/mr_nags/aeroforge')
from aeroforge_production import AeroForgeProduction

app = AeroForgeProduction()
app.print_banner()
app.show_status()