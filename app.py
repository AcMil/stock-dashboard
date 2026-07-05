import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import anthropic
import os
import smtplib
import time
import json
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GMAIL_USER = st.secrets.get("GMAIL_USER", "")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD", "")
ALERT_EMAIL = st.secrets.get("ALERT_EMAIL", "")
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")

# SEC דורש User-Agent עם פרטי קשר. מומלץ להוסיף ב-Secrets:
# SEC_USER_AGENT = "StockDashboard your-email@gmail.com"
SEC_HEADERS = {"User-Agent": st.secrets.get("SEC_USER_AGENT", "PersonalStockDashboard contact@example.com")}

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
    padding: 12px;
    text-align: right;
    box-shadow: inset 0 0 20px rgba(0,255,65,0.05);
    width: 100%;
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

st.markdown('''
<h1 style="text-align:right; font-size:clamp(1rem, 4vw, 2.2rem); white-space:nowrap; overflow:hidden; text-overflow:ellipsis">
📈 דשבורד מניות — ניתוח יומי
</h1>
''', unsafe_allow_html=True)
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

with st.expander("⚙️ הגדרות", expanded=False):
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        stocks_input = st.text_area("מניות (אחת בשורה):", value="\n".join(STOCKS), height=150)
        selected_stocks = [s.strip() for s in stocks_input.split("\n") if s.strip()]
    with col_s2:
        selected_stock = st.selectbox("🔍 בחר מניה:", selected_stocks)
        alert_threshold = st.slider("🔔 התראה כשציון מעל:", 1, 10, 7)
    with col_s3:
        st.write("")
        st.write("")
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


# ============================================================
# 🛰️ מרכז האיתותים — שליפה ישירה בקוד (בלי Make.com)
# מקורות: SEC EDGAR, Capitol Trades / Senate Stock Watcher,
# Yahoo Finance (נפח), Finnhub (דוחות), CNN (Fear & Greed)
# ============================================================

# ---------- Fear & Greed ----------

@st.cache_data(ttl=3600, show_spinner=False)
def get_fear_greed():
    """מדד פחד/חמדנות של CNN, עם fallback ל-alternative.me"""
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            timeout=10,
        )
        score = int(round(r.json()["fear_and_greed"]["score"]))
        return score, "CNN"
    except Exception:
        pass
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        score = int(r.json()["data"][0]["value"])
        return score, "Crypto F&G"
    except Exception:
        return None, None

def fear_greed_label(score):
    if score is None: return "—"
    if score <= 24: return "פחד קיצוני"
    if score <= 44: return "פחד"
    if score <= 55: return "נייטרלי"
    if score <= 75: return "חמדנות"
    return "חמדנות קיצונית"

# ---------- SEC EDGAR — תשתית ----------

@st.cache_data(ttl=86400, show_spinner=False)
def sec_cik_map():
    """מיפוי טיקר → מספר CIK (מזהה חברה ב-SEC)"""
    try:
        r = requests.get("https://www.sec.gov/files/company_tickers.json",
                         headers=SEC_HEADERS, timeout=20)
        data = r.json()
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    except Exception:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def sec_submissions(cik10):
    """כל הדיווחים האחרונים של חברה"""
    try:
        r = requests.get(f"https://data.sec.gov/submissions/CIK{cik10}.json",
                         headers=SEC_HEADERS, timeout=20)
        return r.json()
    except Exception:
        return {}

def _recent_filings(subs, form_type, limit=3, days=None):
    """מסנן דיווחים לפי סוג טופס ותקופה"""
    out = []
    try:
        recent = subs["filings"]["recent"]
        forms = recent.get("form", [])
        items_list = recent.get("items", [""] * len(forms))
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d") if days else None
        for i, form in enumerate(forms):
            if form != form_type:
                continue
            fdate = recent["filingDate"][i]
            if cutoff and fdate < cutoff:
                continue
            out.append({
                "accession": recent["accessionNumber"][i],
                "date": fdate,
                "primary": recent["primaryDocument"][i],
                "items": items_list[i] if i < len(items_list) else "",
            })
            if len(out) >= limit:
                break
    except Exception:
        pass
    return out

def _sec_doc_url(cik10, accession, primary_doc):
    acc = accession.replace("-", "")
    doc = primary_doc.split("/")[-1]
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik10)}/{acc}/{doc}"

# ---------- סעיף: רכישות אנשי פנים (Form 4) ----------

@st.cache_data(ttl=3600, show_spinner=False)
def sec_form4_details(cik10, accession, primary_doc):
    """מפענח טופס 4 בודד: מי, מה התפקיד, קנה/מכר, בכמה"""
    try:
        url = _sec_doc_url(cik10, accession, primary_doc)
        if not url.endswith(".xml"):
            return None
        r = requests.get(url, headers=SEC_HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.content)

        owner = root.findtext(".//rptOwnerName", "") or "—"
        title = root.findtext(".//officerTitle", "") or ""
        if not title:
            if (root.findtext(".//isDirector", "") or "").strip() in ("1", "true"):
                title = "דירקטור"
            elif (root.findtext(".//isTenPercentOwner", "") or "").strip() in ("1", "true"):
                title = "בעל עניין 10%+"
            else:
                title = "איש פנים"

        buy_val = sell_val = buy_sh = sell_sh = 0.0
        for tx in root.findall(".//nonDerivativeTransaction"):
            code = (tx.findtext(".//transactionCode", "") or "").strip()
            try:
                shares = float(tx.findtext(".//transactionShares/value", "0") or 0)
                price = float(tx.findtext(".//transactionPricePerShare/value", "0") or 0)
            except ValueError:
                continue
            if code == "P":      # רכישה בשוק הפתוח
                buy_sh += shares
                buy_val += shares * price
            elif code == "S":    # מכירה
                sell_sh += shares
                sell_val += shares * price

        if buy_sh == 0 and sell_sh == 0:
            return None  # רק הענקות/אופציות — לא מעניין

        return {
            "owner": owner, "title": title,
            "buy_val": buy_val, "sell_val": sell_val,
            "buy_sh": buy_sh, "sell_sh": sell_sh,
        }
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def get_insider_trades(tickers, days=30):
    """כניסות אנשי פנים מ-SEC EDGAR עבור רשימת מניות"""
    ciks = sec_cik_map()
    results = []
    for t in tickers:
        cik = ciks.get(t.upper())
        if not cik:
            continue
        subs = sec_submissions(cik)
        for f in _recent_filings(subs, "4", limit=4, days=days):
            d = sec_form4_details(cik, f["accession"], f["primary"])
            time.sleep(0.15)  # נימוס כלפי SEC (מקס' 10 בקשות/שנייה)
            if d:
                is_buy = d["buy_val"] >= d["sell_val"]
                d.update({
                    "ticker": t.upper(),
                    "date": f["date"],
                    "is_buy": is_buy,
                    "value": d["buy_val"] if is_buy else d["sell_val"],
                    "url": _sec_doc_url(cik, f["accession"], f["primary"]),
                })
                results.append(d)
    results.sort(key=lambda x: x["date"], reverse=True)
    return results

# ---------- סעיף: הודעות 8-K ----------

ITEM_8K_MAP = {
    "1.01": "הסכם מהותי חדש",
    "1.02": "סיום הסכם מהותי",
    "1.03": "פשיטת רגל / כינוס נכסים",
    "2.01": "השלמת רכישה או מכירת נכסים",
    "2.02": "פרסום תוצאות כספיות",
    "2.03": "התחייבות פיננסית חדשה",
    "3.01": "הודעת בורסה / אי-עמידה בדרישות",
    "4.01": "החלפת רואה חשבון",
    "5.02": "שינוי בהנהלה / דירקטוריון",
    "5.03": "שינוי בתקנון",
    "5.07": "תוצאות הצבעת בעלי מניות",
    "7.01": "גילוי לפי Regulation FD",
    "8.01": "אירוע מהותי אחר",
    "9.01": "נספחים ודוחות כספיים",
}

@st.cache_data(ttl=3600, show_spinner=False)
def get_8k_filings(tickers, days=14):
    """הודעות 8-K אחרונות (אירועים מהותיים) עבור רשימת מניות"""
    ciks = sec_cik_map()
    results = []
    for t in tickers:
        cik = ciks.get(t.upper())
        if not cik:
            continue
        subs = sec_submissions(cik)
        for f in _recent_filings(subs, "8-K", limit=3, days=days):
            item_codes = [c.strip() for c in (f["items"] or "").split(",") if c.strip()]
            descs = [ITEM_8K_MAP.get(c, c) for c in item_codes if c != "9.01"] or ["דיווח 8-K"]
            results.append({
                "ticker": t.upper(),
                "date": f["date"],
                "items": " • ".join(descs),
                "is_earnings": "2.02" in item_codes,
                "url": _sec_doc_url(cik, f["accession"], f["primary"]),
            })
        time.sleep(0.1)
    results.sort(key=lambda x: x["date"], reverse=True)
    return results

# ---------- סעיף: פעולות חברי קונגרס ----------

@st.cache_data(ttl=21600, show_spinner=False)
def get_congress_trades(tickers, days=90):
    """
    עסקאות של חברי קונגרס. מקורות לא-רשמיים (חינמיים) —
    עלולים להתעדכן באיחור או להפסיק לעבוד.
    """
    tick_set = {t.upper() for t in tickers}
    cutoff = datetime.now() - timedelta(days=days)
    trades = []

    # מקור 1: Capitol Trades (API לא רשמי)
    for t in tick_set:
        for fmt in (f"{t}:US", t):
            try:
                r = requests.get(
                    "https://bff.capitoltrades.com/trades",
                    params={"ticker": fmt, "pageSize": 8},
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                )
                if r.status_code != 200:
                    continue
                data = r.json().get("data", []) or []
                for it in data:
                    pol = it.get("politician") or {}
                    name = f'{pol.get("firstName", "")} {pol.get("lastName", "")}'.strip()
                    chamber = pol.get("chamber", "")
                    chamber_he = "סנאט" if "sen" in str(chamber).lower() else "בית הנבחרים" if chamber else ""
                    tx_type = str(it.get("txType", "")).lower()
                    tx_date = str(it.get("txDate", ""))[:10]
                    try:
                        if datetime.strptime(tx_date, "%Y-%m-%d") < cutoff:
                            continue
                    except ValueError:
                        pass
                    trades.append({
                        "ticker": t,
                        "name": name or "חבר קונגרס",
                        "role": chamber_he,
                        "date": tx_date,
                        "is_buy": "buy" in tx_type or "purchase" in tx_type,
                        "is_sell": "sell" in tx_type or "sale" in tx_type,
                        "amount": it.get("value") or it.get("size") or "",
                    })
                if data:
                    break
            except Exception:
                continue
    if trades:
        trades.sort(key=lambda x: x["date"], reverse=True)
        return trades, "Capitol Trades (לא רשמי)"

    # מקור 2 (גיבוי): Senate Stock Watcher
    try:
        r = requests.get(
            "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json",
            timeout=30,
        )
        data = r.json()
        for it in data:
            t = str(it.get("ticker", "")).upper()
            if t not in tick_set:
                continue
            raw_date = it.get("transaction_date", "")
            try:
                d = datetime.strptime(raw_date, "%m/%d/%Y")
            except ValueError:
                continue
            if d < cutoff:
                continue
            tx_type = str(it.get("type", "")).lower()
            trades.append({
                "ticker": t,
                "name": it.get("senator", "סנטור"),
                "role": "סנאט",
                "date": d.strftime("%Y-%m-%d"),
                "is_buy": "purchase" in tx_type,
                "is_sell": "sale" in tx_type,
                "amount": it.get("amount", ""),
            })
        trades.sort(key=lambda x: x["date"], reverse=True)
        return trades, "Senate Stock Watcher (לא רשמי)"
    except Exception:
        return [], None

# ---------- סעיף: נפח מסחר חריג ----------

@st.cache_data(ttl=1800, show_spinner=False)
def get_volume_anomalies(tickers, threshold=2.0):
    """משווה נפח יומי אחרון לממוצע 30 יום (מקור: Yahoo Finance)"""
    out = []
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="3mo")
            if len(hist) < 25:
                continue
            last_vol = float(hist["Volume"].iloc[-1])
            avg_vol = float(hist["Volume"].iloc[-31:-1].mean())
            if avg_vol <= 0:
                continue
            ratio = last_vol / avg_vol
            if ratio >= threshold:
                day_change = 0.0
                try:
                    day_change = round(
                        (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100, 1
                    )
                except Exception:
                    pass
                out.append({"ticker": t.upper(), "ratio": round(ratio, 1), "change": day_change})
        except Exception:
            continue
    out.sort(key=lambda x: x["ratio"], reverse=True)
    return out

# ---------- סעיף: לוח אירועים ----------

# מועדי החלטות ריבית של הפד לשנת 2026 (היום השני של כל ישיבה).
# לוח קבוע שמתפרסם מראש — לעדכן ידנית בתחילת כל שנה.
FOMC_DATES = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]

@st.cache_data(ttl=21600, show_spinner=False)
def get_upcoming_events(tickers, days=21):
    """דוחות רבעוניים קרובים (Finnhub) + החלטות ריבית"""
    events = []
    today = datetime.now().date()
    to_date = today + timedelta(days=days)

    if FINNHUB_API_KEY:
        for t in tickers:
            try:
                r = requests.get(
                    "https://finnhub.io/api/v1/calendar/earnings",
                    params={
                        "from": today.isoformat(),
                        "to": to_date.isoformat(),
                        "symbol": t,
                        "token": FINNHUB_API_KEY,
                    },
                    timeout=10,
                )
                for e in (r.json() or {}).get("earningsCalendar", []):
                    events.append({
                        "date": e.get("date", ""),
                        "ticker": t.upper(),
                        "type": "דוח רבעוני",
                        "importance": "high",
                        "eps_est": e.get("epsEstimate"),
                    })
                time.sleep(0.1)
            except Exception:
                continue

    for d in FOMC_DATES:
        try:
            dd = datetime.strptime(d, "%Y-%m-%d").date()
            if today <= dd <= to_date:
                events.append({
                    "date": d, "ticker": "FED",
                    "type": 'החלטת ריבית — ארה"ב',
                    "importance": "high", "eps_est": None,
                })
        except ValueError:
            continue

    events.sort(key=lambda x: x["date"])
    return events

# ---------- סיכום: לוגיקת שקלול איתותים ----------
# הערה: מ-1.8, כשה-API חוזר, מחליפים רק את הפונקציה הזו
# בקריאה ל-Claude — שאר הדשבורד לא משתנה.

def build_summary(tickers, insider, congress, filings_8k, volume, events):
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    two_weeks = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    soon = (datetime.now() + timedelta(days=7)).date()
    summary = []

    for t in tickers:
        t = t.upper()
        score = 0
        reasons = []

        ins = [x for x in insider if x["ticker"] == t and x["date"] >= two_weeks]
        if any(x["is_buy"] for x in ins):
            score += 2
            reasons.append("אנשי פנים קנו")
        if any(not x["is_buy"] for x in ins):
            score -= 1
            reasons.append("אנשי פנים מכרו")

        cong = [x for x in congress if x["ticker"] == t and x["date"] >= two_weeks]
        if any(x["is_buy"] for x in cong):
            score += 1
            reasons.append("חברי קונגרס קנו")
        if any(x.get("is_sell") for x in cong):
            score -= 1
            reasons.append("חברי קונגרס מכרו")

        vol = next((x for x in volume if x["ticker"] == t), None)
        if vol:
            reasons.append(f"נפח פי {vol['ratio']} מהממוצע")

        f8k = [x for x in filings_8k if x["ticker"] == t and x["date"] >= week_ago]
        if f8k:
            reasons.append("דיווח 8-K טרי")

        ev = next(
            (x for x in events
             if x["ticker"] == t and x["date"] and
             datetime.strptime(x["date"], "%Y-%m-%d").date() <= soon),
            None,
        )
        if ev:
            reasons.append(f"דוח רבעוני ב-{datetime.strptime(ev['date'], '%Y-%m-%d').strftime('%d/%m')}")

        n_signals = len(reasons)
        if score >= 2:
            rec, badge = "שקול להגדיל", "badge-buy"
            label = "הגדל"
        elif score <= -2:
            rec, badge = "שקול להקטין", "badge-sell"
            label = "היזהר"
        elif score < 0:
            rec, badge = "היזהר", "badge-hold"
            label = "היזהר"
        elif n_signals >= 2:
            rec, badge = "עקוב מקרוב", "badge-hold"
            label = "עקוב"
        else:
            rec, badge = "אין שינוי", "badge-buy"
            label = "החזק"

        summary.append({
            "ticker": t, "rec": rec, "badge": badge, "label": label,
            "reasons": " + ".join(reasons) if reasons else "אין איתותים חריגים השבוע",
            "n_signals": n_signals, "score": score,
        })

    summary.sort(key=lambda x: (-abs(x["score"]), -x["n_signals"]))
    return summary

# ---------- איסוף הנתונים ----------

st.divider()
st.markdown('<h3 style="text-align:right">🛰️ מרכז האיתותים</h3>', unsafe_allow_html=True)

with st.spinner("אוסף איתותים מ-SEC, Finnhub ומקורות נוספים..."):
    fg_score, fg_source = get_fear_greed()
    insider_trades = get_insider_trades(selected_stocks)
    filings_8k = get_8k_filings(selected_stocks)
    congress_trades, congress_source = get_congress_trades(selected_stocks)
    volume_alerts = get_volume_anomalies(selected_stocks)
    upcoming_events = get_upcoming_events(selected_stocks)
    portfolio_summary = build_summary(
        selected_stocks, insider_trades, congress_trades,
        filings_8k, volume_alerts, upcoming_events,
    )

week_ago_str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
new_signals = (
    len([x for x in insider_trades if x["date"] >= week_ago_str])
    + len([x for x in filings_8k if x["date"] >= week_ago_str])
    + len([x for x in congress_trades if x["date"] >= week_ago_str])
    + len(volume_alerts)
)
earnings_this_week = len([
    x for x in upcoming_events
    if x["date"] and datetime.strptime(x["date"], "%Y-%m-%d").date()
    <= (datetime.now() + timedelta(days=7)).date()
])

# ---------- שורת מדדים עליונה ----------

hdr = st.columns(4, gap="small")
hdr_items = [
    ("אירועים השבוע", f"{earnings_this_week}", "דוחות והחלטות"),
    ("מצב שוק כללי", f"{fg_score if fg_score is not None else '—'}", fear_greed_label(fg_score)),
    ("איתותים חדשים", f"{new_signals}", "7 ימים אחרונים"),
    ("עדכון אחרון", datetime.now().strftime("%H:%M"), "רענון כל שעה"),
]
for col, (label, value, sub) in zip(hdr, hdr_items):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div style="font-size:11px;color:#00aa00">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------- 1. פעולות חברי קונגרס ----------

st.divider()
st.markdown('<div class="section-title">🏛️ פעולות חברי קונגרס — מקור לא רשמי</div>', unsafe_allow_html=True)
st.markdown('''
<div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
מדוע זה רלוונטי: חברי קונגרס מחויבים לדווח על עסקאות תוך 45 יום. היסטורית הם קונים לפני חוזים ממשלתיים ורגולציה חיובית.
שים לב: המקור אינו רשמי ועלול להתעדכן באיחור.
</div>
''', unsafe_allow_html=True)

if congress_trades:
    for tr in congress_trades[:6]:
        badge = "badge-buy" if tr["is_buy"] else "badge-sell" if tr.get("is_sell") else "badge-hold"
        label = "קנה" if tr["is_buy"] else "מכר" if tr.get("is_sell") else "עסקה"
        amount = f' | 💰 {tr["amount"]}' if tr.get("amount") else ""
        role = f' ({tr["role"]})' if tr.get("role") else ""
        st.markdown(f'''
        <div class="metric-card" style="margin-bottom:10px">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
                <span style="font-size:18px; color:#00ff41; font-family:monospace">{tr["ticker"]}</span>
                <span class="{badge}">{label}</span>
            </div>
            <div style="color:#00aa00; font-size:12px">👤 {tr["name"]}{role}{amount}</div>
            <div style="color:#008800; font-size:11px; margin-top:4px">דווח: {tr["date"]} · מקור: {congress_source}</div>
        </div>
        ''', unsafe_allow_html=True)
else:
    st.markdown('<div class="news-item">⚪ לא נמצאו עסקאות קונגרס עדכניות למניות שלך (או שהמקור החינמי אינו זמין כרגע)</div>', unsafe_allow_html=True)

# ---------- 2. רכישות אנשי פנים (Form 4) ----------

st.divider()
st.markdown('<div class="section-title">👤 רכישות אנשי פנים — SEC Form 4</div>', unsafe_allow_html=True)
st.markdown('''
<div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
מדוע זה רלוונטי: כשמנכ"ל קונה במניות החברה שלו בכסף שלו — זה הסיגנל החזק ביותר שיש. הוא יודע יותר מכולם.
מוצגות רק עסקאות אמיתיות בשוק הפתוח (לא הענקות אופציות).
</div>
''', unsafe_allow_html=True)

if insider_trades:
    for tr in insider_trades[:8]:
        badge = "badge-buy" if tr["is_buy"] else "badge-sell"
        label = "קנה" if tr["is_buy"] else "מכר"
        val = tr["value"]
        val_str = f"${val/1e6:.1f}M" if val >= 1e6 else f"${val:,.0f}"
        st.markdown(f'''
        <div class="metric-card" style="margin-bottom:10px">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
                <span style="font-size:18px; color:#00ff41; font-family:monospace">{tr["ticker"]}</span>
                <span class="{badge}">{label} {val_str}</span>
            </div>
            <div style="color:#00aa00; font-size:12px">👤 {tr["owner"]} — {tr["title"]}</div>
            <div style="color:#008800; font-size:11px; margin-top:4px">
                דווח: {tr["date"]} · <a href="{tr["url"]}" target="_blank" style="color:#00cc33">לדיווח המלא ב-SEC</a>
            </div>
        </div>
        ''', unsafe_allow_html=True)
else:
    st.markdown('<div class="news-item">⚪ אין עסקאות אנשי פנים ב-30 הימים האחרונים במניות שלך (הערה: חברות זרות כמו TSM ו-ESLT פטורות מדיווח Form 4)</div>', unsafe_allow_html=True)

# ---------- 3. הודעות 8-K ----------

st.divider()
st.markdown('<div class="section-title">📄 הודעות רשמיות לרשות ניירות ערך (8-K) — SEC EDGAR</div>', unsafe_allow_html=True)
st.markdown('''
<div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
מדוע זה רלוונטי: חברות חייבות לדווח על עסקאות גדולות, שינויי הנהלה וחוזים משמעותיים — לרוב לפני שהתקשורת מגיעה.
</div>
''', unsafe_allow_html=True)

if filings_8k:
    for f in filings_8k[:8]:
        st.markdown(f'''
        <div class="metric-card" style="margin-bottom:10px">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
                <span style="font-size:18px; color:#00ff41; font-family:monospace">{f["ticker"]}</span>
                <span style="font-size:11px; color:#00aa00">{f["date"]}</span>
            </div>
            <div style="color:#00cc33; font-size:13px">{f["items"]}</div>
            <div style="color:#008800; font-size:11px; margin-top:4px">
                <a href="{f["url"]}" target="_blank" style="color:#00cc33">לדיווח המלא ב-SEC</a>
            </div>
        </div>
        ''', unsafe_allow_html=True)
else:
    st.markdown('<div class="news-item">⚪ אין הודעות 8-K ב-14 הימים האחרונים במניות שלך</div>', unsafe_allow_html=True)

# ---------- 4. נפח מסחר חריג ----------

st.divider()
st.markdown('<div class="section-title">📊 נפח מסחר חריג — חריגה מהממוצע של 30 יום</div>', unsafe_allow_html=True)
st.markdown('''
<div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
מדוע זה רלוונטי: כשפתאום סוחרים הרבה יותר ממה שרגיל — מישהו גדול נכנס. לרוב זה קורה לפני חדשות.
</div>
''', unsafe_allow_html=True)

if volume_alerts:
    for v in volume_alerts:
        chg = v["change"]
        chg_str = f'{"▲" if chg >= 0 else "▼"} {abs(chg)}% היום'
        chg_class = "metric-up" if chg >= 0 else "metric-dn"
        st.markdown(f'''
        <div class="metric-card" style="margin-bottom:10px">
            <div style="display:flex; justify-content:space-between; align-items:center">
                <span style="font-size:18px; color:#00ff41; font-family:monospace">{v["ticker"]}</span>
                <span class="badge-hold">נפח פי {v["ratio"]} מהממוצע</span>
            </div>
            <div class="{chg_class}" style="margin-top:6px">{chg_str}</div>
        </div>
        ''', unsafe_allow_html=True)
else:
    st.markdown('<div class="news-item">⚪ אין חריגות נפח כרגע — כל המניות נסחרות בנפח רגיל</div>', unsafe_allow_html=True)

# ---------- 5. אירועים קרובים ----------

st.divider()
st.markdown('<div class="section-title">📅 אירועים קרובים שכדאי לדעת עליהם — Finnhub</div>', unsafe_allow_html=True)
st.markdown('''
<div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
מדוע זה רלוונטי: לפני דוחות רבעוניים ואירועי מאקרו — שווה לבדוק את כל האיתותים האחרים על אותה מניה.
</div>
''', unsafe_allow_html=True)

if upcoming_events:
    today_d = datetime.now().date()
    for e in upcoming_events[:10]:
        try:
            ed = datetime.strptime(e["date"], "%Y-%m-%d").date()
            days_left = (ed - today_d).days
            when = "היום" if days_left == 0 else "מחר" if days_left == 1 else ed.strftime("%d/%m")
            urgency = "קריטי" if days_left <= 2 else "חשוב" if days_left <= 7 else "שים לב"
            badge = "badge-sell" if days_left <= 2 else "badge-hold" if days_left <= 7 else "badge-buy"
        except (ValueError, TypeError):
            when, urgency, badge = e["date"], "שים לב", "badge-buy"
        eps = f' | תחזית EPS: {e["eps_est"]}' if e.get("eps_est") else ""
        st.markdown(f'''
        <div class="news-item">
            📌 <span style="color:#00ff41; font-family:monospace">{e["ticker"]}</span> — {e["type"]}{eps}
            <span style="color:#00aa00; font-size:11px"> | {when}</span>
            <span class="{badge}" style="margin-right:8px; font-size:11px">{urgency}</span>
        </div>
        ''', unsafe_allow_html=True)
else:
    st.markdown('<div class="news-item">⚪ אין אירועים ב-21 הימים הקרובים</div>', unsafe_allow_html=True)

# ---------- 6. סיכום — מה לעשות עם התיק ----------

st.divider()
st.markdown('<div class="section-title">💼 סיכום — שקלול כל האיתותים לפי מניה</div>', unsafe_allow_html=True)
st.markdown('''
<div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
זו המלצה המבוססת על ספירת האיתותים שנאספו — לא ייעוץ פיננסי. ההחלטה הסופית תמיד שלך.
(החל מ-1.8 הסעיף הזה ישודרג לניתוח Claude מלא)
</div>
''', unsafe_allow_html=True)

for s in portfolio_summary:
    st.markdown(f'''
    <div class="metric-card" style="margin-bottom:10px">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
            <span style="font-size:18px; color:#00ff41; font-family:monospace">{s["ticker"]}</span>
            <span class="{s["badge"]}">{s["label"]}</span>
        </div>
        <div style="color:#00cc33; font-size:14px; margin-bottom:4px">{s["rec"]}</div>
        <div style="color:#008800; font-size:12px">{s["reasons"]} — {s["n_signals"]} איתותים</div>
    </div>
    ''', unsafe_allow_html=True)
