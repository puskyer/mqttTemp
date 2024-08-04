#!/usr/bin/python3.8
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

# config.json data file
data_file: TextIO
with open('config.json', "r") as data_file:
    DataJson = json.load(data_file)
data_file.close()

mqttJson = {
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

        # fahrenheit = (celsius * 1.8) + 32
        # celsius = (fahrenheit - 32) / 1.8

loop = asyncio.get_event_loop()
loop.run_until_complete(getweather())

text = '\r\n'.join(['Weather in %s ' % mqttJson["weather"]["observation_point"],
                    'Date / Time %s ' % time.asctime(),
                    'Humidity is %s' % mqttJson["weather"]["humidity"],
                    'Possibility of %s' % mqttJson["weather"]["sky_text"],
                    'Wind is %s' % mqttJson["weather"]["wind_display"],
                    'Temperature is %s %s / %s %s' % (mqttJson["weather"]["Temperature"], mqttJson["weather"]["degree_type"], mqttJson["weather"]["TemperatureF"], mqttJson["weather"]["UnitF"]),
                    'Feels Like %s ' % mqttJson["weather"]["feels_like"],
                    ])
sendemail("Winchester Temperature!", text)
# print(text)
