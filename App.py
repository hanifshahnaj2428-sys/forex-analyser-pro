import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os

# মোবাইল স্ক্রিনের জন্য পেজ সেটআপ
st.set_page_config(page_title="BD Pro Market & Journal", page_icon="📊", layout="centered")

st.title("📊 প্রো মার্কেট ও ট্রেডিং জার্নাল")
st.caption("ফরেক্স, গোল্ড, ইথিরিয়াম অ্যানালাইসিস ও ট্রেড হিস্ট্রি")

# ১. বাংলাদেশ সময় অনুযায়ী লাইভ সেশন নির্ণয়
def get_bd_session():
    bd_tz = pytz.timezone('Asia/Dhaka')
    now_bd = datetime.now(bd_tz)
    hour = now_bd.hour
    time_str = now_bd.strftime("%I:%M %p (BD Time)")
    
    sessions = []
    if 6 <= hour < 15:
        sessions.append("🌏 Asian Session")
    if 13 <= hour < 22:
        sessions.append("🇬🇧 London Session")
    if 18 <= hour or hour < 3:
        sessions.append("🇺🇸 New York Session")
        
    if 18 <= hour < 22:
        status = "🔥 HIGH VOLUME: London + New York Overlap"
        box_type = "success"
    elif sessions:
        status = " | ".join(sessions)
        box_type = "info"
    else:
        status = "💤 অফ-সেশন (ক্রিপ্টো/ETH ২৪/৭ সচল)"
        box_type = "warning"
        
    return time_str, status, box_type

bd_time, session_status, session_box = get_bd_session()
with st.container(border=True):
    st.markdown(f"**🕒 বর্তমান সময়:** {bd_time}")
    if session_box == "success":
        st.success(session_status)
    elif session_box == "info":
        st.info(session_status)
    else:
        st.warning(session_status)

# মোবাইল-ফ্রেন্ডলি মেনু সিলেক্টর
menu = st.radio(
    "মেনু বেছে নিন:",
    ["📊 চার্ট ও জোন", "🚀 অল-পেয়ার স্ক্যানার", "📒 ট্রেডিং জার্নাল"],
    horizontal=True,
    label_visibility="collapsed",
    key="main_navigation_menu"
)
st.divider()

# কারেন্সি, গোল্ড ও ইথিরিয়াম পেয়ার লিস্ট
pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "GOLD (XAU/USD)": "GC=F",
    "ETHEREUM (ETH/USD)": "ETH-USD"
}

def get_clean_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def check_trend(df):
    if len(df) < 50:
        return "ডেটা কম ⚪"
    ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    close = float(df['Close'].iloc[-1])
    
    if close > ema20 and ema20 > ema50:
        return "🟢 Bullish"
    elif close < ema20 and ema20 < ema50:
        return "🔴 Bearish"
    else:
        return "🟡 Ranging"

def analyze_zones(df, decimals):
    current_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    
    lookback = df.iloc[-32:-2]
    res_level = float(lookback['High'].max())
    sup_level = float(lookback['Low'].min())
    zone_buffer = (res_level - sup_level) * 0.05
    
    res_low = res_level - zone_buffer
    res_high = res_level
    sup_low = sup_level
    sup_high = sup_level + zone_buffer
    
    supply_low, supply_high = None, None
    demand_low, demand_high = None, None
    
    body_sizes = (df['Close'] - df['Open']).abs()
    avg_body = float(body_sizes.iloc[-25:-1].mean())
    
    for i in range(len(df)-2, len(df)-20, -1):
        move = float(df['Close'].iloc[i] - df['Open'].iloc[i])
        if move > (avg_body * 1.8) and demand_low is None:
            d_low = float(df['Low'].iloc[i-1])
            d_high = max(float(df['Open'].iloc[i-1]), float(df['Close'].iloc[i-1]))
            if current_close > d_high:
                demand_low, demand_high = d_low, d_high
        if move < -(avg_body * 1.8) and supply_low is None:
            s_high = float(df['High'].iloc[i-1])
            s_low = min(float(df['Open'].iloc[i-1]), float(df['Close'].iloc[i-1]))
            if current_close < s_low:
                supply_low, supply_high = s_low, s_high
                
    breakout_status = "⚪ কোনো ব্রেকআউট/রিটেস্ট নেই"
    is_active_signal = False
    
    if current_close > res_level and prev_close <= res_level:
        breakout_status = f"🚀 Bullish Breakout! ({round(res_level, decimals)})"
        is_active_signal = True
    elif current_close > res_level and abs(float(df['Low'].iloc[-1]) - res_level) <= zone_buffer * 1.5:
        breakout_status = f"🎯 Bullish Breakout + Retest! ({round(res_level, decimals)})"
        is_active_signal = True
    elif current_close < sup_level and prev_close >= sup_level:
        breakout_status = f"🔻 Bearish Breakout! ({round(sup_level, decimals)})"
        is_active_signal = True
    elif current_close < sup_level and abs(float(df['High'].iloc[-1]) - sup_level) <= zone_buffer * 1.5:
        breakout_status = f"🎯 Bearish Breakout + Retest! ({round(sup_level, decimals)})"
        is_active_signal = True
        
    return {
        "price": round(current_close, decimals),
        "res_bounds": (res_low, res_high),
        "sup_bounds": (sup_low, sup_high),
        "supply_bounds": (supply_low, supply_high) if supply_low is not None else None,
        "demand_bounds": (demand_low, demand_high) if demand_low is not None else None,
        "res_text": f"{round(res_low, decimals)} - {round(res_high, decimals)}",
        "sup_text": f"{round(sup_low, decimals)} - {round(sup_high, decimals)}",
        "supply_text": f"{round(supply_low, decimals)} - {round(supply_high, decimals)}" if supply_low is not None else "ফ্রেশ জোন নেই",
        "demand_text": f"{round(demand_low, decimals)} - {round(demand_high, decimals)}" if demand_low is not None else "ফ্রেশ জোন নেই",
        "breakout": breakout_status,
        "active": is_active_signal
    }

def draw_zone_chart(df, zones, title):
    plot_df = df.iloc[-45:].copy()
    fig = go.Figure(data=[go.Candlestick(
        x=plot_df.index,
        open=plot_df['Open'],
        high=plot_df['High'],
        low=plot_df['Low'],
        close=plot_df['Close'],
        name="Price"
    )])
    
    fig.add_hrect(y0=zones["res_bounds"], y1=zones["res_bounds"], fillcolor="rgba(255, 165, 0, 0.25)", line_width=1, line_color="orange", annotation_text="Resistance", annotation_position="top left")
    fig.add_hrect(y0=zones["sup_bounds"], y1=zones["sup_bounds"], fillcolor="rgba(0, 191, 255, 0.25)", line_width=1, line_color="deepskyblue", annotation_text="Support", annotation_position="bottom left")
    
    if zones["supply_bounds"]:
        fig.add_hrect(y0=zones["supply_bounds"], y1=zones["supply_bounds"], fillcolor="rgba(255, 0, 0, 0.28)", line_width=1.5, line_color="red", annotation_text="Supply (Sell)", annotation_position="top right")
    if zones["demand_bounds"]:
        fig.add_hrect(y0=zones["demand_bounds"], y1=zones["demand_bounds"], fillcolor="rgba(0, 200, 83, 0.28)", line_width=1.5, line_color="green", annotation_text="Demand (Buy)", annotation_position="bottom right")

    fig.update_layout(title=title, xaxis_rangeslider_visible=False, height=360, margin=dict(l=10, r=10, t=40, b=10), template="plotly_dark", xaxis_type="category")
    fig.update_xaxes(showticklabels=False)
    return fig

# ==========================================
# মেনু ১: চার্ট ও জোন অ্যানালাইসিস
# ==========================================
if menu == "📊 চার্ট ও জোন":
    selected_pair_name = st.selectbox("অ্যানালাইসিস করার জন্য পেয়ার বেছে নিন:", list(pairs.keys()), key="chart_pair_select")
    ticker = pairs[selected_pair_name]
    
    if st.button(f"🔍 {selected_pair_name} চার্ট ও জোন দেখুন", use_container_width=True, type="primary", key="btn_chart_analyze"):
        with st.spinner("চার্ট এবং জোন তৈরি হচ্ছে..."):
            decimals = 2 if ("GC=F" in ticker or "JPY" in ticker or "ETH" in ticker) else 5
            
            df_1d = get_clean_data(ticker, "6mo", "1d")
            df_1h = get_clean_data(ticker, "1mo", "1h")
            df_15m = get_clean_data(ticker, "5d", "15m")
            
            if df_1d.empty or df_1h.empty or df_15m.empty:
                st.error("মার্কেট ডেটা লোড করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
            else:
                df_4h = df_1h.resample("4h").agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
                
                st.subheader("📈 ১. মার্কেট ট্রেন্ড (1D / 4H / 1H)")
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("1 Day", check_trend(df_1d))
                with c2: st.metric("4 Hour", check_trend(df_4h))
                with c3: st.metric("1 Hour", check_trend(df_1h))
                    
                res_1h = analyze_zones(df_1h, decimals)
                st.subheader(f"⏱️ ২. ১ ঘণ্টা (1H) চার্ট ও জোন (Price: {res_1h['price']})")
                st.plotly_chart(draw_zone_chart(df_1h, res_1h, f"{selected_pair_name} - 1H Zones"), use_container_width=True)
                with st.container(border=True):
                    st.markdown(f"🔴 **Supply:** `{res_1h['supply_text']}` | 🟢 **Demand:** `{res_1h['demand_text']}`")
                    st.markdown(f"🚧 **Resistance:** `{res_1h['res_text']}` | 🛡️ **Support:** `{res_1h['sup_text']}`")
                    st.info(f"**ব্রেকআউট/রিটেস্ট (1H):** {res_1h['breakout']}")

                res_15m = analyze_zones(df_15m, decimals)
                st.subheader("⚡ ৩. ১৫ মিনিট (15m) চার্ট ও জোন")
                st.plotly_chart(draw_zone_chart(df_15m, res_15m, f"{selected_pair_name} - 15m Zones"), use_container_width=True)
                with st.container(border=True):
                    st.markdown(f"🔴 **Supply:** `{res_15m['supply_text']}` | 🟢 **Demand:** `{res_15m['demand_text']}`")
                    st.markdown(f"🚧 **Resistance:** `{res_15m['res_text']}` | 🛡️ **Support:** `{res_15m['sup_text']}`")
                    st.info(f"**ব্রেকআউট/রিটেস্ট (15m):** {res_15m['breakout']}")

