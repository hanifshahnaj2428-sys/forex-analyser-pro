import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz
import time

st.set_page_config(
    page_title="Pro Trader",
    page_icon="📈",
    layout="centered"
)

st.title("📈 Pro Trader")
st.caption("Advanced Market & SMC Intelligence")

# বাংলাদেশ সময়, সেশন ও ICT Killzone ডিটেক্টর
bd_tz = pytz.timezone('Asia/Dhaka')
now_bd = datetime.now(bd_tz)
hr = now_bd.hour

ses = [s for s, cond in [("🌏 Asian", 6<=hr<15), ("🇬🇧 London", 13<=hr<22), ("🇺🇸 NY", 18<=hr or hr<3)] if cond]
kz = "⚡ London Killzone" if 13<=hr<16 else ("🔥 NY Killzone (Best for SMC)" if 18<=hr<22 else "⏳ Normal Hours")

with st.container(border=True):
    st.markdown(f"**🕒 সময়:** {now_bd.strftime('%I:%M %p (BD)')} | **সেশন:** {(' | '.join(ses) if ses else '💤 অফ-সেশন')} | **{kz}**")

# নেভিগেশন মেনু (st.tabs এর বদলে স্থিতিশীল মেনু)
page = st.radio(
    "সেকশন নির্বাচন করুন:",
    ["📊 চার্ট ও RSI", "🧠 SMC অ্যানালাইসিস", "🧭 MTF ও সেশন লিকুইডিটি"],
    horizontal=True,
    label_visibility="collapsed"
)
st.divider()

pairs = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X", "GOLD": "GC=F", "ETH": "ETH-USD"}
tfs = {"5M": ("2d", "5m"), "15M": ("5d", "15m"), "1H": ("1mo", "1h"), "4H": ("2mo", "4h")}
htf_map = {"5M": ("1mo", "1h"), "15M": ("1mo", "1h"), "1H": ("2mo", "4h"), "4H": ("6mo", "1d")}

@st.cache_data(ttl=120)
def get_df(sym, p, iv):
    try:
        df = yf.download(sym, period=p, interval="1h" if iv=="4h" else iv, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close']].dropna()
        if iv == "4h":
            df = df.resample("4h").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
        return df
    except Exception:
        return pd.DataFrame()

def add_indicators(df):
    df = df.copy()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    up_move = df['High'].diff()
    down_move = -df['Low'].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr_safe = df['ATR'].replace(0, 1e-10)
    plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr_safe)
    minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / atr_safe)
    di_sum = (plus_di + minus_di).replace(0, 1e-10)
    dx = (abs(plus_di - minus_di) / di_sum) * 100
    df['ADX'] = dx.ewm(alpha=1/14).mean()
    return df

def trend(df):
    if len(df) < 30: return "N/A"
    e20, e50, c = float(df['EMA20'].iloc[-1]), float(df['EMA50'].iloc[-1]), float(df['Close'].iloc[-1])
    return "🟢 Bullish" if c > e20 > e50 else ("🔴 Bearish" if c < e20 < e50 else "🟡 Ranging")

def analyze(df, dec):
    c, pc = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
    atr = float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else (c * 0.002)
    lookback = min(32, len(df)-2)
    res, sup = float(df.iloc[-lookback:-2]['High'].max()), float(df.iloc[-lookback:-2]['Low'].min())
    buf = atr * 0.5
    dl = dh = sl = sh = None
    avg_b = float((df['Close'] - df['Open']).abs().iloc[-25:-1].mean())
    
    for i in range(len(df)-2, max(len(df)-20, 1), -1):
        mv = float(df['Close'].iloc[i] - df['Open'].iloc[i])
        if mv > avg_b*1.8 and not dl and c > max(df['Open'].iloc[i-1], df['Close'].iloc[i-1]):
            dl, dh = float(df['Low'].iloc[i-1]), float(max(df['Open'].iloc[i-1], df['Close'].iloc[i-1]))
        if mv < -avg_b*1.8 and not sl and c < min(df['Open'].iloc[i-1], df['Close'].iloc[i-1]):
            sh, sl = float(df['High'].iloc[i-1]), float(min(df['Open'].iloc[i-1], df['Close'].iloc[i-1]))
            
    sig = f"🚀 Bull Breakout ({round(res,dec)})" if c>res and pc<=res else (f"🔻 Bear Breakout ({round(sup,dec)})" if c<sup and pc>=sup else "⚪ রানিং মার্কেট")
    tr = trend(df)
    
    if "Bull" in tr or "Bull" in sig:
        d = "BUY 🟢"
        en = dh or c
        stp = (dl - atr*0.5) if dl else (en - atr*1.5)
        tp = en + abs(en - stp) * 2
    elif "Bear" in tr or "Bear" in sig:
        d = "SELL 🔴"
        en = sl or c
        stp = (sh + atr*0.5) if sh else (en + atr*1.5)
        tp = en - abs(stp - en) * 2
    else:
        d, en, stp, tp = "RANGE 🟡", sup + buf, sup - atr, res - buf
        
    return {"p":round(c,dec), "res":(res-buf,res), "sup":(sup,sup+buf), "dem":(dl,dh) if dl else None, "sup_z":(sl,sh) if sl else None, "sig":sig, "dir":d, "en":round(en,dec), "sl":round(stp,dec), "tp":round(tp,dec), "atr":round(atr,dec)}

# ==================== পেজ ১: চার্ট ও RSI ====================
if page == "📊 চার্ট ও RSI":
    c1, c2 = st.columns(2)
    pn = c1.selectbox("পেয়ার", list(pairs.keys()), key="t1_p")
    tfl = c2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="t1_tf")
    
    if st.button("🔍 অ্যানালাইসিস দেখুন", use_container_width=True, type="primary"):
        tk = pairs[pn]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        with st.spinner("ডেটা লোড হচ্ছে..."):
            df = get_df(tk, *tfs[tfl])
            df_htf = get_df(tk, *htf_map[tfl])
            dfd = get_df(tk, "5d", "1d")
        
        if len(df) >= 25:
            pdh = round(float(dfd['High'].iloc[-2]), dec) if len(dfd)>=2 else None
            pdl = round(float(dfd['Low'].iloc[-2]), dec) if len(dfd)>=2 else None
            
            df = add_indicators(df)
            ltf_tr = trend(df)
            htf_tr = trend(add_indicators(df_htf)) if len(df_htf) >= 30 else "N/A"
            z = analyze(df, dec)
            rsi_val = round(float(df['RSI'].iloc[-1]), 1)
            adx_val = round(float(df['ADX'].iloc[-1]), 1) if not pd.isna(df['ADX'].iloc[-1]) else 0
            
            trend_str = "Strong Trend 💪" if adx_val > 25 else "Weak/Choppy 💤"
            
            score = 0
            if ltf_tr == htf_tr and "Ranging" not in ltf_tr: score += 2
            elif "Ranging" not in ltf_tr: score += 1
            if adx_val > 25: score += 1
            if ("BUY" in z["dir"] and rsi_val < 68) or ("SELL" in z["dir"] and rsi_val > 32): score += 1
            
            conf_text = "⭐⭐⭐ High Probability" if score >= 3 else ("⭐⭐ Moderate" if score == 2 else "⚠️ Low / Wait")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("প্রাইস", z["p"])
            m2.metric("ADX (Strength)", f"{adx_val}", trend_str)
            m3.metric("Prev High", pdh)
            m4.metric("Prev Low", pdl)
            
            st.success(f"**Setup:** {conf_text} | **HTF Bias:** {htf_tr}")
            st.info(f"**ট্রেন্ড ({tfl}):** {ltf_tr} | **স্ট্যাটাস:** {z['sig']}")
            
            t1, t2, t3, t4 = st.columns(4)
            t1.metric(f"Entry ({z['dir']})", z["en"])
            t2.metric("Stop Loss", z["sl"])
            t3.metric("Exit (1:2 TP)", z["tp"])
            t4.metric("ATR", z["atr"])
            
            pdf = df.iloc[-50:]
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])
            
            fig.add_trace(go.Candlestick(x=pdf.index, open=pdf['Open'], high=pdf['High'], low=pdf['Low'], close=pdf['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=pdf.index, y=pdf['EMA20'], line=dict(color='cyan', width=1.2), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=pdf.index, y=pdf['EMA50'], line=dict(color='orange', width=1.2), name='EMA 50'), row=1, col=1)
            
            fig.add_hrect(y0=z["res"], y1=z["res"], fillcolor="orange", opacity=0.15, annotation_text="Res", row=1, col=1)
            fig.add_hrect(y0=z["sup"], y1=z["sup"], fillcolor="deepskyblue", opacity=0.15, annotation_text="Sup", row=1, col=1)
            if z["dem"]: fig.add_hrect(y0=z["dem"], y1=z["dem"], fillcolor="green", opacity=0.25, annotation_text="Demand", row=1, col=1)
            if z["sup_z"]: fig.add_hrect(y0=z["sup_z"], y1=z["sup_z"], fillcolor="red", opacity=0.25, annotation_text="Supply", row=1, col=1)
            
            fig.add_hline(y=z["en"], line_dash="dash", line_color="cyan", annotation_text="Entry", row=1, col=1)
            fig.add_hline(y=z["sl"], line_dash="dot", line_color="red", annotation_text="SL", row=1, col=1)
            fig.add_hline(y=z["tp"], line_dash="dash", line_color="lime", annotation_text="TP", row=1, col=1)
            
            fig.add_trace(go.Scatter(x=pdf.index, y=pdf['RSI'], line=dict(color='violet', width=1.5), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="lime", row=2, col=1)
            
            fig.update_layout(xaxis_rangeslider_visible=False, height=480, margin=dict(l=5,r=5,t=20,b=5), template="plotly_dark", showlegend=False)
            fig.update_xaxes(type="category", showticklabels=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ পর্যাপ্ত ডেটা পাওয়া যায়নি। পেজ রিফ্রেশ করে বা অন্য টাইমফ্রেম সিলেক্ট করে আবার চেষ্টা করুন।")

# ==================== পেজ ২: SMC অ্যানালাইসিস ====================
