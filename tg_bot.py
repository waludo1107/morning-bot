import urllib.request, json, os, time

TG_TOKEN = os.environ["TG_TOKEN"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
BASE = f"https://api.telegram.org/bot{TG_TOKEN}"

# Track processed updates to avoid double-reply
STATE_FILE = "/tmp/tg_bot_state.json"

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"last_update": 0, "processed": []}

def save_state(s):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(s, f)
    except:
        pass

def tg(method, data=None):
    url = f"{BASE}/{method}"
    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    return json.loads(urllib.request.urlopen(req, timeout=20).read())

# Your personal context
SYSTEM_PROMPT = """你是waludo的AI助手，已陪伴他多日。以下信息你必须记住：

【用户身份】
- 延边大学 中国少数民族语言文学专业 2025级（大一）
- 回族，共青团员，家乡吉林松原
- 每月生活费2800元，预算紧张
- 最近搬出寝室短租

【用户目标】
- 计划毕业后考江浙二三线城市公务员（镇江、常州、无锡等）
- 中国语言文学类（中文文秘类）可报331个江苏岗+449个浙江岗
- TOPIK韩语等级考试作为加分项
- 不入党（名额被班干部占了），不走选调生路线

【用户性格】
- 喜欢独处、讨厌别人窥探隐私
- 经历初中被老师霸凌、父母不支持
- 正在努力重建生活：健身、学习撬锁、装机、Python脚本
- 喜欢三舅（李雪花故事里的东北硬汉）、麦克·厄门绍特、泰勒·德顿
- 正在玩极乐迪斯科

回复要求：自然、简洁、像认识他很久的朋友。结尾带"喵"。"""

def chat(messages, chat_id):
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": messages[-1]["text"]}
        ],
        "max_tokens": 1000,
    }
    ds_req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
    )
    resp = json.loads(urllib.request.urlopen(ds_req, timeout=30).read())
    reply = resp["choices"][0]["message"]["content"].strip()
    tg("sendMessage", {"chat_id": chat_id, "text": reply})

# Main
state = load_state()
print(f"Checking updates after {state['last_update']}...")

try:
    updates = tg("getUpdates", {"offset": state["last_update"] + 1, "timeout": 10})
    for upd in updates.get("result", []):
        uid = upd["update_id"]
        if uid in state["processed"]:
            continue
        state["processed"] = state["processed"][-100:] + [uid]  # keep last 100

        msg = upd.get("message", {})
        text = msg.get("text", "")
        chat_id = msg.get("chat", {}).get("id", 0)
        if text and chat_id:
            print(f"  Replying to {chat_id}: {text[:60]}")
            chat(messages=[{"text": text}], chat_id=chat_id)

        state["last_update"] = uid
    print("Done.")
except Exception as e:
    print(f"Error: {e}")

save_state(state)
