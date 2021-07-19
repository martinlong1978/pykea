# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import board
import pwmio
import time
import ssl
import socketpool
import wifi
import adafruit_dotstar
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

dotstar = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.5, auto_write=True)

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])
### Feeds ###

# Setup a feed named 'photocell' for publishing to a feed
photocell_feed = secrets["aio_username"] + "/feeds/photocell"

# Setup a feed named 'onoff' for subscribing to changes
onoff_feed = secrets["aio_username"] + "/feeds/onoff"
bright_feed = secrets["aio_username"] + "/feeds/bright"
rgb_feed = secrets["aio_username"] + "/feeds/rgb"

onoff_status = secrets["aio_username"] + "/feeds/onoff/state"
bright_status = secrets["aio_username"] + "/feeds/bright/state"
rgb_status = secrets["aio_username"] + "/feeds/rgb/state"

led_red = pwmio.PWMOut(board.D9, frequency=5000, duty_cycle=0)
led_green = pwmio.PWMOut(board.D6, frequency=5000, duty_cycle=0)
led_blue = pwmio.PWMOut(board.D5, frequency=5000, duty_cycle=0)

red = 0
green = 0
blue = 0
bright = 0

### Code ###

def publishstate():
    #mqtt_client.publish(onoff_status, '{"state": "ON"}')
    #mqtt_client.publish(bright_status, '{"brightness": "100"}')
    #mqtt_client.publish(rgb_status, '{"rgb": [10,10,10]}')
    mqtt_client.publish(onoff_status, 'OFF' if bright == 0 else 'ON')
    mqtt_client.publish(bright_status, bright * 512)
    mqtt_client.publish(rgb_status, f'{red},{green},{blue}')

def updatedot():
    print(f"Setting dot {red} {green} {blue} {bright}")
    dotstar[0] = ( red, green, blue, bright)
    r = int(512 * red * bright)
    led_red.duty_cycle = r
    g = int(512 * green * bright)
    led_green.duty_cycle = g
    b = int(512 * blue * bright)
    led_blue.duty_cycle = b
    print(f"Setting strip {r} {g} {b}")



# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to Adafruit IO! Listening for topic changes on %s" % onoff_feed)
    # Subscribe to all changes on the onoff_feed.
    client.subscribe(onoff_feed)
    client.subscribe(bright_feed)
    client.subscribe(rgb_feed) 

    publishstate()
    updatedot()


def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected 
    print("Disconnected from Adafruit IO!")


def message(client, topic, message):
    global red
    global green
    global blue
    global bright
    # This method is called when a topic the client is subscribed to
    # has a new message.
    print("New message on topic {0}: {1}".format(topic, message))

    if(topic == onoff_feed):
        if(message == 'ON'):
            red = 255 if bright == 0 else red
            green = 255 if bright == 0 else green
            blue = 255 if bright == 0 else blue
            bright = 255/512 if bright == 0 else bright
            updatedot()
            publishstate()
        if(message == 'OFF'):
            red = 0
            green = 0
            blue = 0
            bright = 0
            updatedot()
            publishstate()
    if(topic == bright_feed):
        bright = int(message) / 512
        updatedot()
        publishstate()
    if(topic == rgb_feed):
        vals = message.split(",")
        red = int(vals[0])
        green = int(vals[1])
        blue = int(vals[2])
        updatedot()
        publishstate()


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

# Connect the client to the MQTT broker.
print("Connecting to Adafruit IO...")
mqtt_client.connect()

while True:
    # Poll the message queue
    mqtt_client.loop()

    # Send a new message
    #print("Sending photocell value: %d..." % photocell_val)
    #mqtt_client.publish(photocell_feed, photocell_val)
    #print("Sent!")
    #photocell_val += 1
    time.sleep(0.1)
