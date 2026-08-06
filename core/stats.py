import asyncio
from datetime import datetime
from .utils import get_image_url
from .render import render_page
from .sender import send_separately, send_forward
from ..crawl_api import run_crawler
from astrbot.api import logger

async def handle_gift_stats(plugin_instance, event, page_num=None, start_date=None, end_date=None):
    """
    处理礼物统计逻辑
    
    参数:
        plugin_instance: 插件实例
        event: 消息事件
        page_num: 页码（可选）
        start_date: 起始日期 "YYYY-MM-DD"（可选，默认为当天）
        end_date: 结束日期 "YYYY-MM-DD"（可选，默认为当天）
    """
    username = plugin_instance.username.strip()
    password = plugin_instance.password.strip()
    base_url = plugin_instance.base_url.strip()

    if not username or not password:
        yield event.plain_result("❌ 请先在插件配置中设置用户名和密码喵！")
        return

    # 若未指定日期，默认当天
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # 获取群绑定的房间 ID
    group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') and event.get_group_id() else None
    room_pk = None
    if group_id and group_id in plugin_instance.group_room_bindings:
        room_pk = plugin_instance.group_room_bindings[group_id]

    async with plugin_instance._lock:
        try:
            gifts = await asyncio.to_thread(
                run_crawler,
                username=username,
                password=password,
                base_url=base_url,
                start_date=start_date,
                end_date=end_date,
                room_pk=room_pk
            )
        except Exception as e:
            yield event.plain_result(f"❌ 爬取数据失败喵：{str(e)}")
            return

        if not gifts:
            yield event.plain_result(f"📭 在 {start_date} ~ {end_date} 期间没有礼物记录喵！")
            return

        # ---------- 按用户分组 ----------
        user_map = {}
        for rec in gifts:
            uid = rec.get('viewer_uid', 'unknown')
            if uid not in user_map:
                user_map[uid] = {
                    'uid': uid,
                    'name': rec.get('viewer_name', '未知用户'),
                    'avatar': get_image_url(rec.get('viewer_avatar', ''), base_url),
                }
            current_name = rec.get('viewer_name', '未知用户')
            if user_map[uid]['name'] != current_name:
                user_map[uid]['name'] = current_name

        users = list(user_map.values())
        users.sort(key=lambda x: x['name'])

        total_users = len(users)
        if total_users == 0:
            yield event.plain_result("📭 没有用户数据喵！")
            return

        max_per_page = plugin_instance.max_users_per_page
        total_pages = (total_users + max_per_page - 1) // max_per_page

        # ---------- 单图输出模式 ----------
        if plugin_instance.single_image_output:
            all_uids = {u['uid'] for u in users}
            page_gifts = [rec for rec in gifts if rec.get('viewer_uid', 'unknown') in all_uids]
            try:
                url = await render_page(plugin_instance, page_gifts, "")
                yield event.image_result(url)
            except Exception as e:
                logger.error(f"渲染单图失败: {e}")
                yield event.plain_result(f"❌ 生成图片失败喵：{str(e)}")
            return

        # ---------- 处理页码跳转 ----------
        if page_num is not None:
            if page_num < 1 or page_num > total_pages:
                yield event.plain_result(f"❌ 页码无效，当前共 {total_pages} 页，请输入 1~{total_pages} 之间的数字喵！")
                return
            start = (page_num - 1) * max_per_page
            end = min(start + max_per_page, total_users)
            page_users = users[start:end]
            uids = {u['uid'] for u in page_users}
            page_gifts = [rec for rec in gifts if rec.get('viewer_uid', 'unknown') in uids]
            try:
                url = await render_page(plugin_instance, page_gifts, f" (第{page_num}/{total_pages}页)")
                yield event.image_result(url)
            except Exception as e:
                logger.error(f"渲染第{page_num}页失败: {e}")
                yield event.plain_result(f"❌ 生成第{page_num}页图片失败喵：{str(e)}")
            return

        # ---------- 正常分页 ----------
        image_urls = []
        for page in range(total_pages):
            start = page * max_per_page
            end = min(start + max_per_page, total_users)
            page_users = users[start:end]
            uids = {u['uid'] for u in page_users}
            page_gifts = [rec for rec in gifts if rec.get('viewer_uid', 'unknown') in uids]
            page_info = f" (第{page+1}/{total_pages}页)"
            try:
                url = await render_page(plugin_instance, page_gifts, page_info)
                if url:
                    image_urls.append(url)
            except Exception as e:
                logger.error(f"渲染第{page+1}页失败: {e}")
                yield event.plain_result(f"❌ 生成第{page+1}页图片失败喵：{str(e)}")
                return

        if not image_urls:
            yield event.plain_result("❌ 未能生成任何图片喵！")
            return

        # ---------- 发送 ----------
        if plugin_instance.merge_forward:
            try:
                async for result in send_forward(plugin_instance, event, image_urls):
                    yield result
            except Exception as e:
                logger.error(f"合并转发失败，回退到逐张发送: {e}")
                async for result in send_separately(plugin_instance, event, image_urls):
                    yield result
        else:
            if plugin_instance.send_separately:
                async for result in send_separately(plugin_instance, event, image_urls):
                    yield result
            else:
                if image_urls:
                    yield event.image_result(image_urls[0])
                    if total_pages > 1:
                        yield event.plain_result(f"📌 共 {total_pages} 页，当前仅显示第一页喵")