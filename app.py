#!/usr/bin/env python3.8
import json
import os
import utils

import requests
from werkzeug.exceptions import NotFound

from api import MessageApiClient
from utils import AESCipher
from flask import Flask, jsonify, request
from dotenv import load_dotenv, find_dotenv

from manager import PluginManager, ConfigManger
from models import Event
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()
load_dotenv(find_dotenv())

app = Flask(__name__)

# load from env
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")
LARK_HOST = os.getenv("LARK_HOST")
logger = utils.get_logger()

logger.info("APP_ID                   >>>> %s", APP_ID)
logger.info("APP_SECRET               >>>> %s", APP_SECRET)
logger.info("VERIFICATION_TOKEN       >>>> %s", VERIFICATION_TOKEN)
logger.info("ENCRYPT_KEY              >>>> %s", ENCRYPT_KEY)
logger.info("LARK_HOST                >>>> %s", LARK_HOST)

# init service
config_manger = ConfigManger()
message_api_client = MessageApiClient(APP_ID, APP_SECRET, LARK_HOST)
plugin_manager = PluginManager(message_api_client, config_manger)


def decrypt_data(encrypt_key, data):
    encrypt_data = data.get("encrypt")
    if encrypt_key == "" and encrypt_data is None:
        # data haven't been encrypted
        return data
    if encrypt_key == "":
        raise Exception("ENCRYPT_KEY is necessary")
    cipher = AESCipher(encrypt_key)

    return json.loads(cipher.decrypt_string(encrypt_data))


@app.errorhandler
def msg_error_handler(ex):
    logger.error(ex)
    response = jsonify(message=str(ex))
    response.status_code = (
        ex.response.status_code if isinstance(ex, requests.HTTPError) else 500
    )
    return response


@app.errorhandler(404)
def plugin_web_hook_handler(error):
    web_req = plugin_manager.config_path(request)
    if web_req:
        # 异步执行处理
        executor.submit(plugin_manager.with_web, web_req)
        return jsonify({"code": 0, "msg": "success"})
    raise NotFound()


@app.route("/", methods=["POST"])
def callback_event_handler():
    logger.info("callback_event_handler")
    dict_data = json.loads(request.data)
    logger.info(dict_data)
    dict_data = decrypt_data(ENCRYPT_KEY, dict_data)
    logger.info(dict_data)
    callback_type = dict_data.get("type")
    if callback_type == "url_verification":
        logger.info("================ url_verification")
        if dict_data.get("token") != VERIFICATION_TOKEN:
            raise Exception("VERIFICATION_TOKEN is invalid")
        return jsonify({"challenge": dict_data.get("challenge")})
    else:
        event = Event(dict_data, VERIFICATION_TOKEN, ENCRYPT_KEY)
        # 异步执行处理
        executor.submit(plugin_manager.with_event, event)
    return jsonify({"code": 0, "msg": "success"})


if __name__ == "__main__":
    # init()
    app.run(host="0.0.0.0", port=2020, debug=True)
