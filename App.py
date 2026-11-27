import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="BD Pro Market & Journal", page_icon="📊", layout="centered")
st.title("📊 প্রো মার্কেট ও ট্রেডিং জার্নাল")
st.caption("ফরেক্স, গোল্ড, ইথিরিয়াম অ্যানালাইসিস, এন্ট্রি-এক্সিট ও ট্রেড হিস্ট্রি")

# ১. বাংলাদেশ সময় অনুযায়ী লাইভ সেশন
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

def get_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

def get_trend(df):
    if len(df) < 50: return "ডেটা কম ⚪"
    e20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
    e50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    c = float(df['Close'].iloc[-1])
    if c > e20 > e50: return "🟢 Bullish"
    if c < e20 < e50: return "🔴 Bearish"
    return "🟡 Ranging"

def analyze_zones(df, dec):
    c = float(df['Close'].iloc[-1])
    prev_c = float(df['Close'].iloc[-2])
    lookback = df.iloc[-32:-2]
    res = float(lookback['High'].max())
    sup = float(lookback['Low'].min())
    buf = (res - sup) * 0.05
    
    res_b = [res - buf, res]
    sup_b = [sup, sup + buf]
    supply_b, demand_b = None, None
    
    avg_body = float((df['Close'] - df['Open']).abs().iloc[-25:-1].mean())
    for i in range(len(df)-2, len(df)-20, -1):
        move = float(df['Close'].iloc[i] - df['Open'].iloc[i])
        if move > (avg_body * 1.8) and demand_b is None:
            d_l = float(df['Low'].iloc[i-1])
            d_h = max(float(df['Open'].iloc[i-1]), float(df['Close'].iloc[i-1]))
            if c > d_h: demand_b = [d_l, d_h]
        if move < -(avg_body * 1.8) and supply_b is None:
            s_h = float(df['High'].iloc[i-1])
            s_l = min(float(df['Open'].iloc[i-1]), float(df['Close'].iloc[i-1]))
            if c < s_l: supply_b = [s_l, s_h]

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

    # এন্ট্রি, স্টপ লস (SL) ও এক্সিট (TP) ক্যালকুলেশন
    trend = get_trend(df)
    if "Bullish" in trend or "Bullish" in sig:
        direction = "BUY 🟢"
        entry = demand_b[1] if demand_b else sup_b[1]
        sl = (demand_b[0] if demand_b else sup_b[0]) - (buf * 0.5)
        risk = max(abs(entry - sl), buf)
        tp = entry + (risk * 2.0)  # 1:2 Risk-Reward
    elif "Bearish" in trend or "Bearish" in sig:
        direction = "SELL 🔴"
        entry = supply_b[0] if supply_b else res_b[0]
        sl = (supply_b[1] if supply_b else res_b[1]) + (buf * 0.5)
        risk = max(abs(sl - entry), buf)
        tp = entry - (risk * 2.0)  # 1:2 Risk-Reward
    else:
        direction = "WAIT / RANGE 🟡"
        entry = sup_b[1]
        sl = sup_b[0] - (buf * 0.5)
        tp = res_b[0]

    return {
        "price": round(c, dec), "res_b": res_b, "sup_b": sup_b,
        "supply_b": supply_b, "demand_b": demand_b,
        "res_t": f"{round(res_b[0], dec)} - {round(res_b[1], dec)}",
        "sup_t": f"{round(sup_b[0], dec)} - {round(sup_b[1], dec)}",
        "supply_t": f"{round(supply_b[0], dec)} - {round(supply_b[1], dec)}" if supply_b else "ফ্রেশ জোন নেই",
        "demand_t": f"{round(demand_b[0], dec)} - {round(demand_b[1], dec)}" if demand_b else "ফ্রেশ জোন নেই",
        "sig": sig, "active": active,
        "dir": direction, "entry": round(entry, dec), "sl": round(sl, dec), "tp": round(tp, dec)
    }

tab1, tab2, tab3 = st.tabs(["📊 চার্ট ও জোন", "🚀 অল-পেয়ার স্ক্যানার", "📒 ট্রেডিং জার্নাল"])

with tab1:
    p_name = st.selectbox("পেয়ার বেছে নিন:", list(pairs.keys()))
    if st.button(f"🔍 {p_name} চার্ট ও জোন দেখুন", use_container_width=True, type="primary"):
        tk = pairs[p_name]
        dec = 2 if ("GC=F" in tk or "JPY" in tk or "ETH" in tk) else 5
        df1d = get_data(tk, "6mo", "1d")
        df1h = get_data(tk, "1mo", "1h")
        df15m = get_data(tk, "5d", "15m")
        if not df1h.empty:
            z = analyze_zones(df1h, dec)
            st.subheader(f"💰 প্রাইস: {z['price']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Daily (1D)", get_trend(df1d))
            c2.metric("Hourly (1H)", get_trend(df1h))
            c3.metric("15 Min (15M)", get_trend(df15m))
            
            if z["active"]: st.success(z["sig"])
            else: st.info(z["sig"])

            # এন্ট্রি, স্টপ লস ও এক্সিট বক্স
            with st.container(border=True):
                st.markdown(f"#### 🎯 ট্রেড সেটআপ ({z['dir']})")
                t1, t2, t3 = st.columns(3)
                t1.metric("🔵 Entry Zone", z["entry"])
                t2.metric("🛑 Stop Loss", z["sl"])
                t3.metric("🏁 Exit (TP 1:2)", z["tp"])
            
            plot_df = df1h.iloc[-45:]
            fig = go.Figure(data=[go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'])])
            fig.add_hrect(y0=z["res_b"][0], y1=z["res_b"][1], fillcolor="rgba(255,165,0,0.20)", line_color="orange", annotation_text="Resistance", annotation_position="top left")
            fig.add_hrect(y0=z["sup_b"][0], y1=z["sup_b"][1], fillcolor="rgba(0,191,255,0.20)", line_color="deepskyblue", annotation_text="Support", annotation_position="bottom left")
            if z["supply_b"]:
                fig.add_hrect(y0=z["supply_b"][0], y1=z["supply_b"][1], fillcolor="rgba(255,0,0,0.25)", line_color="red", annotation_text="Supply", annotation_position="top right")
            if z["demand_b"]:
                fig.add_hrect(y0=z["demand_b"][0], y1=z["demand_b"][1], fillcolor="rgba(0,200,83,0.25)", line_color="green", annotation_text="Demand", annotation_position="bottom right")
            
            # চার্টে Entry, SL ও Exit লাইন আঁকা
            fig.add_hline(y=z["entry"], line_dash="dash", line_color="#00E5FF", annotation_text=f"Entry: {z['entry']}", annotation_position="top left")
            fig.add_hline(y=z["sl"], line_dash="dot", line_color="#FF1744", annotation_text=f"SL: {z['sl']}", annotation_position="bottom left")
            fig.add_hline(y=z["tp"], line_dash="dash", line_color="#00E676", annotation_text=f"Exit/TP: {z['tp']}", annotation_position="top right")

            fig.update_layout(xaxis_rangeslider_visible=False, height=400, margin=dict(l=10, r=10, t=30, b=10), template="plotly_dark", xaxis_type="category")
            fig.update_xaxes(showticklabels=False)
            st.plotly_chart(fig, use_container_width=True)
            
            with st.container(border=True):
                col1, col2 = st.columns(2)
                col1.markdown(f"**🔴 Supply (Sell):**\n`{z['supply_t']}`")
                col2.markdown(f"**🟢 Demand (Buy):**\n`{z['demand_t']}`")
                st.divider()
                col3, col4 = st.columns(2)
                col3.markdown(f"**🟠 Resistance:**\n`{z['res_t']}`")
                col4.markdown(f"**🔵 Support:**\n`{z['sup_t']}`")

with tab2:
    st.subheader("🚀 অল-পেয়ার স্ক্যানার (1H)")
    if st.button("🔄 এখনই স্ক্যান করুন", use_container_width=True, type="primary"):
        rows = []
        for name, tk in pairs.items():
            dec = 2 if ("GC=F" in tk or "JPY" in tk or "ETH" in tk) else 5
            df = get_data(tk, "1mo", "1h")
            if not df.empty:
                z = analyze_zones(df, dec)
                rows.append({
                    "Pair": name, "Price": z["price"], "Setup": z["dir"],
                    "Entry": z["entry"], "SL": z["sl"], "Exit (TP)": z["tp"],
                    "Signal": z["sig"]
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📒 ট্রেডিং জার্নাল")
    j_file = "journal.csv"
    with st.form("j_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        jp = c1.selectbox("পেয়ার", list(pairs.keys()))
        jt = c2.selectbox("পজিশন", ["BUY 🟢", "SELL 🔴"])
        c3, c4 = st.columns(2)
        jr = c3.selectbox("ফলাফল", ["Win ✅", "Loss ❌", "BE ⚪"])
        jpnl = c4.number_input("প্রফিট/লস ($)", value=0.0, step=1.0)
        jnote = st.text_input("নোট / স্ট্র্যাটেজি")
        if st.form_submit_button("💾 সেভ করুন", use_container_width=True):
            row = pd.DataFrame([{"Date": now_bd.strftime("%d-%b %I:%M%p"), "Pair": jp, "Type": jt, "Result": jr, "PnL ($)": jpnl, "Note": jnote}])
            df_old = pd.read_csv(j_file) if os.path.exists(j_file) else pd.DataFrame()
            pd.concat([row, df_old], ignore_index=True).to_csv(j_file, index=False)
            st.success("✅ সেভ হয়েছে!")
    if os.path.exists(j_file):
        df_j = pd.read_csv(j_file)
        if not df_j.empty:
