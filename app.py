# -*- coding: utf8 -*-
import json
import os
import urllib.request
from datetime import datetime

import requests
from flask import Flask, request, send_file
from twilio.rest import Client

from utils import get_oauth_token, get_user_by_name, log, get_mongodb, random_with_n_digits, send_message

app = Flask(__name__)

params = {
    "access_token": os.environ["PAGE_ACCESS_TOKEN"]
}
headers = {
    "Content-Type": "application/json"
}

objects = []
np_oauth_token = get_oauth_token()

from services import user_origination, get_user_balance, get_user_movements


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
    try:
        if "messaging" in data['entry'][0]:
            messaging = data['entry'][0]['messaging'][0]
            user_id = data['entry'][0]['messaging'][0]['sender']['id']
            user = json.loads(get_user_by_id(user_id))
            if "error" in user:
                log("Error usuario no encontrado")
                return "OK", 200

            db = get_mongodb()
            objects = db.objects.find()
            result = db.users.find({'id': user_id})
            msg = "Hola te ayudaré a realizar las consultas que necesites de tus tarjetas"

            if result.count() is 0:
                db.users.insert_one(user)
                pic_profile = "profile/" + user["id"] + ".jpg"
                log(pic_profile)
                urllib.request.urlretrieve(user["profile_pic"], pic_profile)
            else:
                for document in result:
                    user = document

            if "message" in messaging:
                if "attachments" in data['entry'][0]['messaging'][0]["message"]:
                    attachment = data['entry'][0]['messaging'][0]["message"]["attachments"]
                    log(attachment)
                    if attachment[0]["type"] == "location":
                        location = json.loads(json.dumps(attachment[0]["payload"]["coordinates"]))
                        app_id = os.environ["APP_ID"]
                        app_code = os.environ["APP_CODE"]
                        here_url = os.environ["REVERSEGEOCODE"] + "prox=" + str(location["lat"]) + "," + str(
                            location["long"])
                        here_url += "&mode=retrieveAddresses&maxresults=1&gen=9&app_id=" + app_id + "&app_code=" + app_code
                        r = requests.get(here_url)
                        here = json.loads(r.text)
                        db.users.update({"id": user['id']},
                                        {'$set': {"registedStatus": 3,
                                                  "date-registedStatus": datetime.now(),
                                                  "location": here["Response"]["View"][0]["Result"][0]["Location"],
                                                  "date-location": datetime.now()}})
                        send_message(user["id"], "Muchas gracias!")
                        send_message(user["id"], "para continuar necesito enviarte un codigo de activación.")
                        options = [{"content_type": "text", "title": "SMS", "payload": "POSTBACK_PAYLOAD"},
                                   {"content_type": "text", "title": "Correo", "payload": "POSTBACK_PAYLOAD"}]
                        send_options(user["id"], options, "por donde prefieres recibirlo?")

                if "text" in data['entry'][0]['messaging'][0]["message"]:
                    message = data['entry'][0]['messaging'][0]["message"]["text"].split(" ")
                    log(message)

                    if "operationStatus" in user:
                        log("operationStatus")
                        if user["operationStatus"] == 1:
                            rsp = get_user_by_name(name=message, operation="SEND_MONEY", db=db)
                            log(rsp)
                            if rsp[1] == 200:
                                send_message(user["id"], "Selecciona la persona a la que quieres enviar el dinero")
                                attachment = rsp[2]
                                recipient = {"id": user["id"]}
                                rsp_message = {"attachment": attachment}
                                data = {"recipient": recipient, "message": rsp_message}
                                log(data)
                                requests.post("https://graph.facebook.com/v2.6/me/messages", params=params,
                                              headers=headers, data=json.dumps(data))
                                return "OK", 200

                    if "registedStatus" in user:
                        response = save_user_information(user, data['entry'][0]['messaging'][0]["message"]["text"], db)
                        if response["rc"] == 0:
                            return "OK", 200

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

                    if "greet" in categories:
                        send_operations(user["id"])

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

                if messaging["postback"]["payload"] == "BALANCE_PAYLOAD":
                    if user["registedStatus"] == 6:
                        get_user_balance(user, db)
                        return "OK", 200

                if messaging["postback"]["payload"] == "MOVEMENTS_PAYLOAD":
                    if user["registedStatus"] == 6:
                        get_user_movements(user, db)
                        return "OK", 200

                if "MOVEMENTS_" in messaging["postback"]["payload"]:
                    if user["registedStatus"] == 6:
                        payload = messaging["postback"]["payload"].split("_")
                        get_user_movements(user, db, payload[1])
                        return "OK", 200

                if messaging["postback"]["payload"] == "GET_STARTED_PAYLOAD":
                    send_message(user["id"], "Claro que si vamos a empezar")
                    send_operations(user["id"])
                    return "OK", 200

                if "registedStatus" not in user:
                    send_message(user["id"], "Primero tenemos que abrir una cuenta")
                    options = [{"content_type": "text", "title": "Si!, Registrame", "payload": "POSTBACK_PAYLOAD"},
                               {"content_type": "text", "title": "No por ahora", "payload": "GET_STARTED_PAYLOAD"}]
                    send_options(user["id"], options, "te gustaria iniciar el proceso?")
                    return "OK", 200

                if user["registedStatus"] == 0:
                    send_message(user["id"], "Aun no terminas tu registro...")
                    options = [{"content_type": "text", "title": "Cedula", "payload": "POSTBACK_PAYLOAD"},
                               {"content_type": "text", "title": "Pasaporte", "payload": "GET_STARTED_PAYLOAD"}]
                    send_options(user["id"], options, "que tipo de documento tienes?")
                    return "OK", 200

                if user["registedStatus"] == 1:
                    send_message(user["id"], "Vamos a continuar tu afiliacion.")
                    send_message(user["id"], "indicame tu numero de identifcación")
                    return "OK", 200

                if user["registedStatus"] == 2:
                    data = json.dumps({
                        "recipient": {
                            "id": user["id"]
                        },
                        "message": {
                            "text": "me gustaria conocer donde te encuentras",
                            "quick_replies": [{
                                "content_type": "location"
                            }]
                        }
                    })
                    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers,
                                  data=data)
                    return "OK", 200

                if user["registedStatus"] == 3:
                    send_message(user["id"], "para continuar necesito enviarte un código de activación.")
                    options = [{"content_type": "text", "title": "SMS", "payload": "SMS_PAYLOAD"},
                               {"content_type": "text", "title": "Correo", "payload": "EMAIL_PAYLOAD"}]
                    send_options(user["id"], options, "por donde prefieres recibirlo?")
                    return "OK", 200

                if messaging["postback"]["payload"] == "PAYBILL_PAYLOAD":
                    send_message(user["id"], "Muy bien! indicame el nombre del que recibira el dinero")
                    db.users.update({"id": user['id']},
                                    {'$set': {"operationStatus": 1}})
                    return "OK", 200

        return "OK", 200
    except Exception as e:
        log("Error " + str(e.args))
        return "OK", 200


@app.route('/images', methods=['GET'])
def get_image():
    try:
        image = request.args.get('file')
        return send_file(image, mimetype='image/gif')
    except Exception as e:
        print("Error: " + str(e.args))
        return "NOT FOUND", 404


def save_user_information(user, message, db):
    response = {"rc": 100, "msg": "Not related data found"}
    if user["registedStatus"] == 1:
        documentNumber = only_numeric(message)
        if user["document"]["documentType"] == "cedula" and documentNumber["rc"] == 0:
            db.users.update({"id": user['id']},
                            {'$set': {"registedStatus": 2,
                                      "document": {"documentType": "cedula",
                                                   "documentNumber": documentNumber["numbers"]},
                                      "date-registedStatus": datetime.now()}})
            send_message(user["id"], "Listo! tu cedula fue registrada exitosamente")
            response = {"rc": 0, "msg": "Process OK"}

        if user["document"]["documentType"] == "passport" and documentNumber["rc"] != -500:
            db.users.update({"id": user['id']},
                            {'$set': {"registedStatus": 2,
                                      "document": {"documentType": "passport",
                                                   "documentNumber": documentNumber["numbers"]},
                                      "date-registedStatus": datetime.now()}})
            send_message(user["id"], "Gracias! ya pude guardar tu info")
            response = {"rc": 0, "msg": "Process OK"}

        if response["rc"] == 0:
            data = json.dumps({
                "recipient": {
                    "id": user["id"]
                },
                "message": {
                    "text": "me gustaria conocer donde te encuentras",
                    "quick_replies": [{
                        "content_type": "location"
                    }]
                }
            })
            requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
        return response

    if user["registedStatus"] == 4:
        cellphone = only_numeric(message)
        if cellphone["rc"] == 0:
            result = db.country.find({"name": user["location"]["Address"]["Country"]})
            if result.count() is not 0:
                for document in result:
                    country = document
                    confirmation = random_with_n_digits(5)
                    client = Client(os.environ["ACCOUNT_ID"], os.environ["AUTH_TOKEN"])
                    response = {"rc": 0, "msg": "Process OK"}
                    message = client.messages.create(
                        from_=os.environ["SMS_ORI"],
                        to=country["code"] + cellphone["numbers"],
                        body="Tu clave de temporal es: " + str(confirmation)
                    )
                    send_message(user["id"],
                                 "Muy bien! Te acabo de enviar el código a tu celular, me lo indicas por favor.")
                    db.users.update({"id": user['id']},
                                    {'$set': {"registedStatus": 5,
                                              "date-registedStatus": datetime.now(),
                                              "cellphone": country["code"] + cellphone["numbers"],
                                              "date-confirmation": datetime.now(),
                                              "confirmation": confirmation,
                                              "date-cellphone": datetime.now()}})
        return response

    if user["registedStatus"] == 5:
        confirmation = only_numeric(message)
        if confirmation["rc"] == 0:
            response = {"rc": 0, "msg": "Process OK"}
            confirmationTime = datetime.now() - user["date-confirmation"]
            log(confirmationTime.seconds)

            if confirmationTime.seconds > 180:
                send_message(user["id"], "El código ya expiro. ")
                send_message(user["id"], "para continuar con el registro necesito enviarte un codigo de activación.")
                options = [{"content_type": "text", "title": "SMS", "payload": "POSTBACK_PAYLOAD"},
                           {"content_type": "text", "title": "Correo", "payload": "POSTBACK_PAYLOAD"}]
                send_options(user["id"], options, "por donde prefieres recibirlo?")
                db.users.update({"id": user['id']},
                                {'$set': {"registedStatus": 3, "date-registedStatus": datetime.now()}})
                return response
            log(user["confirmation"])
            if str(user["confirmation"]) == confirmation["numbers"]:
                send_message(user["id"], "Muy bien! vamos a registrarte una cuenta.")
                origination = user_origination(user, db)
                if origination[1] == 200:
                    send_message(user["id"], "Exito! ya tienes una cuenta!")
                    db.users.update({"id": user['id']},
                                    {'$set': {"registedStatus": 6, "date-registedStatus": datetime.now()}})
                    send_operations(user["id"])
                else:
                    send_message(user["id"], "No pude registrar tu cuenta, por favor intenta mas tarde.")
                return response

            else:
                send_message(user["id"], "El código que me indicas no es correcto")
        return response

    return response


def generator(categories, db, user):
    log("responseGenerator")
    message = "Hola te ayudaré a realizar las consultas que necesites de tus tarjetas"
    global mail_body
    global sms_body

    if "accept" in categories and "negative" not in categories:
        message = ""
        if "tyc" not in user:
            user['tyc'] = 1
            db.users.update({"id": user['id']}, {'$set': {'tyc': 1, "date-tyc": datetime.now()}})
            send_message(user["id"], "Gracias!")
            send_operations(user["id"])

    if "tyc" not in user:
        return {"user": user, "msg": message}

    if "registration" in categories:
        send_message(user["id"], "Listo! vamos a iniciar el proceso")
        db.users.update({"id": user['id']}, {'$set': {'registedStatus': 0, "date-registedStatus": datetime.now()}})
        options = [{"content_type": "text", "title": "Cedula", "payload": "POSTBACK_PAYLOAD"},
                   {"content_type": "text", "title": "Pasaporte", "payload": "GET_STARTED_PAYLOAD"}]
        send_options(user["id"], options, "que tipo de documento tienes?")
        message = ""

    if "registedStatus" in user:
        if user["registedStatus"] == 0:
            if "cedula" in categories or "passport" in categories:
                db.users.update({"id": user['id']},
                                {'$set': {"registedStatus": 1,
                                          'document': {"documentType": get_document_type(categories)},
                                          "date-registedStatus": datetime.now()}})
                message = "indicame tu numero de identifcación"

        if user["registedStatus"] == 3:
            if "sms" in categories:
                db.users.update({"id": user['id']},
                                {'$set': {"registedStatus": 4,
                                          "date-registedStatus": datetime.now()}})
                message = "indicame tu numero de celular"

    return {"user": user, "msg": message}


def get_document_type(categories):
    if "cedula" in categories:
        return categories[categories.index("cedula")]
    if "passport" in categories:
        return categories[categories.index("passport")]


def only_numeric(text):
    log("onlyNumerics: " + text)
    numbs = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    resp = ""
    for char in text:
        if char in numbs:
            resp += char

    log(len(resp))
    if len(text) != len(resp) and len(resp) != 0:
        return {"rc": -123, "msg": "no todos los caracteres no son numeros", "numbers": resp}
    elif len(resp) == 0:
        return {"rc": -500, "msg": "no hay numeros en este texto", "numbers": resp}

    return {"rc": 0, "msg": "Process OK", "numbers": resp}


def get_user_by_id(user_id):
    url = "https://graph.facebook.com/USER_ID?&access_token="
    url = url.replace("USER_ID", user_id) + os.environ["PAGE_ACCESS_TOKEN"]
    r = requests.get(url)
    if r.status_code != 200:
        return r.text
    else:
        return r.text

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
        "recipient": {
            "id": recipient_id
        },
        "message": {
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
        "recipient": {
            "id": recipient_id
        },
        "message": {
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
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "Enviar Dinero",
                            "subtitle": "Envia dinero a tus amigos registrados o no registrados.",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "Enviar Dinero",
                                    "payload": "PAYBILL_PAYLOAD"
                                }
                            ]
                        },
                        {
                            "title": "Consulta de Saldo",
                            "subtitle": "Consulta el saldo Disponible de tus tarjetas.",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "Saldos",
                                    "payload": "BALANCE_PAYLOAD"
                                }
                            ]
                        },
                        {
                            "title": "Consulta de Movimientos",
                            "subtitle": "Consulta las operaciones realizadas.",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "Movimientos",
                                    "payload": "MOVEMENTS_PAYLOAD"
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


if __name__ == '__main__':
    log(np_oauth_token)
    app.run(debug=True)
