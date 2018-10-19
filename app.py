# -*- coding: utf8 -*-
import json
import os
import sys
import re
from datetime import datetime
from twilio.rest import Client
import pymongo
import requests
from flask import Flask, request, send_file
from random import randint
import urllib.request

app = Flask(__name__)

params = {
    "access_token": os.environ["PAGE_ACCESS_TOKEN"]
}
headers = {
    "Content-Type": "application/json"
}
np_ouath_token = "cfa08a760590b543c7cae2796c822ac4"
objects = []


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
                        here_url = os.environ["REVERSEGEOCODE"] + "prox=" + str(location["lat"]) + "," + str(location["long"])
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
                    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
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


def get_user_by_name(name, operation, db):
    if len(name) > 1:
        criteria = {"first_name": {"$regex": name[0]}, "last_name": {"$regex": name[1]}}
    else:
        criteria = {"first_name": {"$regex": name[0]}}
    log(criteria)
    image_url = os.environ["IMAGES_URL"]
    result = db.users.find(criteria)
    buttons = {}
    attachment = {"type": "template"}
    payload = {"template_type": "generic", "elements": []}
    log(result.count())
    if result.count() is 0:
        return "No se encontraron usuarios", 404
    else:
        for friend in result:
            elements = {"buttons": [], "title": friend["first_name"] + " " + friend["last_name"],
                        "subtitle": friend["location"]["Address"]["Label"],
                        "image_url": image_url + "?file=profile/" + friend["id"] + ".jpg"}
            buttons["title"] = "Enviar Dinero"
            buttons["type"] = "postback"
            buttons["payload"] = operation + "|" + friend["id"]
            elements["buttons"].append(buttons)
            payload["elements"].append(elements)
        if result.count() > 1:
            payload["template_type"] = "list"
            payload["top_element_style"] = "compact"
        attachment["payload"] = payload

        return "OK", 200, attachment


def save_user_information(user, message, db):
    response = {"rc": 100, "msg": "Not related data found"}
    if user["registedStatus"] == 1:
        documentNumber = only_numerics(message)
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
        cellphone = only_numerics(message)
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
        confirmation = only_numerics(message)
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


def user_origination(user, db):
    data = {"card-number": "000712", "exp-date": "0320", "document-type": "CC", "document-number": "16084701",
            "name-1": " ", "name-2": " ", "last-name-1": "gómez", " ": " ",
            "birth-date": "01/06/1982", "birth-place": " ", "nationality": "THE WORLD", "sex": "M",
            "marital-status": "S", "phone-1": " ", "phone-2": "00000000000", "phone-3": "00000000000",
            "email": "yecidaltahona1990@hotmail.com", "address-1": "Carrera 11 # 10 - 12",
            "code-address-1": "11001",
            "address-2": "Carrera 11 # 10 - 12", "code-address-2": "11001", "ocupation": "SOME",
            "work-status": "1", "work-center": "SOME PLACE", "work-center-id": "00000000",
            "work-center-position": "SOMEINFO", "monthly-income": "1.000,00", "govt-emp": "0",
            "govt-center": "", "branch-id": "1", "request-user": "JMENESES"}

    account = get_account_from_pool(db)

    data["card-number"] = account["cardNumber"]
    data["exp-date"] = account["fechaExp"]
    data["document-type"] = get_user_document_type(user)
    data["document-number"] = user["document"]["documentNumber"]
    data["name-1"] = user["first_name"]
    data["last-name-1"] = user["last_name"]
    data["phone-1"] = user["cellphone"]
    data["address-2"] = user["location"]["Address"]["Label"]

    api_headers = {"x-country": "Usd",
                   "language": "es",
                   "channel": "API",
                   "accept": "application/json",
                   "Content-Type": "application/json",
                   "Authorization": "Bearer $OAUTH2TOKEN$"}

    api_headers["Authorization"] = api_headers["Authorization"].replace("$OAUTH2TOKEN$", np_ouath_token)

    url = os.environ["NP_URL"] + os.environ["CEOAPI"] + os.environ["CEOAPI_VER"] \
          + account["indx"] + "/employee?trxid=" + str(random_with_n_digits(10))

    api_response = np_api_request(url=url, data=data, api_headers=api_headers)
    if api_response.status_code == 200:
        db.accountPool.update({"_id": account["_id"]},
                              {"codMisc": "AF"})
        db.users.update({"id": user["id"]},
                        {"accountId": account["_id"]})
        return "OK", 200, account
    else:
        return api_response.text, api_response.status_code


def np_api_request(url, data, api_headers, api_params=None):
    log("Conectando a: " + url)
    log("Data:" + json.dumps(data))
    api_response = requests.post(url, params=api_params, headers=api_headers, data=json.dumps(data))
    log("response: " + api_response.text)
    log("status_code: " + str(api_response.status_code))
    if api_response.status_code == 401:
        get_oauth_token()
        # np_api_request(url, data, api_headers, api_params)
    else:
        return api_response


def get_oauth_token():
    api_headers = {"x-channel": "web",
                   "x-language": "es",
                   "accept": "application/json",
                   "Content-Type": "application/json"}

    data = {"grant_type": os.environ["NP_GTYPE"],
            "client_id": os.environ["NP_CID"],
            "client_secret": os.environ["NP_SRT"]}

    url = os.environ["NP_URL"] + os.environ["NP_OAUTH2"] + "token"
    api_response = requests.post(url, headers=api_headers, data=data)
    if api_response.status_code == 200:
        crentials = json.loads(api_response.text)
        np_ouath_token = crentials["access_token"]


def get_user_document_type(user):
    if user["document"]["documentType"] == "cedula":
        return "CC"
    else:
        return "PA"


def get_account_from_pool(db):
    criteria ={"codMisc": "SA"}
    return db.accountPool.find_one(criteria)


def random_with_n_digits(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return randint(range_start, range_end)


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


def only_numerics(text):
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
              "recipient": {
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
              "recipient": {
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
                                 "type": "template",
                                 "payload": {
                                    "template_type":"generic",
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
                                          "title":"Consulta de Saldo",
                                          "subtitle": "Consulta el saldo Disponible de tus tarjetas.",
                                          "buttons":[
                                             {
                                                "type": "postback",
                                                "title": "Saldos",
                                                "payload": "BALANCE_PAYLOAD"
                                             }
                                          ]
                                       },
                                       {
                                          "title":"Consulta de Movimientos",
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
    get_oauth_token()
    log(np_ouath_token)
    app.run(debug=True)

