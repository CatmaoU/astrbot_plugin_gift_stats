import asyncio
import os
import tempfile
import aiohttp
from astrbot.api.message_components import Node, Plain, Image, Nodes
from astrbot.api import logger

async def get_bot_uin_from_api(plugin_instance, event):
    """通过 OneBot API get_login_info 获取机器人 QQ 号"""
    try:
        if hasattr(event, 'bot') and hasattr(event.bot, 'call_action'):
            logger.info("正在通过 get_login_info API 获取机器人 QQ 号...")
            result = await event.bot.call_action('get_login_info')
            if result and isinstance(result, dict) and 'user_id' in result:
                uin = int(result['user_id'])
                logger.info(f"通过 get_login_info 获取到 QQ 号: {uin}")
                return uin
            else:
                logger.warning(f"get_login_info 返回结果无效: {result}")
        else:
            logger.warning("event.bot 或 call_action 不可用")
    except Exception as e:
        logger.error(f"get_login_info API 调用失败: {e}")
    return None

async def send_separately(plugin_instance, event, image_urls):
    for idx, url in enumerate(image_urls):
        yield event.image_result(url)
        if idx < len(image_urls) - 1:
            await asyncio.sleep(0.5)

async def send_forward(plugin_instance, event, image_urls):
    if len(image_urls) == 1:
        yield event.image_result(image_urls[0])
        return

    # ----- 获取 uin（QQ 号）-----
    uin = None

    # 1. 优先使用配置中的 forward_uin
    configured_uin = getattr(plugin_instance, 'forward_uin', '').strip()
    if configured_uin.isdigit():
        uin = int(configured_uin)
        logger.info(f"使用配置 forward_uin: {uin}")

    # 2. 从 event.self_id 获取
    if uin is None:
        if hasattr(event, 'self_id') and event.self_id:
            uin = int(event.self_id)
            logger.info(f"使用 event.self_id: {uin}")

    # 3. 通过 OneBot API 获取
    if uin is None:
        uin = await get_bot_uin_from_api(plugin_instance, event)

    # 4. 从 context.bot.uin 获取
    if uin is None:
        context = getattr(plugin_instance, 'context', None)
        if context and hasattr(context, 'bot') and hasattr(context.bot, 'uin'):
            uin = int(context.bot.uin)
            logger.info(f"使用 context.bot.uin: {uin}")

    # 5. 从 star.bot.uin 获取
    if uin is None:
        star = getattr(plugin_instance, 'star', None)
        if star and hasattr(star, 'bot') and hasattr(star.bot, 'uin'):
            uin = int(star.bot.uin)
            logger.info(f"使用 star.bot.uin: {uin}")

    if uin is None:
        yield event.plain_result("❌ 无法获取机器人自身的 QQ 号，合并转发失败喵！")
        logger.error("所有获取 uin 的方式均失败")
        return

    # ----- 获取发送者名称（sender_name）-----
    sender_name = getattr(plugin_instance, 'sender_name', '礼物统计')
    if not sender_name:
        sender_name = '礼物统计'
    logger.info(f"使用发送者名称: {sender_name}")

    # ----- 构建节点 -----
    nodes = []
    temp_files = []
    try:
        for idx, url in enumerate(image_urls):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        fd, path = tempfile.mkstemp(suffix='.png')
                        os.close(fd)
                        with open(path, 'wb') as f:
                            f.write(await resp.read())
                        temp_files.append(path)
                        img = Image.fromFileSystem(path)
                        node = Node(
                            uin=uin,
                            name=sender_name,
                            content=[
                                Plain(f"第 {idx+1}/{len(image_urls)} 页\n"),
                                img
                            ]
                        )
                        nodes.append(node)
                    else:
                        raise Exception(f"下载图片失败: {url}")
    except Exception as e:
        logger.error(f"构建节点失败: {e}")
        yield event.plain_result(f"❌ 构建合并转发失败喵：{str(e)}")
        # 清理已下载的临时文件
        for path in temp_files:
            try:
                os.unlink(path)
            except:
                pass
        return

    if not nodes:
        yield event.plain_result("❌ 没有生成任何节点喵！")
        # 清理临时文件
        for path in temp_files:
            try:
                os.unlink(path)
            except:
                pass
        return

    # ----- 通过 OneBot API 发送合并转发 -----
    try:
        payload = {"messages": []}
        for node in nodes:
            payload["messages"].append(await node.to_dict())

        is_group = bool(event.get_group_id())
        target = event.get_group_id() if is_group else event.get_sender_id()
        if not target:
            yield event.plain_result("❌ 无法获取目标会话 ID 喵！")
            return

        routing = {}
        self_id = getattr(event.message_obj, 'self_id', None)
        if self_id:
            routing["self_id"] = self_id

        if is_group:
            await event.bot.call_action(
                "send_group_forward_msg",
                group_id=int(target),
                **payload,
                **routing
            )
        else:
            await event.bot.call_action(
                "send_private_forward_msg",
                user_id=int(target),
                **payload,
                **routing
            )
        logger.info(f"合并转发发送成功，共 {len(nodes)} 个节点，目标: {target}")

    except Exception as e:
        logger.error(f"合并转发发送失败: {e}")
        yield event.plain_result(f"❌ 合并转发发送失败喵：{str(e)}")
    finally:
        # ----- 清理临时文件 -----
        for path in temp_files:
            try:
                os.unlink(path)
                logger.debug(f"已删除临时文件: {path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败 {path}: {e}")