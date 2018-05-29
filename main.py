import time

import dht
import machine
import network
from umqtt.simple import MQTTClient

from config import CONFIG
from esp8266_i2c_lcd import I2cLcd

client = None
sensor_pin = None
temperature = None
humidity = None


def topic_name(topic):
    return b"/".join([b"sensors", CONFIG['client_id'], topic])


def setup_pins():
    global sensor_pin
    sensor_pin = machine.Pin(CONFIG['sensor_pin'])


def callback(topic, msg):
    pass


def connect_and_subscribe():
    global client
    client = MQTTClient(CONFIG['client_id'], CONFIG['broker'],
                        user=CONFIG['mqtt_user'],
                        password=CONFIG['mqtt_password'])
    client.set_last_will(topic_name(b'lwt'), 'our lwt')
    client.set_callback(callback)
    client.connect()
    print("Connected to {}".format(CONFIG['broker']))
    for topic in (b'config', b'control'):
        t = topic_name(topic)
        client.subscribe(t)
        print("Subscribed to {}".format(t))


def write_to_lcd(msg=["Hello LCD"]):
    from machine import I2C
    scl = machine.Pin(2)
    sda = machine.Pin(5)
    i2c = I2C(scl=scl, sda=sda, freq=400000)
    # find out the address of the device
    devices = i2c.scan()
    if len(devices) == 0:
        print("no i2c device")
    else:
        print("i2c devices found: ", len(devices))
        for device in devices:
            print("Decimal address: ", device, " | Hexa address: ", hex(device))

    lcd = I2cLcd(i2c, 0x3f, 4, 20)

    lcd.putstr("\n".join(msg))


def check_and_report_temp():
    import ujson as json
    global temperature, humidity
    d = dht.DHT22(sensor_pin)
    try:
        d.measure()
        temperature = (d.temperature() * 9 / 5) + 32
        humidity = d.humidity()
        th = {'temperature': str(temperature), 'humidity': str(humidity)}
        print(th)
        client.publish(topic_name(b'DHT'), bytes(json.dumps(th), 'utf-8'))
    except OSError as e:
        print(e)


def setup():
    connect_and_subscribe()
    setup_pins()


def main_loop():
    i = 0
    current_screen = ''
    while 1:
        client.check_msg()
        if i % 60 == 0:
            check_and_report_temp()
            sta_if = network.WLAN(network.STA_IF)
            next_screen = [str(sta_if.ifconfig()[0]),
                           '{}\u00b0 F'.format(temperature),
                           '{} % humidity'.format(humidity),
                           str(CONFIG['client_id'])]
            if current_screen != next_screen:
                write_to_lcd(msg=next_screen)
                current_screen = next_screen
        i += 1
        time.sleep(1)


def teardown():
    try:
        client.disconnect()
        print("Disconnected.")
    except Exception:
        print("Couldn't disconnect cleanly.")


if __name__ == '__main__':
    # load_config()
    setup()
    main_loop()
