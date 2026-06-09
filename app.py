import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import anthropic
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GMAIL_USER = st.secrets.get("GMAIL_USER", "")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD", "")
ALERT_EMAIL = st.secrets.get("ALERT_EMAIL", "")

st.set_page_config(page_title="דשבורד מניות", page_icon="📈", layout="wide")
st.markdown('<h1>📈 דשבורד מניות — ניתוח יומי</h1>', unsafe_allow_html=True)
st.caption(f"עדכון אחרון: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.divider()

STOCKS = ["AMZN", "ESLT", "FSLR", "IDR", "NVDA", "TSLA", "TSM"]

def get_stock_info(stock):
    try:
        ticker = yf.Ticker(stock)
        info = ticker.fast_info
        price = round(info.last_price, 2)
        prev_close = round(info.previous_close, 2)
        change = round(((price - prev_close) / prev_close) * 100, 2)
        return price, change
    except:
        return None, None

def get_yahoo_news(stock):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={stock}&newsCount=5"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        news = []
        for item in data.get("news", []):
            news.append({"כותרת": item.get("title", ""), "מקור": item.get("publisher", "")})
        return news
    except:
        return []

def get_finnhub_news(stock):
    FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")
    url = f"https://finnhub.io/api/v1/company-news?symbol={stock}&from=2024-01-01&to=2099-01-01&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        news = []
        for item in data[:5]:
            news.append({"כותרת": item.get("headline", ""), "מקור": item.get("source", "Finnhub")})
        return news
    except:
        return []
        def get_reddit_posts(stock, limit=5):
    url = f"https://www.reddit.com/search.json?q={stock}+stock&limit={limit}&sort=new"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        posts = []
        for post in data["data"]["children"]:
            p = post["data"]
            posts.append({"כותרת": p["title"], "ציונים": p["score"], "תגובות": p["num_comments"]})
        return posts
    except:
        return []

def analyze_with_claude(stock, news, price, change):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        news_text = "\n".join([f"- {n['כותרת']}" for n in news])
        prompt = f"""אתה אנליסט פיננסי מנוסה. נתח את המניה הבאה ותן המלצה קצרה.

מניה: {stock}
מחיר נוכחי: ${price}
שינוי יומי: {change}%
חדשות אחרונות:
{news_text}

ענה בפורמט הזה בדיוק:
ציון סנטימנט: [מספר בין 1-10]
המלצה: [קנה / החזק / מכור]
סיבה: [משפט אחד קצר בעברית]"""
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"שגיאה: {e}"

def extract_score(analysis):
    try:
        for line in analysis.split("\n"):
            if "ציון סנטימנט" in line:
                score = int(''.join(filter(str.isdigit, line)))
                return score
    except:
        pass
    return 0

def send_alert_email(stock, analysis, price, change):
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = ALERT_EMAIL
        msg["Subject"] = f"התראת מניה: {stock} — ציון גבוה!"
        body = f"התראה מדשבורד המניות!\n\nמניה: {stock}\nמחיר: ${price}\nשינוי יומי: {change}%\n\nניתוח Claude:\n{analysis}\n\nעדכון: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        msg.attach(MIMEText(body, "plain", "utf-8"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"שגיאה בשליחת מייל: {e}")
        return False
        with st.sidebar:
    st.header("⚙️ הגדרות")
    stocks_input = st.text_area("מניות (אחת בשורה):", value="\n".join(STOCKS))
    selected_stocks = [s.strip() for s in stocks_input.split("\n") if s.strip()]
    st.divider()
    selected_stock = st.selectbox("🔍 בחר מניה:", selected_stocks)
    st.divider()
    alert_threshold = st.slider("🔔 שלח התראה כשציון מעל:", 1, 10, 7)
    st.divider()
    if st.button("🔄 רענן", use_container_width=True):
        st.rerun()

st.subheader("💰 מחירים עכשוויים")
cols = st.columns(len(selected_stocks))
for i, stock in enumerate(selected_stocks):
    price, change = get_stock_info(stock)
    if price:
        cols[i].metric(label=stock, value=f"${price}", delta=f"{change}%")

st.divider()

st.subheader(f"🧠 ניתוח Claude על {selected_stock}")
with st.spinner("Claude מנתח..."):
    price, change = get_stock_info(selected_stock)
    news = get_yahoo_news(selected_stock)
    finnhub_news = get_finnhub_news(selected_stock)
    news = news + finnhub_news

reddit_posts = get_reddit_posts(selected_stock)
all_news = news + [{"כותרת": p["כותרת"], "מקור": "Reddit"} for p in reddit_posts]
analysis = analyze_with_claude(selected_stock, all_news, price, change)
st.info(analysis)

score = extract_score(analysis)
if score >= alert_threshold:
    st.success(f"🔔 ציון גבוה ({score}/10) — שולח התראה במייל!")
    sent = send_alert_email(selected_stock, analysis, price, change)
    if sent:
        st.success("✅ מייל נשלח בהצלחה!")

st.divider()

st.subheader(f"📰 חדשות על {selected_stock}")
if news:
    for item in news:
        st.write(f"📌 {item['כותרת']} — *{item['מקור']}*")
else:
    st.warning("לא נמצאו חדשות")

st.divider()
st.subheader(f"💬 פוסטים מ-Reddit על {selected_stock}")
with st.spinner("שואב פוסטים מ-Reddit..."):
    reddit_posts = get_reddit_posts(selected_stock)

if reddit_posts:
    for post in reddit_posts:
        with st.expander(post["כותרת"]):
            col1, col2 = st.columns(2)
            col1.metric("ציונים", post["ציונים"])
            col2.metric("תגובות", post["תגובות"])
else:
    st.warning("לא נמצאו פוסטים מ-Reddit")
