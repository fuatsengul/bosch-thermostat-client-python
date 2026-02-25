#!/bin/bash

# Deploy Bosch Thermostat Client fixes to Home Assistant
# This script copies the modified database files to the installed library

echo "🚀 Deploying Bosch Thermostat Client fixes to Home Assistant..."

# Check if running in Home Assistant container or server
PYTHON_SITE_PACKAGES="/usr/local/lib/python3.13/site-packages"
BOSCH_LIB_PATH="$PYTHON_SITE_PACKAGES/bosch_thermostat_client"

# Alternative paths for different HA installations
if [ ! -d "$BOSCH_LIB_PATH" ]; then
    PYTHON_SITE_PACKAGES="/usr/local/lib/python3.12/site-packages"
    BOSCH_LIB_PATH="$PYTHON_SITE_PACKAGES/bosch_thermostat_client"
fi

if [ ! -d "$BOSCH_LIB_PATH" ]; then
    PYTHON_SITE_PACKAGES="/usr/lib/python3.13/site-packages"
    BOSCH_LIB_PATH="$PYTHON_SITE_PACKAGES/bosch_thermostat_client"
fi

if [ ! -d "$BOSCH_LIB_PATH" ]; then
    echo "❌ Bosch Thermostat Client library not found"
    echo "   Searched in:"
    echo "   - /usr/local/lib/python3.13/site-packages/"
    echo "   - /usr/local/lib/python3.12/site-packages/"
    echo "   - /usr/lib/python3.13/site-packages/"
    echo ""
    echo "   Make sure the library is installed: pip install bosch-thermostat-client"
    exit 1
fi

echo "✅ Found Bosch library at: $BOSCH_LIB_PATH"

# Create backup
BACKUP_DIR="/tmp/bosch_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "💾 Creating backup at: $BACKUP_DIR"

# Backup original files if they exist
[ -f "$BOSCH_LIB_PATH/db/db_IVT.json" ] && cp "$BOSCH_LIB_PATH/db/db_IVT.json" "$BACKUP_DIR/"
[ -f "$BOSCH_LIB_PATH/db/__init__.py" ] && cp "$BOSCH_LIB_PATH/db/__init__.py" "$BACKUP_DIR/"
[ -d "$BOSCH_LIB_PATH/db/ivt" ] && cp -r "$BOSCH_LIB_PATH/db/ivt" "$BACKUP_DIR/"

echo "📁 Copying database files..."

# Copy the main IVT database with schedule section
cp bosch_thermostat_client/db/db_IVT.json "$BOSCH_LIB_PATH/db/db_IVT.json"
echo "   ✅ Copied db_IVT.json (with schedule section)"

# Copy the firmware-specific database with firmwareVersion field
mkdir -p "$BOSCH_LIB_PATH/db/ivt"
cp bosch_thermostat_client/db/ivt/130003.json "$BOSCH_LIB_PATH/db/ivt/130003.json"
echo "   ✅ Copied ivt/130003.json (with firmwareVersion and schedule)"

# Update the __init__.py to include IVT device type mapping
cp bosch_thermostat_client/db/__init__.py "$BOSCH_LIB_PATH/db/__init__.py"
echo "   ✅ Updated db/__init__.py (IVT device type support)"

# Set proper permissions
chmod 644 "$BOSCH_LIB_PATH/db/db_IVT.json"
chmod 644 "$BOSCH_LIB_PATH/db/ivt/130003.json"
chmod 644 "$BOSCH_LIB_PATH/db/__init__.py"

echo ""
echo "🎯 Deployment complete! Next steps:"
echo ""
echo "1. Get fresh tokens:"
echo "   cd /path/to/bosch-thermostat-client-python"
echo "   python3 examples/pointtapi_oauth_setup.py"
echo "   # Follow OAuth flow, copy tokens from tokens.json"
echo ""  
echo "2. In Home Assistant:"
echo "   - Go to Settings → Devices & Services"
echo "   - Delete existing Bosch integration (if any)"
echo "   - Add Integration → Search 'Bosch'"
echo "   - Use Protocol: OAuth2, Device Type: IVT"
echo "   - Enter Device ID: 101650657"
echo "   - Paste fresh access_token and refresh_token"
echo ""
echo "3. Restart Home Assistant"
echo ""
echo "🌟 Your K30 RF Gateway will provide:"
echo "   📊 Room temperature sensor"
echo "   🎯 Room temperature setpoint control"
echo "   🚿 DHW temperature sensor" 
echo "   🔥 DHW temperature setpoint control"
echo "   💡 Heat pump status and modulation"
echo "   🔄 Automatic token refresh"
echo ""
echo "📋 Backup location: $BACKUP_DIR"
echo "🔧 To restore: cp $BACKUP_DIR/* $BOSCH_LIB_PATH/db/"