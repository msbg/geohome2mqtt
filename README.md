# geohome2mqtt: Send GeoHome smart meter data to MQTT


[![Docker Hub](https://img.shields.io/docker/pulls/msbg/geohome2mqtt)](https://hub.docker.com/r/msbg/geohome2mqtt)

## Background
I live in the UK and have a ['Geo Trio II'](https://assets.geotogether.com/sites/4/20170719152415/SM2D-A-USG-001_1.pdf) Smart Energy monitor, originally supplied by Pure Planet, but now transferred to Shell Energy. I wanted to see my usage in HomeAssistant, and thanks to the example openHAB script [here](https://github.com/owainlloyd/Geohome_Integration), it was possible.

## Running
Available as a docker image ([`msbg/geohome2mqtt`](https://hub.docker.com/r/msbg/geohome2mqtt))

You'll need to have installed and logged in to the [geoHome app](https://support.geotogether.com/en/support/solutions/articles/7000061429-5-setting-up-the-geo-home-app) to register and get the username/password needed.

All environment variables are defined in the example [`docker-compose.yml`](https://github.com/msbg/geohome2mqtt/blob/main/docker-compose.yml).   Please refer to the published image if not developing.

## Home Assistant MQTT Discovery

[Home Assistant](https://home-assistant.io) users can quickly add entities using MQTT discovery ( 'HASS_DISCOVERY = "true"' in the config)


## Status
Support confirmed:
  live Gas power data (Watts) 
  total consumption data (kWh) - gas is converted from m3 
  
Testing undergoing for:
  live Electricity power data (Watts) - my supplier hasn't turned this on yet, so I can't test
  total consumption data (kWh) - as above.
  live tariff data gas - confirming once more data gathered
  live tariff data electricity - as above.


## Tested countries/devices:
UK - TRIO_II_TB_GEO - Gas
