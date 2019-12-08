# bme680-hass-mqtt
BME680 MQTT Sender for home assistant

Based on code from: https://github.com/tdamdouni/Raspberry-Pi-DIY-Projects/tree/master/bme680/bme680-mqtt

# How to run
```
pip3 install -r requirements.txt
./bme680-hass-mqtt.py --broker 192.168.x.x -d
```

# How to install
```
cp bme680-hass-mqtt.py /usr/local/bin
chmod 755 /usr/local/bin/bme680-hass-mqtt.py
# edit the service file to add your broker or options as needed
cp bme680-hass-mqtt.service /etc/systemd/system/bme680-hass-mqtt@0x76.service
systemctl daemon-reload
systemctl enable bme680-hass-mqtt@0x76
systemctl start bme680-hass-mqtt@0x76
```

To add the MQTT output to [Home-assistant](https://home-assistant.io/), we use an [MQTT-switch](https://home-assistant.io/components/switch.mqtt/). Assuming you have your Home-assistant [config split](https://home-assistant.io/docs/configuration/splitting_configuration/) into seperate files, in your sensors.yaml file, add the following:

```yaml
- platform: mqtt
  name: 'bme680-temperature'
  state_topic: 'hass_bme680/bme680-0x76-temperature'
  unit_of_measurement: '°C'
- platform: mqtt
  name: 'bme680-humidity'
  state_topic: 'hass_bme680/bme680-0x76-humidity'
  unit_of_measurement: '%'
- platform: mqtt
  name: 'bme680-pressure'
  state_topic: 'hass_bme680/bme680-0x76-pressure'
  unit_of_measurement: 'hPa'
- platform: mqtt
  name: 'bme680-air_qual'
  state_topic: 'hass_bme680/bme680-0x76-air_qual'
  unit_of_measurement: '%'
- platform: mqtt
  name: 'bme680-gas_ohms'
  state_topic: 'hass_bme680/bme680-0x76-gas_ohms'
  unit_of_measurement: 'Ω'
```

I then created a group, in groups.yaml:

```yaml
BME680:
  entities:
    - sensor.bme680temperature
    - sensor.bme680pressure
    - sensor.bme680humidity
    - sensor.bme680air_qual
```
