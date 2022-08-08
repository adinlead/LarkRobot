# LarkRobot

一个插件式的飞书机器人

**目录结构**

```text
root:
  - conf/               存放配置文件
    - db.json               配置数据存储文件
  - log/                存放运行时日志
  - plugin/             插件文件夹
    - msg/                  消息处理插件
      - ReceiveInfo.py          入站信息插件，用于打印入站信息
    - sys/                  系统级别插件
      - CommandHandler.py       命令处理插件，用于处理机器人接收到的命令（暂未实现）
      - TopicManager.py         订阅主题管理插件，用于分类存放订阅主题与订阅用户或群组
  - api.py              飞书API接口
  - app.py              flask启动入口，也是API服务器
  - enums.py            枚举类集合，公用或者公共的枚举类应当存于此处
  - manager.py          事件或者数据处理类
  - models.py           公用的模型对象
  - test.py             测试文件，不参与业务
  - utils.py            公用的工具类或方法
  - run.sh              启动脚本
  - update2server.sh    此脚本用于将代码同步到服务器
  - .env                环境参数文件，存放飞书或者其他组件模块的环境参数
```
**注意！.env与update2server.sh这两个文件因为要脱敏所以已经删除！源文件内容如下：**  

.env
```properties
APP_ID=cli_xxxxxxxxxxxxxxxx
APP_SECRET=0123456789xxxxxxxxxxxxxxxxxxxxxx
VERIFICATION_TOKEN=0123456789xxxxxxxxxxxxxxxxxxxxxx
ENCRYPT_KEY=0123456789xxxxxxxxxxxxxxxxxxxxxx
LARK_HOST=https://open.feishu.cn
# 数据文件存放位置
CONFIG_FILE_PATH=./conf/db.json
# 机器人OPEN_ID
SELF_OPEN_ID=ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```  

update2server.sh
```shell
rsync -av -e ssh \
  --exclude='.env' \
  --exclude='log/*' \
  --exclude='.idea' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='update2server.sh' \
  --exclude='*.log' \
  --exclude='be.*' \
  ./ ubuntu@18.163.77.194:~/fsbot/
```
**插件示例与说明**

```python
```
