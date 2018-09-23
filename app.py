# -*- coding: utf8 -*-
import sys
import os
import requests
import json
from flask import Flask, request
from flask import render_template
from flask import send_file


app = Flask(__name__)


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
    user_id = data['entry'][0]['messaging'][0]['sender']['id']
    user = json.loads(get_user_by_id(user_id))
    message = data['entry'][0]['messaging'][0]['message']
    log(user["id"])
    msg = "Gracias por su preferencia que tenga un buen dia 👋"
    send_message(user["id"], message["text"])

    return "OK", 200


def get_user_by_id(user_id):
    url = "https://graph.facebook.com/USER_ID?&access_token="
    url = url.replace("USER_ID", user_id) + os.environ["PAGE_ACCESS_TOKEN"]
    # log(url)
    r = requests.get(url)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)
        return r.status_code, r.text
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
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)

