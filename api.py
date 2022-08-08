import os
import utils
import time

import requests

from models import RenderMessage

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")

logger = utils.get_logger()

# const
TENANT_ACCESS_TOKEN_URI = "%(host)s/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URI = "%(host)s/open-apis/im/v1/messages?receive_id_type=%(receive_id_type)s"
REPLY_MESSAGE_URI = "%(host)s/open-apis/im/v1/messages/%(messages_id)s/reply"
USER_INFO_URI = "%(host)s/open-apis/contact/v3/users/%(open_id)s"


class MessageApiClient(object):
    def __init__(self, app_id, app_secret, lark_host):
        self._app_id = app_id
        self._app_secret = app_secret
        self._lark_host = lark_host
        self._tenant_access_token = ""
        self._tenant_access_token_time = 0

    @property
    def tenant_access_token(self):
        return self._tenant_access_token

    def send_message_with_open_id(self, msg: RenderMessage):
        self._send_message("open_id", msg)

    def send_message_with_group_id(self, msg: RenderMessage):
        self._send_message("chat_id", msg)

    def reply_message(self, messages_id: str, msg: RenderMessage):
        url = REPLY_MESSAGE_URI % {
            "host": self._lark_host,
            "messages_id": messages_id
        }
        self._post_json(url, msg.json())

    def _send_message(self, receive_id_type, msg: RenderMessage):
        url = MESSAGE_URI % {
            "host": self._lark_host,
            "receive_id_type": receive_id_type
        }
        self._post_json(url, msg.json())

    def _authorize_tenant_access_token(self):
        now = int(time.time())
        if now - self._tenant_access_token_time > 1200:
            url = TENANT_ACCESS_TOKEN_URI % {"host": self._lark_host}
            req_body = {"app_id": self._app_id, "app_secret": self._app_secret}
            response = requests.post(url, req_body)
            MessageApiClient._check_error_response(response)
            self._tenant_access_token = response.json().get("tenant_access_token")
            self._tenant_access_token_time = now

    @staticmethod
    def _check_error_response(resp: requests.models.Response):
        logger.info(type(resp))
        # check if the response contains error information
        if resp.status_code != 200:
            logger.info("status_code != 200")
            if hasattr(resp, 'msg_content'):
                logger.info(resp.json())
            # resp.raise_for_status()
        response_dict = resp.json()
        code = response_dict.get("code", -1)
        if code != 0:
            logger.error(response_dict)
            raise LarkException(code=code, msg=response_dict.get("msg"))

    def get_user_info_with_open_id(self, open_id: str):
        url = USER_INFO_URI % {
            "host": self._lark_host,
            "open_id": open_id
        }
        body = {
            "user_id_type": "open_id",
            "department_id_type": "open_department_id"
        }
        return self._get_json(url, body)

    def _get_json(self, url, req_body):
        self._authorize_tenant_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.tenant_access_token,
        }
        logger.info("==========[_get_json]==========")
        logger.info(url)
        logger.info(headers)
        logger.info(req_body)
        logger.info("===============================")
        response = requests.get(url=url, headers=headers, json=req_body)
        self._check_error_response(response)
        return response.json()

    def _post_json(self, url, req_body):
        self._authorize_tenant_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.tenant_access_token,
        }
        logger.info("==========[_post_json]==========")
        logger.info(url)
        logger.info(headers)
        logger.info(req_body)
        logger.info("================================")
        response = requests.post(url=url, headers=headers, json=req_body)
        self._check_error_response(response)
        return response.json()


class LarkException(Exception):
    def __init__(self, code=0, msg=None):
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return "{}:{}".format(self.code, self.msg)

    __repr__ = __str__
