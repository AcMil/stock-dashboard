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

# מפתחות
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GMAIL_USER = "romank199018@gmail.com"
GMAIL_PASSWORD = "exgvveglgicvwggk"
ALERT_EMAIL = "romank199018@gmail.com"

st.set_page_config(
    page_title="דשבורד מניות",
    page_icon="📈",
    layout="wide"
)

st.markdown('<h1>📈 דשבורד מניות — ניתוח יומי</h1>', unsafe_allow_html=True)
st.caption(f"עדכון אחרון: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.divider()

STOCKS = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]

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
            news.append({
                "כותרת": item.get("title", ""),
                "מקור": item.get("publisher", "")
            })
        return news
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
        
        body = f"""
התראה מדשבורד המניות שלך!

מניה: {stock}
מחיר: ${price}
שינוי יומי: {change}%

ניתוח Claude:
{analysis}

עדכון: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
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

# סרגל צד
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

# כרטיסי מחיר
st.subheader("💰 מחירים עכשוויים")
cols = st.columns(len(selected_stocks))
for i, stock in enumerate(selected_stocks):
    price, change = get_stock_info(stock)
    if price:
        cols[i].metric(
            label=stock,
            value=f"${price}",
            delta=f"{change}%"
        )

st.divider()

# ניתוח Claude
st.subheader(f"🧠 ניתוח Claude על {selected_stock}")
with st.spinner("Claude מנתח..."):
    price, change = get_stock_info(selected_stock)
    news = get_yahoo_news(selected_stock)
    analysis = analyze_with_claude(selected_stock, news, price, change)

st.info(analysis)

# שליחת התראה אם ציון גבוה
score = extract_score(analysis)
if score >= alert_threshold:
    st.success(f"🔔 ציון גבוה ({score}/10) — שולח התראה במייל!")
    sent = send_alert_email(selected_stock, analysis, price, change)
    if sent:
        st.success("✅ מייל נשלח בהצלחה!")

st.divider()

# חדשות
st.subheader(f"📰 חדשות על {selected_stock}")
if news:
    for item in news:
        st.write(f"📌 {item['כותרת']} — *{item['מקור']}*")
else:
    st.warning("לא נמצאו חדשות")