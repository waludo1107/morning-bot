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
news_titles = []

# Use rss2json as free proxy to fetch Google News RSS
rss_urls = [
    "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://news.google.com/rss/headlines/section/topic/WORLD?hl=zh-CN",
]
for rss_url in rss_urls:
    if len(news_titles) >= 12:
        break
    try:
        proxy_url = f"https://api.rss2json.com/v1/api.json?rss_url={quote(rss_url, safe='')}"
        print(f"  Trying rss2json...")
        req = urllib.request.Request(proxy_url, headers={"User-Agent": "MorningBot/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        if data.get("status") == "ok":
            for item in data.get("items", []):
                t = item.get("title", "").strip()
                if t and len(t) > 8 and t not in news_titles:
                    news_titles.append(t)
            print(f"  Got {len(news_titles)} titles so far")
    except Exception as e:
        print(f"  rss2json failed: {e}")

# Fallback: try direct Google News RSS (works on GitHub Actions US servers)
if not news_titles:
    try:
        req = urllib.request.Request(rss_urls[0], headers={"User-Agent": "curl/8.0"})
        xml_data = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
        titles = re.findall(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', xml_data)
        for t in titles[2:]:
            t = re.sub(r'<[^>]+>', '', t).strip()
            t = re.sub(r'&[a-z]+;', '', t)
            if len(t) > 8 and t not in news_titles:
                news_titles.append(t)
        print(f"  Direct RSS: {len(news_titles)} titles")
    except Exception as e:
        print(f"  Direct RSS failed: {e}")

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
