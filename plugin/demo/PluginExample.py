from enums import LarkEvent, PluginType
from manager import PluginInfo, PluginManagerTools
from models import ReceiveMessage, UserInfo, ApiRequest, RenderMessage

PLUGIN_INFO = PluginInfo(
    # 插件名称，建议控制在18个字符以内
    plugin_name="插件示例",
    # 要响应的飞书事件
    plugin_event=LarkEvent.IM_MESSAGE_RECEIVE,
    # API路径，如果你想要接受第三方数据，那么你可以在此提供API接口
    api_path="/plugin/example",
    # 插件类型
    plugin_type=PluginType.EVENT,
    weight=500
)


def init(tools: PluginManagerTools):
    tools.ok()


def handler_event(receive_message: ReceiveMessage, tools: PluginManagerTools):
    """
    事件处理方法
    :param receive_message: 入站信息
    :param tools: 插件工具
    :return:
    """
    if receive_message.is_text and "hello" in receive_message.text_content.lower() and receive_message.at_me():
        tools.api_client.reply_message(receive_message.msg_id, RenderMessage.text("Hi!"))
    pass


def handler_api(api_request: ApiRequest, tools: PluginManagerTools):
    """
    API处理方法
    :param api_request: API请求
    :param tools: 插件工具
    :return:
    """
    pass
