#!/bin/bash

echo "🚀 Installing fixed bosch-thermostat-client with database fixes..."

# Step 1: Uninstall existing version
echo "📦 Uninstalling existing bosch-thermostat-client..."
pip uninstall bosch-thermostat-client -y

# Step 2: Install from local directory with fixes  
echo "📦 Installing fixed version from local directory..."
cd /Users/user/repo/GIT/bosch-thermostat-homeassistant/bosch-thermostat-client-python
pip install .

# Step 3: Verify installation
echo "✅ Verifying installation..."
python3 -c "
import bosch_thermostat_client
print('Library version:', bosch_thermostat_client.__version__ if hasattr(bosch_thermostat_client, '__version__') else 'Unknown')
print('Library location:', bosch_thermostat_client.__file__)

import json
import os
lib_path = os.path.dirname(bosch_thermostat_client.__file__)
db_path = os.path.join(lib_path, 'db')

# Check database files
print('=== Database Status ===')
try:
    ivt_db = os.path.join(db_path, 'db_IVT.json')
    with open(ivt_db) as f:
        db = json.load(f)
        print('✅ db_IVT.json has schedule:', 'schedule' in db)
    
    fw_db = os.path.join(db_path, 'ivt', '130003.json')
    if os.path.exists(fw_db):
        with open(fw_db) as f:
            db = json.load(f)
            print('✅ ivt/130003.json has schedule:', 'schedule' in db)
            print('✅ ivt/130003.json has firmwareVersion:', 'firmwareVersion' in db)
    else:
        print('❌ ivt/130003.json missing')
        
except Exception as e:
    print('❌ Error:', e)
"

echo ""
echo "🎯 Next steps:"
echo "1. Restart Home Assistant"
echo "2. Test your heat pump integration" 
echo "3. You should now see temperature sensors and controls!"