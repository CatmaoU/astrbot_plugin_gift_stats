import json
from astrbot.api import logger

async def render_page(plugin_instance, page_gifts, page_info):
    try:
        html_template = plugin_instance.html_template.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"读取模板失败: {e}")
        raise

    data_js = f"var allRecords = {json.dumps(page_gifts, ensure_ascii=False)};"
    html_content = html_template.replace(
        '<script src="gifts_data.js"></script>',
        f'<script>{data_js}</script>'
    )
    if page_info:
        html_content = html_content.replace(
            '今日份礼物记录',
            f'今日份礼物记录{page_info}'
        )

    render_func = None
    if hasattr(plugin_instance, 'html_render'):
        render_func = plugin_instance.html_render
    elif hasattr(plugin_instance.context, 'html_render'):
        render_func = plugin_instance.context.html_render
    else:
        raise Exception("未找到 html_render 方法")

    url = await render_func(
        html_content,
        {},
        options={
            "full_page": True,
            "viewport_width": 1280,
            "type": "png",
            "wait_until": "networkidle",
            "timeout": 30000
        }
    )
    return url