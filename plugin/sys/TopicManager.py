import time

import app
from enums import ReceiveType, PluginType
from manager import PluginInfo, PluginManagerTools, ConfigManger
from utils import singleton

PLUGIN_INFO: PluginInfo = PluginInfo(plugin_name="Topic管理", weight=1000, plugin_type=PluginType.UTILS)

_TOPIC_MANAGER_KEY = "topic_data"


def init(tools: PluginManagerTools):
    manager = TopicManager(tools.config_manger)
    setattr(tools, "topic_manager", manager)
    if not manager.CONFIG_MANGER.get(_TOPIC_MANAGER_KEY):
        manager.CONFIG_MANGER.put(_TOPIC_MANAGER_KEY, {"__init__": time.strftime("%Y-%m-%d %H:%M:%S")})


class TopicSubscriber:
    def __init__(self, open_id, receive_type: ReceiveType, user_name=""):
        self.open_id: str = open_id
        self.receive_type: ReceiveType = receive_type
        self.user_name: str = user_name

    def dump(self):
        return {
            "id": self.open_id,
            "type": self.receive_type.value,
            "name": self.user_name
        }


@singleton
class TopicManager(object):

    def __init__(self, config_manager: ConfigManger):
        if config_manager:
            self.CONFIG_MANGER = config_manager

    def _get_topic_data(self) -> dict:
        data = self.CONFIG_MANGER.get(_TOPIC_MANAGER_KEY)
        return self.CONFIG_MANGER.get(_TOPIC_MANAGER_KEY, {})

    def get_subscribers(self, topic_name: str) -> list:
        return self._get_topic_data().get(topic_name, [])

    def add_subscriber(self, topic_name: str, subscriber: TopicSubscriber):
        topic_data: dict = self._get_topic_data()
        subscribers: list = topic_data.get(topic_name, [])
        subscribers.append(subscriber)
        topic_data[topic_name] = subscribers
        TopicManager.CONFIG_MANGER.save()

    def topic_list(self):
        topic_data: dict = self._get_topic_data()
        return topic_data.keys()

    def has_topic(self, topic):
        if self._get_topic_data().get(topic):
            return True
        return False

    def create_topic(self, topic):
        self._get_topic_data()[topic] = []
        app.config_manger.save()
