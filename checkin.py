import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

COOKIE = os.getenv("GLADOS_COOKIE", "").strip().replace("\n", "")
PUSH_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
STATE_FILE = Path(".glados-checkin-state.json")

BASE = "https://glados.cloud/api/user"
HEADERS = {"Cookie": COOKIE, "Content-Type": "application/json"}
today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


def get(url):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.json()


def push(content):
    if PUSH_TOKEN:
        requests.post(
            "https://www.pushplus.plus/send",
            json={
                "token": PUSH_TOKEN,
                "title": "GLaDOS自动签到",
                "content": content,
                "template": "txt",
            },
            timeout=15,
        )


def main():
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    msg = []

    try:
        response = requests.post(
            f"{BASE}/checkin",
            json={"token": "glados.cloud"},
            headers=HEADERS,
            timeout=10,
        )
        data = response.json()
        text = str(data.get("message", ""))
        api_points = int(float(data.get("points", 0)))

        is_new = "Checkin! Got" in text
        is_repeat = "Checkin Repeats" in text or "Today's observation logged" in text

        if is_new:
            msg.append("✅ 签到成功")
        elif is_repeat:
            msg.append("ℹ️ 今日已签到，无需重复操作")
        else:
            raise RuntimeError(text or "未知签到错误")

        total = int(float(get(f"{BASE}/points").get("points", 0)))

        # 同一天直接读取第一次保存的奖励；新的一天则和昨天总积分相减。
        if state.get("date") == today:
            earned = state["earned"]
        elif is_new and api_points > 0:
            earned = api_points
        else:
            earned = max(0, total - int(state.get("total", total)))

        msg.append(f"🎁 今日获取积分：{earned}")
        msg.append(f"💰 当前总积分：{total}")

        days = int(float(get(f"{BASE}/status").get("data", {}).get("leftDays", 0)))
        msg.append(f"📅 会员剩余可用：{days} 天")

        if total >= 500:
            exchange = requests.post(
                f"{BASE}/exchange",
                json={"planType": "plan500"},
                headers=HEADERS,
                timeout=10,
            ).json()

            if exchange.get("code") == 0:
                msg.append("🎁 500积分兑换100天成功！")
                total = int(float(get(f"{BASE}/points").get("points", 0)))
            else:
                msg.append(f"❌ 兑换失败：{exchange.get('message', '未知错误')}")
        else:
            msg.append(f"🎯 {total}/500 积分，暂不兑换")

        STATE_FILE.write_text(
            json.dumps(
                {"date": today, "earned": earned, "total": total},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    except Exception as error:
        msg.append(f"❌ 执行失败：{error}")

    content = "\n".join(msg)
    print(content)
    push(content)


if __name__ == "__main__":
    main()
