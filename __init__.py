import logging
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'mqtt_monitor'

def setup(hass, config):
    """Set up the MQTT Monitor component."""
    hass.http.register_view(MQTTMonitorDataView(hass))
    return True

class MQTTMonitorDataView(HomeAssistantView):
    """View to return MQTT monitor data."""

    url = '/api/mqtt_monitor/data'
    name = 'api:mqtt_monitor:data'
    requires_auth = False  # Allow unauthenticated access

    def __init__(self, hass):
        """Initialize the view."""
        self.hass = hass

    async def get(self, request):
        """Handle the GET request."""
        data = {
            'clients': self.hass.data.get('mqtt_monitor_clients', []),
            'messages': self.hass.data.get('mqtt_monitor_messages', [])
        }
        return self.json(data)