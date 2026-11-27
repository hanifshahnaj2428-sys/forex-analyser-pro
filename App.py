import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="BD Pro Market", page_icon="📊", layout="centered")
st.title("📊 প্রো মার্কেট ও ট্রেডিং জার্নাল")

pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "GOLD (XAU/USD)": "GC=F",
    "ETHEREUM (ETH/USD)": "ETH-USD"
}

bd_tz = pytz.timezone('Asia/Dhaka')
now_bd = datetime.now(bd_tz)
st.info(f"🕒 বাংলাদেশ সময়: {now_bd.strftime('%I:%M %p')}")

def get_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

def get_trend(df):
    if len(df) < 50: return "N/A"
    e20 = df['Close'].ewm(span=20).mean().iloc[-1]
    e50 = df['Close'].ewm(span=50).mean().iloc[-1]
    c = float(df['Close'].iloc[-1])
    if c > e20 > e50: return "🟢 Bullish"
    if c < e20 < e50: return "🔴 Bearish"
    return "🟡 Ranging"

def get_zones(df, dec):
    c = float(df['Close'].iloc[-1])
    res = float(df.iloc[-32:-2]['High'].max())
    sup = float(df.iloc[-32:-2]['Low'].min())
    buf = (res - sup) * 0.05
    status = "⚪ রানিং মার্কেট"
    if c > res: status = f"🚀 Bullish Breakout ({round(res, dec)})"
    elif c < sup: status = f"🔻 Bearish Breakout ({round(sup, dec)})"
    return round(c, dec), (res - buf, res), (sup, sup + buf), status

tab1, tab2, tab3 = st.tabs(["📊 চার্ট ও জোন", "🚀 স্ক্যানার", "📒 জার্নাল"])

with tab1:
    p_name = st.selectbox("পেয়ার বেছে নিন:", list(pairs.keys()))
    if st.button("🔍 অ্যানালাইসিস দেখুন", use_container_width=True, type="primary"):
        tk = pairs[p_name]
        dec = 2 if ("GC=F" in tk or "JPY" in tk or "ETH" in tk) else 5
        df1h = get_data(tk, "1mo", "1h")
        df1d = get_data(tk, "6mo", "1d")
        if not df1h.empty:
            price, res_b, sup_b, sig = get_zones(df1h, dec)
            c1, c2, c3 = st.columns(3)
            c1.metric("প্রাইস", price)
            c2.metric("Daily", get_trend(df1d))
            c3.metric("Hourly", get_trend(df1h))
            st.success(sig)
            plot_df = df1h.iloc[-40:]
            fig = go.Figure(data=[go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'])])
            fig.add_hrect(y0=res_b, y1=res_b, fillcolor="orange", opacity=0.25, annotation_text="Resistance")
            fig.add_hrect(y0=sup_b, y1=sup_b, fillcolor="deepskyblue", opacity=0.25, annotation_text="Support")
            fig.update_layout(xaxis_rangeslider_visible=False, height=350, template="plotly_dark", xaxis_type="category")
            fig.update_xaxes(showticklabels=False)
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("🚀 অল-পেয়ার স্ক্যানার (1H)")
    if st.button("🔄 স্ক্যান শুরু করুন", use_container_width=True, type="primary"):
        rows = []
        for name, tk in pairs.items():
            dec = 2 if ("GC=F" in tk or "JPY" in tk or "ETH" in tk) else 5
            df = get_data(tk, "1mo", "1h")
            if not df.empty:
                p, _, _, sig = get_zones(df, dec)
                rows.append({"Pair": name, "Price": p, "Trend": get_trend(df), "Signal": sig})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📒 ট্রেডিং জার্নাল")
    j_file = "journal.csv"
    with st.form("j_form", clear_on_submit=True):
        jp = st.selectbox("পেয়ার", list(pairs.keys()))
        jt = st.selectbox("ধরন", ["BUY 🟢", "SELL 🔴"])
        jr = st.selectbox("রেজাল্ট", ["Win ✅", "Loss ❌"])
        jpnl = st.number_input("প্রফিট/লস ($)", value=0.0)
        if st.form_submit_button("💾 সেভ করুন", use_container_width=True):
            row = pd.DataFrame([{"Time": now_bd.strftime("%d-%b %I:%M%p"), "Pair": jp, "Type": jt, "Result": jr, "PnL": jpnl}])
            df_old = pd.read_csv(j_file) if os.path.exists(j_file) else pd.DataFrame()
            pd.concat([row, df_old], ignore_index=True).to_csv(j_file, index=False)
            st.success("সেভ হয়েছে!")
    if os.path.exists(j_file):
        df_j = pd.read_csv(j_file)
        st.metric("মোট PnL ($)", f"${df_j['PnL'].sum():.2f}")
        st.dataframe(df_j, use_container_width=True, hide_index=True)
