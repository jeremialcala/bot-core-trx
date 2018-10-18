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


URL = "https://platform-lookaside.fbsbx.com/platform/profilepic/?psid=1752570331535883&width=1024&ext=1542401477&hash=AeTHTMYTrg4KJbaX"
if __name__ == '__main__':
    try:
        db = get_mongodb()
        # app.run(debug=True)
        urllib.request.urlretrieve(URL, "profile/pic.jpg")
        # for line in open('accountPool.txt'):
        #    data = json.loads(line.strip())
        #    print(db.accountPool.insert_one(data))
    except Exception as e:
        print("Error: " + str(e.args))
