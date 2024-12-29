# File: /config/custom_components/mqtt_monitor/sensor.py

import logging
import asyncio
import sys
from datetime import datetime

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)

CONF_BROKER = 'broker'
CONF_PORT = 'port'
CONF_USERNAME = 'username'
CONF_PASSWORD = 'password'
CONF_MONITOR_TOPIC = 'monitor_topic'
CONF_CLIENT_ID = 'client_id'

DEFAULT_NAME = 'MQTT Monitor'
DEFAULT_PORT = 1883
DEFAULT_MONITOR_TOPIC = '#'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_BROKER): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_MONITOR_TOPIC, default=DEFAULT_MONITOR_TOPIC): cv.string,
    vol.Optional(CONF_CLIENT_ID, default='mqtt_monitor'): cv.string,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the MQTT Monitor sensor."""
    name = config.get(CONF_NAME)
    broker = config.get(CONF_BROKER)
    port = config.get(CONF_PORT)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    monitor_topic = config.get(CONF_MONITOR_TOPIC)
    client_id = config.get(CONF_CLIENT_ID)

    sensor = MQTTMonitorSensor(hass, name)
    async_add_entities([sensor], update_before_add=True)

    # Start MQTT client in a separate thread
    def run_mqtt_client():
        client = mqtt.Client(client_id=client_id)
        if username and password:
            client.username_pw_set(username, password)
        client.on_connect = sensor.on_connect
        client.on_message = sensor.on_message
        client.on_subscribe = sensor.on_subscribe
        client.message_callback_add('$SYS/broker/clients/connected', sensor.on_sys_message)

        try:
            client.connect(broker, port, 60)
            client.loop_forever()
        except Exception as e:
            _LOGGER.error(f"Error connecting to MQTT broker: {e}")

    hass.loop.run_in_executor(None, run_mqtt_client)

class MQTTMonitorSensor(Entity):
    """Representation of an MQTT Monitor sensor."""

    def __init__(self, hass, name):
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._state = None
        self._attributes = {}

        # Initialize data storage
        self.hass.data.setdefault('mqtt_monitor_clients', [])
        self.hass.data.setdefault('mqtt_monitor_messages', [])

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            _LOGGER.debug("Connected to MQTT broker successfully")
        else:
            _LOGGER.error(f"Failed to connect to MQTT broker, return code {rc}")
        client.subscribe('#')
        client.subscribe('$SYS/#')

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        topic = msg.topic
        timestamp = datetime.now().isoformat()
        payload = msg.payload.decode('utf-8', 'ignore')
        qos = msg.qos

        # Store the message
        message_info = {
            'topic': topic,
            'payload': payload,
            'timestamp': timestamp,
            'qos': qos
        }
        self.hass.data['mqtt_monitor_messages'].append(message_info)
        _LOGGER.debug(f"Added message: {message_info}")

        # Limit the number of stored messages
        if len(self.hass.data['mqtt_monitor_messages']) > 100:
            removed_message = self.hass.data['mqtt_monitor_messages'].pop(0)
            _LOGGER.debug(f"Removed oldest message: {removed_message}")

        # Update sensor state
        self._state = f"Last message on {topic}"

        # Limit attributes to essential data
        self._attributes = {
            'last_message_topic': topic,
            'last_message_timestamp': timestamp
        }

        # Schedule an update
        self.schedule_update_ha_state()

    def on_sys_message(self, client, userdata, msg):
        """Handle $SYS messages for client connections."""
        topic = msg.topic
        payload = msg.payload.decode('utf-8', 'ignore')
        timestamp = datetime.now().isoformat()

        if topic == '$SYS/broker/clients/connected':
            _LOGGER.debug(f"Connected clients count: {payload}")
            # Optionally, you can handle the connected clients count here

        # For more detailed client information, you might need to configure your MQTT broker to publish client connections

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Handle subscription acknowledgment."""
        _LOGGER.debug("Subscribed to topic")

    # The on_log method may not provide reliable client connection info, so we might need to remove or adjust it

