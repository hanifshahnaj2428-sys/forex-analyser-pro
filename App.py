import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

st.set_page_config(page_title="Pro Trader", page_icon="📈", layout="centered")
st.title("📈 Pro Trader")

bd_tz = pytz.timezone('Asia/Dhaka')
now_bd = datetime.now(bd_tz)
hr = now_bd.hour
ses = [s for s, c in [("🌏 Asian", 6<=hr<15), ("🇬🇧 London", 13<=hr<22), ("🇺🇸 NY", 18<=hr or hr<3)] if c]
with st.container(border=True):
    st.markdown(f"**🕒 সময়:** {now_bd.strftime('%I:%M %p (BD)')} | " + ("🔥 **Overlap (NY Killzone)**" if 18<=hr<22 else (" | ".join(ses) if ses else "💤 অফ-সেশন")))

pairs = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X", "GOLD": "GC=F", "ETH": "ETH-USD"}
tfs = {"5M": ("5d", "5m"), "15M": ("5d", "15m"), "1H": ("1mo", "1h"), "4H": ("2mo", "4h")}

@st.cache_data(ttl=60)
def get_df(sym, p, iv):
    try:
        df = yf.download(sym, period=p, interval="1h" if iv=="4h" else iv, progress=False)
        if df is None or df.empty:
            df = yf.download(sym, period="3mo", interval="1d", progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close']].dropna()
        if iv == "4h" and len(df) > 20:
            r = df.resample("4h").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
            return r if len(r) >= 15 else df
        return df
    except Exception:
        return pd.DataFrame()

def trend(df):
    if len(df) < 15: return "N/A"
    e20 = float(df['Close'].ewm(span=min(20, len(df))).mean().iloc[-1])
    e50 = float(df['Close'].ewm(span=min(50, len(df))).mean().iloc[-1])
    c = float(df['Close'].iloc[-1])
    if c > e20 > e50: return "🟢 Bullish"
    if c < e20 < e50: return "🔴 Bearish"
    return "🟡 Ranging"

def get_rsi(df):
    d = df['Close'].diff()
    g = d.where(d > 0, 0).rolling(14).mean()
    l = (-d.where(d < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + g / l.replace(0, 1e-10)))
    return round(float(rsi.iloc[-1]), 1) if not pd.isna(rsi.iloc[-1]) else 50.0

def make_chart(df_s):
    fig = go.Figure(data=[go.Candlestick(x=df_s.index, open=df_s['Open'], high=df_s['High'], low=df_s['Low'], close=df_s['Close'])])
    fig.update_layout(xaxis_rangeslider_visible=False, height=390, margin=dict(l=5, r=5, t=25, b=5), template="plotly_dark", xaxis_type="category", showlegend=False)
    fig.update_xaxes(showticklabels=False)
    return fig

def run_tab1(pn, tfl):
    tk = pairs[pn]
    dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
    df = get_df(tk, *tfs[tfl])
    dfd = get_df(tk, "5d", "1d")
    if len(df) < 15:
        st.warning("⚠️ ডেটা লোড হয়নি, আবার চেষ্টা করুন।")
        return
    c = float(df['Close'].iloc[-1])
    lb = min(32, len(df)-2)
    res, sup = float(df.iloc[-lb:-2]['High'].max()), float(df.iloc[-lb:-2]['Low'].min())
    buf = (res - sup) * 0.05
    tr = trend(df)
    d, en, stp = ("BUY 🟢", sup + buf, sup - buf * 0.5) if "Bull" in tr else (("SELL 🔴", res - buf, res + buf * 0.5) if "Bear" in tr else ("RANGE 🟡", sup + buf, sup - buf * 0.5))
    tp = en + abs(en - stp) * 2 if "BUY" in d or "RANGE" in d else en - abs(stp - en) * 2
    pdh = round(float(dfd['High'].iloc[-2]), dec) if len(dfd) >= 2 else None
    pdl = round(float(dfd['Low'].iloc[-2]), dec) if len(dfd) >= 2 else None
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("প্রাইস", round(c, dec))
    m2.metric("RSI (14)", get_rsi(df))
    m3.metric("Prev High", pdh)
    m4.metric("Prev Low", pdl)
    st.info(f"**ট্রেন্ড:** {tr}")
    t1, t2, t3 = st.columns(3)
    t1.metric(f"Entry ({d})", round(en, dec))
    t2.metric("Stop Loss", round(stp, dec))
    t3.metric("Exit (TP)", round(tp, dec))
    fig = make_chart(df.iloc[-45:])
    fig.add_hrect(y0=res - buf, y1=res, fillcolor="orange", opacity=0.22, annotation_text="Res")
    fig.add_hrect(y0=sup, y1=sup + buf, fillcolor="deepskyblue", opacity=0.22, annotation_text="Sup")
    fig.add_hline(y=en, line_dash="dash", line_color="cyan", annotation_text="Entry")
    fig.add_hline(y=stp, line_dash="dot", line_color="red", annotation_text="SL")
    fig.add_hline(y=tp, line_dash="dash", line_color="lime", annotation_text="TP")
    if pdh: fig.add_hline(y=pdh, line_dash="dashdot", line_color="gold", annotation_text="PDH")
    if pdl: fig.add_hline(y=pdl, line_dash="dashdot", line_color="violet", annotation_text="PDL")
    st.plotly_chart(fig, use_container_width=True)

def run_tab2(sp, stf, item):
    tk = pairs[sp]
    dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
    dfs = get_df(tk, *tfs[stf])
    if len(dfs) < 15:
        st.warning("⚠️ ডেটা লোড হয়নি, আবার চেষ্টা করুন।")
        return
    ps = dfs.iloc[-45:].copy()
    c = float(ps['Close'].iloc[-1])
    mid = max(2, len(ps) // 2)
    h1, h2 = float(ps.iloc[:mid]['High'].max()), float(ps.iloc[mid:]['High'].max())
    l1, l2 = float(ps.iloc[:mid]['Low'].min()), float(ps.iloc[mid:]['Low'].min())
    sw_hi, sw_lo = max(h1, h2), min(l1, l2)
    rng, eq = max(sw_hi - sw_lo, 1e-6), (sw_hi + sw_lo) / 2
    bf_l = bf_h = sf_l = sf_h = bob_l = bob_h = sob_l = sob_h = None
    avg_b = float((ps['Close'] - ps['Open']).abs().mean())
    for i in range(len(ps)-1, 1, -1):
        if float(ps['Low'].iloc[i]) > float(ps['High'].iloc[i-2]) and bf_l is None:
            bf_l, bf_h = round(float(ps['High'].iloc[i-2]), dec), round(float(ps['Low'].iloc[i]), dec)
        if float(ps['High'].iloc[i]) < float(ps['Low'].iloc[i-2]) and sf_l is None:
            sf_l, sf_h = round(float(ps['High'].iloc[i]), dec), round(float(ps['Low'].iloc[i-2]), dec)
        mv = float(ps['Close'].iloc[i] - ps['Open'].iloc[i])
        if mv > avg_b * 1.4 and bob_l is None:
            bob_l, bob_h = round(float(ps['Low'].iloc[i-1]), dec), round(max(float(ps['Open'].iloc[i-1]), float(ps['Close'].iloc[i-1])), dec)
        if mv < -avg_b * 1.4 and sob_l is None:
            sob_h, sob_l = round(float(ps['High'].iloc[i-1]), dec), round(min(float(ps['Open'].iloc[i-1]), float(ps['Close'].iloc[i-1])), dec)
    if bob_l is None: bob_l, bob_h = round(l2, dec), round(l2 + rng * 0.08, dec)
    if sob_l is None: sob_h, sob_l = round(h2, dec), round(h2 - rng * 0.08, dec)
    fig = make_chart(ps)
    if "FVG" in item:
        f1, f2 = st.columns(2)
        f1.metric("Bullish FVG", f"{bf_l} - {bf_h}" if bf_l else "গ্যাপ নেই")
        f2.metric("Bearish FVG", f"{sf_l} - {sf_h}" if sf_l else "গ্যাপ নেই")
        if bf_l is not None:
            fig.add_hrect(y0=bf_l, y1=bf_h, fillcolor="lime", opacity=0.25, annotation_text="Bull FVG")
            fig.add_hline(y=round((bf_l + bf_h) / 2, dec), line_dash="dot", line_color="lime", annotation_text="Bull 50% CE")
        if sf_l is not None:
            fig.add_hrect(y0=sf_l, y1=sf_h, fillcolor="red", opacity=0.25, annotation_text="Bear FVG")
            fig.add_hline(y=round((sf_l + sf_h) / 2, dec), line_dash="dot", line_color="red", annotation_text="Bear 50% CE")
    elif "OB" in item:
        o1, o2 = st.columns(2)
        o1.metric("Bullish OB", f"{bob_l} - {bob_h}")
        o2.metric("Bearish OB", f"{sob_l} - {sob_h}")
        fig.add_hrect(y0=bob_l, y1=bob_h, fillcolor="cyan", opacity=0.25, annotation_text="Bullish OB")
        fig.add_hrect(y0=sob_l, y1=sob_h, fillcolor="magenta", opacity=0.25, annotation_text="Bearish OB")
    elif "BOS" in item:
        hl, ll = ("HH" if h2 > h1 else "LH"), ("HL" if l2 > l1 else "LL")
        st.info(f"**Structure:** {hl} & {ll} | **High:** {round(h2, dec)} | **Low:** {round(l2, dec)}")
        fig.add_hline(y=h2, line_dash="dash", line_color="orange", annotation_text=f"Break High ({round(h2, dec)})")
        fig.add_hline(y=l2, line_dash="dash", line_color="cyan", annotation_text=f"Break Low ({round(l2, dec)})")
    elif "OTE" in item:
        st.info(f"{'🔴 **Premium Zone**' if c > eq else '🟢 **Discount Zone**'} | **EQ (50%):** {round(eq, dec)}")
        fig.add_hrect(y0=eq, y1=sw_hi, fillcolor="red", opacity=0.14, annotation_text="PREMIUM")
        fig.add_hrect(y0=sw_lo, y1=eq, fillcolor="green", opacity=0.14, annotation_text="DISCOUNT")
        fig.add_hline(y=eq, line_dash="dash", line_color="white", annotation_text="EQ 50%")
        ol, oh = (sw_lo + rng * 0.618, sw_lo + rng * 0.786) if c > eq else (sw_hi - rng * 0.786, sw_hi - rng * 0.618)
        fig.add_hrect(y0=ol, y1=oh, fillcolor="gold", opacity=0.30, annotation_text="OTE (0.62-0.79)")
    elif "BSL" in item:
        st.warning(f"🎯 **BSL:** {round(sw_hi, dec)} | **SSL:** {round(sw_lo, dec)}")
        fig.add_hline(y=sw_hi, line_dash="dash", line_color="red", annotation_text=f"BSL: {round(sw_hi, dec)}")
        fig.add_hline(y=sw_lo, line_dash="dash", line_color="lime", annotation_text=f"SSL: {round(sw_lo, dec)}")
    st.plotly_chart(fig, use_container_width=True)

tab1, tab2 = st.tabs(["📊 চার্ট ও জোন", "🧠 SMC অ্যানালাইসিস"])

with tab1:
    c1, c2 = st.columns(2)
    pn = c1.selectbox("পেয়ার", list(pairs.keys()), key="p1")
    tfl = c2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf1")
    if st.button("🔍 অ্যানালাইসিস দেখুন", use_container_width=True, type="primary", key="b1"):
        run_tab1(pn, tfl)

with tab2:
    s1, s2 = st.columns(2)
    sp = s1.selectbox("পেয়ার", list(pairs.keys()), key="p2")
    stf = s2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf2")
    smc_item = st.selectbox("SMC উপাদান নির্বাচন করুন:", ["১. ফেয়ার ভ্যালু গ্যাপ (FVG & 50% CE)", "২. অর্ডার ব্লক (Order Block)", "৩. মার্কেট স্ট্রাকচার (BOS / CHoCH)", "৪. প্রিমিয়াম / ডিসকাউন্ট ও OTE", "৫. লিকুইডিটি পুল (BSL / SSL)"], key="smc_item")
    if st.button("⚡ ফুল SMC অ্যানালাইসিস দেখুন", use_container_width=True, type="primary", key="b2"):
        run_tab2(sp, stf, smc_item)
