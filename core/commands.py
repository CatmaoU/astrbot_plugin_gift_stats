import re
from datetime import datetime, timedelta
from astrbot.api import logger
from .stats import handle_gift_stats
from .render import render_page
from .room import RoomManager
from .utils import save_bindings, load_bindings

# ---------- 房间列表命令 ----------
async def list_rooms_command(plugin_instance, event):
    """列出所有可用直播间及其序号"""
    if not plugin_instance.username or not plugin_instance.password:
        yield event.plain_result("❌ 请先在插件配置中设置用户名和密码喵！")
        return

    rooms = await RoomManager.fetch_rooms(plugin_instance)
    if not rooms:
        yield event.plain_result("❌ 获取房间列表失败或没有房间喵！")
        return

    group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') and event.get_group_id() else None
    current_room_pk = None
    if group_id and group_id in plugin_instance.group_room_bindings:
        current_room_pk = plugin_instance.group_room_bindings[group_id]

    result = "📋 **可用直播间列表**\n"
    for idx, room in enumerate(rooms, 1):
        room_name = room.get('room_name', '未命名')
        room_id = room.get('room_id', '')
        room_pk = room.get('id', '')
        is_current = (current_room_pk == room_pk)
        marker = " ✅ (当前)" if is_current else ""
        result += f"{idx}. {room_name} [房间号: {room_id}] {marker}\n"
        result += f"   地址：https://live.bilibili.com/{room_id}\n"
    result += "\n使用 `/礼物房间 绑定 [序号]` 切换当前群的绑定房间喵！"
    yield event.plain_result(result)

# ---------- 绑定房间命令 ----------
async def bind_room_command(plugin_instance, event):
    """将当前群绑定到指定房间序号，如 /礼物房间 绑定 2"""
    parts = event.message_str.strip().split()
    if len(parts) < 2:
        yield event.plain_result("❌ 请指定序号，如 /礼物房间 绑定 2 喵！")
        return

    group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') and event.get_group_id() else None
    if not group_id:
        yield event.plain_result("❌ 此功能仅支持群聊喵！")
        return

    try:
        idx = int(parts[-1]) - 1
    except ValueError:
        yield event.plain_result("❌ 序号必须是数字喵！")
        return

    rooms = await RoomManager.fetch_rooms(plugin_instance)
    if not rooms:
        yield event.plain_result("❌ 获取房间列表失败喵！")
        return
    if idx < 0 or idx >= len(rooms):
        yield event.plain_result(f"❌ 序号无效，当前共有 {len(rooms)} 个房间喵！")
        return

    room = rooms[idx]
    room_pk = room.get('id')
    room_name = room.get('room_name', '未命名')
    room_id = room.get('room_id', '')

    plugin_instance.group_room_bindings[group_id] = room_pk
    RoomManager.save_group_bindings(plugin_instance)
    yield event.plain_result(f"✅ 当前群已绑定房间：{room_name} [房间号: {room_id}]喵！")

# ---------- 主统计命令 ----------
async def gift_stats_command(plugin_instance, event):
    """获取当天/最近N天/指定日期范围的礼物统计"""
    parts = event.message_str.strip().split()
    start_date = None
    end_date = None
    date_desc = ""

    if len(parts) == 1:
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        date_desc = "当天的"
    elif len(parts) == 2:
        param = parts[1]
        if param.isdigit():
            num = int(param)
            if 1 <= num <= 30:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=num-1)).strftime("%Y-%m-%d")
                date_desc = f"最近 {num} 天的"
            else:
                yield event.plain_result("❌ 数字参数必须在 1~30 之间喵！")
                return
        else:
            yield event.plain_result("❌ 参数必须是数字（1-30天）或日期格式喵！")
            return
    elif len(parts) == 3:
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if date_pattern.match(parts[1]) and date_pattern.match(parts[2]):
            start_date = parts[1]
            end_date = parts[2]
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                yield event.plain_result("❌ 日期格式无效，请使用 YYYY-MM-DD 喵！")
                return
            if start_date > end_date:
                yield event.plain_result("❌ 起始日期不能晚于结束日期喵！")
                return
            date_desc = f"{start_date} 到 {end_date} 的"
        else:
            yield event.plain_result("❌ 参数格式不正确，请使用 /礼物统计 数字 或 /礼物统计 YYYY-MM-DD YYYY-MM-DD 喵！")
            return
    else:
        yield event.plain_result("❌ 参数数量过多，请参考 /礼物统计帮助 喵！")
        return

    yield event.plain_result(f"⏳ 正在获取 {date_desc}礼物数据并生成统计图，请稍候喵...")

    async for result in handle_gift_stats(plugin_instance, event, page_num=None, start_date=start_date, end_date=end_date):
        yield result

# ---------- 页码跳转命令 ----------
async def page_command(plugin_instance, event):
    """跳转到指定页码，如 /礼物统计页 2"""
    parts = event.message_str.strip().split()
    if len(parts) < 2:
        yield event.plain_result("❌ 请指定页码，如 /礼物统计页 2 喵！")
        return
    if not parts[-1].isdigit():
        yield event.plain_result("❌ 页码必须为数字喵！")
        return
    page_num = int(parts[-1])
    if page_num < 1:
        yield event.plain_result("❌ 页码必须大于 0 喵！")
        return

    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    yield event.plain_result("⏳ 正在获取当天的礼物数据并生成统计图，请稍候喵...")

    async for result in handle_gift_stats(plugin_instance, event, page_num=page_num, start_date=start_date, end_date=end_date):
        yield result

# ---------- 帮助命令 ----------
async def help_command(plugin_instance, event):
    """显示插件帮助信息"""
    if plugin_instance.help_text:
        yield event.plain_result(plugin_instance.help_text)
    else:
        yield event.plain_result("❌ 帮助信息为空，请检查 help.json 文件喵！")

# ---------- 绑定UID命令 ----------
async def bind_uid_command(plugin_instance, event):
    """绑定您的 B 站 UID，如 /礼物统计 绑定 123456"""
    parts = event.message_str.strip().split()
    if len(parts) < 2:
        yield event.plain_result("❌ 请输入B站uid喵！")
        return
    uid_candidate = parts[-1]
    if not uid_candidate.isdigit():
        yield event.plain_result("❌ 绑定的 UID 必须为数字喵！")
        return
    uid = uid_candidate.strip()
    sender_id = str(event.get_sender_id())
    if sender_id in plugin_instance.bindings:
        yield event.plain_result("❌ 你已经绑定过了喵！")
        return
    plugin_instance.bindings[sender_id] = uid
    save_bindings(plugin_instance)
    yield event.plain_result(f"✅ 绑定成功喵！已绑定 UID: {uid}")

# ---------- 解绑UID命令 ----------
async def unbind_uid_command(plugin_instance, event):
    """解除已绑定的 UID"""
    sender_id = str(event.get_sender_id())
    if sender_id not in plugin_instance.bindings:
        yield event.plain_result("❌ 你还没有绑定任何 UID 呢喵！")
        return
    del plugin_instance.bindings[sender_id]
    save_bindings(plugin_instance)
    yield event.plain_result("✅ 解绑成功喵！")

# ---------- 贡献命令 ----------
async def contribution_command(plugin_instance, event):
    """查询已绑定 UID 的礼物贡献，生成专属图片"""
    sender_id = str(event.get_sender_id())
    if sender_id not in plugin_instance.bindings:
        yield event.plain_result("❌ 你还没有绑定任何 UID 呢喵！请先使用 /礼物 绑定 [uid]")
        return
    bind_uid = plugin_instance.bindings[sender_id]
    yield event.plain_result(f"⏳ 正在查询 UID {bind_uid} 的礼物贡献喵...")

    username = plugin_instance.username.strip()
    password = plugin_instance.password.strip()
    base_url = plugin_instance.base_url.strip()
    if not username or not password:
        yield event.plain_result("❌ 请先在插件配置中设置用户名和密码喵！")
        return

    from ..crawl_api import run_crawler
    try:
        gifts = await asyncio.to_thread(
            run_crawler,
            username=username,
            password=password,
            base_url=base_url,
            days=30
        )
    except Exception as e:
        yield event.plain_result(f"❌ 爬取数据失败喵：{str(e)}")
        return

    user_gifts = [rec for rec in gifts if rec.get('viewer_uid', '') == bind_uid]
    if not user_gifts:
        yield event.plain_result(f"📭 UID {bind_uid} 在近30天内没有礼物记录喵！")
        return

    try:
        url = await render_page(plugin_instance, user_gifts, f" (UID: {bind_uid})")
        yield event.image_result(url)
    except Exception as e:
        logger.error(f"渲染贡献图失败: {e}")
        yield event.plain_result(f"❌ 生成图片失败喵：{str(e)}")