import urllib.request, json, datetime, time, os, xml.etree.ElementTree as ET
from urllib.parse import quote

DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
BARK_KEY = os.environ["BARK_KEY"]
BARK_URL = f"https://api.day.app/{BARK_KEY}"
CITY = "Yanji"

today_str = datetime.date.today().strftime("%Y年%m月%d日")
weekday = ["一","二","三","四","五","六","日"][datetime.date.today().weekday()]

# === 1. WEATHER ===
print("Fetching weather...")
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

# === 2. NEWS ===
print("Fetching news...")
news_entries = []
news_urls = [
    "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",
]
for url in news_urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        xml_data = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(xml_data)
        for item in root.iter("item"):
            title = item.find("title").text if item.find("title") is not None else ""
            source = item.find("source").text if item.find("source") is not None else ""
            news_entries.append(f"- {title}")
            if len(news_entries) >= 12:
                break
        if len(news_entries) >= 12:
            break
    except Exception as e:
        print(f"News source {url}: {e}")

news_text = "\n".join(news_entries[:12]) if news_entries else "新闻获取失败"

# === 3. DEEPSEEK ANALYSIS ===
print("Generating briefing...")
ds_req = urllib.request.Request(
    "https://api.deepseek.com/v1/chat/completions",
    data=json.dumps({
        "model": "deepseek-chat",
        "messages": [{
            "role": "user",
            "content": f"""今天是{today_str}，星期{weekday}。

{weather_text}

以下是今日要闻：
{news_text}

请生成一份早安简报，包含：
1. 天气提醒（一两句话）
2. 从要闻中选出2-3条最重要的政治经济大事，简要讲解其背景和影响（每条2-3句话）

语气自然简洁，不要啰嗦。总共控制在200字以内。"""
        }],
        "max_tokens": 500,
    }).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
)
ds_resp = json.loads(urllib.request.urlopen(ds_req, timeout=30).read())
brief = ds_resp["choices"][0]["message"]["content"].strip()

# === 4. BARK PUSH ===
print("Pushing to Bark...")
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
