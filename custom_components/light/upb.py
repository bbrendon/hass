"""
This is using /dev/shm to get the current values into the hass update method.

Support for UPB lights

Improvements:
- ditch upb-cli and do everything natively
- listen for status changes in real time on the network
- optionally poll all the devices in the network every x minutes for their
  status
- instead of recreating the light config in configuration.yaml, read the config
  from the upstart export file

"""
import logging
import time
import os

from subprocess import check_output, CalledProcessError, STDOUT

import voluptuous as vol


from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, SUPPORT_BRIGHTNESS, SUPPORT_FLASH,
    ATTR_FLASH, FLASH_SHORT, FLASH_LONG, Light, PLATFORM_SCHEMA)

from homeassistant.const import (CONF_NAME, CONF_ID, CONF_DEVICES)

import homeassistant.helpers.config_validation as cv

serial_port = ''
network_id = ''

_LOGGER = logging.getLogger(__name__)

CONF_SERIAL_PORT = 'serial_port'
CONF_NETWORK_ID = 'network_id'


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        {
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
        }
    ]),
    vol.Required(CONF_SERIAL_PORT): cv.string,
    vol.Required(CONF_NETWORK_ID): cv.string,

})



def dump(obj):
    for attr in dir(obj):
        if hasattr( obj, attr ):
            print( "obj.%s = %s" % (attr, getattr(obj, attr)))



def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the UPB Light platform"""
    
    global serial_port, network_id

    serial_port = config.get(CONF_SERIAL_PORT)
    network_id = config.get(CONF_NETWORK_ID)
    
    try:
        upb_command('-V')
    except CalledProcessError as err:
        _LOGGER.error(err.output)
        return False

    add_devices(UPBLight(light) for light in config[CONF_DEVICES])

class UPBLight(Light):
    """Representation of an UPB Light"""

    def __init__(self, light):
        """Initialize an UPB Light"""
        self._light = light
        self._name = 'upb_' + light['name']
        self._id = light['id']
        self._brightness = None
        self._state = None

    @property
    def name(self):
        """Return the display name of this light"""
        return self._name

    @property
    def supported_features(self):
        """Flag supported features"""
        return (SUPPORT_BRIGHTNESS | SUPPORT_FLASH)

    @property
    def brightness(self):
        """Return the brightness of the light"""
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on"""
        return self._state

    # Pass id and brightness (%) to write file.
    def write_file(self, id,level):
        outfile = open('/dev/shm/upb_device_'+id,'w')
        outfile.write(level)
        outfile.close()

    def turn_on(self, **kwargs):
        """Instruct the light to turn on""" 
        _LOGGER.debug("TURN_ON")
  
        flash = kwargs.get(ATTR_FLASH)

        bright_pct = int((kwargs.get(ATTR_BRIGHTNESS,255)/255)*100)

        if flash:
            # flashing is full on/off. so lets just say its on.
            bright_pct = 255
            # upb-cli -n 22 -i 83 -t device -c blink -b 50  --send -p /dev/ttyS1
            if flash == "short":
                flash_val = 50
            if flash == "long":
                flash_val = 100
            upb_command(' -i ' + self._id + ' -t device -c blink -b ' + str(flash_val) + ' --send' )
        else:
            upb_command(' -i ' + self._id + ' -t device -c goto -l ' + str(bright_pct) + ' --send' )

        time.sleep(0.5)
        self.write_file(self._id, str(bright_pct))
        self._brightness = kwargs.get(ATTR_BRIGHTNESS)
        self._state = True
        time.sleep(0.5)

    def turn_off(self, **kwargs):
        """Instruct the light to turn off"""
        _LOGGER.debug("TURN_OFF")

        upb_command(' -i ' + self._id + ' -t device -c goto -l 0 --send' )
        time.sleep(1)        
        upb_command(' -i ' + self._id + ' -t device -c goto -l 0 --send' )
        time.sleep(1)

        self._brightness = 0
        self._state = False
        self.write_file(self._id, "0" )

    def update(self):
        """Fetch new state data for this light. Do not put sleep in here because
            this method runs over 100 times per minute"""
        #print("UPDATE")

        #self._state = bool(get_unit_status(self._id))
        #self._light.update()
        #self._state = self._light.is_on()
        #self._brightness = self._light.brightness
        #id = self._id

        filepath = '/dev/shm/upb_device_'+self._id
        try:
            readfile = open(filepath,'r')
        except FileNotFoundError:
            # file doesn't exist. the updater daemon hasn't yet created it.
            # create it with value 0.
            writefile = open(filepath,'w') 
            writefile.write("0")
            writefile.close()

        else:
            # file exists
            bright_pct = int(readfile.read())
            readfile.close()

            self._brightness = int(bright_pct / 100 * 255)
            if self._brightness > 0:
                self._state = True
            elif self._brightness == 0:
                self._state = False
            #print('UPDATE : id / brt(0-255): ' + self._id +' / ' + str(self._brightness))
            _LOGGER.debug('UPDATE : id / brt(0-255): %s / %d',
                    self._id, int(self._brightness))
            #bright_pct = int((kwargs.get(ATTR_BRIGHTNESS,255)/255)*100)
            

def upb_command(command):
    """Execute UPB command and check output"""

    return check_output(['upb-cli','-p',serial_port,'-n',network_id] + command.split(' '), stderr=STDOUT)
 
