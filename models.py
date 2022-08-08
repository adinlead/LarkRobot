import abc
import hashlib
import json
import os
import time
from enum import Enum

from flask import request

from utils import dict_2_obj

_USER_INFO_DICT = {}
_SELF_OPEN_ID = os.getenv("SELF_OPEN_ID")


class UserInfo(object):
    def __init__(self, open_id, union_id, username, description):
        super().__init__()
        self.open_id = open_id
        self.union_id = union_id
        self.username = username
        self.description = ""
        if description:
            self.description = description
        self.createAt = int(time.time())

    def string(self):
        return (json.dumps({
            "username": self.username,
            "description": self.description,
            "open_id": self.open_id
        }, ensure_ascii=False))

    @staticmethod
    def find_user_with_open_id(open_id, union_id: str = None, name: str = None):
        user_info = _USER_INFO_DICT.get(open_id)
        if not user_info or int(time.time()) - user_info.createAt > 3600:
            from app import message_api_client
            try:
                user_info_data = message_api_client.get_user_info_with_open_id(open_id)
                if user_info_data["data"] and user_info_data["data"]["user"]:
                    data_user = user_info_data["data"]["user"]
                    user_info = UserInfo(open_id,
                                         data_user["union_id"],
                                         data_user["name"],
                                         data_user["description"])
                    _USER_INFO_DICT[open_id] = user_info
            except BaseException as e:
                if name or union_id:
                    user_info = UserInfo(open_id, union_id, name, "")
                    _USER_INFO_DICT[open_id] = user_info

        return user_info


class Event(object):
    callback_handler = None

    # event base
    def __init__(self, dict_data, token, encrypt_key):
        # event check and init
        header = dict_data.get("header")
        event = dict_data.get("event")
        if header is None or event is None:
            raise InvalidEventException("request is not callback event(v2)")
        self.header = dict_2_obj(header)
        self.event = dict_2_obj(event)
        self._validate(token, encrypt_key)
        self._event_type = self.header.event_type

    def _validate(self, token, encrypt_key):
        if self.header.token != token:
            raise InvalidEventException("invalid token")
        timestamp = request.headers.get("X-Lark-Request-Timestamp")
        nonce = request.headers.get("X-Lark-Request-Nonce")
        signature = request.headers.get("X-Lark-Signature")
        body = request.data
        bytes_b1 = (timestamp + nonce + encrypt_key).encode("utf-8")
        bytes_b = bytes_b1 + body
        h = hashlib.sha256(bytes_b)
        if signature != h.hexdigest():
            raise InvalidEventException("invalid signature in event")

    def event_type(self):
        return self._event_type


class ReceiveMessage(object):
    """
    请求信息封装
    """

    def __init__(self, event: Event):
        self.event = event
        self.message = event.event.message
        self.msg_type = event.event.message.chat_type
        self.msg_id = event.event.message.message_id
        self.msg_content = event.event.message.content
        self.is_text = False
        try:
            text_content = json.loads(self.msg_content)
            if text_content.get("text"):
                self.text_content = text_content.get("text")
                self.is_text = True
        except BaseException as e:
            pass

        self.mentions = None
        if hasattr(event.event.message, "mentions"):
            self.mentions = event.event.message.mentions

        self.group_id = event.event.message.chat_id

        self.sender_open_id = event.event.sender.sender_id.open_id
        self.sender_id = event.event.sender.sender_id
        self.sender_type = event.event.sender.sender_type
        self.sender_info = UserInfo.find_user_with_open_id(self.sender_open_id,
                                                           name=self.sender_id.name if self.sender_id else None)

    def at_me(self) -> bool:
        if self.mentions:
            for m in self.mentions:
                if hasattr(m, "id") and hasattr(m.id, "open_id") and m.id.open_id == _SELF_OPEN_ID:
                    return True
        return False


class WebRequest(object):
    def __init__(self, req: request):
        self.data: bytes = req.data
        self.path: str = req.path
        self.args: dict = req.args.to_dict()
        self.form: dict = req.form.to_dict()
        self.params: dict = {}
        self.params.update(self.form)
        self.params.update(self.args)
        self.json: dict = {}
        self.is_json: bool = False
        if req.is_json:
            self.is_json = True
            self.json = request.get_json()
        elif self.data and chr(self.data[0]) in ['{', '[']:
            self.is_json = True
            self.json = json.loads(self.data)
        self.method: str = req.method
        self.request = req

    def is_post(self):
        return self.method.upper() == "POST"


class _RenderMessageType(Enum):
    TEXT = "text"
    POST = "post"


class RenderMessage:
    """
    消息体
    """

    def __init__(self, msg_type: _RenderMessageType, content="", receive_id=""):
        self.receive_id = receive_id
        self.msg_type = msg_type.value
        self.content = content

    @abc.abstractmethod
    def set_open_id(self, open_id):
        self.receive_id = open_id

    @staticmethod
    def text(content: str):
        return RenderText(content)

    @staticmethod
    def post():
        return RenderPost()

    @abc.abstractmethod
    def json(self):
        return {
            "receive_id": self.receive_id,
            "msg_type": self.msg_type
        }


class RenderText(RenderMessage):
    def __init__(self, content, receive_id=""):
        super().__init__(_RenderMessageType.TEXT, receive_id=receive_id)
        self.content = content

    def at_user(self, user_id, user_name):
        self.content = "<at user_id=\"%(user_id)s\">%(user_name)s</at>%(content)s" % {
            "user_id": user_id,
            "user_name": user_name,
            "content": self.content
        }

    def at_all_user(self):
        self.content = "<at user_id=\"all\">所有人</at>%s" % self.content

    def json(self):
        content = {"text": self.content}
        return {
            "receive_id": self.receive_id,
            "msg_type": self.msg_type,
            "content": json.dumps(content, ensure_ascii=False)
        }

    def set_open_id(self, open_id):
        self.receive_id = open_id


class RenderPost(RenderMessage):
    def __init__(self, receive_id=""):
        super().__init__(_RenderMessageType.POST, receive_id=receive_id)
        self.zh_cn = {
            "title": "",
            "content": []
        }

    def title(self, title):
        """
        设置标题
        :param title:
        :return:
        """
        self.zh_cn["title"] = title

    def line(self, *items: dict, index: int = 0):
        """
        添加/修改行
        :param items:
        :param index:
        :return:
        """
        items = list(items)
        if index > 0:
            idx = index - 1
            if len(self.zh_cn["content"]) < idx:
                raise IndexError("No line rows is: %s" % index)
            elif len(self.zh_cn["content"]) == idx:
                self.zh_cn["content"].append(items)
                return index
            else:
                self.zh_cn["content"][idx] = items
                return index
        else:
            self.zh_cn["content"].append(items)
            return len(self.zh_cn["content"])

    def json(self):
        self.content = {"zh_cn": self.zh_cn}
        return {
            "receive_id": self.receive_id,
            "msg_type": self.msg_type,
            "content": json.dumps(self.content, ensure_ascii=False)
        }

    def set_open_id(self, open_id):
        self.receive_id = open_id

    @staticmethod
    def create_text(text) -> dict:
        return {
            "tag": "text",
            "text": text
        }

    @staticmethod
    def create_link(link: str, text: str = None) -> dict:
        return {
            "tag": "a",
            "href": link,
            "text": text or link
        }

    @staticmethod
    def at_user(user_id, user_name) -> dict:
        return {
            "tag": "at",
            "user_id": user_id,
            "user_name": user_name
        }


class InvalidEventException(Exception):
    def __init__(self, error_info):
        self.error_info = error_info

    def __str__(self) -> str:
        return "Invalid event: {}".format(self.error_info)

    __repr__ = __str__
