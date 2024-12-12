import sys
import socks
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, MessageMediaDocument
import asyncio
import logging
from datetime import datetime
from telethon.errors import SessionPasswordNeededError
import smtplib
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import pytz
import re
import random
import shutil
import base64

# 从环境变量读取配置
# api_id = os.environ.get("TG_API_ID")
# api_hash = os.environ.get("TG_API_HASH")

# use_proxy = False
# proxy_host = os.environ.get("PROXY_HOST")
# proxy_type = socks.HTTP  # 如果需要可配置，可以使用 getattr(socks, os.environ.get("PROXY_TYPE", "HTTP"))
# proxy_port = int(os.environ.get("PROXY_PORT", "7890"))  # 提供默认值并转换为整数
# proxy = (proxy_type, proxy_host, proxy_port)
api_id = None
api_hash = None
botids = None
daily_checkin_str = None
use_proxy = False
proxy_host = None
proxy_type = socks.HTTP
proxy_port = None
proxy = None

BUTTON_KEYWORD_CONFIG = {}

# # botids 必须从环境变量读取，daily_checkin_str 保留默认值
# botids = [int(id.strip()) for id in os.environ["TG_BOT_IDS"].split(",")]
# daily_checkin_str = os.environ.get("TG_CHECKIN_COMMAND", "/start")


BUTTON_KEYWORD_CONFIG["签到"] = {
    'chats': botids
}

processed_messages = set()

def setup_logger():
    """配置日志"""
    logger = logging.getLogger('telegram_monitor')
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler('telegram_monitor.log', encoding='utf-8')
    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = setup_logger()


# === 异步输入函数 ===
async def ainput(prompt: str = '') -> str:
    """自定义异步输入函数，确保正确处理编码"""
    loop = asyncio.get_event_loop()
    print(prompt, end='', flush=True)
    return (await loop.run_in_executor(None, sys.stdin.readline)).rstrip('\n')

# === Telegram登录处理 ===
async def telegram_login(client):
    """处理Telegram登录流程"""
    logger.info('开始Telegram登录流程...')

    phone = (await ainput('请输入您的Telegram手机号 (格式如: +8613800138000): ')).strip()

    try:
        await client.send_code_request(phone)
        logger.info('验证码已发送到您的Telegram账号')

        code = (await ainput('请输入您收到的验证码: ')).strip()

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            logger.info('检测到两步验证，需要输入密码')
            password = (await ainput('请输入您的两步验证密码: ')).strip()
            await client.sign_in(password=password)

        logger.info('Telegram登录成功！')

    except Exception as e:
        error_message = repr(e)
        logger.error(f'登录过程中发生错误：{error_message}')
        raise


def match_user(sender, user_set):

    sender_id = sender.id
    sender_username = sender.username.lower() if sender.username else None
    sender_first_name = sender.first_name if sender.first_name else ''
    sender_last_name = sender.last_name if sender.last_name else ''
    sender_full_name = f"{sender_first_name} {sender_last_name}".strip()

    logger.info(f"匹配用户：sender_id={sender_id}, sender_username={sender_username}, sender_full_name={sender_full_name}, user_set={user_set}")

    return sender_id in user_set

async def message_handler(event):
    global monitor_active, own_user_id, processed_messages

    if not monitor_active:
        return
    # 增加消息和按钮的空值检查
    if not event or not event.message:
        return
    
    chat_id = event.chat_id
    message_id = event.message.id
    message_text = event.raw_text or ''
    message_text_lower = message_text.lower().strip()

    if (chat_id, message_id) in processed_messages:
        return
    processed_messages.add((chat_id, message_id))

    try:
        sender = await event.get_sender()
        sender_id = sender.id if sender else None

        if sender_id == own_user_id:
            return
        # 检查按钮关键词
        if event.message.buttons:
            for b_keyword, b_config in BUTTON_KEYWORD_CONFIG.items():
                if chat_id in b_config['chats']:
                    if True:
                        for row_i, row in enumerate(event.message.buttons):
                            for col_i, button in enumerate(row):
                                if b_keyword in button.text.lower():
                                    await event.message.click(row_i, col_i)
                                    logger.info(f"已点击对话 {chat_id} 中包含按钮关键词 '{b_keyword}' 的按钮: {button.text}")
                                    return

    except Exception as e:
        error_message = repr(e)
        logger.error(f'处理消息时发生错误：{error_message}')
        await client.disconnect()
        scheduler.shutdown()
        logger.info('程序已退出')


async def send_scheduled_message():
    """定时发送消息到指定的bot"""
    try:
        for bot_id in botids:
            await client.send_message(bot_id, daily_checkin_str)
            logger.info(f"已发送定时消息到 bot_id: {bot_id}")
    except Exception as e:
        logger.error(f"发送定时消息时发生错误：{e}")


# === 主程序 ===
async def main():
    global monitor_active, client, scheduler, own_user_id, api_id, api_hash, botids, daily_checkin_str

    logger.info('启动Telegram监控程序...')
    
    # 检查 session 文件是否存在
    session_file = 'session_name.session'
    if os.path.exists(session_file):
        logger.info('检测到已存在的 session 文件，开始读取环境变量...')
        # 读取环境变量
        api_id = os.environ.get("TG_API_ID")
        api_hash = os.environ.get("TG_API_HASH")
        try:
            botids = [int(id.strip()) for id in os.environ["TG_BOT_IDS"].split(",")]
        except KeyError:
            logger.error('未找到必需的环境变量 TG_BOT_IDS')
            return
        daily_checkin_str = os.environ.get("TG_CHECKIN_COMMAND", "/start")
    else:
        logger.info('未检测到 session 文件，进入登录流程...')
        # 登录流程需要的基本配置
        api_id = input('请输入 API ID: ').strip()
        api_hash = input('请输入 API Hash: ').strip()
        botids = [int(id.strip()) for id in input('请输入 Bot IDs (用逗号分隔): ').strip().split(",")]
        daily_checkin_str = "/start"  # 使用默认值

    if use_proxy:
        client = TelegramClient('session_name', api_id, api_hash, proxy=proxy)
    else:
        client = TelegramClient('session_name', api_id, api_hash)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await telegram_login(client)
        me = await client.get_me()
        own_user_id = me.id

        # 添加消息处理器来处理按钮事件
        client.add_event_handler(message_handler, events.NewMessage())

        # 立即发送消息
        logger.info('开始发送定时消息...')
        await send_scheduled_message()
        logger.info('定时消息发送完成')

        # 等待5分钟后退出
        logger.info('程序将在5分钟后退出...')
        await asyncio.sleep(300)  # 300秒 = 5分钟
        
        logger.info('5分钟时间到，程序准备退出...')

    except Exception as e:
        error_message = repr(e)
        logger.error(f'运行时发生错误：{error_message}')
    finally:
        await client.disconnect()
        scheduler.shutdown()
        logger.info('程序已退出')

if __name__ == '__main__':
    monitor_active = True
    client = None
    scheduler = AsyncIOScheduler()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('程序被用户中断')
    except Exception as e:
        error_message = repr(e)
        logger.error(f'程序发生错误：{error_message}')
        sys.exit(1)  # 确保程序真正退出