import requests
import os

# 从GitHub密钥自动读取（无需手动填写，安全）
COOKIE = os.getenv("GLADOS_COOKIE")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")

# Glados 接口
CHECKIN_URL = "https://glados.cloud/api/user/checkin"
STATUS_URL = "https://glados.cloud/api/user/status"
POINTS_URL = "https://glados.cloud/api/user/points"
EXCHANGE_URL = "https://glados.cloud/api/user/exchange"
HEADERS = {"Cookie": COOKIE, "Content-Type": "application/json"}

# PushPlus 推送函数
def push_message(content):
    try:
        url = "http://www.pushplus.plus/send"
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": "GLaDOS自动签到",
            "content": content
        }
        requests.post(url, json=data, timeout=10)
    except:
        pass

def main():
    msg = []
    # 1. 执行签到
    try:
        res = requests.post(CHECKIN_URL, json={"token": "glados.cloud"}, headers=HEADERS)
        data = res.json()
        today_point = data.get("points", 0)
        if "Checkin! Got" in data.get("message", ""):
            msg.append(f"✅ 签到成功 | 今日积分：{today_point}")
        else:
            msg.append("ℹ️ 今日已签到")
    except:
        msg.append("❌ 签到失败")
        push_message("\n".join(msg))
        return

    # 2. 获取总积分
    try:
        total = int(requests.get(POINTS_URL, headers=HEADERS).json().get("points", 0))
        msg.append(f"💰 总积分：{total}")
    except:
        total = 0
        msg.append("💰 获取积分失败")

    # 3. 获取会员剩余天数
    try:
        days = int(float(requests.get(STATUS_URL, headers=HEADERS).json().get("data", {}).get("leftDays", 0)))
        msg.append(f"📅 会员剩余：{days} 天")
    except:
        msg.append("📅 获取天数失败")

    # 4. 500积分自动兑换（仅这一个档位）
    if total >= 500:
        try:
            requests.post(EXCHANGE_URL, json={"planType": "plan500"}, headers=HEADERS)
            msg.append("🎁 500积分兑换100天成功！")
        except:
            msg.append("❌ 积分兑换失败")
    else:
        msg.append(f"🎯 {total}/500 积分，暂不兑换")

    # 发送到手机
    content = "\n".join(msg)
    push_message(content)
    print(content)

if __name__ == "__main__":
    main()
