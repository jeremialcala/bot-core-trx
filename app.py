# -*- coding: utf8 -*-
import sys
import os
import requests
import json
import pymongo
import time
from flask import Flask, request
from flask import render_template
from flask import send_file
from pymongo.errors import DuplicateKeyError


app = Flask(__name__)
movimientos = ['movimientos', 'transacciones']
registration = ['resgistro', 'registrarme', 'afiliarme', 'registrar']
acepto = ['acepto', 'aceptar', 'entiendo', 'aceptado', 'entendido', 'admitir', 'consentir', 'aceder']


@app.route('/', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200
    return "Hello world", 200


@app.route('/', methods=['POST'])
def getMessage():
    data = request.get_json()
    log(data)
    return "OK", 200


def get_user_by_id(user_id):
    url = "https://graph.facebook.com/USER_ID?&access_token="
    url = url.replace("USER_ID", user_id) + os.environ["PAGE_ACCESS_TOKEN"]
    # log(url)
    r = requests.get(url)
    if r.status_code != 200:
        # log(r.status_code)
        # log(r.text)
        return r.text
    else:
        return r.text


def send_message(recipient_id, message_text):
    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)


def send_termandc(recipient_id):
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        }, "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "Novopayment",
                            "subtitle": "Terminos y Condiciones del Servicio",
                            "buttons": [
                                {
                                    "type": "web_url",
                                    "url": "https://novopayment.com/privacy-policy/",
                                    "title": "+ info"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    })
    log(data)
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def aceptTyC(recipient_id):
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
              "recipient":{
                "id":"1752570331535883"
              },
              "message":{
                "text": "Solo tienes que hacer clic en \"Acepto\" para iniciar...",
                "quick_replies":[
                  {
                    "content_type":"text",
                    "title":"Acepto",
                    "payload":"<POSTBACK_PAYLOAD>"
                  },
                  {
                    "content_type":"text",
                    "title":"No acepto",
                    "payload":"<POSTBACK_PAYLOAD>"
                  }
                ]
              }
            })
    log(data)
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def sendMenu():
    menu = json.dumps({"persistent_menu":
                {
                  "locale": "default",
                  "composer_input_disabled": True,
                  "call_to_actions": [
                    {
                      "title":"My Account",
                      "type":"nested",
                      "call_to_actions": [
                        {
                          "title": "Pay Bill",
                          "type": "postback",
                          "payload": "PAYBILL_PAYLOAD"
                        },
                        {
                          "type": "web_url",
                          "title": "Latest News",
                          "url": "https://www.messenger.com/",
                          "webview_height_ratio": "full"
                        }
                      ]
                    }
                  ]
                }
    })
    return menu


def classification(sentence, registered, db):
    my_categories = []
    dictionary = db.dictionary.find_one()
    for word in sentence:
        for concept in dictionary:
            if type(dictionary[concept]) is list:
                for mean in dictionary[concept]:
                    if word.lower().find(mean) != -1 and concept not in my_categories:
                        log("palabra: " + word + " Significado: " + mean + " Concepto: " + concept, file)
                        my_categories.append(concept)

        for movimiento in movimientos:
            if 'movimientos' not in my_categories:
                if word.lower().find(movimiento) != -1 and registered:
                    my_categories.append('movimientos')

        for reg in registration:
            if 'registration' not in my_categories:
                if word.lower().find(reg) != -1 or not registered:
                    my_categories.append('registration')

    return my_categories


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()


def get_mongodb():
    try:
        db = None
        log(os.environ["MONGO"])
        _dev = pymongo.MongoClient(os.environ["MONGO"])
        db = _dev[os.environ["SCHEMA"]]
    except Exception as e:
        log("Error: " + str(e.args))
    return db


if __name__ == '__main__':
    app.run(debug=True)

