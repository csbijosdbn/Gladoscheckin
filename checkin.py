import requests
import os

# 从GitHub密钥自动读取，并自动清洗Cookie（去除换行、空格）
raw_cookie = os.getenv("GLADOS_COOKIE", "")
COOKIE = raw_cookie.strip().replace("\n", "").replace("\r", "")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# Glados 接口
CHECKIN_URL = "https://glados.cloud/api/user/checkin"
STATUS_URL = "https://glados.cloud/api/user/status"
POINTS_URL = "https://glados.cloud/api/user/points"
EXCHANGE_URL = "https://glados.cloud/api/user/exchange"
HEADERS = {"Cookie": COOKIE, "Content-Type": "application/json"}

# PushPlus 推送函数（优化稳定版）
def push_message(content):
    try:
        url = "https://www.pushplus.plus/send"
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": "GLaDOS自动签到",
            "content": content,
            "template": "txt"
        }
        for _ in range(2):
            response = requests.post(url, json=data, timeout=15)
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("code") == 200:
                    print("✅ PushPlus推送成功")
                    return
                else:
                    print(f"⚠️ 推送返回错误：{res_data.get('msg')}")
        print("❌ 推送重试失败")
    except Exception as e:
        print(f"❌ 推送异常：{str(e)}")

def main():
    msg = []
    # 1. 执行签到，精准区分重复签到和真失败
    try:
        res = requests.post(CHECKIN_URL, json={"token": "glados.cloud"}, headers=HEADERS, timeout=10)
        data = res.json()
        today_point = data.get("points", 0)
        message = data.get("message", "")

        if "Checkin! Got" in message:
            msg.append(f"✅ 签到成功 | 今日获得积分：{today_point}")
        elif "Checkin Repeats" in message or "Today's observation logged" in message:
            msg.append(f"ℹ️ 今日已签到，无需重复操作")
        else:
            msg.append(f"❌ 签到失败：{message}")
    except Exception as e:
        msg.append(f"❌ 签到请求异常：{str(e)}")
        push_message("\n".join(msg))
        return

    # 2. 获取总积分（完美兼容浮点数/整数格式）
    total = 0
    try:
        res = requests.get(POINTS_URL, headers=HEADERS, timeout=10)
        points_str = res.json().get("points", "0")
        # 核心修复：先转float，再转int，完美处理带小数点的积分
        total = int(float(points_str))
        msg.append(f"💰 当前总积分：{total}")
    except Exception as e:
        msg.append(f"💰 获取总积分失败：{str(e)}")

    # 3. 获取会员剩余天数
    days = 0
    try:
        res = requests.get(STATUS_URL, headers=HEADERS, timeout=10)
        days = int(float(res.json().get("data", {}).get("leftDays", 0)))
        msg.append(f"📅 会员剩余可用：{days} 天")
    except Exception as e:
        msg.append(f"📅 获取剩余天数失败：{str(e)}")

    # 4. 500积分自动兑换（仅这一个档位）
    if total >= 500:
        try:
            res = requests.post(EXCHANGE_URL, json={"planType": "plan500"}, headers=HEADERS, timeout=10)
            if res.json().get("code") == 0:
                msg.append("🎁 500积分兑换100天成功！")
            else:
                msg.append(f"❌ 兑换失败：{res.json().get('message', '未知错误')}")
        except Exception as e:
            msg.append(f"❌ 兑换请求异常：{str(e)}")
    else:
        msg.append(f"🎯 {total}/500 积分，暂不兑换")

    # 发送到手机
    content = "\n".join(msg)
    print("\n" + "="*50)
    print(content)
    print("="*50 + "\n")
    push_message(content)

if __name__ == "__main__":
    main()
