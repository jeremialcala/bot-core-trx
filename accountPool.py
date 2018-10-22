# -*- coding: utf8 -*-
import pymongo
import json
import urllib.request
from flask import Flask, request, send_file
import requests
import cv2


app = Flask(__name__)


def get_mongodb():
    try:
        db = None
        _dev = pymongo.MongoClient("mongodb://admin:password@54.164.193.15:27017")
        db = _dev["bot"]
    except Exception as e:
        print("Error: " + str(e.args))
    return db


def testMetod():
    return "OK", 200, {"Name": "Hello", "Number": 4}


URL = "https://platform-lookaside.fbsbx.com/platform/profilepic/?psid=1752570331535883&width=1024&ext=1542401477&hash=AeTHTMYTrg4KJbaX"
if __name__ == '__main__':
    try:
        print(testMetod()[2])
        db = get_mongodb()
        name = "Je"
        names = name.split()
        criteria = {"codMisc": "SA"}
        data = {"card-number": "000712", "exp-date": "0320", "document-type": "CC", "document-number": "16084701",
                "name-1": "Yecid", "name-2": "Jesús", "last-name-1": "gómez", "last-name-2": "Altahoña",
                "birth-date": "01/06/1982", "birth-place": "BOGOTA", "nationality": "THE WORLD", "sex": "M",
                "marital-status": "C", "phone-1": "3017828825", "phone-2": "00000000000", "phone-3": "00000000000",
                "email": "yecidaltahona1990@hotmail.com", "address-1": "Carrera 11 # 10 - 12",
                "code-address-1": "11001",
                "address-2": "Carrera 11 # 10 - 12", "code-address-2": "11001", "ocupation": "SOME",
                "work-status": "1", "work-center": "SOME PLACE", "work-center-id": "00000000",
                "work-center-position": "SOMEINFO", "monthly-income": "1.000,00", "govt-emp": "0",
                "govt-center": "", "branch-id": "1", "request-user": "JMENESES"}
        # print(json.dumps(data))
        api_headers = {"x-country": "Usd",
                       "language": "es",
                       "channel": "API",
                       "accept": "application/json",
                       "Content-Type": "application/json",
                       "Authorization": "Bearer $OAUTH2TOKEN$"}
        api_params = {"trxid=" + "1234567890"}
        url = "http://72.46.255.110:8008/ceoapi/1.0/11/employee?trxid=1234567890"
        # api_response = requests.post(url, headers=api_headers, data=json.dumps(data))
        # print("response: " + api_response.text)
        criteria = {"id": "1752570331535883"}
        # user = db.users.find_one(criteria)
        # print(user)
        # account = db.accountPool.find_one({"_id": user["accountId"]})
        # result = db.accountPool.find_one(criteria)
        # db.accountPool.update({"_id": result["_id"]},
        #                    {"codMisc": "AF"})
        # criteria = {"first_name": {"$regex": names[0]}}
        # result = db.users.find(criteria)
        # print(account)
        # for object in result:
        #    print(object[0])
        # app.run(debug=True)
        # urllib.request.urlretrieve(URL, "profile/pic.jpg")
        # for line in open('accountPool.txt'):
        #    data = json.loads(line.strip())
        #    print(db.accountPool.insert_one(data))
    except Exception as e:
        print(e.__str__())
        print("Error: " + str(e.args))
