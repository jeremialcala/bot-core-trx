# -*- coding: utf8 -*-
import sys
import os
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


if __name__ == '__main__':
    app.run(debug=True)

