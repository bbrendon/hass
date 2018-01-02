# UPB component for Home Assistant

Custom component https://home-assistant.io


## Getting Started

1. Install upb-cli -- https://github.com/DaAwesomeP/upb-cli
1. Make sure upb-cli is in the system path
1. Edit upb.py and set your network number and serial port
1. Update your configuration.yaml with the platform setting such as the example below.
1. Make sure the user running HASS has access to the serial port.

```
light:
  - platform: upb
    devices:
      - id: 13
        name: Bathroom Fan
      - id: 12
        name: Bathroom Vanity
```        
