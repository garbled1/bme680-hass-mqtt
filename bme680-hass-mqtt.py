#!/usr/bin/env python3

import bme680
import time
import argparse
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

debug_mode = False

def parse_cmdline():
    parser = argparse.ArgumentParser(description='Collect data from a BME680 i2c Sensor and publish to MQTT')

    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='Debug mode')
    parser.add_argument('-a', '--address', type=str, action='store',
                        default='0x76', help='i2c address of BME680')
    parser.add_argument('-b', '--burn_in', type=int, action='store',
                        default=300, help='Seconds to warm up gas sensor')
    parser.add_argument('-p', '--poll_time', type=int, action='store',
                        default=5, help='How often in seconds to poll sensor')
    parser.add_argument('-t', '--topic', type=str, action='store',
                        default='hass_bme680/', help='MQTT Topic')
    parser.add_argument('--broker', type=str, action='store',
                        default='127.0.0.1', help='MQTT Broker')
    parser.add_argument('--humid_baseline', type=int, action='store',
                        default=40, help='Humidity baseline')
    parser.add_argument('--humid_weight', type=float, action='store',
                        default=0.25, help='Humitidy weight for air quality calc')
    args = parser.parse_args()
    return args


def init_bme680(bme_addr):
    try:
        sensor = bme680.BME680(i2c_addr=bme_addr)
        sensor.set_humidity_oversample(bme680.OS_2X)
        sensor.set_pressure_oversample(bme680.OS_4X)
        sensor.set_temperature_oversample(bme680.OS_8X)
        sensor.set_filter(bme680.FILTER_SIZE_0)
        sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
        sensor.set_gas_heater_temperature(320)
        sensor.set_gas_heater_duration(150)
        sensor.select_gas_heater_profile(0)
        return sensor
    except Exception:
        print("Cannot initialize BME680 at addr {0}".format(str(bme_addr)))


def burn_in_sensor(sensor, burn_in_time):
    global debug_mode
    start_time = time.time()
    curr_time = time.time()
    burn_in_data = []
    gas_baseline = 0

    while curr_time - start_time < burn_in_time:
        curr_time = time.time()
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            gas = sensor.data.gas_resistance
            burn_in_data.append(gas)
            if debug_mode:
                print("Gas: {0:.2f} Ohms  Time:{1:.2f}".format(gas, curr_time - start_time))
        time.sleep(1)

    gas_baseline = sum(burn_in_data[-50:]) / 50.0
    if debug_mode:
        print("Computed gas baseline: {0} Ohms".format(gas_baseline))

    return gas_baseline


def init_mqtt(broker):
    global debug_mode
    try:
        mq_client = mqtt.Client()
        mq_client.connect(broker)
        mq_client.loop_start()
    except Exception:
        print("Unable to connect to MQTT broker at {0}".format(str(broker)))
        exit(1)
    return mq_client


def poll_sensor(sensor, mq_client, poll_time, topic, hum_baseline, gas_baseline, hum_weighting, bme_addr):
    while True:
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            gas = sensor.data.gas_resistance
            gas_offset = gas_baseline - gas
            hum = sensor.data.humidity
            hum_offset = hum - hum_baseline
            # When the gas sensor is running, the temp is high by 2 deg C
            temp = sensor.data.temperature - 2.0
            send_temp = temp

            # Calculate hum_score as the distance from the hum_baseline.
            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * (hum_weighting * 100)

            else:
                hum_score = (hum_baseline + hum_offset) / hum_baseline * (hum_weighting * 100)

            # Calculate gas_score as the distance from the gas_baseline.
            if gas_offset > 0:
                gas_score = (gas / gas_baseline) * (100 - (hum_weighting * 100))

            else:
                gas_score = 100 - (hum_weighting * 100)

            # Calculate air_quality_score. 
            air_quality_score = hum_score + gas_score
            
            humidity = str(round(hum, 2))
            temperature = str(round(sensor.data.temperature, 2))
            pressure = str(round(sensor.data.pressure, 2))
            air_qual = str(round(air_quality_score, 2))
            raw_gas = str(round(gas, 2))

            if debug_mode:
                print("Gas: {0:.2f} Ohms,humidity: {1:.2f} %RH,air quality: {2:.2f}".format(gas, hum, air_quality_score))
            
            mq_client.publish(topic + 'bme680-' + bme_addr + '-humidity', humidity)
            mq_client.publish(topic + 'bme680-' + bme_addr + '-temperature', temperature)
            mq_client.publish(topic + 'bme680-' + bme_addr + '-pressure', pressure)
            mq_client.publish(topic + 'bme680-' + bme_addr + '-air_qual', air_qual)
            mq_client.publish(topic + 'bme680-' + bme_addr + '-gas_ohms', raw_gas)
            time.sleep(poll_time)


def main():
    global debug_mode

    args = parse_cmdline()
    if args.debug:
        debug_mode = args.debug

    i2c_addr_int = int(args.address, 16)

    sensor = init_bme680(i2c_addr_int)
    if sensor is None:
        print("Could not initialize BME680 at {0}".format(args.address))
        exit(1)

    mq_client = init_mqtt(args.broker)

    gas_baseline = burn_in_sensor(sensor, args.burn_in)

    poll_sensor(sensor, mq_client, args.poll_time, args.topic,
                args.humid_baseline, gas_baseline, args.humid_weight,
                args.address)
    return


if __name__ == "__main__":
    main()

