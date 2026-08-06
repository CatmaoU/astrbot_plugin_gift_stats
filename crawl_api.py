import requests
import json
from datetime import datetime, timedelta

def login(session, username, password, base_url):
    login_url = f"{base_url}/api/auth/login"
    payload = {"username_or_email": username, "password": password}
    resp = session.post(login_url, json=payload)
    if resp.status_code == 200:
        print("✅ 登录成功")
        return True
    print(f"❌ 登录失败: {resp.text}")
    return False

def get_rooms(session, base_url):
    resp = session.get(f"{base_url}/api/rooms")
    if resp.status_code == 200:
        return resp.json()
    return []

def get_gifts(session, base_url, room_pk, start_date, end_date, limit=50, offset=0):
    params = {
        "room_pk": room_pk,
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit,
        "offset": offset
    }
    resp = session.get(f"{base_url}/api/data/gifts", params=params)
    if resp.status_code == 200:
        data = resp.json()
        print(f"   返回数据类型: {type(data)}")
        if isinstance(data, list):
            print(f"   数据条数: {len(data)}")
        return data
    return None

def fetch_all_gifts(session, base_url, room_pk, start_date, end_date, limit=50):
    all_gifts = []
    offset = 0
    while True:
        print(f"📄 获取第 {offset//limit + 1} 页 (offset={offset})")
        data = get_gifts(session, base_url, room_pk, start_date, end_date, limit, offset)
        if not data:
            break
        if isinstance(data, list):
            items = data
        else:
            items = data.get("items") or data.get("data") or []
        if not items:
            break
        all_gifts.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return all_gifts

def run_crawler(username, password, base_url="https://bot.star-yu.cn", days=30,
                start_date=None, end_date=None, room_pk=None):
    """
    执行爬虫，获取礼物数据。

    参数:
        username: 登录用户名
        password: 登录密码
        base_url: API基础地址
        days: 当未指定 start_date/end_date 时，获取最近 days 天的数据，默认30
        start_date: 自定义起始日期，格式 "YYYY-MM-DD"
        end_date: 自定义结束日期，格式 "YYYY-MM-DD"
        room_pk: 房间 ID（可选），若指定则只爬取该房间，否则取第一个房间
    返回:
        礼物记录列表
    """
    session = requests.Session()
    if not login(session, username, password, base_url):
        raise Exception("登录失败，请检查用户名和密码")

    rooms = get_rooms(session, base_url)
    if not rooms:
        raise Exception("未找到任何房间")

    print(f"📋 找到 {len(rooms)} 个房间")
    for room in rooms:
        print(f"  - {room['room_name']} (ID: {room['id']}, room_id: {room['room_id']})")

    # 选择房间
    if room_pk is not None:
        selected_room = next((r for r in rooms if r['id'] == room_pk), None)
        if not selected_room:
            raise Exception(f"未找到 ID 为 {room_pk} 的房间")
        room = selected_room
    else:
        room = rooms[0]

    room_pk = room['id']

    # 日期处理
    if start_date and end_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise Exception("日期格式错误，请使用 YYYY-MM-DD 格式")
        print(f"\n📊 获取礼物数据: 房间 {room['room_name']}")
        print(f"   日期范围: {start_date} ~ {end_date}")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        print(f"\n📊 获取礼物数据: 房间 {room['room_name']}")
        print(f"   日期范围: {start_date} ~ {end_date}（最近 {days} 天）")

    gifts = fetch_all_gifts(session, base_url, room_pk, start_date, end_date, limit=50)
    print(f"🎁 共获取 {len(gifts)} 条礼物记录")
    return gifts