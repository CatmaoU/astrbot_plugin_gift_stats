import json
import requests
from astrbot.api import logger
from ..crawl_api import get_rooms, login

class RoomManager:
    """房间管理类，负责群绑定和获取房间列表"""
    
    @staticmethod
    def load_group_bindings(plugin_instance):
        """加载群房间绑定数据"""
        if plugin_instance.group_bindings_file.exists():
            try:
                with open(plugin_instance.group_bindings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载群绑定数据失败: {e}")
        return {}

    @staticmethod
    def save_group_bindings(plugin_instance):
        """保存群房间绑定数据"""
        try:
            with open(plugin_instance.group_bindings_file, 'w', encoding='utf-8') as f:
                json.dump(plugin_instance.group_room_bindings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存群绑定数据失败: {e}")

    @staticmethod
    async def fetch_rooms(plugin_instance):
        """获取房间列表"""
        session = requests.Session()
        if not login(session, plugin_instance.username, plugin_instance.password, plugin_instance.base_url):
            logger.error("登录失败，无法获取房间列表")
            return None
        rooms = get_rooms(session, plugin_instance.base_url)
        return rooms