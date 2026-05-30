import urllib.request, json, datetime, time, os, re
from urllib.parse import quote

DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
BARK_KEY = os.environ["BARK_KEY"]
BARK_URL = f"https://api.day.app/{BARK_KEY}"
CITY = "Yanji"

today_str = datetime.date.today().strftime("%Y年%m月%d日")
weekday = ["一","二","三","四","五","六","日"][datetime.date.today().weekday()]

# === 1. WEATHER ===
print("Fetching weather...")
weather_text = "延吉天气: (获取失败)"
for attempt in range(3):
    try:
        req = urllib.request.Request(
            f"https://wttr.in/{CITY}?format=j1",
            headers={"User-Agent": "curl/8.0"}
        )
        wdata = json.loads(urllib.request.urlopen(req, timeout=10).read())
        cc = wdata["current_condition"][0]
        tw = wdata["weather"][0]
        weather_text = (
            f"延吉天气: {cc['weatherDesc'][0]['value']}, {cc['temp_C']}°C"
            f"(体感{cc['FeelsLikeC']}°C), 最高{tw['maxtempC']}°C/最低{tw['mintempC']}°C, "
            f"湿度{cc['humidity']}%, 风速{cc['windspeedKmph']}km/h"
        )
        print(f"  Weather OK")
        break
    except Exception as e:
        print(f"  Weather attempt {attempt+1}: {e}")
        time.sleep(2)

# === 2. NEWS ===
print("Fetching news...")
feeds = [
    ("People Daily", "http://www.people.com.cn/rss/politics.xml"),
    ("China Daily", "https://www.chinadaily.com.cn/rss/world_rss.xml"),
    ("RSSHub Toutiao", "https://rsshub.app/toutiao/hot"),
    ("BBC Chinese", "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"),
]
news_titles = []

for source_name, url in feeds:
    if news_titles:
        break
    try:
        print(f"  Trying {source_name}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; bot)"})
        xml_data = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
        print(f"  Got {len(xml_data)} bytes from {source_name}")
        titles = re.findall(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', xml_data)
        print(f"  Found {len(titles)} raw titles")
        for t in titles[2:]:
            t = t.strip()
            t = re.sub(r'<[^>]+>', '', t)
            t = re.sub(r'&[a-z]+;', '', t)
            if len(t) > 8 and t not in news_titles:
                news_titles.append(t)
                if len(news_titles) >= 15:
                    break
    except Exception as e:
        print(f"  {source_name} failed: {e}")

print(f"Total headlines: {len(news_titles)}")

# === 3. DEEPSEEK BRIEFING ===
if news_titles:
    print("Generating briefing with news...")
    news_text = "\n".join(f"- {t}" for t in news_titles[:15])
    ds_prompt = f"""今天是{today_str}，星期{weekday}。
【天气】{weather_text}
【新闻头条】{news_text}
请生成一份早安简报。要求：
1. 天气提醒（一句话，是否需要带伞、加外套等）
2. 从上面新闻头条中选2-3条最重要的政治经济事件，讲解背景和影响（每条2-3句话）
回复控制在300字以内。用纯文本，不要加emoji。"""
    try:
        ds_req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": ds_prompt}],
                "max_tokens": 500,
            }).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
        )
        ds_resp = json.loads(urllib.request.urlopen(ds_req, timeout=30).read())
        brief = ds_resp["choices"][0]["message"]["content"].strip()
        print(f"  Briefing generated ({len(brief)} chars)")
    except Exception as e:
        print(f"  DeepSeek failed: {e}")
        brief = f"{today_str} 星期{weekday}\n\n{weather_text}\n\n{news_text[:300]}"
else:
    print("  Weather-only mode")
    brief = f"{today_str} 星期{weekday}\n\n{weather_text}\n\n今日新闻源暂不可用，仅推送天气。"

# === 4. BARK PUSH ===
print("Pushing to Bark...")
title = brief.strip().split("\n")[0][:80] if brief else "早安简报"
body = brief.strip()[:1000]

for i in range(5):
    try:
        payload = json.dumps({
            "title": title,
            "body": body,
            "group": "morning",
            "isArchive": 1
        }).encode()
        req = urllib.request.Request(f"{BARK_URL}/push", data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        print(f"  Bark OK: {resp}")
        break
    except Exception as e:
        print(f"  Bark attempt {i+1}: {e}")
        time.sleep(5)

print("Done!")
