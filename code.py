import board
import pwmio
import time
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import displayio
import adafruit_requests as requests
import supervisor
#import traceback

from adafruit_display_text import label
import adafruit_displayio_sh1107

def setdisplay():

    displayio.release_displays()

    # Use for I2C
    i2c = board.I2C()
    display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)

    # SH1107 is vertically oriented 64x128
    WIDTH = 128
    HEIGHT = 64
    BORDER = 2

    display = adafruit_displayio_sh1107.SH1107(
        display_bus, width=WIDTH, height=HEIGHT, rotation=0
    )


### Code ###

def publishstate():
    mqtt_client.publish(bright_status, bright)
    mqtt_client.publish(rgb_status, f'{red},{green},{blue}')
    mqtt_client.publish(onoff_status, 'ON' if state else 'OFF')
    mqtt_client.publish(bright_status, bright)
    mqtt_client.publish(rgb_status, f'{red},{green},{blue}')
    # with open("/state.txt", "w") as fp:
    #     fp.write('ON\n' if state else 'OFF\n')
    #     fp.write('{0:n}\n'.format(bright))
    #     rgb = f'{red},{green},{blue}'
    #     print(rgb)
    #     fp.write(rgb)
    #     fp.flush()   

def updatedot():
    #print(f"Setting dot {red} {green} {blue} {bright}")
    #dotstar[0] = ( red, green, blue, bright/512)
    r = int(red * bright) if state else 0
    g = int(green * bright) if state else 0
    b = int(blue * bright) if state else 0
    print(f"Setting strip {r} {g} {b}")
    led_red.duty_cycle = r
    led_green.duty_cycle = g
    led_blue.duty_cycle = b



# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    global isconnected
    isconnected = True
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to Adafruit IO! Listening for topic changes on %s" % onoff_feed)
    # Subscribe to all changes on the onoff_feed.
    client.subscribe(onoff_feed)
    client.subscribe(bright_feed)
    client.subscribe(rgb_feed) 
    client.subscribe(update_status) 
    client.subscribe(username + update_status) 

    loadstate()
    updatedot()
    publishstate()
    mqtt_client.publish(update_status + '/response', f'{username} is connected')


def disconnected(client, userdata, rc):
    global isconnected
    # This method is called when the client is disconnected 
    print("Disconnected from Adafruit IO!")
    isconnected = False

def onoff(message):
    global red
    global green
    global blue
    global bright
    global state
    red = 255 if bright == 0 else red
    green = 255 if bright == 0 else green
    blue = 255 if bright == 0 else blue
    bright = 255 if bright == 0 else bright
    if(message == 'ON'):
        state = True
    if(message == 'OFF'):
        state = False

def brightmsg(message):
    global bright
    bright = int(message)

def rgbmsg(message):
    global red
    global green
    global blue
    vals = message.split(",")
    red = int(vals[0])
    green = int(vals[1])
    blue = int(vals[2])

def loadstate(): 
    print("")
    # with open("/state.txt", "r") as fp:
    #     lines = fp.read().splitlines() 
    #     try:
    #         print(lines[0])
    #         print(lines[1])
    #         print(lines[2])
    #         onoff(lines[0])
    #         brightmsg(lines[1])
    #         rgbmsg(lines[2])
    #     except:
    #         pass

def message(client, topic, message):
    # This method is called when a topic the client is subscribed to
    # has a new message.
    print("New message on topic {0}: {1}".format(topic, message))

    if(topic == onoff_feed):
        onoff(message)
        updatedot()
        publishstate()
    if(topic == bright_feed):
        brightmsg(message)
        updatedot()
        publishstate()
    if(topic == rgb_feed):
        rgbmsg(message)
        updatedot()
        publishstate()
    if(topic == update_status or topic == username + update_status):
        runupdate(message)


def runupdate(message):
    print(f"Got message: {message}")
    http_get(message)


def http_get(url):
    session = requests.Session(pool)
    idx = url.rfind("/") + 1
    file = url[idx:]
    url = url[:idx]
    if(len(file) == 0):
        file = "light_update.txt"
    print(f"Index is: {idx} path {url} file {file}")
    datafile = session.get(url + file)
    files = datafile.text.splitlines()
    for file in files:
        data = session.get(url + file)
        fileindex = file.find('/')
        local = file[fileindex:]
        print(f"Updating file {file} to {local}")
        try:
            if(len(local) > 1):
                with open(file[fileindex:], "w") as fp:
                    for chunk in data.iter_content(1000):
                        fp.write(chunk)
                    fp.flush()
        except:
            print(f"Failed updating {file}")
        try:
            mqtt_client.publish(update_status + '/response', f'Successfully updated {username} file {file}')
        except:
            print("Failed to publish update state")
    supervisor.reload()

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

try:
    #setdisplay()
    #dotstar = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.5, auto_write=True)

    # Set your Adafruit IO Username and Key in secrets.py
    # (visit io.adafruit.com if you need to create an account,
    # or if you need your Adafruit IO key.)
    aio_username = secrets["aio_username"]
    aio_key = secrets["aio_key"]

    print("Connecting to %s" % secrets["ssid"])
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("Connected to %s!" % secrets["ssid"])
    ### Feeds ###
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

    # Setup a feed named 'onoff' for subscribing to changes
    onoff_feed = secrets["aio_username"] + "/feeds/onoff"
    bright_feed = secrets["aio_username"] + "/feeds/bright"
    rgb_feed = secrets["aio_username"] + "/feeds/rgb"
    username = secrets["aio_username"] 

    onoff_status = secrets["aio_username"] + "/feeds/onoff/state"
    bright_status = secrets["aio_username"] + "/feeds/bright/state"
    rgb_status = secrets["aio_username"] + "/feeds/rgb/state"

    update_status = "/feeds/updates"

    led_green = pwmio.PWMOut(board.D9, frequency=5000, duty_cycle=0)
    led_blue = pwmio.PWMOut(board.D6, frequency=5000, duty_cycle=0)
    led_red = pwmio.PWMOut(board.D5, frequency=5000, duty_cycle=0) 

    red = 255
    green = 255
    blue = 255
    bright = 255
    state = False
    isconnected = False

    # Setup the callback methods above
    mqtt_client.on_connect = connected
    mqtt_client.on_disconnect = disconnected
    mqtt_client.on_message = message

    # Connect the client to the MQTT broker.

    while True:
        if(not isconnected) :
            try :
                print("Connecting to MQTT.")
                mqtt_client.connect()
                isconnected = True
            except MQTT.MMQTTException as msg:
                isconnected = False
                print(msg)

        # Poll the message queue
        try:
            mqtt_client.loop(timeout= 5)
        except MQTT.MMQTTException as msg:
            isconnected = False
            print(msg)

        time.sleep(0.1)
except Exception as err:
    try:
        exception_type = type(err).__name__
        print(exception_type)
        #traceback.print_tb(err.__traceback__)
        runupdate("http://hass.lan/")
    except Exception as err:
        time.sleep(30)
        supervisor.reload()
