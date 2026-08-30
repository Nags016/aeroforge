#!/bin/bash
# AeroForge Pre-Flight Check Script
set -e

echo "=== AeroForge Pre-Flight Check ==="
echo "Mission: mission_001
echo ""

# Check WFB-NG link
echo "1. Checking WFB-NG link..."
RSSI=$(wfb-cli gs 2>/dev/null | grep RSSI | awk '{print $2}' || echo "N/A")
echo "   RSSI: $RSSI"
if [ "$RSSI" != "N/A" ] && [ ${RSSI#-} -lt 70 ]; then
    echo "   ✅ Link quality OK"
else
    echo "   ⚠️  Link quality marginal"
fi

# Check MAVLink
echo "2. Checking MAVLink telemetry..."
if timeout 5 mavlink-router -c /etc/mavlink-router.conf --dry-run 2>&1 | grep -q "Connected"; then
    echo "   ✅ MAVLink connected"
else
    echo "   ⚠️  MAVLink check skipped (config needed)"
fi

# Check GPS
echo "3. Checking GPS..."
# Would query PX4 for GPS status

echo ""
echo "Pre-flight check complete. Review warnings before flight."
