# 1 Telegram 日常签到脚本

该脚本适用与青龙面板，可用于emby公益服日常签到(仅限tg按钮方式)

参考开源仓库：https://github.com/djksps1/tg-monitor

# 2 使用方法

## 2.1 青龙添加单文件

``` bash
ql raw https://raw.githubusercontent.com/EnterTang/telegram_daily_checkin/refs/heads/main/tg_daily_checkin.py
```

![image.png](https://piclist-1257076368.cos.ap-shanghai.myqcloud.com/picture/202412121646556.png)


## 2.2 添加依赖

``` bash
telethon
apscheduler
pytz
PySocks
```

![image.png](https://piclist-1257076368.cos.ap-shanghai.myqcloud.com/picture/202412121553129.png)

## 2.3 环境变量

```
TG_API_ID = # 从TG官网获取
TG_API_HASH = # 从TG官网获取
PROXY_HOST = # 当脚本内的use_proxy为True时需填写
PROXY_PORT = # 当脚本内的use_proxy为True时需填写
TG_BOT_IDS = "123,345" #多个bot_id用','隔开
TG_CHECKIN_COMMAND = "/start" #根据bot的指令修改，一般都是/start
```

![image.png](https://piclist-1257076368.cos.ap-shanghai.myqcloud.com/picture/202412121602429.png)

## 2.4 首次执行

首次执行需要在qinglong docker容器内执行

``` bash
docker exec -it qinglong bash
```

```bash
cd /ql/data/repo/EnterTang_telegram_daily_checkin_main

python3 tg_daily_checkin.py

cp session_name.session /ql/data/scripts/
```

根据提示输入tg 手机号和验证码，登录成功后当前路径下将生成`session_name.session`文件

![image.png](https://piclist-1257076368.cos.ap-shanghai.myqcloud.com/picture/202412121625047.png)

![image.png](https://piclist-1257076368.cos.ap-shanghai.myqcloud.com/picture/202412121604128.png)

