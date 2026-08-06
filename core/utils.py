import json
from astrbot.api import logger

def load_bindings(plugin_instance):
    bindings_file = plugin_instance.bindings_file
    if bindings_file.exists():
        try:
            with open(bindings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载绑定数据失败: {e}")
    return {}

def save_bindings(plugin_instance):
    try:
        with open(plugin_instance.bindings_file, 'w', encoding='utf-8') as f:
            json.dump(plugin_instance.bindings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存绑定数据失败: {e}")

def load_help_text(plugin_instance):
    help_file = plugin_instance.help_file
    if help_file.exists():
        try:
            with open(help_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('help', '')
        except Exception as e:
            logger.warning(f"加载 help.json 失败: {e}")
    return "❌ 帮助信息未加载，请检查 help.json 文件。"

def get_image_url(path, base_url="https://bot.star-yu.cn"):
    if not path:
        return ''
    if path.startswith(('http://', 'https://')):
        return path
    return f"{base_url}{path}"