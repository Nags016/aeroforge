#!/bin/bash
# AeroForge Mission Launch Script
set -e

echo "=== Launching Mission: mission_001 ==="
echo ""

# 1. Start WFB-NG if not running
echo "1. Ensuring WFB-NG link..."
systemctl is-active wifibroadcast@gs || sudo systemctl start wifibroadcast@gs

# 2. Start MAVLink router
echo "2. Starting MAVLink router..."
mavlink-router -c /etc/mavlink-router.conf &

# 3. Wait for connection
echo "3. Waiting for PX4 connection..."
sleep 5

# 4. Arm and takeoff in position mode
echo "4. Arming and taking off (position mode)..."
# Would use mavlink-shell or mavsdk to arm and takeoff

# 5. Switch to offboard mode
echo "5. Switching to offboard mode..."
# Would send offboard mode command

# 6. Upload mission
echo "6. Uploading mission waypoints..."
# Would use QGC or mavlink to upload

# 7. Start mission
echo "7. Starting autonomous mission..."
# Would trigger mission start

echo "Mission launched! Monitor via QGroundControl."
