import pymongo
import requests
import json
import os
import sys
import re
from random import randint
from datetime import datetime
from bson import ObjectId


params = {
    "access_token": os.environ["PAGE_ACCESS_TOKEN"]
}
headers = {
    "Content-Type": "application/json"
}


def get_oauth_token():
    api_headers = {"x-channel": "web",
                   "x-language": "es",
                   "accept": "application/json",
                   "Content-Type": "application/json"}

    data = {"grant_type": os.environ["NP_GTYPE"],
            "client_id": os.environ["NP_CID"],
            "client_secret": os.environ["NP_SRT"]}

    url = os.environ["NP_URL"] + os.environ["NP_OAUTH2"] + "token"
    api_response = requests.post(url, headers=api_headers, data=json.dumps(data))
    # log(api_response.text)
    if api_response.status_code == 200:
        credentials = json.loads(api_response.text)
        return credentials["accessToken"]


def get_user_by_name(name, operation, db):
    if len(name) > 1:
        criteria = {"first_name": {"$regex": name[0]}, "last_name": {"$regex": name[1]}}
    else:
        criteria = {"first_name": {"$regex": name[0]}}
    log(criteria)
    result = db.users.find(criteria)

    attachment = {"type": "template"}
    payload = {"template_type": "generic", "elements": []}
    log(result.count())
    if result.count() is 0:
        return "No se encontraron usuarios", 404
    else:
        for friend in result:
            buttons = {}
            elements = {"buttons": [], "title": friend["first_name"] + " " + friend["last_name"],
                        "subtitle": friend["location"]["Address"]["Label"],
                        "image_url": friend["profile_pic"]}
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


def np_api_request(url, data, api_headers, api_params=None, http_method=None):
    log("Conectando a: " + url)
    if http_method is "GET":
        api_response = requests.get(url, headers=api_headers)
    else:
        log("Data:" + json.dumps(data))
        api_response = requests.post(url, params=api_params, headers=api_headers, data=json.dumps(data))

    log("response: " + api_response.text)
    log("status_code: " + str(api_response.status_code))
    if api_response.status_code == 401:
        os.environ["NP_OAUTH2_TOKEN"] = get_oauth_token()
        api_headers["Authorization"] = "Bearer " + os.environ["NP_OAUTH2_TOKEN"]
        return np_api_request(url, data, api_headers, api_params, http_method)
    else:
        return api_response


def get_user_document_type(user):
    if user["document"]["documentType"] == "cedula":
        return "CC"
    else:
        return "PA"


def get_account_from_pool(db):
    criteria = {"codMisc": "SA"}
    return db.accountPool.find_one(criteria)


def random_with_n_digits(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return randint(range_start, range_end)


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


def validate_re(pattern, text):
    match = re.match(pattern, str(text))
    print(match)
    if match is None:
        return False
    return True


def send_options(recipient_id, options, text):
    data = {"recipient": {"id": recipient_id}, "message": {"text": text, "quick_replies": []}}
    for option in options:
        data["message"]["quick_replies"].append(option)
    log(data)
    requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=json.dumps(data))


def get_current_transaction(user):
    db = get_mongodb()
    transactions = db.transactions.find({"sender": user["id"], "status": 3})
    ccurr_transaction = {"status": 0, "observation": "Not Transaction found"}
    if transactions is None:
        return ccurr_transaction

    for transaction in transactions:
        transactionTime = datetime.now() - transaction["status-date"]
        log(transactionTime.seconds)
        if transactionTime.seconds > 180:
            db.transactions.update({"_id": ObjectId(transaction["_id"])},
                                   {"$set": {"status": 0}})
        else:
            return transaction

    return ccurr_transaction


def send_payment_receipt(transaction):
    db = get_mongodb()

    user = db.users.find_one({"id": transaction["sender"]})
    friend = db.users.find_one({"id": transaction["recipient"]})

    account = db.accountPool.find_one({"_id": ObjectId(user["accountId"])})

    payload = {"template_type": "receipt", "recipient_name": friend["first_name"],
               "order_number": str(transaction["_id"]), "currency": "USD",
               "payment_method": "VISA " + account["cardNumber"][2:], "order_url": "",
               "timestamp": str(datetime.timestamp(datetime.now())).split(".")[0],
               "summary": {"total_cost": transaction["amount"]}, "elements": []}

    element = {"title": "Envio de Dinero a " + friend["first_name"],
               "subtitle": "Envio de Dinero", "price": transaction["amount"], "currency": "USD",
               "image_url": friend["profile_pic"]}
    payload["elements"].append(element)
    message = {"attachment": {"type": "template", "payload": payload}}
    data = {"recipient": {"id": user["id"]}, "message": message}
    db.transactions.update({"_id": ObjectId(transaction["_id"])},
                           {"$set": {"status": 4}})
    log(data)
    rsp = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params,
                        headers=headers,
                        data=json.dumps(data))
    log(rsp.text)
    options = [
        {"content_type": "text", "title": "Confirmado", "payload": "TRX_DO_CONFIRM_" + str(transaction["_id"])},
        {"content_type": "text", "title": "Cancelar", "payload": "TRX_DO_CANCEL_" + str(transaction["_id"])}]

    send_options(user["id"], options, "Estamos listos para enviar el pago, estas de acuerdo?")
