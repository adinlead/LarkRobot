import functools
import json
import utils
import os
import time
import traceback

from dotenv import find_dotenv, load_dotenv
from flask import request

from api import MessageApiClient
from enums import LarkEvent, PluginType
from models import Event, ReceiveMessage, ApiRequest

load_dotenv(find_dotenv())

logger = utils.get_logger()


class PluginInfo(object):
    """
    插件信息体
    """
    members = []

    def __init__(self,
                 plugin_name: str,
                 plugin_type: PluginType = PluginType.EVENT,
                 plugin_event: LarkEvent = None,
                 api_path: str = None,
                 weight=0):
        """
        初始化插件信息
        :param plugin_name: 插件名称，建议控制在18个字符以内
        :param plugin_type: 插件类型，详见 PluginType
        :param plugin_event: 注册事件
        :param api_path: API路径，建议控制在30个字符以内
        :param weight: 插件权重，仅针对事件型插件，权重越大越先调用
        """
        self.name = plugin_name
        self.event_type = plugin_event
        self.type = plugin_type
        self.weight = weight
        self.api_path = api_path

    def set_members(self, members):
        """
        设置成员方法与变量等信息(dir)
        :param members:
        :return:
        """
        self.members = members


class ConfigManger(object):
    """
    配置管理器
    注意！体积较大的数据建议自行创建文件进行管理！不要将比较大的数据写入配置中！
    """
    file_save_path = os.getenv("CONFIG_FILE_PATH")
    config = {}

    def __init__(self):
        logger.info("===========ConfigManger INIT===========")
        self._load()

    def _load(self):
        logger.info("self.file_save_path >>> %s" % self.file_save_path)
        with open(self.file_save_path, 'r') as r:
            self.config = json.loads(r.read() or "{}")

    def save(self):
        with open(self.file_save_path, 'w') as w:
            w.write(json.dumps(self.config, ensure_ascii=False, indent=2))
        self._load()

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def put(self, key: str, value):
        self.config[key] = value
        self.save()

    def remove(self, key: str):
        del self.config[key]
        self.save()


class PluginManagerTools(object):
    """
    插件工具
    此工具会在掉用插件时传入
    工具性插件可以在初始化时将自身实例化后加入该类中已供别的插件使用
    """

    def __init__(self, api_client: MessageApiClient, config_manger: ConfigManger, __logger=utils.get_logger()):
        """
        初始化插件工具
        :param api_client:      飞书API
        :param config_manger:   配置管理器
        :param __logger:        日志工具
        """
        self.api_client: MessageApiClient = api_client
        self.config_manger: ConfigManger = config_manger
        self.logger = __logger

    def ok(self):
        pass


class PluginManager(object):
    """
    插件管理器
    """
    EVENT_PLUGIN_DICT = dict()
    API_PLUGIN_DICT = dict()
    PLUGIN_UPDATE_AT = 0

    def __init__(self, api_client: MessageApiClient, config_manger: ConfigManger):
        """
        初始化插件管理器
        :param api_client: 飞书API
        :param config_manger: 配置管理器
        """
        self.tools = PluginManagerTools(api_client, config_manger)
        self._scanning_plugin()

    def _scanning_plugin(self):
        """
        扫描并注册插件
        :return:
        """
        now = int(time.time())
        if now - self.PLUGIN_UPDATE_AT > 60:
            for item in LarkEvent:
                self.EVENT_PLUGIN_DICT[item.value] = list()

            import pkgutil
            # 1. 先扫描MOD，进行排序
            mod_info_list = []
            for finder, name, ispck in pkgutil.walk_packages(["./plugin"]):
                loader = finder.find_module(name)  # 返回一个loader对象或者None。
                if loader:
                    mod = loader.load_module(name)  # 返回一个module对象或者raise an exception
                    mod_members = dir(mod)
                    if "PLUGIN_INFO" in mod_members:
                        plugin_info: PluginInfo = mod.PLUGIN_INFO
                        mod_info_list.append((plugin_info.weight, mod, mod_members))

            def mod_info_list_sort(o1, o2):
                if o1[0] > o2[0]:
                    return -1
                elif o1[1].PLUGIN_INFO.name < o2[1].PLUGIN_INFO.name:
                    return 1
                return 1

            # 2. 将MOD进行初始化并归类
            mod_info_list = sorted(mod_info_list, key=functools.cmp_to_key(mod_info_list_sort))
            for weight, mod, mod_members in mod_info_list:
                plugin_info: PluginInfo = mod.PLUGIN_INFO
                if plugin_info.type == PluginType.EVENT and "handler_event" in mod_members:
                    plugin_list: list = self.EVENT_PLUGIN_DICT.get(plugin_info.event_type.value)
                    if plugin_list is None:
                        logger.info("事件【%s】未被支持，事件处理插件【%s】已禁用" % (plugin_info.event_type.value, plugin_info.name))
                    else:
                        logger.info("【%s】发现事件处理插件【%s】" % (plugin_info.event_type.value, plugin_info.name))
                        plugin_info.set_members(mod_members)
                        if "init" in mod_members:
                            try:
                                logger.info("\t\t事件处理插件【%s】开始初始化" % plugin_info.name)
                                mod.init(self.tools)
                                logger.info("\t\t事件处理插件【%s】初始化成功" % plugin_info.name)
                            except BaseException as e:
                                logger.info("\t\t事件处理插件【%s】初始化失败，已被禁用" % plugin_info.name, e)
                                traceback.print_exc()
                                continue
                        plugin_list.append(mod)
                        logger.info("\t\t事件处理插件【%s】加载成功" % plugin_info.name)
                    if plugin_info.api_path and "handler_api" in mod_members:
                        self.API_PLUGIN_DICT[plugin_info.api_path] = mod
                        logger.info("\t\t事件处理插件【%s】已绑定至WEB路径【%s】" % (plugin_info.name, plugin_info.api_path))
                elif plugin_info.type == PluginType.UTILS:
                    logger.info("发现工具性插件【%s】" % plugin_info.name)
                    if "init" in mod_members:
                        try:
                            logger.info("\t\t工具性插件【%s】开始初始化" % plugin_info.name)
                            mod.init(self.tools)
                            logger.info("\t\t工具性插件【%s】初始化成功" % plugin_info.name)
                        except BaseException as e:
                            logger.info("\t\t工具性插件【%s】初始化失败，已被禁用" % plugin_info.name, e)
                            traceback.print_exc()
                            continue
                    logger.info("\t\t工具性插件【%s】加载完成" % plugin_info.name)
                elif plugin_info.type == PluginType.WEB and "handler_api" in mod_members:
                    logger.info("发现API插件【%s】" % plugin_info.name)
                    if "init" in mod_members:
                        try:
                            logger.info("\t\tAPI插件【%s】开始初始化" % plugin_info.name)
                            mod.init(self.tools)
                            logger.info("\t\tAPI插件【%s】初始化成功" % plugin_info.name)
                        except BaseException as e:
                            logger.info("\t\tAPI插件【%s】初始化失败，已被禁用" % plugin_info.name, e)
                            traceback.print_exc()
                            continue
                    self.API_PLUGIN_DICT[plugin_info.api_path] = mod
                    logger.info("\t\tAPI插件【%s】已绑定至WEB路径【%s】" % (plugin_info.name, plugin_info.api_path))

            self.PLUGIN_UPDATE_AT = now

            logger.info("插件加载完成！")
            for key in self.EVENT_PLUGIN_DICT:
                logger.info("事件【%s】插件：" % key)
                logger.info("\t\t| weight |    plugin name    |")
                for mod in self.EVENT_PLUGIN_DICT[key]:
                    mod_info: PluginInfo = mod.PLUGIN_INFO
                    logger.info("\t\t| %s| %s|" % (str(mod_info.weight).ljust(7), mod_info.name.center(18)))
            logger.info("API插件：")
            logger.info("\t\t|           api path           |    plugin name    |")
            for path in self.API_PLUGIN_DICT:
                mod_info: PluginInfo = self.API_PLUGIN_DICT[path].PLUGIN_INFO
                logger.info("\t\t|%s| %s|" % (path.center(30), mod_info.name.center(18)))

    def with_event(self, event: Event):
        for key in self.EVENT_PLUGIN_DICT:
            if key == event.event_type():
                if key == LarkEvent.IM_MESSAGE_RECEIVE.value:
                    event = ReceiveMessage(event)
                for mod in self.EVENT_PLUGIN_DICT.get(key):
                    try:
                        if mod.handler_event(event, self.tools):
                            return
                    except BaseException as e:
                        logger.info(mod.PLUGIN_INFO)
                        logger.info("插件【%s】发生错误:" % mod.PLUGIN_INFO.name)
                        traceback.print_exc()

    def with_api(self, api_request: ApiRequest):
        mod = self.API_PLUGIN_DICT[api_request.path]
        if mod:
            try:
                mod.handler_api(api_request, self.tools)
            except BaseException as e:
                logger.info("插件【%s】发生错误:" % mod.PLUGIN_INFO.name)
                traceback.print_exc()

    def config_path(self, req: request) -> ApiRequest:
        mod = self.API_PLUGIN_DICT[request.path]
        if mod:
            return ApiRequest(req)
