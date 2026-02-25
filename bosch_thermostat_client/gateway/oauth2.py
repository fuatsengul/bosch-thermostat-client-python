"""Gateway module connecting to Bosch thermostat via PoinTT API."""

import json
import logging

from bosch_thermostat_client.connectors import connector_ivt_chooser
from bosch_thermostat_client.const import (
    GATEWAY,
    HC,
    AC,
    MODELS,
    OAUTH2,
    SENSORS,
    VALUE,
    VALUES,
    FIRMWARE_VERSION,
    TYPE,
    ID,
    REFERENCES,
    SYSTEM_BUS,
    UUID,
    DHW,
)
from bosch_thermostat_client.const.ivt import SYSTEM_INFO
from bosch_thermostat_client.const.oauth2 import CIRCUIT_TYPES, SYSTEM_MODEL
from bosch_thermostat_client.exceptions import DeviceException, FirmwareException, UnknownDevice
from bosch_thermostat_client.db import get_db_of_firmware, async_get_errors
from bosch_thermostat_client.circuits import Circuits
from bosch_thermostat_client.circuits.circuits import choose_circuit_type

from .base import BaseGateway

_LOGGER = logging.getLogger(__name__)


class Oauth2Gateway(BaseGateway):
    """Gateway connecting to the Bosch PoinTT API."""

    circuit_types = CIRCUIT_TYPES

    def __init__(
        self,
        session,
        device_type,
        session_type=None,
        host=None,
        access_key=None,
        access_token=None,
        refresh_token=None,
        token_expires_at=None,
        token_file=None,
        **kwargs
    ):
        """OAuth2 Gateway constructor

        Args:
            session: aiohttp session for HTTP requests (required for OAuth2)
            session_type (str, optional): Protocol type (accepted for compatibility, ignored - always HTTP)
            device_type (str, optional): Device type for database loading (e.g., "IVT", "NEFIT", "EASYCONTROL")
            host (str): Device ID for the OAuth2 API
            access_key (optional): Not used for OAuth (accepted for compatibility with HA)
            access_token (str): OAuth access token
            refresh_token (str, optional): OAuth refresh token for token renewal
            token_expires_at (str, optional): ISO format timestamp when token expires
            token_file (str, optional): Path to token storage file (for standalone use, not HA)
            **kwargs: Additional arguments for compatibility
        """
        self._device_id = host  # For OAuth2 API, host is the device ID
        self._access_token = access_token
        self._refresh_token = refresh_token
        self.device_type = device_type

        # Use the connector chooser to get the right connector
        Connector = connector_ivt_chooser(OAUTH2)
        self._connector = Connector(
            host=host,  # Device ID
            access_token=access_token,
            device_type=device_type,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            loop=session,
            token_file=token_file,
        )
        self._data = {GATEWAY: {}, HC: None, DHW: None, AC: None, SENSORS: None}
        super().__init__(host)

    async def _update_info(self, initial_db):
        """Update gateway info from Bosch device."""
        for name, uri in initial_db.items():
            try:
                response = await self._connector.get(uri)
                if VALUE in response:
                    self._data[GATEWAY][name] = response[VALUE]
                elif name == SYSTEM_INFO:
                    self._data[GATEWAY][SYSTEM_INFO] = response.get(VALUES, [])
            except DeviceException as err:
                _LOGGER.debug("Can't fetch data for update_info %s", err)
                pass

    def _update_circuit_types(self, device_type):
        """Update circuit types based on detected device type.
        
        This ensures we only initialize circuits that the device actually has.
        For example, IVT heat pumps don't have AC circuits.
        """
        from bosch_thermostat_client.const.oauth2 import CIRCUIT_TYPES as OAUTH2_CIRCUIT_TYPES
        from bosch_thermostat_client.const.ivt import CIRCUIT_TYPES as IVT_CIRCUIT_TYPES
        from bosch_thermostat_client.const.easycontrol import CIRCUIT_TYPES as EASYCONTROL_CIRCUIT_TYPES
        
        _LOGGER.debug(f"_update_circuit_types called with device_type={device_type}")
        
        if device_type == "IVT":
            self.circuit_types = IVT_CIRCUIT_TYPES
            _LOGGER.info(f"✓ Updated circuit types to IVT: {list(IVT_CIRCUIT_TYPES.keys())}")
        elif device_type == "EASYCONTROL":
            self.circuit_types = EASYCONTROL_CIRCUIT_TYPES
            _LOGGER.info(f"✓ Updated circuit types to EASYCONTROL: {list(EASYCONTROL_CIRCUIT_TYPES.keys())}")
        else:
            # For IVTAIR and other types, use OAuth2 circuit types
            self.circuit_types = OAUTH2_CIRCUIT_TYPES
            _LOGGER.info(f"✓ Updated circuit types to {device_type}: {list(OAUTH2_CIRCUIT_TYPES.keys())}")

    def get_device_model(self, _db):
        """Find device model."""
        system_bus = self._data[GATEWAY].get(SYSTEM_BUS)
        model_scheme = _db[MODELS]
        self._bus_type = system_bus
        system_info = self._data[GATEWAY].get(SYSTEM_INFO)
        attached_devices = {}
        _LOGGER.warning(f"[Detection] init")
        # Initialize detected type from user config
        self._detected_device_type = self.device_type
        
        # DETECTION METHOD 1: Check hardware version
        hw_version = self._data[GATEWAY].get("versionHardware", "")
        _LOGGER.debug(f"[Detection] versionHardware from GATEWAY data: '{hw_version}'")
        if hw_version and "K30RF" in hw_version:
            _LOGGER.info(f"✓ [Detection] Detected K30RF heat pump from versionHardware: {hw_version}")
            self._detected_device_type = "IVT"
        
        # DETECTION METHOD 2: Check system_info for heat pump modules
        if system_info:
            _LOGGER.debug(f"[Detection] System info available with {len(system_info)} devices")
            for i, info in enumerate(system_info):
                if not isinstance(info, dict):
                    _LOGGER.debug(f"[Detection] Skipping non-dict entry {i}: {type(info)}")
                    continue
                    
                _id = info.get("ModuleHwIdentStr", "")
                _LOGGER.debug(f"[Detection] Device {i}: ModuleHwIdentStr='{_id}'")
                
                # Check if this is a heat pump device
                if _id in ("CUHP", "K30RF", "HMC310"):
                    _LOGGER.info(f"✓ [Detection] Detected heat pump hardware in system_info: {_id}")
                    self._detected_device_type = "IVT"
                
                model = model_scheme.get(_id)
                
                # 2. Try Tok field (numeric ID)
                if not model:
                    tok = info.get("Tok", -1)
                    if tok != -1:
                        _LOGGER.debug(f"  [Detection] Checking Tok: {tok}")
                        model = model_scheme.get(tok)
                
                # 3. Try to find by value match
                if not model:
                    for key, val in model_scheme.items():
                        if isinstance(val, dict) and val.get("value") == _id:
                            model = val
                            _id = key
                            break
                
                if model is not None:
                    _LOGGER.debug(f"  [Detection] Found model: {model}")
                    attached_devices[str(_id)] = model
            
            if attached_devices:
                found_model = attached_devices[sorted(attached_devices.keys())[-1]]
                _LOGGER.debug("[Detection] Using detected model %s as database schema", found_model[VALUE])
                return found_model
        else:
            _LOGGER.debug("[Detection] No system_info available for device detection")
        
        # DETECTION METHOD 3: Check by system model
        sys_model = self._data[GATEWAY].get(SYSTEM_MODEL)
        if sys_model:
            _LOGGER.debug(f"[Detection] Checking SYSTEM_MODEL: {sys_model}")
            model = model_scheme.get(sys_model)
            if model is not None:
                _LOGGER.debug("[Detection] Found model via SYSTEM_MODEL: %s", model)
                return model

        # Fallback: create a generic model with detected device type
        if model_scheme:
            _LOGGER.info(f"[Detection] Creating generic model for device_type={self._detected_device_type}")
            generic_model = {
                VALUE: f"generic_{self._detected_device_type}",
                "name": f"Generic {self._detected_device_type} Device (OAuth2)",
                TYPE: self._detected_device_type
            }
            _LOGGER.warning(
                "[Detection] No specific device model found. Using generic model for device_type=%s", 
                self._detected_device_type
            )
            return generic_model
        
        _LOGGER.error(
            "I cannot find supported device. Your devices: %s", json.dumps(system_info)
        )
        exit(1)

    async def initialize(self):
        """Initialize gateway asynchronously.
        
        Override base class to handle OAuth2 where firmware version might not be available.
        """
        from bosch_thermostat_client.db import get_initial_db
        
        initial_db = await self.get_base_db()
        await self._update_info(initial_db.get(GATEWAY))
        self._firmware_version = self._data[GATEWAY].get(FIRMWARE_VERSION)
        self._device = self.get_device_model(initial_db)
        
        if self._device and VALUE in self._device:
            _LOGGER.debug("Found device %s", json.dumps(self._device))
            
            # Get the detected device type
            detected_type = self._device.get(TYPE, self.device_type)
            _LOGGER.info(f"[Init] Device model TYPE: {self._device.get(TYPE)} | Detected: {detected_type} | User config: {self.device_type}")
            
            # If detected type differs from user's config, reload the correct database
            if detected_type != self.device_type:
                _LOGGER.info(
                    f"🔄 [Init] Device type mismatch! User selected {self.device_type}, "
                    f"but device is {detected_type}. Reloading correct database..."
                )
                initial_db = await get_initial_db(detected_type)
                if not initial_db:
                    _LOGGER.error(f"Could not load database for detected type {detected_type}")
                    raise UnknownDevice(f"Cannot load database for device type {detected_type}")
                _LOGGER.info(f"✓ [Init] Successfully reloaded {detected_type} database")
            
            # Update circuit types based on detected device type
            # This ensures we only try to initialize circuits that the device actually has
            self._update_circuit_types(detected_type)
            
            # For OAuth2, try to load firmware-specific DB, but don't fail if we can't
            if self._firmware_version:
                self._db = await get_db_of_firmware(
                    detected_type, self._firmware_version
                )
                if self._db:
                    _LOGGER.debug(
                        f"Loading database: {detected_type} for firmware {self._firmware_version}"
                    )
                    initial_db.pop(MODELS, None)
                    self._db.update(initial_db)
                    self._errors = await async_get_errors(self.device_type)
                    self._initialized = True
                    return
                _LOGGER.warning(
                    f"Could not find firmware-specific database for {self._firmware_version}. Using initial database."
                )
            
            # Fallback: use initial database without firmware-specific DB
            _LOGGER.info(f"Using {detected_type} database for OAuth2 connection")
            initial_db.pop(MODELS, None)
            self._db = initial_db
            self._errors = await async_get_errors(self.device_type)
            self._initialized = True
            return
        
        raise UnknownDevice("Your device is unknown %s" % json.dumps(self._device))

    async def initialize_circuits(self, circ_type):
        """Initialize circuits for PoinTT API.

        PoinTT API doesn't expose circuit discovery endpoints. We create the single
        AC circuit directly instead of using the crawl() discovery mechanism.
        """
        # Get the database key for this circuit type
        db_key = CIRCUIT_TYPES.get(circ_type)
        
        # Check if this circuit type is supported in the database
        if db_key not in self._db:
            _LOGGER.debug(f"Circuit type {circ_type} ({db_key}) not supported in database, skipping")
            return []
        
        # Log warning if we're using placeholder database entries (list instead of dict)
        if isinstance(self._db.get(db_key), list):
            _LOGGER.warning(
                f"Circuit type {circ_type} ({db_key}) has placeholder database entry. "
                f"Firmware {self._firmware_version} may not be fully supported. "
                "Attempting to create circuit with limited functionality."
            )
        
        if circ_type == AC:
            # Create Circuits container
            self._data[circ_type] = Circuits(
                self._connector,
                circ_type,
                self._bus_type,
                self.device_type
            )

            # Create static circuit data for the single AC unit
            # This replaces the need for /acCircuits and /ac1 endpoints
            circuit_id = "ac1"

            # Get the circuit class for AC + POINTTAPI
            CircuitClass = choose_circuit_type(self.device_type, circ_type)

            # Create the AC circuit directly
            # Note: _type should be the database key (e.g., "acCircuits"), not the const (e.g., "ac")
            try:
                circuit_object = CircuitClass(
                    connector=self._connector,
                    attr_id=circuit_id,
                    db=self._db,
                    _type=db_key,  # Maps AC -> "acCircuits"
                    bus_type=self._bus_type,
                )
                _LOGGER.debug(f"Created AC circuit object: {circuit_object}")
            except Exception as e:
                _LOGGER.error(f"Failed to create AC circuit object: {e}", exc_info=True)
                return []

            if circuit_object:
                try:
                    await circuit_object.initialize()
                    _LOGGER.debug(f"AC circuit initialized, state={circuit_object.state}")
                except Exception as e:
                    _LOGGER.error(f"Failed to initialize AC circuit: {e}", exc_info=True)
                    return []

                if circuit_object.state:
                    self._data[circ_type]._items.append(circuit_object)
                    _LOGGER.info("Successfully initialized AC circuit: ac1")
                else:
                    _LOGGER.warning("AC circuit ac1 failed to initialize (state=False)")
            else:
                _LOGGER.warning("Failed to create AC circuit object")

            # Return the list of circuits for get_capabilities() to detect
            return self.get_circuits(circ_type)

        else:
            # For other circuit types (HC, DHW, etc.), use standard discovery
            return await super().initialize_circuits(circ_type)

    @property
    def ac_circuits(self):
        """Get AC circuit list."""
        if AC in self._data and self._data[AC]:
            return self._data[AC].circuits
        return []

    @property
    def access_token(self):
        """Return current OAuth access token.

        May differ from initial token if refresh occurred.
        Home Assistant should read this after operations and update
        entry.data if it changed.
        """
        return self._connector._access_token

    @property
    def access_key(self):
        """Return None - OAuth doesn't use access_key.

        Provided for compatibility with Home Assistant's standard pattern.
        """
        return None

    @property
    def refresh_token(self):
        """Return current OAuth refresh token.

        Home Assistant should store this in entry.data for persistence.
        """
        return self._connector._refresh_token

    @property
    def token_expires_at(self):
        """Return token expiration timestamp as ISO string.

        Returns:
            str: ISO format timestamp (e.g., "2025-10-30T15:30:00+00:00")
            None: If expiration not set
        """
        if self._connector._token_expires_at:
            return self._connector._token_expires_at.isoformat()
        return None

    def get_token_info(self):
        """Get all token information for HA to store/compare.

        Returns:
            dict: Dictionary with token information:
                - access_token: Current OAuth access token
                - refresh_token: Current OAuth refresh token
                - token_expires_at: ISO string of expiration time
                - device_id: Device ID (for validation)

        Example for HA:
            # Get current tokens
            token_info = gateway.get_token_info()

            # Compare with stored tokens
            if token_info != entry.data.get('token_info'):
                # Update config entry
                hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, **token_info}
                )
        """
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expires_at': self.token_expires_at,
            'device_id': self._device_id,
        }

    def tokens_changed(self, stored_access_token, stored_refresh_token=None):
        """Check if tokens have changed since last storage.

        Useful for HA to determine if config entry needs updating.

        Args:
            stored_access_token: The access token stored in HA config entry
            stored_refresh_token: The refresh token stored in HA config entry (optional)

        Returns:
            bool: True if tokens have changed, False otherwise

        Example for HA:
            # In thermostat_refresh or after any gateway operation
            if gateway.tokens_changed(
                entry.data['access_token'],
                entry.data.get('refresh_token')
            ):
                _LOGGER.info("OAuth tokens refreshed, updating config entry")
                hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        'access_token': gateway.access_token,
                        'refresh_token': gateway.refresh_token,
                        'token_expires_at': gateway.token_expires_at,
                    }
                )
        """
        if self.access_token != stored_access_token:
            return True
        if stored_refresh_token and self.refresh_token != stored_refresh_token:
            return True
        return False

    async def check_firmware_validity(self):
        """Check firmware validity.

        PoinTT API doesn't expose firmware version endpoint.
        We hardcode firmware version during initialize(), so if
        the database loaded successfully, firmware is valid.

        Returns:
            bool: Always True for PoinTT API
        """
        return True

    async def check_connection(self):
        """Check connection and return UUID.

        For PoinTT API, the device_id is the unique identifier.
        The API doesn't expose a separate /gateway/uuid endpoint.

        Returns:
            str: Device ID (which serves as the UUID)
        """
        try:
            # Initialize if needed (validates credentials, loads database)
            if not self._initialized:
                await self.initialize()

            # For PoinTT API, device_id IS the UUID
            # Store it in expected location for HA component
            if UUID not in self._data[GATEWAY]:
                self._data[GATEWAY][UUID] = self._device_id

            _LOGGER.debug("PoinTT API connection validated, UUID: %s", self.uuid)

        except Exception as err:
            _LOGGER.error("Failed to check_connection: %s", err)
            raise

        return self.uuid
