"""
Support for C by GE lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.c_by_ge/
"""
import logging

import time
import voluptuous as vol

from homeassistant.core import callback
from homeassistant.const import CONF_NAME, CONF_PASSWORD
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, ATTR_COLOR_TEMP, SUPPORT_COLOR_TEMP,
    ATTR_HS_COLOR, SUPPORT_COLOR, Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv
from homeassistant.util.color import \
    color_temperature_kelvin_to_mired as kelvin_to_mired
from homeassistant.util.color import \
    color_temperature_mired_to_kelvin as mired_to_kelvin

from homeassistant.util.color import color_RGB_to_hs, color_hs_to_RGB

REQUIREMENTS = ['laurel==0.3']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


def setup_platform(hass, config, add_entities,
                               discovery_info=None):
    """Set up the C by GE platform."""
    import laurel

    l = laurel.laurel(config[CONF_NAME], config[CONF_PASSWORD])
    for network in l.networks:
        network.connect()

    lights = []
    for bulb in l.devices:
        lights.append(GELight(bulb))

    add_entities(lights)


class GELight(Light):
    """Representation of a C by GE light."""

    def __init__(self, bulb):
        """Initialize the light."""

        self._bulb = bulb
        self._state = False
        self._brightness = 255
        bulb.set_callback(self.callback, None)

        self._features = SUPPORT_BRIGHTNESS

        if bulb.supports_rgb():
            self._features |= SUPPORT_COLOR

        if bulb.supports_temperature():
            self._features |= SUPPORT_COLOR_TEMP
            
    def callback(self, args):
        if self.hass is not None:
            self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._bulb.name

    @property
    def is_on(self):
        """Return true if device is on."""
        if self._bulb.brightness == 0:
            return False
        else:
            return True

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return (self._bulb.brightness * 2.55)

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._features

    @property
    def color_temp(self):
        """Return the color temperature of this light."""
        if not self._bulb.rgb:
            kelvin = self._bulb.temperature * 50 + 2000
            return kelvin_to_mired(kelvin)
        return None

    @property
    def hs_color(self):
        """Return the color of this light."""
        if self._bulb.rgb:
            r = self._bulb.red
            g = self._bulb.green
            b = self._bulb.blue
            return color_RGB_to_hs(r, g, b)
        return None

    @property
    def min_mireds(self):
        """Return minimum supported color temperature."""
        return kelvin_to_mired(7000)

    @property
    def max_mireds(self):
        """Return maximum supported color temperature."""
        return kelvin_to_mired(2000)

    @property
    def should_poll(self):
        """Don't need to poll"""
        return False

    def turn_on(self, **kwargs):
        """Turn the specified light on."""

        if not self.is_on:
            self._bulb.set_power(True)
            time.sleep(0.1)

        color = kwargs.get(ATTR_HS_COLOR)
        temperature = kwargs.get(ATTR_COLOR_TEMP)
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if color is not None:
            self._bulb.set_rgb(*color_hs_to_RGB(*color))
            time.sleep(0.1)
        elif temperature is not None:
            # Colour temperature is a percentage between 2000K and 7000K
            kelvin = mired_to_kelvin(temperature)
            percent = int((kelvin - 2000) / 50)
            self._bulb.set_temperature(percent)
            time.sleep(0.1)

        if brightness is not None:
            self._bulb.set_brightness(int(brightness/2.55))
            time.sleep(0.1)

    def turn_off(self, **kwargs):
        """Turn the specified light off."""
        self._bulb.set_power(False)
        time.sleep(0.1)
