#!/usr/bin/python3
# -*- coding: utf-8 -*-

# import the module
import python_weather
import asyncio

import json
import random
import time
import smtplib
import ssl
from typing import TextIO
from paho.mqtt import client as mqtt_client

# config.json data file
data_file: TextIO
with open('config.json', "r") as data_file:
    DataJson = json.load(data_file)
data_file.close()

broker = DataJson["mqtt"]["broker"]
port = DataJson["mqtt"]["port"]
username = DataJson["mqtt"]["mqtt_user"]
password = DataJson["mqtt"]["mqtt_password"]
client_id = f'mqtt-{random.randint(0, 1000)}'
mqttJson = {
    "TH16": {
        "TemperatureC": 0.0,
        "UnitC": "C",
        "TemperatureF": 0.0,
        "UnitF": "F",
        "Device Date": "devdate",
        "Device Time": "devtime",
        "Date": "thedate",
        "Time": "thetime"
        },
    "PowR2": {
        "Device Date": "devdate",
        "Device Time": "devtime",
        "Date": "thedate",
        "Time": "thetime",
        "ENERGY": {
            "TotalStartTime": "16:12:22",
            "TotalStartDate": "2021-11-17",
            "Total": 0.0,
            "Yesterday": 0.0,
            "Today": 0.0,
            "Period": 0,
            "Power": 0,
            "ApparentPower": 0,
            "ReactivePower": 0,
            "Factor": 0.0,
            "Voltage": 0,
            "Current": 0.0
            },
        "PowR2 State": "OFF"
        },
    "weather": {
            "timezone_offset": "-5",
            "Temperature": 0.0,
            "degree_type": "C",
            "TemperatureF": 0.0,
            "UnitF": "F",
            "feels_like": 0.0,
            "feels_like_conv": 0.0,
            "humidity": 0,
            "wind_display": "",
            "sky_text": "",
            "date": {               # datetime.datetime(2021, 11, 17, 19, 15)
                "year": 0000,
                "month": 00,
                "day": 00,
                "hour": 00,
                "minutes": 00
            },
            "day": " ",
            "observation_point": ""
        }
}

# mosquitto_sub -v  -h mqtt.lan -u mqttUser -P MqttPass  -t HotTubTemp/tele/SENSOR
# PowR2/tele/SENSOR = {"Time":"2021-11-17T18:08:34","ENERGY":{"TotalStartTime":"2021-11-17T16:12:22","Total":0.734,
# "Yesterday":0.000,"Today":0.734,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,
# "Voltage":119,"Current":0.000}}

# HotTubTemp/tele/SENSOR =
# {"Time":"2021-11-17T17:13:36","DS18B20":{"Id":"05167219F3FF","Temperature":32.3},"TempUnit":"C"}

topic_fp_SENSOR = "HotTubTemp/tele/SENSOR"
topic_pow_SENSOR = "PowR2/tele/SENSOR"
topic_sub = [(topic_fp_SENSOR, 0), (topic_pow_SENSOR, 0)]
pow_conntected = False

topic_pub_POWER = b'HotTubTemp/cmnd/POWER'
topic_pub_STATUS = "HotTubTemp/cmnd/STATUS"
topic_pub = "HotTubTemp/stat/python"
last_temp_left = 0
last_temp_right = 0
PowR2EmailOnce = 0
last_time_check = 0
last_email_check = int(time.time())
NumSecBetweenEmails = 900
email_control = True


async def getweather():
    # declare the client. format defaults to the metric system (celcius, km/h, etc.)
    weatherclient = python_weather.Client(format=python_weather.METRIC)

    # fetch a weather forecast from a city
    weather = await weatherclient.find("Winchester Ontario")

    mqttJson["weather"]["timezone_offset"] = weather.timezone_offset

    if weather.degree_type == "C":
        mqttJson["weather"]["Temperature"] = weather.current.temperature
        mqttJson["weather"]["degree_type"] = weather.degree_type
        # convert to fahrenheit
        mqttJson["weather"]["TemperatureF"] = round(((mqttJson["weather"]["Temperature"] * 1.8) + 32), 2)
        mqttJson["weather"]["UnitF"] = "F"
        mqttJson["weather"]["feels_like"] = (str(weather.current.feels_like) + " " + weather.degree_type
                                             + " / " + str(round(((weather.current.feels_like * 1.8) + 32), 2)) + " F")
    else:
        mqttJson["weather"]["TemperatureF"] = weather.current.temperature
        mqttJson["weather"]["UnitF"] = weather.degree_type
        # covert to celsius
        mqttJson["weather"]["Temperature"] = round(((mqttJson["weather"]["Temperature"] - 32) / 1.8), 2)
        mqttJson["weather"]["degree_type"] = "C"
        mqttJson["weather"]["feels_like"] = (str(round(((weather.current.feels_like - 32) / 1.8), 2)) + " F / "
                                             + str(weather.current.feels_like) + " " + weather.degree_type)

    mqttJson["weather"]["humidity"] = weather.current.humidity
    mqttJson["weather"]["wind_display"] = weather.current.wind_display
    mqttJson["weather"]["sky_text"] = weather.current.sky_text
    mqttJson["weather"]["date"]["year"] = weather.forecasts[0].date.year
    mqttJson["weather"]["date"]["month"] = weather.forecasts[0].date.month
    mqttJson["weather"]["date"]["day"] = weather.forecasts[0].date.day
    mqttJson["weather"]["date"]["hour"] = weather.forecasts[0].date.hour
    mqttJson["weather"]["date"]["minutes"] = weather.forecasts[0].date.minute
    mqttJson["weather"]["day"] = weather.current.day
    mqttJson["weather"]["observation_point"] = weather.current.observation_point

    # close the wrapper once done
    await weatherclient.close()


def sendemail(subject, text):
    to = DataJson["email"]["To"]
    # Gmail Sign In
    smtp_sender = DataJson["email"]["From"]
    smtp_passwd = DataJson["email"]["Password"]
    smtp_server = DataJson["email"]["SMTPServer"]
    smtp_port = DataJson["email"]["SMTPPort"]
    body = '\r\n'.join(['To: %s' % to,
                        'From: %s' % smtp_sender,
                        'Subject: %s' % subject,
                        '', text])

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        # server.set_debuglevel(1)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(smtp_sender, smtp_passwd)
        try:
            server.sendmail(smtp_sender, [to], body)
            print('email sent')
        except:
            print('error sending mail')
        server.quit()

# Connection Return Codes

#    0: Connection successful
#    1: Connection refused – incorrect protocol version
#    2: Connection refused – invalid client identifier
#    3: Connection refused – server unavailable
#    4: Connection refused – bad username or password
#    5: Connection refused – not authorised
#    6-255: Currently unused.

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)


def connect_mqtt():
    # Set Connecting Client ID
    mqttclient = mqtt_client.Client(client_id)
    mqttclient.username_pw_set(username, password)
    mqttclient.on_connect = on_connect
    mqttclient.connect(broker, port)
    return mqttclient

# {"StatusSNS": {"Time": "2021-11-14T19:39:49", "DS18B20": {"Id": "05167219F3FF",
# "Temperature": 32.9}, "TempUnit": "C"}}

# PowR2/tele/SENSOR = {"Time":"2021-11-17T18:08:34","ENERGY":{"TotalStartTime":"2021-11-17T16:12:22","Total":0.734,
# "Yesterday":0.000,"Today":0.734,"Period": 0,"Power": 0,"ApparentPower": 0,"ReactivePower": 0,"Factor":0.00,
# "Voltage":119,"Current":0.000}}

def on_message(client, userdata, msg):
    global last_temp_left
    global last_temp_right
    global PowR2EmailOnce
    global last_time_check
    global last_email_check
    global email_control
    tempmqttdata = json.loads(msg.payload.decode())
    print(f"Received `{tempmqttdata}` from `{msg.topic}` topic")

    if time.localtime().tm_hour != last_time_check:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(getweather())
            last_time_check = time.localtime().tm_hour
        except:
            print("Get Weather failed!")
            last_time_check = time.localtime().tm_hour

    if msg.topic == topic_fp_SENSOR:
        mytime = time.localtime()
        mqttJson["TH16"]["Date"] = str(mytime[0]) + '/' + str(mytime[1]) + '/' + str(mytime[2])
        mqttJson["TH16"]["Time"] = str(mytime[3]) + ':' + str(mytime[4]) + ':' + str(mytime[5])
        tempdate = tempmqttdata['Time']
        tempSdate = tempdate.split("T")
        mqttJson["TH16"]["Device Date"] = tempSdate[0]
        mqttJson["TH16"]["Device Time"] = tempSdate[1]
        if tempmqttdata['TempUnit'] == "C":
            mqttJson["TH16"]["TemperatureC"] = tempmqttdata['DS18B20']['Temperature']
            mqttJson["TH16"]["Unit"] = tempmqttdata['TempUnit']
            # convert to fahrenheit
            mqttJson["TH16"]["TemperatureF"] = round(((tempmqttdata['DS18B20']['Temperature'] * 1.8) + 32), 2)
            mqttJson["TH16"]["UnitF"] = "F"
        else:
            mqttJson["TH16"]["TemperatureF"] = tempmqttdata['DS18B20']['Temperature']
            mqttJson["TH16"]["UnitF"] = tempmqttdata['TempUnit']
            # covert to celsius
            mqttJson["TH16"]["TemperatureC"] = round(((tempmqttdata['DS18B20']['Temperature'] - 32) / 1.8), 2)
            mqttJson["TH16"]["Unit"] = "C"
    elif msg.topic == topic_pow_SENSOR and pow_conntected:
        mytime = time.localtime()
        mqttJson["PowR2"]["Date"] = str(mytime[0]) + '/' + str(mytime[1]) + '/' + str(mytime[2])
        mqttJson["PowR2"]["Time"] = str(mytime[3]) + ':' + str(mytime[4]) + ':' + str(mytime[5])
        tempdate = tempmqttdata["ENERGY"]["TotalStartTime"]
        tempSdate = tempdate.split("T")
        mqttJson["PowR2"]["ENERGY"]["TotalStartDate"] = tempSdate[0]
        mqttJson["PowR2"]["ENERGY"]["TotalStartTime"] = tempSdate[1]
        mqttJson["PowR2"]["ENERGY"]["Total"] = tempmqttdata["ENERGY"]["Total"]
        mqttJson["PowR2"]["ENERGY"]["Yesterday"] = tempmqttdata["ENERGY"]["Yesterday"]
        mqttJson["PowR2"]["ENERGY"]["Today"] = tempmqttdata["ENERGY"]["Today"]
        mqttJson["PowR2"]["ENERGY"]["Period"] = tempmqttdata["ENERGY"]["Period"]
        mqttJson["PowR2"]["ENERGY"]["Power"] = tempmqttdata["ENERGY"]["Power"]
        mqttJson["PowR2"]["ENERGY"]["ApparentPower"] = tempmqttdata["ENERGY"]["ApparentPower"]
        mqttJson["PowR2"]["ENERGY"]["ReactivePower"] = tempmqttdata["ENERGY"]["ReactivePower"]
        mqttJson["PowR2"]["ENERGY"]["Factor"] = tempmqttdata["ENERGY"]["Factor"]
        mqttJson["PowR2"]["ENERGY"]["Voltage"] = tempmqttdata["ENERGY"]["Voltage"]
        mqttJson["PowR2"]["ENERGY"]["Current"] = tempmqttdata["ENERGY"]["Current"]

        # fahrenheit = (celsius * 1.8) + 32
        # celsius = (fahrenheit - 32) / 1.8

        if (mqttJson["PowR2"]["ENERGY"]["Power"] != 0 and PowR2EmailOnce == 0):
            mqttJson["PowR2"]["PowR2 State"] = "ON"
            PowR2EmailOnce = 1
        elif (mqttJson["PowR2"]["ENERGY"]["Power"] == 0 and PowR2EmailOnce == 2):
            mqttJson["PowR2"]["PowR2 State"] = "OFF"
            PowR2EmailOnce = 0

    JsonMqtt = json.dumps(mqttJson)
    # config.json data file
    data_file: TextIO
    with open('temperature.json', "a") as data_file:
        data_file.write(JsonMqtt)
        data_file.write(",")
        data_file.close()
    lrtemp = str(mqttJson["TH16"]["TemperatureC"])
    l, r = map(int, lrtemp.split(".", 1))

    # print(last_email_check, email_control)
    if ((int(time.time()) - last_email_check) > NumSecBetweenEmails):
        # print(last_email_check)
        last_email_check = int(time.time())
        email_control = True
        # print((last_email_check), email_control)

    if (email_control and ((l != last_temp_left and last_temp_right == 0)
       or (mqttJson["PowR2"]["PowR2 State"] == "ON" and PowR2EmailOnce == 1))):
        email_control = False
        last_temp_left = [l]
        last_temp_right = [r]
        text = '\r\n'.join(['Weather in %s ' % mqttJson["weather"]["observation_point"],
                            'Date / Time %s ' % time.asctime(),
                            'Humidity is %s' % mqttJson["weather"]["humidity"],
                            'Possibility of %s' % mqttJson["weather"]["sky_text"],
                            'Wind is %s' % mqttJson["weather"]["wind_display"],
                            'Temperature is %s %s / %s %s' % (mqttJson["weather"]["Temperature"], mqttJson["weather"]["degree_type"], mqttJson["weather"]["TemperatureF"], mqttJson["weather"]["UnitF"]),
                            'Feels Like %s ' % mqttJson["weather"]["feels_like"],
                            'Hot Tub Temperature is %s  %s / %s %s' % (mqttJson["TH16"]["TemperatureC"], mqttJson["TH16"]["Unit"], mqttJson["TH16"]["TemperatureF"], mqttJson["TH16"]["UnitF"]),
                            'TH16 Date is %s' % mqttJson["TH16"]["Device Date"],
                            'TH16 Time is %s' % mqttJson["TH16"]["Device Time"],
                            'PowR2 stat %s' % mqttJson["PowR2"]["PowR2 State"],
                            'PowR2 Voltage %s' % mqttJson["PowR2"]["ENERGY"]["Voltage"],
                            'PowR2 Current %s' % mqttJson["PowR2"]["ENERGY"]["Current"],
                            'PowR2 Power %s' % mqttJson["PowR2"]["ENERGY"]["Power"],
                            'PowR2 ApparentPower %s' % mqttJson["PowR2"]["ENERGY"]["ApparentPower"],
                            'PowR2 Period %s' % mqttJson["PowR2"]["ENERGY"]["Period"],
                            'PowR2 Today %s' % mqttJson["PowR2"]["ENERGY"]["Today"],
                            'PowR2 Total %s' % mqttJson["PowR2"]["ENERGY"]["Total"],
                            'PowR2 Total Start Date %s' % mqttJson["PowR2"]["ENERGY"]["TotalStartDate"],
                            'PowR2 Total Start Time %s' % mqttJson["PowR2"]["ENERGY"]["TotalStartTime"]
                            ])
        sendemail("Hot Tub Temperature change!", text)
        # print(text)
        PowR2EmailOnce = 2


# mqtt.MQTT_ERR_AGAIN = -1
# mqtt.MQTT_ERR_SUCCESS = 0
# mqtt.MQTT_ERR_NOMEM = 1
# mqtt.MQTT_ERR_PROTOCOL = 2
# mqtt.MQTT_ERR_INVAL = 3
# mqtt.MQTT_ERR_NO_CONN = 4
# mqtt.MQTT_ERR_CONN_REFUSED = 5
# mqtt.MQTT_ERR_NOT_FOUND = 6
# mqtt.MQTT_ERR_TLS = 8
# mqtt.MQTT_ERR_PAYLOAD_SIZE = 9
# mqtt.MQTT_ERR_NOT_SUPPORTED = 10
# mqtt.MQTT_ERR_AUTH = 11
# mqtt.MQTT_ERR_ACL_DENIED = 12
# mqtt.MQTT_ERR_UNKNOWN = 13
# mqtt.MQTT_ERR_ERRNO = 14
# mqtt.MQTT_ERR_QUEUE_SIZE = 15

def subscribe(client: mqtt_client):
    reply = client.subscribe(topic_sub)
    print(reply)
    client.on_message = on_message

def publish(client: mqtt_client, topic, msg):
    time.sleep(1)
    result = client.publish(topic, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
       print(f"Send `{msg}` to topic `{topic}`")
    else:
       print(f"Failed to send message to topic {topic}")

client = connect_mqtt()
subscribe(client)
print("Connected to MQTT broker " + str(broker) + " subscribed to " + str(topic_sub) + " topic ")

client.loop_forever()
