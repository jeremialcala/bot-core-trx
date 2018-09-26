# -*- coding: utf8 -*-
import json
import os
import sys
from datetime import datetime

import pymongo
import requests
from flask import Flask, request

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200
    return "Hello world", 200


@app.route('/', methods=['POST'])
def get_message():
    data = request.get_json()
    log(data)

    if "messaging" in data['entry'][0]:
        messaging = data['entry'][0]['messaging'][0]
        user_id = data['entry'][0]['messaging'][0]['sender']['id']
        user = json.loads(get_user_by_id(user_id))
        if "error" in user:
            log("Error usuario no encontrado")
            return "OK", 200

        db = get_mongodb()
        result = db.users.find({'id': user_id})
        msg = "Hola te ayudaré a realizar las consultas que necesites de tus tarjetas"

        if result.count() is 0:
            db.users.insert_one(user)
        else:
            for document in result:
                user = document

        if "message" in messaging:

            if "text" in data['entry'][0]['messaging'][0]["message"]:
                message = data['entry'][0]['messaging'][0]["message"]["text"].split(" ")
                log(message)
                categories = classification(message, False, db)
                log(categories)
                response = generator(categories, db, user)
                log(response)
                user = response["user"]
                send_message(user["id"], response["msg"])

                if "tyc" not in user:
                    send_termandc(user["id"])
                    accept_tyc(user["id"])
                    return "OK", 200

        if "postback" in messaging:
            if "tyc" not in user:
                send_message(user["id"], msg)
                send_termandc(user["id"])
                accept_tyc(user["id"])
                return "OK", 200

            if messaging["postback"]["payload"] == "GET_STARTED_PAYLOAD":
                send_message(user["id"], "Claro que si vamos a empezar")
                send_operations(user["id"])
                return "OK", 200

            if "registedStatus" not in user:
                send_message(user["id"], "Primero tenemos que abrir una cuenta")
                options = [{"content_type": "text", "title": "Registrame", "payload": "POSTBACK_PAYLOAD"},
                           {"content_type": "text", "title": "No por ahora", "payload": "GET_STARTED_PAYLOAD"}]
                send_options(user["id"], options, "te gustaria iniciar el proceso?")
                return "OK", 200

            if user["registedStatus"] == 0:
                send_message(user["id"], "Aun no terminas tu registro...")
                send_message(user["id"], "indicame tu numero de identifcación")
                options = [{"content_type": "text", "title": "Cedula", "payload": "POSTBACK_PAYLOAD"},
                           {"content_type": "text", "title": "Pasaporte", "payload": "GET_STARTED_PAYLOAD"}]
                send_options(user["id"], options, "que tipo de documento tienes?")
                return "OK", 200

            if messaging["postback"]["payload"] == "PAYBILL_PAYLOAD":
                send_message(user["id"], "Muy bien! indicame el nombre del que recibira el dinero")
                return "OK", 200

    return "OK", 200


def generator(categries, db, user):
    log("responseGenerator")
    message = "Hola te ayudaré a realizar las consultas que necesites de tus tarjetas"
    global mail_body
    global sms_body

    if "accept" in categries and "negative" not in categries:
        message = "Gracias!"
        if "tyc" not in user:
            user['tyc'] = 1
            db.users.update({"id": user['id']}, {'$set': {'tyc': 1, "date-tyc": datetime.now()}})

    if "tyc" not in user:
        return {"user": user, "msg": message}

    if "registration" in categries:
        send_message(user["id"], "Listo! vamos a iniciar el proceso")
        db.users.update({"id": user['id']}, {'$set': {'registedStatus': 0, "date-registedStatus": datetime.now()}})
        options = [{"content_type": "text", "title": "Cedula", "payload": "POSTBACK_PAYLOAD"},
                   {"content_type": "text", "title": "Pasaporte", "payload": "GET_STARTED_PAYLOAD"}]
        send_options(user["id"], options, "que tipo de documento tienes?")
        message = ""

    if "cedula" in categries or "passport" in categries:
        message = "indicame tu numero de identifcación"

    return {"user": user, "msg": message}


def get_user_by_id(user_id):
    url = "https://graph.facebook.com/USER_ID?&access_token="
    url = url.replace("USER_ID", user_id) + os.environ["PAGE_ACCESS_TOKEN"]
    r = requests.get(url)
    if r.status_code != 200:
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
    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)


def send_options(recipient_id, options, text):
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
              "recipient":{
                "id": recipient_id
              },
              "message":{
                "text": text,
                "quick_replies": [
                    options[0],
                    options[1]
                ]
              }
            })
    log(data)
    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)


def accept_tyc(recipient_id):
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
              "recipient":{
                "id": recipient_id
              },
              "message":{
                "text": "Solo tienes que hacer clic en \"Acepto\" para iniciar...",
                "quick_replies": [
                    {
                        "content_type": "text",
                        "title": "Acepto",
                        "payload": "POSTBACK_PAYLOAD"
                    },
                    {
                        "content_type": "text",
                        "title": "No Acepto",
                        "payload": "POSTBACK_PAYLOAD"
                    }
                ]
              }
            })
    log(data)
    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)


def send_operations(recipient_id):
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
                        "recipient":{
                          "id": recipient_id
                           },
                           "message": {
                              "attachment": {
                                 "type":"template",
                                 "payload": {
                                    "template_type":"generic",
                                    "elements": [
                                       {
                                          "title": "sample",
                                          "subtitle": "We ve got the right hat for everyone.",
                                          "buttons": [
                                             {
                                                "type": "postback",
                                                "title": "Screen 01",
                                                "payload": "Book Me a Venue"
                                             }
                                          ]
                                       },
                                       {
                                          "title":"sample",
                                          "subtitle": "We ve got the right hat for everyone.",
                                          "buttons":[
                                             {
                                                "type": "postback",
                                                "title": "Screen 02",
                                                "payload": "Book Me a Venue"
                                             }
                                          ]
                                       },
                                       {
                                          "title":"sample",
                                          "subtitle": "We ve got the right hat for everyone.",
                                          "buttons": [
                                             {
                                                "type": "postback",
                                                "title": "Screen 03",
                                                "payload": "Book Me a Venue"
                                             }
                                          ]
                                       }
                                    ]
                                 }
                              }
                           }
                        })
    log(data)
    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)


def classification(sentence, registered, db):
    my_categories = []
    dictionary = db.dictionary.find_one()
    for word in sentence:
        for concept in dictionary:
            if type(dictionary[concept]) is list:
                for mean in dictionary[concept]:
                    if word.lower().find(mean) != -1 and concept not in my_categories:
                        log("palabra: " + word + " Significado: " + mean + " Concepto: " + concept)
                        my_categories.append(concept)

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

