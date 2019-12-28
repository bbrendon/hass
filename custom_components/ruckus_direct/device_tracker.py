"""

Issues:
- if the WAP isn't accessible (aka reboot), the component stops working and HASS must be restarted.
  Things do not fail cleanly.

Improvements.
- use pxssh library like unifi_direct.

Configuration Notes:
- the master WAP has to be contacted for the wireless client information.

"""


"""Support for Ruckus Access Points."""
import logging
import re

import pexpect
import voluptuous as vol

from homeassistant.components.device_tracker import (
    DOMAIN,
    PLATFORM_SCHEMA,
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)


_DEVICE_REGEX = re.compile(
    r"Mac Address= (?P<mac>([0-9a-f]{2}[:-]){5}([0-9a-f]{2})).+"
    r"Host Name= (?P<name>([^\s]+)?).+"
    r"IP= (?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})",
    re.DOTALL,
)


# _DEVICES_REGEX = re.compile(
#     r"(?P<name>([^\s]+)?)\s+"
#     + r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s+"
#     + r"(?P<mac>([0-9a-f]{2}[:-]){5}([0-9a-f]{2}))\s+"
# )

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
    }
)


def get_scanner(hass, config):
    """Validate the configuration and return a Ruckus scanner."""
    scanner = RuckusDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class RuckusDeviceScanner(DeviceScanner):
    """This class queries a Ruckus Access Point for connected devices."""

    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]

        self.last_results = {}

        # Test the router is accessible.
        data = self.get_ruckus_data()
        self.success_init = data is not None

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        _LOGGER.debug("scan_devices")

        self._update_info()
        return [client["mac"] for client in self.last_results]

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        if not self.last_results:
            return None
        for client in self.last_results:
            if client["mac"] == device:
                return client["name"]
        return None

    def _update_info(self):
        """Ensure the information from the Ruckus Access Point is up to date.

        Return boolean if scanning successful.
        """
        _LOGGER.debug("_update_info")

        if not self.success_init:
            return False

        data = self.get_ruckus_data()
        if not data:
            return False

        self.last_results = data.values()
        return True

    def get_ruckus_data(self):
        """Retrieve data from Ruckus Access Point and return parsed result."""

        _LOGGER.debug("get_ruckus_data : Connecting to WAP to fetch data")

        connect = "ssh -o 'StrictHostKeyChecking no' -o 'ConnectTimeout 2' {}@{}"
        ssh = pexpect.spawn(connect.format(self.username, self.host))

        ssh.expect("Please login")
        ssh.sendline(self.username)
        ssh.expect("Password")
        ssh.sendline(self.password)
        ssh.expect("> ")
        ssh.sendline("enable")
        ssh.expect("# ")
        ssh.sendline("show current-active-clients all")
        ssh.expect("# ")
        # devices_result = ssh.before.split(b"\r\n")
        devices_result = ssh.before
        ssh.sendline("exit")

        devices = {}

        for client in re.split("Clients:", devices_result.decode("utf-8")):
            match = _DEVICE_REGEX.search(client)
            if match:
                devices[match.group("ip")] = {
                    "ip": match.group("ip"),
                    "mac": match.group("mac"),
                    "name": match.group("name"),
                }

        _LOGGER.debug("get_ruckus_data : Done fetching. Returning data")

        return devices

