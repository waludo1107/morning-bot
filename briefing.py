import urllib.request, json, datetime, time, os
from urllib.parse import quote

DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
BARK_KEY = os.environ["BARK_KEY"]
BARK_URL = f"https://api.day.app/{BARK_KEY}"
CITY = "Yanji"

today_str = datetime.date.today().strftime("%Y年%m月%d日")
weekday = ["一","二","三","四","五","六","日"][datetime.date.today().weekday()]

# 1. Weather
weather_text = None
for attempt in range(3):
    try:
        req = urllib.request.Request(
            f"https://wttr.in/{CITY}?format=j1",
            headers={"User-Agent": "curl/8.0"}
        )
        wdata = json.loads(urllib.request.urlopen(req, timeout=10).read())
        cc = wdata["current_condition"][0]
        tw = wdata["weather"][0]
        weather_text = f"延吉天气: {cc['weatherDesc'][0]['value']}, {cc['temp_C']}°C(体感{cc['FeelsLikeC']}°C), 最高{tw['maxtempC']}°C/最低{tw['mintempC']}°C, 湿度{cc['humidity']}%, 风速{cc['windspeedKmph']}km/h"
        break
    except Exception as e:
        print(f"Weather attempt {attempt+1}: {e}")
        time.sleep(2)

if not weather_text:
    weather_text = "延吉天气: (获取失败)"

# 2. DeepSeek
ds_req = urllib.request.Request(
    "https://api.deepseek.com/v1/chat/completions",
    data=json.dumps({
        "model": "deepseek-chat",
        "messages": [{
            "role": "user",
            "content": f"今天是{today_str}，星期{weekday}。延吉天气：{weather_text}\n\n请用一两句话生成简短早安简报，提醒天气注意事项。语气自然简洁。"
        }],
        "max_tokens": 150,
    }).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
)
ds_resp = json.loads(urllib.request.urlopen(ds_req, timeout=30).read())
brief = ds_resp["choices"][0]["message"]["content"].strip()

# 3. Bark push
brief_short = brief.split("\n")[0][:120]
for i in range(5):
    try:
        bark_url = f"{BARK_URL}/{quote('morning')}/{quote(brief_short)}?isArchive=1"
        resp = json.loads(urllib.request.urlopen(urllib.request.Request(bark_url, method="POST"), timeout=10).read())
        print(f"Bark: {resp}")
        break
    except Exception as e:
        print(f"Bark attempt {i+1}: {e}")
        time.sleep(5)

print("Done!")
