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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
}

.stApp {
    background-color: #000000;
    background-image: 
        linear-gradient(rgba(0,255,65,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,65,0.03) 1px, transparent 1px);
    background-size: 14px 14px;
}

.block-container {
    position: relative;
    z-index: 1;
}

h1, h2, h3 {
    color: #00ff41 !important;
    font-family: 'Share Tech Mono', monospace !important;
    text-align: right;
    text-shadow: 0 0 8px #00ff41;
}

.metric-card {
    background: rgba(0, 15, 0, 0.85);
    border: 1px solid rgba(0,255,65,0.4);
    border-radius: 10px;
    padding: 14px 16px;
    text-align: right;
    box-shadow: inset 0 0 20px rgba(0,255,65,0.05);
}

.metric-label {
    font-size: 11px;
    color: #00cc33;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
    font-family: 'Share Tech Mono', monospace;
}

.metric-value {
    font-size: 24px;
    font-weight: 500;
    color: #00ff41;
    font-family: 'Share Tech Mono', monospace;
    text-shadow: 0 0 6px rgba(0,255,65,0.5);
}

.metric-up { color: #4ade80; font-size: 13px; text-shadow: 0 0 4px rgba(74,222,128,0.5); }
.metric-dn { color: #f87171; font-size: 13px; text-shadow: 0 0 4px rgba(248,113,113,0.5); }

.analysis-card {
    background: rgba(0, 15, 0, 0.85);
    border: 1px solid rgba(0,255,65,0.4);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 12px;
    text-align: right;
    color: #00ee44;
    line-height: 1.8;
    font-family: 'Share Tech Mono', monospace;
    font-size: 14px;
}

.badge-buy  { background:#14532d; color:#4ade80; border:1px solid #00cc00; padding:4px 14px; border-radius:6px; font-size:12px; font-family:monospace; }
.badge-hold { background:#451a03; color:#fb923c; border:1px solid #fb923c; padding:4px 14px; border-radius:6px; font-size:12px; font-family:monospace; }
.badge-sell { background:#450a0a; color:#f87171; border:1px solid #f87171; padding:4px 14px; border-radius:6px; font-size:12px; font-family:monospace; }

.news-item {
    padding: 8px 0;
    border-bottom: 0.5px solid rgba(0,255,65,0.15);
    color: #00cc33;
    font-size: 13px;
    text-align: right;
    font-family: 'Share Tech Mono', monospace;
}

.section-title {
    font-size: 11px;
    font-weight: 500;
    color: #00aa00;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 10px;
    text-align: right;
    font-family: 'Share Tech Mono', monospace;
}

[data-testid="stSidebar"] {
    background-color: rgba(0, 10, 0, 0.95) !important;
    border-left: 1px solid rgba(0,255,65,0.2);
}

[data-testid="stMetricValue"] { color: #00ff41 !important; }
[data-testid="stMetricDelta"] { color: #4ade80 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="text-align:right">📈 דשבורד מניות — ניתוח יומי</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#00aa00;text-align:right">עדכון אחרון: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>', unsafe_allow_html=True)
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
                import re
                numbers = re.findall(r'\b([1-9]|10)\b', line)
                if numbers:
                    return int(numbers[0])
    except:
        pass
    return 0

def extract_recommendation(analysis):
    for line in analysis.split("\n"):
        if "המלצה" in line:
            if "קנה" in line: return "קנה"
            if "מכור" in line: return "מכור"
            if "החזק" in line: return "החזק"
    return "החזק"

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
    st.markdown('<p style="color:#00ff41;font-size:16px;font-weight:500;text-align:right">⚙️ הגדרות</p>', unsafe_allow_html=True)
    stocks_input = st.text_area("מניות (אחת בשורה):", value="\n".join(STOCKS))
    selected_stocks = [s.strip() for s in stocks_input.split("\n") if s.strip()]
    st.divider()
    selected_stock = st.selectbox("🔍 בחר מניה:", selected_stocks)
    st.divider()
    alert_threshold = st.slider("🔔 שלח התראה כשציון מעל:", 1, 10, 7)
    st.divider()
    if st.button("🔄 רענן", use_container_width=True):
        st.rerun()

st.markdown('<div class="section-title">מחירים עכשוויים</div>', unsafe_allow_html=True)
n = len(selected_stocks)
cols_per_row = 2 if n > 4 else n
rows = [selected_stocks[i:i+cols_per_row] for i in range(0, n, cols_per_row)]
for row_stocks in rows:
    cols = st.columns(len(row_stocks), gap="small")
    for i, stock in enumerate(row_stocks):
        price, change = get_stock_info(stock)
        if price:
            delta_class = "metric-up" if change >= 0 else "metric-dn"
            arrow = "▲" if change >= 0 else "▼"
            cols[i].markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{stock}</div>
                <div class="metric-value">${price}</div>
                <div class="{delta_class}">{arrow} {change}%</div>
            </div>
            """, unsafe_allow_html=True)
            <div class="metric-label">{stock}</div>
            <div class="metric-value">${price}</div>
            <div class="{delta_class}">{arrow} {change}%</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

st.markdown(f'<div class="section-title">ניתוח Claude — {selected_stock}</div>', unsafe_allow_html=True)
with st.spinner("Claude מנתח..."):
    price, change = get_stock_info(selected_stock)
    news = get_yahoo_news(selected_stock)
    finnhub_news = get_finnhub_news(selected_stock)
    news = news + finnhub_news
    reddit_posts = get_reddit_posts(selected_stock)
    all_news = news + [{"כותרת": p["כותרת"], "מקור": "Reddit"} for p in reddit_posts]
    analysis = analyze_with_claude(selected_stock, all_news, price, change)

rec = extract_recommendation(analysis)
badge_class = "badge-buy" if rec == "קנה" else "badge-sell" if rec == "מכור" else "badge-hold"
st.markdown(f'<span class="{badge_class}">{rec}</span>', unsafe_allow_html=True)
st.markdown(f'<div class="analysis-card">{analysis}</div>', unsafe_allow_html=True)

score = extract_score(analysis)
if score >= alert_threshold:
    st.success(f"🔔 ציון גבוה ({score}/10) — שולח התראה במייל!")
    sent = send_alert_email(selected_stock, analysis, price, change)
    if sent:
        st.success("✅ מייל נשלח בהצלחה!")
st.divider()

st.markdown('<div class="section-title">המלצות לכל המניות</div>', unsafe_allow_html=True)
rec_cols = st.columns(len(selected_stocks))
for i, stock in enumerate(selected_stocks):
    price, change = get_stock_info(stock)
    if price:
        news_tmp = get_yahoo_news(stock)
        analysis_tmp = analyze_with_claude(stock, news_tmp, price, change)
        rec_tmp = extract_recommendation(analysis_tmp)
        score_tmp = extract_score(analysis_tmp)
        badge = "badge-buy" if rec_tmp == "קנה" else "badge-sell" if rec_tmp == "מכור" else "badge-hold"
        arrow = "▲" if change >= 0 else "▼"
        delta_class = "metric-up" if change >= 0 else "metric-dn"
        rec_cols[i].markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{stock}</div>
            <div class="metric-value">${price}</div>
            <div class="{delta_class}">{arrow} {change}%</div>
            <div style="margin-top:8px">
                <div class="strack-wrap" style="height:3px;background:rgba(0,200,0,0.15);border-radius:2px;margin-bottom:6px">
                    <div style="width:{score_tmp*10}%;height:100%;background:{'#4ade80' if score_tmp>=7 else '#fb923c' if score_tmp>=5 else '#f87171'};border-radius:2px"></div>
                </div>
                <span class="{badge}">{rec_tmp}</span>
                <span style="font-size:11px;color:#00aa00;margin-right:6px">{score_tmp}/10</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

st.markdown(f'<div class="section-title">גרף שנה אחרונה — {selected_stock}</div>', unsafe_allow_html=True)

try:
    import plotly.graph_objects as go
    hist = yf.Ticker(selected_stock).history(period="1y")
    if not hist.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index,
            y=hist['Close'],
            mode='lines',
            line=dict(color='#00ff41', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(0,255,65,0.05)',
            name=selected_stock
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,15,0,0.85)',
            font=dict(color='#00aa00', family='monospace'),
            margin=dict(l=40, r=20, t=20, b=40),
            height=300,
            xaxis=dict(
                gridcolor='rgba(0,255,65,0.1)',
                showgrid=True,
                color='#00aa00'
            ),
            yaxis=dict(
                gridcolor='rgba(0,255,65,0.1)',
                showgrid=True,
                color='#00aa00'
            ),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("לא נמצאו נתונים היסטוריים")
except Exception as e:
    st.warning(f"שגיאה בטעינת גרף: {e}")

st.divider()

st.markdown('<div class="section-title">חדשות אחרונות</div>', unsafe_allow_html=True)
if news:
    for item in news:
        st.markdown(f'<div class="news-item">📌 {item["כותרת"]} — <span style="color:#006600">{item["מקור"]}</span></div>', unsafe_allow_html=True)
else:
    st.warning("לא נמצאו חדשות")

st.divider()

st.markdown(f'<div class="section-title">פוסטים מ-Reddit — {selected_stock}</div>', unsafe_allow_html=True)
if reddit_posts:
    for post in reddit_posts:
        with st.expander(post["כותרת"]):
            col1, col2 = st.columns(2)
            col1.metric("ציונים", post["ציונים"])
            col2.metric("תגובות", post["תגובות"])
else:
    st.warning("לא נמצאו פוסטים מ-Reddit")
