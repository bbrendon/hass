"""
Support for UPB lights.

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
from subprocess import check_output, CalledProcessError, STDOUT

import voluptuous as vol


from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, SUPPORT_BRIGHTNESS, Light,
    PLATFORM_SCHEMA)

from homeassistant.const import (CONF_NAME, CONF_ID, CONF_DEVICES)

import homeassistant.helpers.config_validation as cv

# Home Assistant depends on 3rd party packages for API specific code.
#REQUIREMENTS = ['awesome_lights==1.2.3']

serial_port = '/dev/ttyS1'
upb_net = '999'

_LOGGER = logging.getLogger(__name__)

#DOMAIN = 'UPB'

#CONF_SERIAL_PORT = 'serial_port'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        {
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
        }
    ]),
    #vol.Required(CONF_SERIAL_PORT): cv.string,

})


# CONFIG_SCHEMA = vol.Schema({
#     DOMAIN: vol.Schema({
#         vol.Optional(CONF_SERIAL_PORT, default=''): cv.string,
#     }),
# }, extra=vol.ALLOW_EXTRA)


def dump(obj):
    for attr in dir(obj):
        if hasattr( obj, attr ):
            print( "obj.%s = %s" % (attr, getattr(obj, attr)))






# def get_unit_status(code):
#     """Get on/off status for given unit"""
#     output = check_output('heyu onstate ' + code, shell=True)
#     return int(output.decode('utf-8')[0])
    

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the UPB Light platform"""
    try:
        #upb_command('info')
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
        self._name = light['name']
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
        return SUPPORT_BRIGHTNESS

    @property
    def brightness(self):
        """Return the brightness of the light"""
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on"""
        return self._state


    def turn_on(self, **kwargs):
        """Instruct the light to turn on"""

        #int(255 * brightness_pct/100)
        #self._brightness = kwargs.get(ATTR_BRIGHTNESS)
        
        
        bright_pct = int((kwargs.get(ATTR_BRIGHTNESS,255)/255)*100)

        #upb_command('on ' + self._id)
        print(str(self._id)) ## This is the id value from the configutaion.yaml
        #upb_command('-n 99 -i 83 -t device -c goto -l 100 --send -p /dev/ttyS1' )
        upb_command(' -i ' + self._id + ' -t device -c goto -l ' + str(bright_pct) + ' --send' )
        
        print("ddfk3k: " + str(bright_pct))
        #print("asdf: " + str(self._brightness_pct))
        print(kwargs)
        self._state = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off"""
        print('off ' + self._id)
        #upb_command('off ' + self._id)
        upb_command(' -i ' + self._id + ' -t device -c goto -l 0 --send' )
        time.sleep(1)
        upb_command(' -i ' + self._id + ' -t device -c goto -l 0 --send' )
        self._state = False

    # def update(self):
    #     """Fetch new state data for this light.
    #     This is the only method that should fetch new data for Home Assistant.
    #     """
    #     #self._state = bool(get_unit_status(self._id))
    #     self._light.update()
    #     #self._state = self._light.is_on()
    #     #self._brightness = self._light.brightness
    #     print("asdfupdate: " )        

def upb_command(command):
    """Execute UPB command and check output"""
    #return check_output(['heyu'] + command.split(' '), stderr=STDOUT)
    #global config
    #print("config: " + config[CONF_SERIAL_PORT])
    print("serial: "+ serial_port)
    return check_output(['upb-cli','-p',serial_port,'-n',upb_net] + command.split(' '), stderr=STDOUT)
    
