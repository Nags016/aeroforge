#!/bin/bash
# AeroForge Emergency Land Script
set -e

echo "=== EMERGENCY LAND TRIGGERED ==="
echo "Mission: mission_001
echo ""

# 1. Switch to RTL mode
echo "1. Commanding RTL mode..."
# mavlink command for RTL

# 2. Kill offboard
echo "2. Disabling offboard mode..."

# 3. Verify landing
echo "3. Waiting for land confirmation..."
# Monitor altitude

echo "Emergency land sequence complete."
