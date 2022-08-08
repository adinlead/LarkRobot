from enum import Enum


class PluginType(Enum):
    EVENT = "event"
    UTILS = "utils"
    WEB = "web"


class LarkEvent(Enum):
    IM_MESSAGE_RECEIVE = "im.message.receive_v1"
    IM_MESSAGE_READ = "im.message.message_read_v1"


class ReceiveType(Enum):
    USER = "user"
    GROUP = "group"
