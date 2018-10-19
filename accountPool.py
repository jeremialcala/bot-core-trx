# -*- coding: utf8 -*-
import pymongo
import json
import urllib.request
from flask import Flask, request, send_file


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
        criteria = {"first_name": {"$regex": names[0]}}
        result = db.users.find(criteria)
        print(result.count())
        for object in result:
            print(object)
        # app.run(debug=True)
        # urllib.request.urlretrieve(URL, "profile/pic.jpg")
        # for line in open('accountPool.txt'):
        #    data = json.loads(line.strip())
        #    print(db.accountPool.insert_one(data))
    except Exception as e:
        print("Error: " + str(e.args))
