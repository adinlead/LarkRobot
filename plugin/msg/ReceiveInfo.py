from enums import LarkEvent
from manager import PluginInfo, PluginManagerTools
from models import ReceiveMessage, UserInfo

PLUGIN_INFO = PluginInfo(plugin_name="ReceiveInfo",
                         plugin_event=LarkEvent.IM_MESSAGE_RECEIVE,
                         weight=1000)


def init(tools: PluginManagerTools):
    tools.ok()


def handler_event(receive_message: ReceiveMessage, tools: PluginManagerTools):
    if receive_message.group_id:
        head = "+++++++++++++++ [%s] +++++++++++++++" % receive_message.msg_id
        tools.logger.info(head)
        tools.logger.info("GROUP_ID         >>> %s" % receive_message.group_id)
        tools.logger.info("SENDER           >>> %s[%s][%s]" % (
            receive_message.sender_info.open_id, receive_message.sender_info.username,
            receive_message.sender_info.description))
        tools.logger.info("AT_ME            >>> %s" % receive_message.at_me())
        tools.logger.info("SENDER_TYPE      >>> %s" % receive_message.sender_type)
        tools.logger.info("MSG_TYPE         >>> %s" % receive_message.msg_type)
        tools.logger.info("IS_TEXT          >>> %s" % receive_message.is_text)
        if receive_message.is_text:
            tools.logger.info("TEXT_CONTENT     >>> %s" % receive_message.text_content)
        else:
            tools.logger.info("MSG_CONTENT      >>> %s" % receive_message.msg_content)
        if receive_message.mentions:
            for men in receive_message.mentions:
                if hasattr(men, "id") and hasattr(men, "name") and hasattr(men.id, "open_id"):
                    open_id = men.id.open_id
                    user_info: UserInfo = UserInfo.find_user_with_open_id(open_id, name=men.name)
                    if user_info:
                        tools.logger.info("\t mention    >>> %s[%s][%s]" % (
                            user_info.open_id, user_info.username, user_info.description))
                    else:
                        tools.logger.info("\t mention    >>> %s[%s]" % (open_id, men.name))
        tools.logger.info("+" * len(head))
