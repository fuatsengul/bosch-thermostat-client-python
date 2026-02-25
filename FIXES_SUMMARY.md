# K30RF Heat Pump System Support - Fixes Summary

## Overview
Fixed full support for K30RF/IVT heat pump systems via OAUTH2 (PoinTT API) cloud connection for Home Assistant integration.

## Key Issues Fixed

### 1. ✅ OAUTH2 Protocol Handling
**File**: `bosch_thermostat_client/bosch_cli.py`
- **Issue**: CLI was trying to use local gateway classes (IVTGateway, NefitGateway) with OAUTH2 protocol parameters they don't support
- **Fix**: OAUTH2 connections now always use `Oauth2Gateway` regardless of device_type
- **Impact**: Cloud API access now works properly

### 2. ✅ Device Type Parameter Compatibility  
**Files**: 
- `bosch_thermostat_client/gateway/ivt.py`
- `bosch_thermostat_client/gateway/nefit.py`
- `bosch_thermostat_client/gateway/easycontrol.py`

- **Issue**: Local gateway classes didn't accept `device_type` parameter
- **Fix**: Added `device_type=None` parameter to all gateway `__init__` methods for compatibility
- **Impact**: Gateway initialization no longer crashes when device_type is passed

### 3. ✅ Firmware Version Handling for OAUTH2
**File**: `bosch_thermostat_client/gateway/oauth2.py`
- **Issue**: K30RF doesn't expose firmware version, causing "unsupported firmware version None" error
- **Fix**: Custom `initialize()` method in Oauth2Gateway:
  - Tries to load firmware-specific database if available
  - Falls back to initial database gracefully if firmware version unavailable
  - Logs warnings instead of failing
- **Impact**: Gateway initializes successfully without firmware version

### 4. ✅ Device Model Detection
**File**: `bosch_thermostat_client/gateway/oauth2.py`
- **Issue**: Device detection failed, fell back to wrong models (e.g., IVTAIR for IVT device)
- **Fix**: 
  - Multi-strategy device lookup: ModuleHwIdentStr, Tok field, value matching
  - Creates generic model based on user's device_type parameter if no specific match found
  - Respects the device_type specified in configuration instead of guessing
- **Impact**: Correct database is loaded based on user's configuration

### 5. ✅ Missing Circuit Type Handling
**File**: `bosch_thermostat_client/gateway/oauth2.py`
- **Issue**: KeyError when circuit types missing from database (e.g., 'acCircuits' not in IVT database)
- **Fix**: 
  - Check if circuit type exists in database before trying to initialize
  - Skip gracefully with debug log if not supported
  - Return empty list instead of crashing
- **Impact**: Gateway initializes even when some circuit types not available

### 6. ✅ Data Dictionary Initialization
**File**: `bosch_thermostat_client/gateway/oauth2.py`
- **Issue**: KeyError on SENSORS when accessing `_data[SENSORS]`
- **Fix**: Initialize `_data` with all required keys: `{GATEWAY: {}, HC: None, DHW: None, AC: None, SENSORS: None}`
- **Impact**: No KeyError exceptions during initialization

### 7. ✅ Database Updates
**Files**:
- `bosch_thermostat_client/db/db_IVT.json`
- `bosch_thermostat_client/db/db_IVTAIR.json`
- `bosch_thermostat_client/db/db_POINTTAPI.json`

**Changes**:
- **db_IVT.json**: 
  - Added heating circuits, DHW circuits, heat sources definitions
  - Added K30RF model entries (both "72" and "K30RF" keys)
  - Fixed dateTime path: `/gateway/DateTime` → `/gateway/dateTime`

- **db_IVTAIR.json**: 
  - Added AC circuits, heating circuits, DHW circuits, heat sources definitions
  - Fixed dateTime path
  - Added K30RF model support

- **db_POINTTAPI.json** (new): 
  - Created for PoinTT API cloud devices
  - Includes all circuit types: AC, heating, DHW, heat sources
  - Generic model fallback support

### 8. ✅ Database Loader Updates
**File**: `bosch_thermostat_client/db/__init__.py`
- **Issue**: POINTTAPI device type not recognized
- **Fix**: Added POINTTAPI to DEVICE_TYPES mapping
- **Impact**: Can load POINTTAPI-specific databases

## Home Assistant Configuration Options

Users can now use any of these device types with OAUTH2:

```yaml
bosch:
  protocol: OAUTH2
  device_type: ivt          # IVT heat pump systems
  # OR
  device_type: ivtair       # Air handlers / IVTAIR systems
  # OR
  device_type: pointtapi    # Generic PoinTT API devices
  
  host: "101650657"         # Device ID
  token_file: "tokens.json" # Or use refresh_token in entry
```

## Testing Results

✅ **CLI Test**:
```bash
bosch_cli query --protocol OAUTH2 --host 101650657 --token tokens.json --device ivt -p /heatingCircuits/hc1/currentRoomSetpoint
```
Returns: `21.0°C` ✓

✅ **Python Integration Test** (`test_oauth2_init.py`):
- Gateway initializes without errors
- UUID retrieved successfully: `101650657`
- Check connection succeeds
- All circuit types handled gracefully

✅ **Database Validation**:
- All JSON files valid and syntactically correct
- K30RF models included
- All circuit types defined

## Backwards Compatibility

✅ All changes are backwards compatible:
- Local gateway classes (HTTP, XMPP) unchanged
- Existing configurations continue to work
- New device_type parameter is optional
- Generic model fallback for unknown devices

## Files Modified

1. `bosch_thermostat_client/bosch_cli.py` - OAUTH2 protocol handling
2. `bosch_thermostat_client/gateway/oauth2.py` - Device detection, circuit handling, initialization
3. `bosch_thermostat_client/gateway/ivt.py` - Device type parameter
4. `bosch_thermostat_client/gateway/nefit.py` - Device type parameter
5. `bosch_thermostat_client/gateway/easycontrol.py` - Device type parameter
6. `bosch_thermostat_client/db/__init__.py` - POINTTAPI support
7. `bosch_thermostat_client/db/db_IVT.json` - Circuit definitions, models
8. `bosch_thermostat_client/db/db_IVTAIR.json` - Circuit definitions, models
9. `bosch_thermostat_client/db/db_POINTTAPI.json` - New database file

## Next Steps for Home Assistant Integration

1. Install the updated bosch-thermostat-client package
2. Configure with `protocol: OAUTH2` and `device_type: ivt`
3. Use PoinTT API tokens for authentication
4. All heating circuits, DHW, and heat pump sensors should be detected automatically

---
**Date**: February 20, 2026
**Status**: Complete and tested ✅
