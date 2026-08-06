import asyncio
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .core.utils import load_bindings, save_bindings, load_help_text
from .core.room import RoomManager
from .core.commands import (
    list_rooms_command,
    bind_room_command,
    gift_stats_command,
    page_command,
    help_command,
    bind_uid_command,
    unbind_uid_command,
    contribution_command,
)

@register(
    "astrbot_plugin_gift_stats",
    "iMuli",
    "B 站直播间礼物数据统计，支持多群直播间绑定、日期范围查询、个人礼物贡献查询",
    "1.0.2"
)
class GiftStatsPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        if isinstance(config, dict):
            self.username = config.get('username', '')
            self.password = config.get('password', '')
            self.base_url = config.get('base_url', 'https://bot.star-yu.cn')
            self.merge_forward = config.get('merge_forward', True)
            self.send_separately = config.get('send_separately', True)
            self.single_image_output = config.get('single_image_output', False)
            self.max_users_per_page = config.get('single_image_max_users', 15)
            self.sender_name = config.get('sender_name', '礼物统计')
            self.forward_uin = config.get('forward_uin', '')
            if not isinstance(self.max_users_per_page, int) or self.max_users_per_page < 1:
                self.max_users_per_page = 1
            elif self.max_users_per_page > 20:
                self.max_users_per_page = 20
        else:
            self.username = ''
            self.password = ''
            self.base_url = 'https://bot.star-yu.cn'
            self.merge_forward = True
            self.send_separately = True
            self.single_image_output = False
            self.max_users_per_page = 15
            self.sender_name = '礼物统计'
            self.forward_uin = ''

        self.base_dir = Path(__file__).parent
        self.html_template = self.base_dir / "gifts_viewer.html"
        self._lock = asyncio.Lock()

        # 用户绑定数据（UID绑定）
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.bindings_file = self.data_dir / "bindings.json"
        self.bindings = load_bindings(self)

        # 群房间绑定数据
        self.group_bindings_file = self.data_dir / "group_room_bindings.json"
        self.group_room_bindings = RoomManager.load_group_bindings(self)

        # 帮助文本
        self.help_file = self.base_dir / "help.json"
        self.help_text = load_help_text(self)

        logger.info(f"礼物统计插件已加载，用户名: {self.username or '(未配置)'}，合并转发: {self.merge_forward}，逐张发送: {self.send_separately}，单图输出: {self.single_image_output}，每页用户数: {self.max_users_per_page}，发送者名称: {self.sender_name}，自定义头像QQ: {self.forward_uin or '(未设置)'}")

    # ---------- 命令路由 ----------
    @filter.command("礼物统计房间", alias={"礼物房间列表", "房间列表"})
    async def list_rooms(self, event: AstrMessageEvent):
        async for result in list_rooms_command(self, event):
            yield result

    @filter.command("礼物房间绑定", alias={"礼物房间 绑定", "房间绑定"})
    async def bind_room(self, event: AstrMessageEvent):
        async for result in bind_room_command(self, event):
            yield result

    @filter.command("礼物统计")
    async def gift_stats(self, event: AstrMessageEvent):
        async for result in gift_stats_command(self, event):
            yield result

    @filter.command("礼物统计页", alias={"礼物统计 页", "礼物页"})
    async def gift_stats_page(self, event: AstrMessageEvent):
        async for result in page_command(self, event):
            yield result

    @filter.command("礼物统计帮助", alias={"礼物 帮助", "礼物 help"})
    async def gift_stats_help(self, event: AstrMessageEvent):
        async for result in help_command(self, event):
            yield result

    @filter.command("礼物统计绑定", alias={"礼物 绑定", "礼物 bind"})
    async def gift_stats_bind(self, event: AstrMessageEvent):
        async for result in bind_uid_command(self, event):
            yield result

    @filter.command("礼物统计解绑", alias={"礼物 解绑", "礼物 unbind"})
    async def gift_stats_unbind(self, event: AstrMessageEvent):
        async for result in unbind_uid_command(self, event):
            yield result

    @filter.command("礼物统计贡献", alias={"礼物 贡献", "礼物 contribution"})
    async def gift_stats_contribution(self, event: AstrMessageEvent):
        async for result in contribution_command(self, event):
            yield result