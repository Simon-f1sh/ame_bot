import random
import re
import os
import sys
import shelve
import psutil
import platform

from PIL import Image
from nonebot import on_command, on_message, on_notice, require, get_driver, on_regex
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Message, Event, Bot
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from random import randint
import asyncio

from src.libraries.image import image_to_base64, path, draw_text, get_jlpx, text_to_image
from src.libraries.tool import hash

import time
from collections import defaultdict

scheduler = require("nonebot_plugin_apscheduler").scheduler

help = on_command('help')


@help.handle()
async def _(bot: Bot, event: Event, state: T_State):
    v = str(event.get_message()).strip()
    help_text: dict = get_driver().config.help_text
    if v == "":
        help_str = '\n'.join([f'help {key}\t{help_text[key][0]}' for key in help_text])
        await help.finish(help_str)
    else:
        await help.finish(Message([{
            "type": "image",
            "data": {
                "file": f"base64://{str(image_to_base64(text_to_image(help_text[v][1])), encoding='utf-8')}"
            }
        }]))


jrrp = on_command('jrrp')


@jrrp.handle()
async def _(bot: Bot, event: Event, state: dict):
    qq = int(event.get_user_id())
    h = hash(qq)
    rp = h % 100
    await jrrp.finish("【%s】今天的人品值为：%d" % (event.sender.nickname, rp))


async def _group_poke(bot: Bot, event: Event, state: dict) -> bool:
    value = (event.notice_type == "notify" and event.sub_type == "poke" and event.target_id == int(bot.self_id))
    return value


poke = on_notice(rule=_group_poke, priority=10, block=True)


async def invoke_poke(group_id, user_id) -> str:
    db = get_driver().config.db
    ret = "default"
    ts = int(time.time())
    c = await db.cursor()
    await c.execute(f"select * from group_poke_table where group_id={group_id}")
    data = await c.fetchone()
    if data is None:
        await c.execute(f'insert into group_poke_table values ({group_id}, {ts}, 1, 0, "default")')
    else:
        t2 = ts
        if data[3] == 1:
            return "disabled"
        if data[4].startswith("limited"):
            duration = int(data[4][7:])
            if ts - duration < data[1]:
                ret = "limited"
                t2 = data[1]
        await c.execute(
            f'update group_poke_table set last_trigger_time={t2}, triggered={data[2] + 1} where group_id={group_id}')
    await c.execute(f"select * from user_poke_table where group_id={group_id} and user_id={user_id}")
    data2 = await c.fetchone()
    if data2 is None:
        await c.execute(f'insert into user_poke_table values ({user_id}, {group_id}, 1)')
    else:
        await c.execute(
            f'update user_poke_table set triggered={data2[2] + 1} where user_id={user_id} and group_id={group_id}')
    await db.commit()
    return ret


@poke.handle()
async def _(bot: Bot, event: Event, state: T_State):
    v = "default"
    group_id = event.__getattribute__('group_id')
    sender_id = event.sender_id
    if group_id is None:
        event.__delattr__('group_id')
    else:
        poke_dict = shelve.open('src/static/poke.db', writeback=True)
        if str(group_id) not in poke_dict:
            poke_dict[str(group_id)] = {}
        if str(sender_id) not in poke_dict[str(group_id)]:
            poke_dict[str(group_id)][str(sender_id)] = 0
        poke_dict[str(group_id)][str(sender_id)] += 1
        poke_dict.close()
        v = await invoke_poke(event.group_id, event.sender_id)
        if v == "disabled":
            await poke.finish()
            return
    r = randint(1, 20)
    if v == "limited":
        await poke.send(Message([{
            "type": "poke",
            "data": {
                "qq": f"{event.sender_id}"
            }
        }]))
    elif r == 1:
        await poke.send(Message('妈你戳'))
    elif r == 2:
        url = await get_jlpx('戳', '你妈', '闲着没事干')
        await poke.send(Message([{
            "type": "image",
            "data": {
                "file": url
            }
        }]))
    elif r == 3:
        img_p = Image.open(path)
        draw_text(img_p, '戳你妈', 0)
        draw_text(img_p, '有尝试过玩Cytus II吗', 400)
        await poke.send(Message([{
            "type": "image",
            "data": {
                "file": f"base64://{str(image_to_base64(img_p), encoding='utf-8')}"
            }
        }]))
    elif r == 4:
        await poke.send(Message('15级？'))
    elif 4 < r <= 8:
        await poke.send(Message([{
            "type": "image",
            "data": {
                "file": "file:///" + os.path.abspath("src/static/mai/poke/meimei" + str(r - 4) + ".gif")
            }
        }]))
    elif 8 < r <= 20:
        await poke.send(Message([{
            "type": "image",
            "data": {
                "file": "file:///" + os.path.abspath("src/static/mai/poke/meimei" + str(r - 8) + ".jpg")
            }
        }]))
    # elif r <= 12:
    #     await poke.send(Message([{
    #         "type": "image",
    #         "data": {
    #             "file": f"https://www.diving-fish.com/images/poke/{r - 7}.jpg",
    #         }
    #     }]))
    # elif r == 1:
    #     await poke.send(Message('戳你妈'))
    else:
        await poke.send(Message([{
            "type": "poke",
            "data": {
                "qq": f"{event.sender_id}"
            }
        }]))


async def send_poke_stat(group_id: int, bot: Bot):
    poke_dict = shelve.open('src/static/poke.db')
    if str(group_id) not in poke_dict:
        poke_dict.close()
        return
    else:
        group_stat = poke_dict[str(group_id)]
        poke_dict.close()
        sorted_dict = {k: v for k, v in sorted(group_stat.items(), key=lambda item: item[1], reverse=True)}
        index = 0
        data = []
        for k in sorted_dict:
            data.append((k, sorted_dict[k]))
            index += 1
            if index == 3:
                break
        await bot.send_msg(group_id=group_id, message="接下来公布一下我上次失忆以来，本群最闲着没事干玩戳一戳的人")
        await asyncio.sleep(1)
        if len(data) == 3:
            await bot.send_msg(group_id=group_id, message=Message([
                {"type": "text", "data": {"text": "第三名，"}},
                {"type": "at", "data": {"qq": f"{data[2][0]}"}},
                {"type": "text", "data": {"text": f"，一共戳了我{data[2][1]}次，这就算了"}},
            ]))
            await asyncio.sleep(1)
        if len(data) >= 2:
            await bot.send_msg(group_id=group_id, message=Message([
                {"type": "text", "data": {"text": "第二名，"}},
                {"type": "at", "data": {"qq": f"{data[1][0]}"}},
                {"type": "text", "data": {"text": f"，一共戳了我{data[1][1]}次，也太几把闲得慌了，建议多戳戳自己肚皮"}},
            ]))
            await asyncio.sleep(1)
        await bot.send_msg(group_id=group_id, message=Message([
            {"type": "text", "data": {"text": "最JB离谱的第一名，"}},
            {"type": "at", "data": {"qq": f"{data[0][0]}"}},
            {"type": "text", "data": {"text": f"，一共戳了我{data[0][1]}次，就那么喜欢听我骂你吗"}},
        ]))


poke_stat = on_command("本群戳一戳情况")


@poke_stat.handle()
async def _(bot: Bot, event: Event, state: T_State):
    group_id = event.group_id
    await send_poke_stat(group_id, bot)


poke_setting = on_command("戳一戳设置")


@poke_setting.handle()
async def _(bot: Bot, event: Event, state: T_State):
    db = get_driver().config.db
    group_members = await bot.get_group_member_list(group_id=event.group_id)
    for m in group_members:
        if m['user_id'] == event.user_id:
            break
    su = get_driver().config.superusers
    if m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in su:
        await poke_setting.finish("只有管理员可以设置戳一戳")
        return
    argv = str(event.get_message()).strip().split(' ')
    try:
        if argv[0] == "默认":
            c = await db.cursor()
            await c.execute(
                f'update group_poke_table set disabled=0, strategy="default" where group_id={event.group_id}')
        elif argv[0] == "限制":
            c = await db.cursor()
            await c.execute(
                f'update group_poke_table set disabled=0, strategy="limited{int(argv[1])}" where group_id={event.group_id}')
        elif argv[0] == "禁用":
            c = await db.cursor()
            await c.execute(
                f'update group_poke_table set disabled=1 where group_id={event.group_id}')
        else:
            raise ValueError
        await poke_setting.send("设置成功")
        await db.commit()
    except (IndexError, ValueError):
        await poke_setting.finish(
            "命令格式：\n戳一戳设置 默认   将启用默认的戳一戳设定\n戳一戳设置 限制 <秒>   在戳完一次bot的指定时间内，调用戳一戳只会让bot反过来戳你\n戳一戳设置 禁用   将禁用戳一戳的相关功能")
    pass


random_person = on_regex("随个([男女]?)人", priority=1)


@random_person.handle()
async def _(bot: Bot, event: Event, state: T_State):
    try:
        gid = event.group_id
        glst = await bot.get_group_member_list(group_id=gid, self_id=int(bot.self_id))
        v = re.match("随个([男女]?)人", str(event.get_message())).group(1)
        if v == '男':
            for member in glst[:]:
                if member['sex'] != 'male':
                    glst.remove(member)
        elif v == '女':
            for member in glst[:]:
                if member['sex'] != 'female':
                    glst.remove(member)
        m = random.choice(glst)
        await random_person.finish(Message([{
            "type": "at",
            "data": {
                "qq": event.user_id
            }
        }, {
            "type": "text",
            "data": {
                "text": f"\n{m['card'] if m['card'] != '' else m['nickname']}({m['user_id']})"
            }
        }]))

    except AttributeError:
        await random_person.finish("请在群聊使用")


snmb = on_regex("随个.+", priority=5)


@snmb.handle()
async def _(bot: Bot, event: Event, state: T_State):
    try:
        gid = event.group_id
        if random.random() < 0.3:
            await snmb.finish(Message([
                {"type": "text", "data": {"text": "随你"}},
                {"type": "image", "data": {"file": "https://www.diving-fish.com/images/emoji/horse.png"}}
            ]))
        else:
            glst = await bot.get_group_member_list(group_id=gid, self_id=int(bot.self_id))
            m = random.choice(glst)
            await random_person.finish(Message([{
                "type": "at",
                "data": {
                    "qq": event.user_id
                }
            }, {
                "type": "text",
                "data": {
                    "text": f"\n{m['card'] if m['card'] != '' else m['nickname']}({m['user_id']})"
                }
            }]))
    except AttributeError:
        await random_person.finish("请在群聊使用")


shuffle = on_command('shuffle')


@shuffle.handle()
async def _(bot: Bot, event: Event):
    argv = int(str(event.get_message()))
    if argv > 100:
        await shuffle.finish('请输入100以内的数字')
        return
    d = [str(i + 1) for i in range(argv)]
    random.shuffle(d)
    await shuffle.finish(','.join(d))


repeat = on_message(priority=20)
repeat_dict = defaultdict(list)


@repeat.handle()
async def _(bot: Bot, event: Event, state: T_State):
    if event.__getattribute__('group_id') is None:
        event.__delattr__('group_id')
    else:
        repeat_list = repeat_dict[event.__getattribute__('group_id')]
        if len(repeat_list) == 0:
            repeat_list.append('')
            repeat_list.append(False)
        msg = event.get_message()
        p = 0.0114514
        if repeat_list[0] == msg and not repeat_list[1]:
            p = 1
        elif repeat_list[0] != msg and repeat_list[1]:
            repeat_list[0] = msg
            repeat_list[1] = False
        elif repeat_list[0] != msg:
            repeat_list[0] = msg
        r = random.random()
        if r <= p:  # 0.0114514 default
            repeat_list[1] = True
            await repeat.finish(msg)


status = on_command("status", permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, block=True)


@status.handle()
async def _(bot: Bot, event: Event, state: T_State):
    try:
        py_info = platform.python_version()
        pla = platform.platform()
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        memory = round(memory, 2)
        disk = psutil.disk_usage('/').percent
    except Exception:  # ignore
        await status.finish("获取状态失败")
        return

    msg = ""

    if cpu > 80 or memory > 80 or disk > 80:
        ex_msg = "蚌埠住了..."
    else:
        ex_msg = "一般"

    msg += "server status:\n"
    msg += f"OS: {pla}"
    msg += f"Running on Python {py_info}\n"
    msg += f"CPU {cpu}%\n"
    msg += f"MEM {memory}%\n"
    msg += f"DISK {disk}%\n"
    msg += ex_msg
    await status.finish(msg)


reset = on_command("reset", priority=0, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, block=True)


@reset.handle()
async def _(bot: Bot, event: Event, state: dict):
    await reset.send(Message([{
        "type": "image",
        "data": {
            "file": "file:///" + os.path.abspath("src/static/mai/pic/meimeireset.png")
        }
    }]))

    os.execl(sys.executable, sys.executable, *sys.argv)


STFU = on_command("STFU", priority=0, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, block=True)


@STFU.handle()
async def _(bot: Bot, event: Event, state: dict):
    await reset.send(Message([{
        "type": "image",
        "data": {
            "file": "file:///" + os.path.abspath("src/static/mai/pic/meimeistfu.jpg")
        }
    }]))

    sys.exit(0)

# taro_lst = []
#
# with open('src/static/taro.txt', encoding='utf-8') as f:
#     for line in f:
#         elem = line.strip().split('\t')
#         taro_lst.append(elem)
#
#
# taro = on_regex("溜冰塔罗牌")
#
#
# @taro.handle()
# async def _(bot: Bot, event: Event):
#     group_id = event.group_id
#     nickname = event.sender.nickname
#     if str(group_id) != "702156482":
#         return
#     c = randint(0, 10)
#     a = randint(0, 1)
#     s1 = "正位" if a == 0 else "逆位"
#     s2 = taro_lst[c][3 + a]
#     await taro.finish(f"来看看{ nickname }抽到了什么：\n{taro_lst[c][0]}（{taro_lst[c][1]}，{taro_lst[c][2]}）{s1}：\n{s2}")
