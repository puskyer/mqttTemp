#!/usr/bin/python3
# -*- coding: utf-8 -*-

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
    "Temperature": 0.0,
    "Unit": "C",
    "Device Date": "devdate",
    "Device Time": "devtime",
    "Date": "thedate",
    "Time": "thetime"
}

# mosquitto_sub -v  -h mqtt.lan -u mqttUser -P MqttPass  -t fireplacefan/tele/SENSOR
topic_sub_SENSOR = "fireplacefan/tele/SENSOR"
topic_sub_STATUS10 = "fireplacefan/stat/STATUS10"
topic_pub_POWER = b'fireplacefan/cmnd/POWER'
topic_pub_STATUS = "fireplacefan/cmnd/STATUS"
topic_pub_STATUS_data = '0'
topic_pub = "fireplacefan/stat/python"
topic_sub = topic_sub_SENSOR
keepalive = 0
message_interval = 60
counter = 0
last_temp = mqttJson["Temperature"]

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
        #server.set_debuglevel(1)
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

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    # Set Connecting Client ID
    mqttclient = mqtt_client.Client(client_id)
    mqttclient.username_pw_set(username, password)
    mqttclient.on_connect = on_connect
    mqttclient.connect(broker, port)
    return mqttclient


# {"StatusSNS": {"Time": "2021-11-14T19:39:49", "DS18B20": {"Id": "05167219F3FF",
# "Temperature": 32.9}, "TempUnit": "C"}}
def subscribe(client: mqtt_client):

    def on_message(client, userdata, msg):
        global last_temp
        mqttdata = json.loads(msg.payload.decode())
        print(f"Received `{mqttdata}` from `{msg.topic}` topic")
        mytime = time.localtime()
        mqttJson["Date"] = str(mytime[0]) + '/' + str(mytime[1]) + '/' + str(mytime[2])
        mqttJson["Time"] = str(mytime[3]) + ':' + str(mytime[4]) + ':' + str(mytime[5])
        if topic ==  topic_sub_STATUS10:
            tempdate = mqttdata['StatusSNS']['Time']
            mqttJson["Temperature"] = mqttdata['StatusSNS']['DS18B20']['Temperature']
            mqttJson["Unit"] = mqttdata['StatusSNS']['TempUnit']
        else:
            tempdate = mqttdata['Time']
            mqttJson["Temperature"] = mqttdata['DS18B20']['Temperature']
            mqttJson["Unit"] = mqttdata['TempUnit']
        temp1date = tempdate.split("T")
        mqttJson["Device Date"] = temp1date[0]
        mqttJson["Device Time"] = temp1date[1]
        JsonMqtt = json.dumps(mqttJson)
        # config.json data file
        data_file: TextIO
        with open('temperature.json', "a") as data_file:
            data_file.write(JsonMqtt)
            data_file.write(",")
            data_file.close()
        if int(mqttJson["Temperature"]) != last_temp:
            last_temp = int(mqttJson["Temperature"])
            sendemail("Hot Tub Temperature!", JsonMqtt)

    client.subscribe(topic)
    client.on_message = on_message

# def publish(client: mqtt_client):
#    client.publish(topic, msg)
#    client.connect(broker, port)
#    return client


def publish(client: mqtt_client):
    time.sleep(1)
    result = client.publish(topic, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
       print(f"Send `{msg}` to topic `{topic}`")
    else:
       print(f"Failed to send message to topic {topic}")


client = connect_mqtt()
topic = topic_sub
subscribe(client)
print("Connected to MQTT broker " + str(broker) + " subscribed to " + str(topic_sub) + " topic ")

client.loop_forever()
