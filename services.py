import os
import json
import requests
from utils import log, get_account_from_pool, get_user_document_type, random_with_n_digits, np_api_request, send_message
from app import np_oauth_token, headers, params


def user_origination(user, db):
    data = {"card-number": "000712", "exp-date": "0320", "document-type": "CC", "document-number": "16084701",
            "name-1": " ", "name-2": " ", "last-name-1": "", "last-name-2": " ",
            "birth-date": "01/06/1982", "birth-place": " ", "nationality": "THEWORLD", "sex": "M",
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
    data["last-name-2"] = user["last_name"]
    data["birth-place"] = user["location"]["Address"]["Country"]
    data["phone-1"] = user["cellphone"]
    data["address-2"] = user["location"]["Address"]["Label"]

    api_headers = {"x-country": "Usd",
                   "language": "es",
                   "channel": "API",
                   "accept": "application/json",
                   "Content-Type": "application/json",
                   "Authorization": "Bearer $OAUTH2TOKEN$"}

    api_headers["Authorization"] = api_headers["Authorization"].replace("$OAUTH2TOKEN$", np_oauth_token)

    url = os.environ["NP_URL"] + os.environ["CEOAPI"] + os.environ["CEOAPI_VER"] \
          + account["indx"] + "/employee?trxid=" + str(random_with_n_digits(10))

    api_response = np_api_request(url=url, data=data, api_headers=api_headers)
    if api_response.status_code == 200:
        db.accountPool.update({"_id": str(account["_id"])},
                              {'$set': {"codMisc": "AF"}})
        db.users.update({"id": user["id"]},
                        {'$set': {"accountId": account["_id"]}})
        return "OK", 200, account
    else:
        return api_response.text, api_response.status_code


def get_user_balance(user, db):
    account = db.accountPool.find_one({"_id": user["accountId"]})
    url = os.environ["NP_URL"] + os.environ["CEOAPI"] + os.environ["CEOAPI_VER"] \
          + account["indx"] + "/employee/" + user["document"]["documentNumber"] \
          + "/balance-inq?trxid=" + str(random_with_n_digits(10))
    api_headers = {"x-country": "Usd",
                   "language": "es",
                   "channel": "API",
                   "accept": "application/json",
                   "Content-Type": "application/json",
                   "Authorization": "Bearer $OAUTH2TOKEN$"}
    image_url = os.environ["IMAGES_URL"]
    api_headers["Authorization"] = api_headers["Authorization"].replace("$OAUTH2TOKEN$", np_oauth_token)
    api_response = np_api_request(url=url, data=None, api_headers=api_headers, http_method="GET")
    if api_response.status_code == 200:
        attachment = {"type": "template"}
        payload = {"template_type": "generic", "elements": []}
        balance = json.dumps(api_response.text)
        elements = {"title": "Tarjeta: " + balance["card-number"],
                    "subtitle": "available-balance: " + balance["available-balance"],
                    "image_url": image_url + "?file=product/Tarjeta-Plata_NB.png"}
        payload["elements"].append(elements)
        attachment["payload"] = payload
        recipient = {"id": user["id"]}
        rsp_message = {"attachment": attachment}
        data = {"recipient": recipient, "message": rsp_message}
        log(data)
        requests.post("https://graph.facebook.com/v2.6/me/messages", params=params,
                      headers=headers, data=json.dumps(data))
        return "OK", 200
    else:
        attachment = {"type": "template"}
        payload = {"template_type": "generic", "elements": []}
        elements = {"title": "En estos momentos no pude procesar tu operación.",
                    "subtitle": "available-balance: 0.00",
                    "image_url": image_url + "?file=products/Tarjeta-Plata_NB.png"}
        payload["elements"].append(elements)
        attachment["payload"] = payload
        recipient = {"id": user["id"]}
        rsp_message = {"attachment": attachment}
        data = {"recipient": recipient, "message": rsp_message}
        log(data)
        requests.post("https://graph.facebook.com/v2.6/me/messages", params=params,
                      headers=headers, data=json.dumps(data))
        # send_message(user["id"], "En estos momentos no pude procesar tu operación.")
        return "OK", 200


def get_user_movements(user, db, mov_id=None):
    account = db.accountPool.find_one({"_id": user["accountId"]})
    log(mov_id)
    if mov_id is None:
        url = os.environ["NP_URL"] + os.environ["CEOAPI"] + os.environ["CEOAPI_VER"] \
              + account["indx"] + "/employee/" + user["document"]["documentNumber"] \
              + "/mov-inq?trxid=" + str(random_with_n_digits(10))
        api_headers = {"x-country": "Usd",
                       "language": "es",
                       "channel": "API",
                       "accept": "application/json",
                       "Content-Type": "application/json",
                       "Authorization": "Bearer $OAUTH2TOKEN$"}
        api_headers["Authorization"] = api_headers["Authorization"].replace("$OAUTH2TOKEN$", np_oauth_token)
        api_response = np_api_request(url=url, data=None, api_headers=api_headers, http_method="GET")
        if api_response.status_code == 200:
            response = json.loads(api_response.text)
            if "mov-list" in response:
                movements = {
                    "userId": user["id"],
                    "movements": response["mov-list"],
                    "count": len(response["mov-list"]),
                    "page": 1,
                    "status": 1
                }
                mov_id = db.movements.insert(movements)
                movements["_id"] = mov_id
            attachment = create_mov_attachment(movements)
            recipient = {"id": user["id"]}
            rsp_message = {"attachment": attachment}
            data = {"recipient": recipient, "message": rsp_message}
            log(data)
            requests.post("https://graph.facebook.com/v2.6/me/messages", params=params,
                          headers=headers, data=json.dumps(data))
            return "OK", 200
        else:
            send_message(user["id"], "En estos momentos no pudimos procesar tu operación.")
            return "OK", 200

    else:
        criteria = {"_id": mov_id, "userId": user["id"], "status": 1}
        movements = db.movements.find_one(criteria)
        pages = movements["count"] / 4

        if movements is None:
            send_message(user["id"], "No se encontraron movimientos...")
            return "OK", 200

        if movements["status"] == 0 or pages == movements["page"]:
            send_message(user["id"], "No hay mas movimientos...")
            return "OK", 200

        attachment = create_mov_attachment(movements)

        recipient = {"id": user["id"]}
        rsp_message = {"attachment": attachment}
        data = {"recipient": recipient, "message": rsp_message}
        log(data)
        requests.post("https://graph.facebook.com/v2.6/me/messages", params=params,
                      headers=headers, data=json.dumps(data))
        return "OK", 200


def create_mov_attachment(mov_list):
    attachment = {"type": "template"}
    payload = {"template_type": "list", "top_element_style": "compact", "elements": []}
    mov_count = 0
    for mov in mov_list["movements"]:
        if mov_count < (4 * mov_list["page"]):
            payload["elements"].append(
                {
                    "title": mov["mov-desc"],
                    "subtitle": "💰" + mov["mov-amount"] + "\n🗓️" + mov["mov-date"]
                })
            mov_count += 1

    payload["buttons"] = [{"title": "View More", "type": "postback", "payload": "MOVEMENT_" +
                                                                                str(mov_list["_id"])}]
    attachment["payload"] = payload
    return attachment
