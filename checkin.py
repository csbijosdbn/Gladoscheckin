import os

import requests

# 从 GitHub Secrets 读取 Cookie，并清理换行和空格
raw_cookie = os.getenv("GLADOS_COOKIE", "")
COOKIE = raw_cookie.strip().replace("\n", "").replace("\r", "")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# GLaDOS 接口
CHECKIN_URL = "https://glados.cloud/api/user/checkin"
STATUS_URL = "https://glados.cloud/api/user/status"
POINTS_URL = "https://glados.cloud/api/user/points"
EXCHANGE_URL = "https://glados.cloud/api/user/exchange"

HEADERS = {
    "Cookie": COOKIE,
    "Content-Type": "application/json",
}


def push_message(content):
    """通过 PushPlus 推送签到结果。"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN，跳过 PushPlus 推送")
        return

    url = "https://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "GLaDOS 自动签到",
        "content": content,
        "template": "txt",
    }

    for attempt in range(1, 3):
        try:
            response = requests.post(url, json=data, timeout=15)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                print("✅ PushPlus 推送成功")
                return

            print(f"⚠️ PushPlus 返回错误：{result.get('msg', '未知错误')}")
        except (requests.RequestException, ValueError) as error:
            print(f"⚠️ PushPlus 第 {attempt} 次推送异常：{error}")

    print("❌ PushPlus 推送失败")


def get_latest_earned_points(history):
    """
    从积分记录中取最近一笔正向积分。

    自动兑换会生成负数积分记录，因此不能直接读取 history[0]；
    倒序记录中最近的一笔正数，就是当天签到获得的积分。
    """
    for item in history or []:
        try:
            change = int(float(item.get("change", 0)))
            if change > 0:
                return change
        except (TypeError, ValueError):
            continue

    return 0


def main():
    if not COOKIE:
        content = "❌ 未配置 GLADOS_COOKIE"
        print(content)
        push_message(content)
        return

    msg = []
    checkin_success = False
    is_new_checkin = False
    response_points = 0

    # 1. 执行签到
    try:
        response = requests.post(
            CHECKIN_URL,
            json={"token": "glados.cloud"},
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        message = str(data.get("message", ""))

        try:
            response_points = int(float(data.get("points", 0)))
        except (TypeError, ValueError):
            response_points = 0

        if "Checkin! Got" in message:
            checkin_success = True
            is_new_checkin = True
            msg.append("✅ 签到成功")
        elif "Checkin Repeats" in message or "Today's observation logged" in message:
            checkin_success = True
            msg.append("ℹ️ 今日已签到，无需重复操作")
        else:
            msg.append(f"❌ 签到失败：{message or '未知错误'}")

    except (requests.RequestException, ValueError) as error:
        msg.append(f"❌ 签到请求异常：{error}")
        content = "\n".join(msg)
        print(content)
        push_message(content)
        return

    # 2. 查询积分和当天签到所得积分
    total = 0
    try:
        response = requests.get(POINTS_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        points_data = response.json()

        total = int(float(points_data.get("points", "0")))
        history_points = get_latest_earned_points(points_data.get("history", []))

        # 第一次签到优先使用签到接口直接返回的积分；
        # 第二、三次运行则从积分历史中获取第一次签到奖励。
        if is_new_checkin and response_points > 0:
            today_checkin_points = response_points
        else:
            today_checkin_points = history_points

        if checkin_success:
            msg.append(f"🎁 今日获取积分：{today_checkin_points}")

        msg.append(f"💰 当前总积分：{total}")

    except (requests.RequestException, ValueError, TypeError) as error:
        msg.append(f"💰 获取总积分失败：{error}")

    # 3. 查询会员剩余天数
    try:
        response = requests.get(STATUS_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        status_data = response.json()

        days = int(float(status_data.get("data", {}).get("leftDays", 0)))
        msg.append(f"📅 会员剩余可用：{days} 天")

    except (requests.RequestException, ValueError, TypeError) as error:
        msg.append(f"📅 获取剩余天数失败：{error}")

    # 4. 满 500 积分自动兑换 100 天
    if total >= 500:
        try:
            response = requests.post(
                EXCHANGE_URL,
                json={"planType": "plan500"},
                headers=HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            exchange_data = response.json()

            if exchange_data.get("code") == 0:
                msg.append("🎁 500 积分兑换 100 天成功！")
            else:
                msg.append(
                    f"❌ 兑换失败：{exchange_data.get('message', '未知错误')}"
                )

        except (requests.RequestException, ValueError) as error:
            msg.append(f"❌ 兑换请求异常：{error}")
    else:
        msg.append(f"🎯 {total}/500 积分，暂不兑换")

    # 5. 输出并推送
    content = "\n".join(msg)

    print("\n" + "=" * 50)
    print(content)
    print("=" * 50 + "\n")

    push_message(content)


if __name__ == "__main__":
    main()
