#!/bin/bash
# Setup Uptime Kuma monitors via API
# Run this after first login to Uptime Kuma web interface

KUMA_URL="http://localhost:3001"

echo "=== Uptime Kuma Monitor Setup ==="
echo ""
echo "NOTE: You need to create an admin account first via web interface."
echo "Open http://status.149.154.65.75.nip.io/ in browser and create admin user."
echo ""
echo "Then run this script with credentials:"
echo "  $0 <username> <password>"
echo ""

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <username> <password>"
    exit 1
fi

USER="$1"
PASS="$2"

# Login
TOKEN=$(curl -s -X POST "$KUMA_URL/api/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "ERROR: Login failed. Check credentials."
    exit 1
fi

echo "Logged in successfully."

# Add monitors
add_monitor() {
    local name="$1"
    local url="$2"
    local type="${3:http}"
    local interval="${4:60}"
    
    curl -s -X POST "$KUMA_URL/api/monitor" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{\"name\":\"$name\",\"url\":\"$url\",\"type\":\"$type\",\"interval\":$interval}" 2>/dev/null
    echo "  Added: $name"
}

echo "Adding monitors..."
add_monitor "Nexus API" "http://127.0.0.1:8000/" "http" 60
add_monitor "Loki Dashboard" "http://127.0.0.1:8080/" "http" 60
add_monitor "Uptime Kuma" "http://127.0.0.1:3001/" "http" 60
add_monitor "Nginx HTTPS" "https://127.0.0.1/" "http" 120
add_monitor "VPN WireGuard" "127.0.0.1" "port" 300
add_monitor "PostgreSQL" "127.0.0.1" "port" 300
add_monitor "Redis" "127.0.0.1" "port" 300
add_monitor "MySQL" "127.0.0.1" "port" 300
add_monitor "Qdrant" "127.0.0.1" "port" 300

echo ""
echo "Done! Monitors added to Uptime Kuma."
echo "Configure notification channels (Telegram) in web interface."
