#!/usr/bin/env python3.8
import functools
import json
import utils
import os
import time
import traceback

from dotenv import find_dotenv, load_dotenv
from flask import request

from api import MessageApiClient
from enums import LarkEvent, PluginFunction
from models import Event, ReceiveMessage, WebRequest

load_dotenv(find_dotenv())

logger = utils.get_logger()


class PluginInfo(object):
    members = []

    def __init__(self,
                 plugin_name: str,
                 plugin_event: LarkEvent = None,
                 plugin_filter: dict = None,
                 api_path: str = None,
                 function: PluginFunction = PluginFunction.EVENT,
                 weight=0):
        self.name = plugin_name
        self.event_type = plugin_event
        self.filter = plugin_filter
        self.function = function
        self.weight = weight
        self.api_path = api_path

    def set_members(self, members):
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
    def __init__(self, api_client: MessageApiClient, config_manger: ConfigManger):
        self.api_client: MessageApiClient = api_client
        self.config_manger: ConfigManger = config_manger
        self.logger = utils.get_logger()

    def ok(self):
        pass


class PluginManager(object):
    """
    插件管理器
    """
    EVENT_PLUGIN_DICT = dict()
    WEB_PLUGIN_DICT = dict()
    PLUGIN_UPDATE_AT = 0

    def __init__(self, api_client: MessageApiClient, config_manger: ConfigManger):
        self.tools = PluginManagerTools(api_client, config_manger)
        self._update_plugin_dict()

    def test_model(self, mod):
        pass

    def _update_plugin_dict(self):
        now = int(time.time())
        if now - self.PLUGIN_UPDATE_AT > 60:
            for item in LarkEvent:
                self.EVENT_PLUGIN_DICT[item.value] = list()

            import pkgutil
            # 1. 先扫描MOD，进行排序
            # 2. 将MOD进行初始化并归类
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

            mod_info_list = sorted(mod_info_list, key=functools.cmp_to_key(mod_info_list_sort))
            for weight, mod, mod_members in mod_info_list:
                plugin_info: PluginInfo = mod.PLUGIN_INFO
                if plugin_info.function == PluginFunction.EVENT and "handler_event" in mod_members:
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
                    if plugin_info.api_path and "handler_web" in mod_members:
                        self.WEB_PLUGIN_DICT[plugin_info.api_path] = mod
                        logger.info("\t\t事件处理插件【%s】已绑定至WEB路径【%s】" % (plugin_info.name, plugin_info.api_path))
                elif plugin_info.function == PluginFunction.UTILS:
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
                elif plugin_info.function == PluginFunction.WEB and "handler_web" in mod_members:
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
                    self.WEB_PLUGIN_DICT[plugin_info.api_path] = mod
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
            for path in self.WEB_PLUGIN_DICT:
                mod_info: PluginInfo = self.WEB_PLUGIN_DICT[path].PLUGIN_INFO
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

    def with_web(self, web_request: WebRequest):
        mod = self.WEB_PLUGIN_DICT[web_request.path]
        if mod:
            try:
                mod.handler_web(web_request, self.tools)
            except BaseException as e:
                logger.info("插件【%s】发生错误:" % mod.PLUGIN_INFO.name)
                traceback.print_exc()

    def config_path(self, req: request) -> WebRequest:
        mod = self.WEB_PLUGIN_DICT[request.path]
        if mod:
            return WebRequest(req)
