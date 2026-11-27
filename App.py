import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="BD Pro Market & SMC", page_icon="📊", layout="centered")
st.title("📊 প্রো মার্কেট, SMC ও জার্নাল")
st.caption("মাল্টি-টাইমফ্রেম, PDH/PDL, Smart Money Concept ও ট্রেড হিস্ট্রি")

bd_tz = pytz.timezone('Asia/Dhaka')
now_bd = datetime.now(bd_tz)
hr = now_bd.hour
sessions = []
if 6 <= hr < 15: sessions.append("🌏 Asian")
if 13 <= hr < 22: sessions.append("🇬🇧 London")
if 18 <= hr or hr < 3: sessions.append("🇺🇸 New York")

with st.container(border=True):
    st.markdown(f"**🕒 বর্তমান সময়:** {now_bd.strftime('%I:%M %p (BD Time)')}")
    if 18 <= hr < 22:
        st.success("🔥 HIGH VOLUME: London + New York Overlap")
    elif sessions:
        st.info(" | ".join(sessions) + " Session")
    else:
        st.warning("💤 অফ-সেশন (ক্রিপ্টো/ETH ২৪/৭ সচল)")

pairs = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X", "GOLD (XAU/USD)": "GC=F", "ETHEREUM (ETH/USD)": "ETH-USD"
}

tf_options = {
    "5 মিনিট (5M)": ("5d", "5m"),
    "15 মিনিট (15M)": ("5d", "15m"),
    "1 ঘণ্টা (1H)": ("1mo", "1h"),
    "4 ঘণ্টা (4H)": ("2mo", "4h")
}

def get_data(symbol, period, interval):
    fetch_int = "1h" if interval == "4h" else interval
    df = yf.download(symbol, period=period, interval=fetch_int, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    if interval == "4h" and not df.empty:
        df = df.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    return df

def get_trend(df):
    if len(df) < 50: return "ডেটা কম ⚪"
    e20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
    e50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    c = float(df['Close'].iloc[-1])
    if c > e20 > e50: return "🟢 Bullish"
    if c < e20 < e50: return "🔴 Bearish"
    return "🟡 Ranging"

def get_prev_day_hl(symbol, dec):
    df_d = get_data(symbol, "5d", "1d")
    if len(df_d) >= 2:
        pdh = round(float(df_d['High'].iloc[-2]), dec)
        pdl = round(float(df_d['Low'].iloc[-2]), dec)
        return pdh, pdl
    return None, None

def analyze_zones(df, dec):
    c = float(df['Close'].iloc[-1])
    prev_c = float(df['Close'].iloc[-2])
    lookback = df.iloc[-32:-2]
    res = float(lookback['High'].max())
    sup = float(lookback['Low'].min())
    buf = (res - sup) * 0.05
    
    res_low, res_high = res - buf, res
    sup_low, sup_high = sup, sup + buf
    s_low, s_high, d_low, d_high = None, None, None, None
    
    avg_body = float((df['Close'] - df['Open']).abs().iloc[-25:-1].mean())
    for i in range(len(df)-2, max(len(df)-20, 1), -1):
        move = float(df['Close'].iloc[i] - df['Open'].iloc[i])
        if move > (avg_body * 1.8) and d_low is None:
            dl = float(df['Low'].iloc[i-1])
            dh = max(float(df['Open'].iloc[i-1]), float(df['Close'].iloc[i-1]))
            if c > dh: d_low, d_high = dl, dh
        if move < -(avg_body * 1.8) and s_low is None:
            sh = float(df['High'].iloc[i-1])
            sl_val = min(float(df['Open'].iloc[i-1]), float(df['Close'].iloc[i-1]))
            if c < sl_val: s_low, s_high = sl_val, sh

    sig = "⚪ কোনো ব্রেকআউট/রিটেস্ট নেই"
    active = False
    if c > res and prev_c <= res:
        sig, active = f"🚀 Bullish Breakout! ({round(res, dec)})", True
    elif c > res and abs(float(df['Low'].iloc[-1]) - res) <= buf * 1.5:
        sig, active = f"🎯 Bullish Breakout + Retest! ({round(res, dec)})", True
    elif c < sup and prev_c >= sup:
        sig, active = f"🔻 Bearish Breakout! ({round(sup, dec)})", True
    elif c < sup and abs(float(df['High'].iloc[-1]) - sup) <= buf * 1.5:
        sig, active = f"🎯 Bearish Breakout + Retest! ({round(sup, dec)})", True

    trend = get_trend(df)
    if "Bullish" in trend or "Bullish" in sig:
        direction = "BUY 🟢"
        entry = d_high if d_high is not None else sup_high
        sl_price = (d_low if d_low is not None else sup_low) - (buf * 0.5)
        risk = max(abs(entry - sl_price), buf)
        tp_price = entry + (risk * 2.0)
    elif "Bearish" in trend or "Bearish" in sig:
        direction = "SELL 🔴"
        entry = s_low if s_low is not None else res_low
        sl_price = (s_high if s_high is not None else res_high) + (buf * 0.5)
        risk = max(abs(sl_price - entry), buf)
        tp_price = entry - (risk * 2.0)
    else:
        direction = "WAIT / RANGE 🟡"
        entry, sl_price, tp_price = sup_high, sup_low - (buf * 0.5), res_low

    return {
        "price": round(c, dec), "res_b": (res_low, res_high), "sup_b": (sup_low, sup_high),
        "supply_b": (s_low, s_high) if s_low is not None else None,
        "demand_b": (d_low, d_high) if d_low is not None else None,
        "res_t": f"{round(res_low, dec)} - {round(res_high, dec)}",
        "sup_t": f"{round(sup_low, dec)} - {round(sup_high, dec)}",
        "supply_t": f"{round(s_low, dec)} - {round(s_high, dec)}" if s_low is not None else "ফ্রেশ জোন নেই",
        "demand_t": f"{round(d_low, dec)} - {round(d_high, dec)}" if d_low is not None else "ফ্রেশ জোন নেই",
        "sig": sig, "active": active, "dir": direction,
        "entry": round(entry, dec), "sl": round(sl_price, dec), "tp": round(tp_price, dec)
    }

def analyze_smc(df, dec):
    c = float(df['Close'].iloc[-1])
    swing_h = float(df.iloc[-25:-3]['High'].max())
    swing_l = float(df.iloc[-25:-3]['Low'].min())
    
    # BOS ও CHoCH ডিটেকশন
    trend = get_trend(df)
    if c > swing_h:
        structure = f"🟢 Bullish BOS / CHoCH ({round(swing_h, dec)} ব্রেক)"
    elif c < swing_l:
        structure = f"🔴 Bearish BOS / CHoCH ({round(swing_l, dec)} ব্রেক)"
    else:
        structure = f"🟡 Internal Structure ({round(swing_l, dec)} - {round(swing_h, dec)})"

    # Fair Value Gap (FVG) ও Order Block (OB) খোঁজা
    bull_fvg, bear_fvg = None, None
    bull_ob, bear_ob = None, None

    for i in range(len(df)-2, max(len(df)-25, 2), -1):
        c1_h, c1_l = float(df['High'].iloc[i-2]), float(df['Low'].iloc[i-2])
        c3_h, c3_l = float(df['High'].iloc[i]), float(df['Low'].iloc[i])
        
        # Bullish FVG
        if c3_l > c1_h and bull_fvg is None:
            bull_fvg = (round(c1_h, dec), round(c3_l, dec))
            if float(df['Close'].iloc[i-2]) < float(df['Open'].iloc[i-2]):
                bull_ob = (round(float(df['Low'].iloc[i-2]), dec), round(float(df['High'].iloc[i-2]), dec))
        # Bearish FVG
        if c3_h < c1_l and bear_fvg is None:
            bear_fvg = (round(c3_h, dec), round(c1_l, dec))
            if float(df['Close'].iloc[i-2]) > float(df['Open'].iloc[i-2]):
                bear_ob = (round(float(df['Low'].iloc[i-2]), dec), round(float(df['High'].iloc[i-2]), dec))

    return {
        "price": round(c, dec), "structure": structure, "trend": trend,
        "bull_fvg": bull_fvg, "bear_fvg": bear_fvg,
        "bull_ob": bull_ob, "bear_ob": bear_ob
    }

tab1, tab2, tab3, tab4 = st.tabs(["📊 চার্ট ও জোন", "🧠 SMC অ্যানালাইসিস", "🚀 স্ক্যানার", "📒 জার্নাল"])

with tab1:
    c_sel1, c_sel2 = st.columns(2)
    p_name = c_sel1.selectbox("পেয়ার বেছে নিন:", list(pairs.keys()), key="t1_pair")
    tf_label = c_sel2.selectbox("টাইমফ্রেম বেছে নিন:", list(tf_options.keys()), index=2, key="t1_tf")
    
    if st.button(f"🔍 {p_name} ({tf_label}) অ্যানালাইসিস", use_container_width=True, type="primary"):
        tk = pairs[p_name]
        dec = 2 if ("GC=F" in tk or "JPY" in tk or "ETH" in tk) else 5
        period, interval = tf_options[tf_label]
        df_tf = get_data(tk, period, interval)
        pdh, pdl = get_prev_day_hl(tk, dec)
        
        if not df_tf.empty:
            z = analyze_zones(df_tf, dec)
            st.subheader(f"💰 প্রাইস: {z['price']} ({tf_label})")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("ট্রেন্ড", get_trend(df_tf))
            m2.metric("আগের দিনের High", pdh if pdh else "N/A")
            m3.metric("আগের দিনের Low", pdl if pdl else "N/A")
            
            if z["active"]: st.success(z["sig"])
            else: st.info(z["sig"])

            with st.container(border=True):
                st.markdown(f"#### 🎯 ট্রেড সেটআপ ({z['dir']})")
                t1, t2, t3 = st.columns(3)
                t1.metric("🔵 Entry Zone", z["entry"])
                t2.metric("🛑 Stop Loss", z["sl"])
                t3.metric("🏁 Exit (TP 1:2)", z["tp"])
            
            plot_df = df_tf.iloc[-45:]
            fig = go.Figure(data=[go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'])])
            fig.add_hrect(y0=z["res_b"], y1=z["res_b"], fillcolor="rgba(255,165,0,0.18)", line_color="orange", annotation_text="Res", annotation_position="top left")
            fig.add_hrect(y0=z["sup_b"], y1=z["sup_b"], fillcolor="rgba(0,191,255,0.18)", line_color="deepskyblue", annotation_text="Sup", annotation_position="bottom left")
            if z["supply_b"]:
                fig.add_hrect(y0=z["supply_b"], y1=z["supply_b"], fillcolor="rgba(255,0,0,0.22)", line_color="red", annotation_text="Supply", annotation_position="top right")
            if z["demand_b"]:
                fig.add_hrect(y0=z["demand_b"], y1=z["demand_b"], fillcolor="rgba(0,200,83,0.22)", line_color="green", annotation_text="Demand", annotation_position="bottom right")
            
            fig.add_hline(y=z["entry"], line_dash="dash", line_color="#00E5FF", annotation_text=f"Entry: {z['entry']}", annotation_position="top left")
            fig.add_hline(y=z["sl"], line_dash="dot", line_color="#FF1744", annotation_text=f"SL: {z['sl']}", annotation_position="bottom left")
