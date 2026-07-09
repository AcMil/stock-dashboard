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
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Heebo', sans-serif;
}

.stApp {
    background-color: #17181c;
}

.block-container {
    position: relative;
    z-index: 1;
}

h1, h2, h3 {
    color: #ece9e2 !important;
    font-family: 'Heebo', sans-serif !important;
    text-align: right;
    font-weight: 700;
}

.metric-card {
    background: #1e1f24;
    border: 0.5px solid #2e2f36;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: right;
    width: 100%;
}

.metric-label {
    font-size: 12px;
    color: #8b8a83;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
    font-family: 'JetBrains Mono', monospace;
}

.metric-value {
    font-size: 24px;
    font-weight: 600;
    color: #ece9e2;
    font-family: 'JetBrains Mono', monospace;
}

.metric-up { color: #7fc796; font-size: 13px; font-family: 'JetBrains Mono', monospace; }
.metric-dn { color: #e07b72; font-size: 13px; font-family: 'JetBrains Mono', monospace; }

.analysis-card {
    background: #1e1f24;
    border: 0.5px solid #2e2f36;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 12px;
    text-align: right;
    color: #c9c6bd;
    line-height: 1.7;
    font-family: 'Heebo', sans-serif;
    font-size: 14.5px;
}

.badge-buy  { background:#1e2d23; color:#7fc796; border:1px solid #2f4a38; padding:4px 14px; border-radius:6px; font-size:12.5px; font-weight:500; }
.badge-hold { background:#33291a; color:#e2b45f; border:1px solid #4a3d24; padding:4px 14px; border-radius:6px; font-size:12.5px; font-weight:500; }
.badge-sell { background:#33201f; color:#e07b72; border:1px solid #4a2e2c; padding:4px 14px; border-radius:6px; font-size:12.5px; font-weight:500; }

.news-item {
    padding: 9px 0;
    border-bottom: 0.5px solid rgba(236,233,226,0.08);
    color: #c9c6bd;
    font-size: 13.5px;
    text-align: right;
}

.section-title {
    font-size: 13px;
    font-weight: 500;
    color: #e2b45f;
    letter-spacing: 0.05em;
    margin: 4px 0 10px;
    text-align: right;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 5px;
    direction: rtl;
    background: #1f2025 !important;
    border: 0.5px solid #2e2f36;
    border-radius: 16px !important;
    padding: 5px !important;
    width: fit-content;
}

.stTabs [data-baseweb="tab"] {
    color: #b3b1a8;
    font-family: 'Heebo', sans-serif;
    font-size: 14px;
    background: transparent !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 8px 26px !important;
    height: auto !important;
    min-width: 120px;
    justify-content: center;
    transition: background 0.15s ease, color 0.15s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    background: #26272d !important;
    color: #ece9e2;
}

.stTabs [data-baseweb="tab"] p { color: inherit !important; font-size: 14px !important; }

.stTabs [aria-selected="true"] {
    color: #17181c !important;
    background: #e2b45f !important;
    border-radius: 14px !important;
    font-weight: 500;
}

.stTabs [aria-selected="true"]:hover {
    background: #e2b45f !important;
    color: #17181c;
}

.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none;
}

[data-testid="stSidebar"] {
    background-color: #17181c !important;
    border-left: 1px solid #2a2b31;
}

[data-testid="stMetricValue"] { color: #ece9e2 !important; }
[data-testid="stMetricDelta"] { color: #7fc796 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('''
<h1 style="text-align:right; font-size:clamp(1rem, 4vw, 2.2rem); white-space:nowrap; overflow:hidden; text-overflow:ellipsis">
📈 דשבורד מניות — ניתוח יומי
</h1>
''', unsafe_allow_html=True)

# ============================================================
# 🔒 מסך כניסה — שם משתמש וסיסמה מוגדרים ב-Secrets:
# DASHBOARD_USER = "שם_משתמש"
# DASHBOARD_PASSWORD = "סיסמה_חזקה"
# ============================================================

import hmac

def check_login():
    if st.session_state.get("authenticated"):
        return True

    valid_user = str(st.secrets.get("DASHBOARD_USER", ""))
    valid_pass = str(st.secrets.get("DASHBOARD_PASSWORD", ""))
    if not valid_user or not valid_pass:
        st.error("🔒 הכניסה לא הוגדרה עדיין: יש להוסיף DASHBOARD_USER ו-DASHBOARD_PASSWORD ב-Secrets של Streamlit Cloud")
        return False

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="section-title" style="font-size:14px">🔒 כניסה לדשבורד</div>', unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("שם משתמש")
            password = st.text_input("סיסמה", type="password")
            submitted = st.form_submit_button("כניסה", use_container_width=True)
        if submitted:
            if hmac.compare_digest(username, valid_user) and hmac.compare_digest(password, valid_pass):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")
    return False

if not check_login():
    st.stop()

st.markdown(f'<p style="color:#9a998f;text-align:right">עדכון אחרון: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>', unsafe_allow_html=True)
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

# ניתוח Claude עם מטמון של שעה — קריאת API אחת לשעה לכל מניה
# במקום קריאה בכל רענון דף. חיסכון של ~90% בעלויות.
@st.cache_data(ttl=3600, show_spinner=False)
def cached_claude_analysis(stock, full_context=False):
    price, change = get_stock_info(stock)
    news_items = get_yahoo_news(stock)
    if full_context:
        news_items = news_items + get_finnhub_news(stock)
        news_items = news_items + [
            {"כותרת": p["כותרת"], "מקור": "Reddit"}
            for p in get_reddit_posts(stock)
        ]
    return analyze_with_claude(stock, news_items, price, change)

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
        if st.button("🔒 התנתק", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

tab_prices, tab_analysis, tab_signals, tab_news = st.tabs(
    ["מחירים", "ניתוח Claude", "איתותים והמלצות", "חדשות"]
)

with tab_prices:
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

with tab_analysis:
    st.markdown(f'<div class="section-title">ניתוח Claude — {selected_stock}</div>', unsafe_allow_html=True)
    with st.spinner("Claude מנתח..."):
        price, change = get_stock_info(selected_stock)
        news = get_yahoo_news(selected_stock)
        finnhub_news = get_finnhub_news(selected_stock)
        news = news + finnhub_news
        reddit_posts = get_reddit_posts(selected_stock)
        analysis = cached_claude_analysis(selected_stock, full_context=True)

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
            analysis_tmp = cached_claude_analysis(stock)
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
                    <div class="strack-wrap" style="height:3px;background:rgba(236,233,226,0.1);border-radius:2px;margin-bottom:6px">
                        <div style="width:{score_tmp*10}%;height:100%;background:{'#7fc796' if score_tmp>=7 else '#e2b45f' if score_tmp>=5 else '#e07b72'};border-radius:2px"></div>
                    </div>
                    <span class="{badge}">{rec_tmp}</span>
                    <span style="font-size:11px;color:#9a998f;margin-right:6px">{score_tmp}/10</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

with tab_prices:
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
                line=dict(color='#e2b45f', width=1.5),
                fill='tozeroy',
                fillcolor='rgba(226,180,95,0.06)',
                name=selected_stock
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,31,36,0.9)',
                font=dict(color='#8b8a83', family='JetBrains Mono, monospace'),
                margin=dict(l=40, r=20, t=20, b=40),
                height=300,
                xaxis=dict(
                    gridcolor='rgba(236,233,226,0.07)',
                    showgrid=True,
                    color='#9a998f'
                ),
                yaxis=dict(
                    gridcolor='rgba(236,233,226,0.07)',
                    showgrid=True,
                    color='#9a998f'
                ),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("לא נמצאו נתונים היסטוריים")
    except Exception as e:
        st.warning(f"שגיאה בטעינת גרף: {e}")

    st.divider()

with tab_news:
    st.markdown('<div class="section-title">חדשות אחרונות</div>', unsafe_allow_html=True)
    if news:
        for item in news:
            st.markdown(f'<div class="news-item">📌 {item["כותרת"]} — <span style="color:#8b8a83">{item["מקור"]}</span></div>', unsafe_allow_html=True)
    else:
        st.warning("לא נמצאו חדשות")

    st.divider()

with tab_news:
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
    עסקאות של חברי קונגרס.
    מקור 1: Finnhub (עם המפתח הקיים). מקורות גיבוי: לא-רשמיים.
    """
    tick_set = {t.upper() for t in tickers}
    cutoff = datetime.now() - timedelta(days=days)
    trades = []

    # מקור 1: Finnhub — congressional-trading
    if FINNHUB_API_KEY:
        from_date = cutoff.strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        for t in tick_set:
            try:
                r = requests.get(
                    "https://finnhub.io/api/v1/stock/congressional-trading",
                    params={"symbol": t, "from": from_date, "to": to_date,
                            "token": FINNHUB_API_KEY},
                    timeout=10,
                )
                if r.status_code != 200:
                    continue
                for it in (r.json() or {}).get("data", []) or []:
                    tx_type = str(it.get("transactionType", "")).lower()
                    amt_from = it.get("amountFrom")
                    amt_to = it.get("amountTo")
                    amount = ""
                    try:
                        if amt_from and amt_to:
                            amount = f"${int(amt_from):,}–${int(amt_to):,}"
                    except (ValueError, TypeError):
                        pass
                    pos = str(it.get("position", ""))
                    role = "סנאט" if "senat" in pos.lower() else "בית הנבחרים" if pos else ""
                    trades.append({
                        "ticker": t,
                        "name": it.get("name", "חבר קונגרס"),
                        "role": role,
                        "date": str(it.get("transactionDate", ""))[:10],
                        "is_buy": "purchase" in tx_type or "buy" in tx_type,
                        "is_sell": "sale" in tx_type or "sell" in tx_type,
                        "amount": amount,
                    })
                time.sleep(0.1)
            except Exception:
                continue
        if trades:
            trades.sort(key=lambda x: x["date"], reverse=True)
            return trades, "Finnhub"

    # מקור 2: Capitol Trades (API לא רשמי)
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

    # מקור 3 (גיבוי אחרון, סנאט בלבד): Senate Stock Watcher
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

# ---------- גילוי מניות: סריקת שוק + באזז ----------

@st.cache_data(ttl=3600, show_spinner=False)
def scan_market_insider_buys(days=1, min_value_k=200, max_rows=100):
    """סורק את כל השוק לרכישות אנשי פנים (מקור: OpenInsider)"""
    try:
        from io import StringIO
        url = (
            "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh="
            f"&fd={days}&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=0"
            f"&vl={min_value_k}&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999"
            "&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h="
            f"&sortcol=0&cnt={max_rows}&page=1"
        )
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code != 200:
            return []
        tables = pd.read_html(StringIO(r.text))
        df = None
        for tbl in tables:
            cols = [str(c) for c in tbl.columns]
            if any("Ticker" in c for c in cols):
                df = tbl
                break
        if df is None:
            return []

        def find_col(df, name):
            for c in df.columns:
                if name.lower() in str(c).lower():
                    return c
            return None

        c_tick = find_col(df, "Ticker")
        c_comp = find_col(df, "Company")
        c_name = find_col(df, "Insider")
        c_title = find_col(df, "Title")
        c_date = find_col(df, "Filing")
        c_val = find_col(df, "Value")
        out = []
        for _, row in df.iterrows():
            try:
                ticker = str(row[c_tick]).strip().upper()
                if not ticker or ticker == "NAN" or len(ticker) > 5:
                    continue
                val = float(str(row[c_val]).replace("$", "").replace(",", "").replace("+", "").strip())
                out.append({
                    "ticker": ticker,
                    "company": str(row[c_comp]).strip() if c_comp else "",
                    "insider": str(row[c_name]).strip() if c_name else "",
                    "title": str(row[c_title]).strip() if c_title else "",
                    "date": str(row[c_date]).strip()[:10] if c_date else "",
                    "value": val,
                })
            except Exception:
                continue
        return out
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def get_reddit_buzz():
    """מדד אזכורים ברדיט לכל השוק (מקור: ApeWisdom)"""
    try:
        r = requests.get("https://apewisdom.io/api/v1.0/filter/all-stocks/page/1",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        buzz = {}
        for item in r.json().get("results", []):
            t = str(item.get("ticker", "")).upper()
            if t:
                buzz[t] = {"rank": int(item.get("rank", 999)),
                           "mentions": int(item.get("mentions", 0) or 0)}
        return buzz
    except Exception:
        return {}

def pick_daily_discovery(buys, buzz, exclude):
    """הבחירה היומית: רכישת אנשי הפנים הבולטת של היום + בונוס באזז"""
    candidates = [dict(b) for b in buys if b["ticker"] not in exclude]
    if not candidates:
        return None
    for c in candidates:
        bz = buzz.get(c["ticker"])
        c["buzz_rank"] = bz["rank"] if bz else None
        c["buzz_mentions"] = bz["mentions"] if bz else 0
        bonus = 1.5 if bz and bz["rank"] <= 30 else 1.2 if bz and bz["rank"] <= 100 else 1.0
        c["score"] = c["value"] * bonus
    return max(candidates, key=lambda x: x["score"])

def pick_monthly_discovery(buys30, buzz, exclude):
    """הבחירה החודשית: המניה עם הכי הרבה רכישות אנשי פנים ב-30 יום"""
    counts, values, latest = {}, {}, {}
    for b in buys30:
        t = b["ticker"]
        if t in exclude:
            continue
        counts[t] = counts.get(t, 0) + 1
        values[t] = values.get(t, 0) + b["value"]
        latest[t] = b
    if not counts:
        return None
    winner = max(counts, key=lambda t: (counts[t], values[t]))
    bz = buzz.get(winner)
    return {
        "ticker": winner,
        "company": latest[winner]["company"],
        "count": counts[winner],
        "total_value": values[winner],
        "buzz_rank": bz["rank"] if bz else None,
        "buzz_mentions": bz["mentions"] if bz else 0,
    }

# ---------- סיכום: ניתוח Claude (עם גיבוי לוגי) ----------
# Claude מקבל את כל האיתותים שנאספו ומחזיר המלצה לכל מניה.
# התוצאה נשמרת במטמון לשעה כדי לחסוך בעלויות API.
# אם הקריאה נכשלת — עוברים אוטומטית ללוגיקת השקלול המקומית.

@st.cache_data(ttl=3600, show_spinner=False)
def claude_portfolio_summary(signals_json):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = f"""אתה אנליסט תיק השקעות. קיבלת איתותים שנאספו אוטומטית ממקורות רשמיים (SEC, נתוני נפח, לוח דוחות) עבור מניות בתיק.

האיתותים (JSON):
{signals_json}

הנחיות:
- עסקת קנייה של איש פנים (במיוחד מנכ"ל/סמנכ"ל כספים) היא איתות חיובי חזק. מכירה היא איתות חלש בלבד (מנהלים מוכרים מסיבות רבות).
- נפח חריג + דוח קרוב + קניית אנשי פנים = איתותים חופפים שמחזקים זה את זה.
- 8-K על תוצאות כספיות או שינוי הנהלה — שים לב להקשר.
- היה שמרן: אם אין איתותים מהותיים, ההמלצה היא "החזק".

החזר אך ורק מערך JSON תקין, בלי טקסט לפני או אחרי, בפורמט:
[{{"ticker": "XXX", "label": "הגדל|היזהר|עקוב|החזק", "rec": "משפט המלצה קצר בעברית", "reasons": "האיתותים המרכזיים בקצרה"}}]
כלול את כל המניות שברשימה."""
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        import re as _re
        match = _re.search(r'\[[\s\S]*\]', text)
        if not match:
            return None
        parsed = json.loads(match.group())
        out = []
        badge_map = {"הגדל": "badge-buy", "היזהר": "badge-sell",
                     "עקוב": "badge-hold", "החזק": "badge-buy"}
        for item in parsed:
            label = item.get("label", "החזק")
            out.append({
                "ticker": str(item.get("ticker", "")).upper(),
                "label": label,
                "badge": badge_map.get(label, "badge-hold"),
                "rec": item.get("rec", ""),
                "reasons": item.get("reasons", ""),
                "n_signals": None, "score": 0,
            })
        return out if out else None
    except Exception:
        return None

def build_signals_json(tickers, insider, congress, filings_8k, volume, events, fg_score):
    """אורז את כל האיתותים ל-JSON קומפקטי עבור Claude"""
    data = {"fear_greed": fg_score, "stocks": {}}
    for t in tickers:
        t = t.upper()
        data["stocks"][t] = {
            "insider": [
                {"name": x["owner"], "title": x["title"], "date": x["date"],
                 "action": "buy" if x["is_buy"] else "sell",
                 "value_usd": round(x["value"])}
                for x in insider if x["ticker"] == t
            ][:4],
            "congress": [
                {"name": x["name"], "date": x["date"],
                 "action": "buy" if x["is_buy"] else "sell" if x.get("is_sell") else "other"}
                for x in congress if x["ticker"] == t
            ][:4],
            "filings_8k": [
                {"date": x["date"], "items": x["items"]}
                for x in filings_8k if x["ticker"] == t
            ][:3],
            "unusual_volume": next(
                ({"ratio": x["ratio"], "day_change_pct": x["change"]}
                 for x in volume if x["ticker"] == t), None),
            "upcoming_events": [
                {"date": x["date"], "type": x["type"]}
                for x in events if x["ticker"] == t
            ][:2],
        }
    return json.dumps(data, ensure_ascii=False, sort_keys=True)

# ---------- סיכום: לוגיקת שקלול איתותים (גיבוי) ----------

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

with tab_signals:
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
        signals_json = build_signals_json(
            selected_stocks, insider_trades, congress_trades,
            filings_8k, volume_alerts, upcoming_events, fg_score,
        )
        portfolio_summary = claude_portfolio_summary(signals_json)
        summary_source = "Claude"
        if not portfolio_summary:
            portfolio_summary = build_summary(
                selected_stocks, insider_trades, congress_trades,
                filings_8k, volume_alerts, upcoming_events,
            )
            summary_source = "לוגיקה מקומית (Claude לא זמין כרגע)"

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
            <div style="font-size:11px;color:#9a998f">{sub}</div>
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
                    <span style="font-size:18px; color:#ece9e2; font-family:'JetBrains Mono',monospace">{tr["ticker"]}</span>
                    <span class="{badge}">{label}</span>
                </div>
                <div style="color:#9a998f; font-size:12px">👤 {tr["name"]}{role}{amount}</div>
                <div style="color:#8b8a83; font-size:11px; margin-top:4px">דווח: {tr["date"]} · מקור: {congress_source}</div>
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
                    <span style="font-size:18px; color:#ece9e2; font-family:'JetBrains Mono',monospace">{tr["ticker"]}</span>
                    <span class="{badge}">{label} {val_str}</span>
                </div>
                <div style="color:#9a998f; font-size:12px">👤 {tr["owner"]} — {tr["title"]}</div>
                <div style="color:#8b8a83; font-size:11px; margin-top:4px">
                    דווח: {tr["date"]} · <a href="{tr["url"]}" target="_blank" style="color:#c9c6bd">לדיווח המלא ב-SEC</a>
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
                    <span style="font-size:18px; color:#ece9e2; font-family:'JetBrains Mono',monospace">{f["ticker"]}</span>
                    <span style="font-size:11px; color:#9a998f">{f["date"]}</span>
                </div>
                <div style="color:#c9c6bd; font-size:13px">{f["items"]}</div>
                <div style="color:#8b8a83; font-size:11px; margin-top:4px">
                    <a href="{f["url"]}" target="_blank" style="color:#c9c6bd">לדיווח המלא ב-SEC</a>
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
                    <span style="font-size:18px; color:#ece9e2; font-family:'JetBrains Mono',monospace">{v["ticker"]}</span>
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
                📌 <span style="color:#ece9e2; font-family:'JetBrains Mono',monospace">{e["ticker"]}</span> — {e["type"]}{eps}
                <span style="color:#9a998f; font-size:11px"> | {when}</span>
                <span class="{badge}" style="margin-right:8px; font-size:11px">{urgency}</span>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.markdown('<div class="news-item">⚪ אין אירועים ב-21 הימים הקרובים</div>', unsafe_allow_html=True)

    # ---------- 6. סיכום — מה לעשות עם התיק ----------

    st.divider()
    st.markdown('<div class="section-title">💼 סיכום Claude — מה לעשות עם התיק שלי</div>', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
    ניתוח המשלב את כל האיתותים שנאספו — לא ייעוץ פיננסי. ההחלטה הסופית תמיד שלך.
    מקור הניתוח: {summary_source} · מתעדכן אחת לשעה
    </div>
    ''', unsafe_allow_html=True)

    for s in portfolio_summary:
        extra = f' — {s["n_signals"]} איתותים' if s.get("n_signals") is not None else ""
        st.markdown(f'''
        <div class="metric-card" style="margin-bottom:10px">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
                <span style="font-size:18px; color:#ece9e2; font-family:'JetBrains Mono',monospace">{s["ticker"]}</span>
                <span class="{s["badge"]}">{s["label"]}</span>
            </div>
            <div style="color:#c9c6bd; font-size:14px; margin-bottom:4px">{s["rec"]}</div>
            <div style="color:#8b8a83; font-size:12px">{s["reasons"]}{extra}</div>
        </div>
        ''', unsafe_allow_html=True)

    # ---------- 7. גילוי מניות — מחוץ לתיק ----------

    st.divider()
    st.markdown('<div class="section-title">🔍 גילוי מניות — המלצות מחוץ לתיק</div>', unsafe_allow_html=True)
    st.markdown('''
    <div class="analysis-card" style="font-size:12px; padding: 8px 14px;">
    סריקה של כל השוק: איפה אנשי פנים קונים בכסף שלהם, משוקלל עם באזז ברדיט. מניות שכבר בתיק שלך מסוננות החוצה.
    מקורות: OpenInsider + ApeWisdom · לא ייעוץ פיננסי.
    </div>
    ''', unsafe_allow_html=True)

    with st.spinner("סורק את השוק..."):
        buzz_data = get_reddit_buzz()
        exclude_set = {s.upper() for s in selected_stocks}
        daily_buys = scan_market_insider_buys(days=1)
        daily_label = "היום"
        if not daily_buys:
            daily_buys = scan_market_insider_buys(days=3)
            daily_label = "3 הימים האחרונים"
        if not daily_buys:
            # סופי שבוע ארוכים וחגים — מתרחבים לשבוע
            daily_buys = scan_market_insider_buys(days=7)
            daily_label = "השבוע האחרון"
        monthly_buys = scan_market_insider_buys(days=30, min_value_k=100, max_rows=500)
        daily_pick = pick_daily_discovery(daily_buys, buzz_data, exclude_set)
        monthly_pick = pick_monthly_discovery(monthly_buys, buzz_data, exclude_set)

    col_d, col_m = st.columns(2, gap="medium")

    with col_d:
        st.markdown(f'<div class="section-title">☀️ המלצת {daily_label}</div>', unsafe_allow_html=True)
        if daily_pick:
            t = daily_pick["ticker"]
            p, c = get_stock_info(t)
            price_str = f"${p} ({'▲' if (c or 0) >= 0 else '▼'} {c}%)" if p else ""
            val = daily_pick["value"]
            val_str = f"${val/1e6:.1f}M" if val >= 1e6 else f"${val/1e3:.0f}K"
            buzz_str = (f'🔥 מקום {daily_pick["buzz_rank"]} בבאזז רדיט ({daily_pick["buzz_mentions"]} אזכורים)'
                        if daily_pick["buzz_rank"] else "ללא באזז חריג ברדיט")
            st.markdown(f'''
            <div class="metric-card" style="margin-bottom:10px">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
                    <span style="font-size:22px; color:#ece9e2; font-family:'JetBrains Mono',monospace">{t}</span>
                    <span class="badge-buy">קניית פנים {val_str}</span>
                </div>
                <div style="color:#9a998f; font-size:12px; margin-bottom:4px">🏢 {daily_pick["company"]} {price_str}</div>
                <div style="color:#c9c6bd; font-size:12px; margin-bottom:4px">👤 {daily_pick["insider"]} — {daily_pick["title"]}</div>
                <div style="color:#8b8a83; font-size:12px">{buzz_str}</div>
            </div>
            ''', unsafe_allow_html=True)
            with st.spinner("Claude בודק..."):
                take = cached_claude_analysis(t)
            st.markdown(f'<div class="analysis-card" style="font-size:12px">{take}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="news-item">⚪ לא נמצאו רכישות אנשי פנים בולטות (או שהמקור אינו זמין כרגע)</div>', unsafe_allow_html=True)

    with col_m:
        st.markdown('<div class="section-title">📆 המלצת החודש</div>', unsafe_allow_html=True)
        if monthly_pick:
            t = monthly_pick["ticker"]
            p, c = get_stock_info(t)
            price_str = f"${p} ({'▲' if (c or 0) >= 0 else '▼'} {c}%)" if p else ""
            tv = monthly_pick["total_value"]
            tv_str = f"${tv/1e6:.1f}M" if tv >= 1e6 else f"${tv/1e3:.0f}K"
            buzz_str = (f'🔥 מקום {monthly_pick["buzz_rank"]} בבאזז רדיט ({monthly_pick["buzz_mentions"]} אזכורים)'
                        if monthly_pick["buzz_rank"] else "ללא באזז חריג ברדיט")
            st.markdown(f'''
            <div class="metric-card" style="margin-bottom:10px">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
                    <span style="font-size:22px; color:#ece9e2; font-family:'JetBrains Mono',monospace">{t}</span>
                    <span class="badge-buy">{monthly_pick["count"]} רכישות פנים בחודש</span>
                </div>
                <div style="color:#9a998f; font-size:12px; margin-bottom:4px">🏢 {monthly_pick["company"]} {price_str}</div>
                <div style="color:#c9c6bd; font-size:12px; margin-bottom:4px">💰 סה"כ נרכש: {tv_str}</div>
                <div style="color:#8b8a83; font-size:12px">{buzz_str}</div>
            </div>
            ''', unsafe_allow_html=True)
            with st.spinner("Claude בודק..."):
                take_m = cached_claude_analysis(t)
            st.markdown(f'<div class="analysis-card" style="font-size:12px">{take_m}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="news-item">⚪ לא נמצאו נתונים חודשיים (או שהמקור אינו זמין כרגע)</div>', unsafe_allow_html=True)
