# -*- coding: utf-8 -*-

import re
import os
import json
import time

from mcdreforged.api.decorator import new_thread
from mcdreforged.api.types import ServerInterface, Info, CommandSource
from mcdreforged.api.command import *
from mcdreforged.api.rtext import *

PLUGIN_METADATA = {
    'id': 'markit',
    'version': '1.0.0',
    'name': 'Markit',
    'author': "mrxiaozhuox"
}

# 服务器最高标记数
# 包括私有坐标（建议控制在 30 - 50）
MAXNUM = 30

config_path = os.path.join("config", PLUGIN_METADATA['id'])
cor_path = os.path.join(config_path, 'coordinates')

HELP_MESSAGE = '''
§6!!mk §3显示帮助文档
§6!!mk <name> §3获取坐标位置
§6!!mk list §3获取坐标列表（包含公开与私有）
§6!!mk mark <name> §3设置坐标点
§6!!mk share <name> <title> §3分享坐标点（所有人可见）
§6!!mk private <name> §3私有坐标点（撤回分享）
§6!!mk delete <name> §3删除坐标点（分享同时删除）
§2---------- §9[ mrxiaozhuox ] §2----------
§3PS: §5当公开与私有坐标重名，则优先显示私有坐标。
'''

LIST_TEMP = '''
§2------ §9[公开坐标] §2------\n
'''

task = {}


def process_coordinate(text):
    data = text[1:-1].replace('d', '').split(', ')
    data = [(x + 'E0').split('E') for x in data]
    return tuple([float(e[0]) * 10 ** int(e[1]) for e in data])


def on_load(server: ServerInterface, old):

    server.register_command(
        Literal('!!mk').
        runs(lambda src: src.reply(HELP_MESSAGE)).
        then(
            Literal('list').runs(list_get)
        ).
        then(
            Text('name').runs(find_crd)
        ).
        then(
            Literal('mark').
            then(
                Text('name').runs(create_crd)
            )
        ).then(
            Literal('share').
            then(
                Text('name').then(
                    Text("title").runs(share_crd)
                )
            )
        ).then(
            Literal('private').
            then(
                Text('name').runs(private_crd)
            )
        ).then(
            Literal('delete').
            then(
                Text('name').runs(delete_crd)
            )
        )
    )

    # 插件初始化
    if not os.path.isdir(config_path):
        try:
            os.mkdir(config_path)
        except Exception:
            server.logger.error("插件初始化失败！（文件夹无法创建")
        else:
            os.mkdir(os.path.join(config_path, "coordinates"))
            with open(os.path.join(config_path, "sharelist.txt"), 'w') as f:
                f.write("{}")


def list_get(src, ctx):

    info = LIST_TEMP
    public = ""
    private = ""

    saves = os.listdir(os.path.join(config_path, 'coordinates'))

    if not saves:
        info = "\n§a当前暂无任何坐标信息！\n"
    else:

        with open(os.path.join(config_path, "sharelist.txt")) as f:
            data = f.read()
        if data == "":
            data = "{}"
        data = json.loads(data)

        used = []

        for save in saves:

            name = save.split("@")[1].split(".")[0]
            user = save.split('@')[0]

            if user == src.player:

                oeit = "§b个人私有 §3<未公开>"
                for point in data:
                    if data[point] == user + "@" + name:
                        oeit = "§c个人公开 §3<{}>".format(point)
                        used.append(point)
                        break

                private += RText("§e[{}] : {}\n".format(name, oeit)).c(
                    RAction.suggest_command, "!!mk " + name).set_hover_text("立刻获取坐标！")

        for point in data:
            if point not in used:
                if os.path.isfile(os.path.join(cor_path, data[point] + ".txt")):
                    player = data[point].split("@")[0]
                    public += RText("§e[{}] : §3公开自 - {}\n".format(point, player)).c(RAction.suggest_command,"!!mk " + point).set_hover_text("立刻获取坐标！")

        public += "\n§2         §4 [私有坐标] §2         \n\n"

        info += public + private + "\n§2---------------------"
        info += ""

    return src.reply(info)


def create_crd(src: CommandSource, ctx):

    server = src.get_server()

    task[src.player] = "markcrd:" + ctx['name']
    server.execute("data get entity " + src.player)


def show_info(name, file, player="private"):

    with open(os.path.join(cor_path, file)) as f:
        data = f.read()
    data = json.loads(data)

    x, y, z = str(data['x']), str(data['y']), str(data['z'])

    dim = data['dimension'].split(":")[1]
    ext = ''

    if dim == 'overworld':
        dim = "主世界"
    elif dim == 'the_nether':
        dim = "下界"
    elif dim == 'the_end':
        dim = "末地"

    info = "§e[_{}_] §1@ §c{} §a[ {}, {}, {} ]{}  §3({})".format(
        name, dim, x, y, z, ext, player)

    return info


def pri_crd(name, player, server=None):
    savefile = player + "@" + name
    with open(os.path.join(config_path, 'sharelist.txt'), 'r') as f:
        data = f.read()
    if data == "":
        data = "{}"
    data = json.loads(data)

    flag = False

    if data.get(name) != None:
        if data[name].split("@")[0] == player:
            data.pop(name)
            flag = True
    else:
        for point in data:
            if data[point] == savefile:
                data.pop(point)
                flag = True
                break
    if flag:
        with open(os.path.join(config_path, 'sharelist.txt'), 'w') as f:
            server.logger.info(data)
            f.write(json.dumps(data))

        if server != None:
            server.broadcast("§a[{}] 坐标点已被创建者取消了共享！".format(name))

        return '§e[{}] 坐标点已取消共享！'.format(name)
    return '§c[{}] 坐标点共享信息不存在！'.format(name)


def delete_crd(src: CommandSource, ctx):
    savefile = src.player + "@" + ctx['name']
    if os.path.isfile(os.path.join(cor_path, savefile + ".txt")):
        pri_crd(ctx['name'], src.player, src.get_server())
        os.remove(os.path.join(cor_path, savefile + ".txt"))
        src.reply('§e[{}] 坐标点删除成功！'.format(ctx['name']))
    else:
        src.reply('§c[{}] 坐标点信息不存在！'.format(ctx['name']))


def find_crd(src: CommandSource, ctx):

    savename = ctx['name']
    filename = src.player + "@" + savename + ".txt"
    if os.path.isfile(os.path.join(cor_path, filename)):
        info = show_info(savename, filename)
        src.reply(info)
        return True
    else:
        with open(os.path.join(config_path, 'sharelist.txt')) as f:
            data = f.read()
        if data == "":
            data = "{}"
        data = json.loads(data)

        if savename in data:
            src.reply(data[savename])
            if os.path.isfile(os.path.join(cor_path, data[savename] + ".txt")):
                info = show_info(
                    savename, data[savename] + ".txt", data[savename].split("@")[0])
                src.reply(info)
                return True

    src.reply("§e[{}] §c坐标不存在！ 请检查名称是否正确！".format(savename))


def private_crd(src: CommandSource, ctx):
    src.reply(pri_crd(ctx['name'], src.player, src.get_server()))


def share_crd(src: CommandSource, ctx):

    server = src.get_server()

    savename = src.player + "@" + ctx["name"]

    with open(os.path.join(config_path, 'sharelist.txt'), 'r') as f:
        data = f.read()

    if data == "":
        data = {}
    else:
        data = json.loads(data)

    # src.reply("§c[{}] 坐标信息无效！".format(ctx['name']))

    for point in data:
        if data[point] == ctx['name']:
            src.reply("§a本坐标已共享，请勿重复共享! [{}]".format(point))
            return None
    if ctx['title'] in data:
        src.reply("§c共享标题重复了，请更换后重试！")
        return None

    savefile = os.path.join(config_path, "sharelist.txt")
    data[ctx['title']] = savename
    with open(savefile, 'w') as f:
        f.write(json.dumps(data))

    server.broadcast("§a" + src.player + " §e共享了坐标: " + RText("§d" + ctx['title']).c(
        RAction.run_command, "!!mk " + ctx['title']).set_hover_text("点我立刻获取坐标！") + " §e！")


def on_info(server: ServerInterface, info: Info):

    check = re.match(r'\w+ has the following entity data: ',
                     info.content) is not None

    if not info.is_player and check:

        player = re.findall(
            r'(\w+) has the following entity data: ', info.content)[0]

        if player in task:

            dimension = re.search(
                r'(?<= Dimension: )(.*?),', info.content).group().replace('"', '').replace(',', '')
            position = re.search(r'(?<=Pos: )\[.*?\]', info.content).group()
            position = process_coordinate(position)

            if re.match(r'markcrd:(.*)', task[player]):

                num = len(os.listdir(cor_path))
                if num >= MAXNUM:
                    server.tell(player, "§c服务器坐标点数量已达到最大值 ( " +
                                str(num) + " / " + str(MAXNUM) + " )")
                    return

                savename = re.findall(r'markcrd:(.*)', task[player])[0]
                savename = player + "@" + savename

                if os.path.isfile(os.path.join(cor_path, savename + ".txt")):

                    add = 1
                    newname = savename + "#" + str(add)
                    while os.path.isfile(os.path.join(cor_path, newname + ".txt")):
                        add = add + 1
                        newname = savename + "#" + str(add)
                    savename = newname

                    server.tell(player, "\n§c坐标点重名, 已自动更改为 " + savename)

                saveinfo = savename.split("@")[1]

                x = round(position[0])
                y = round(position[1])
                z = round(position[2])

                with open(os.path.join(cor_path, savename + '.txt'), 'w') as f:
                    f.write(json.dumps({
                        "x": x,
                        "y": y,
                        "z": z,
                        'dimension': dimension,
                    }))

                message = "\n§b已成功保存坐标: §c[" + str(x) + ", " + \
                    str(y) + ", " + str(z) + "] §b到 §d<" + saveinfo + ">\n"

                server.tell(player, message)

            task.pop(player)
