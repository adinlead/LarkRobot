from enums import LarkEvent
from manager import PluginInfo, PluginManagerTools
from models import ReceiveMessage

PLUGIN_INFO: PluginInfo = PluginInfo(plugin_name="Command处理",
                                     plugin_event=LarkEvent.IM_MESSAGE_RECEIVE,
                                     plugin_filter={},
                                     weight=0)


def init(tools: PluginManagerTools):
    tools.ok()


def handler_event(receive_message: ReceiveMessage, tools: PluginManagerTools):
    pass