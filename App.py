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
    return "🟢 Bullish" if c > e20 > e50 else ("🔴 Bearish" if c < e20 < e50 else "🟡 Ranging")

def get_rsi(df):
    d = df['Close'].diff()
    g = d.where(d > 0, 0).rolling(14).mean()
    l = (-d.where(d < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + g / l.replace(0, 1e-10)))
    return round(float(rsi.iloc[-1]), 1) if not pd.isna(rsi.iloc[-1]) else 50.0

def make_fig(df_s, h=400):
    xl = [str(i) for i in df_s.index]
    fig = go.Figure(data=[go.Candlestick(
        x=xl,
        open=df_s['Open'].tolist(),
        high=df_s['High'].tolist(),
        low=df_s['Low'].tolist(),
        close=df_s['Close'].tolist(),
        name="Price"
    )])
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=h,
        margin=dict(l=5, r=5, t=30, b=5),
        template="plotly_dark",
        xaxis_type="category",
        showlegend=False
    )
    fig.update_xaxes(showticklabels=False)
    return fig, xl

# ক্যান্ডেলস্টিকের ওপর ১০০% দৃশ্যমান জোন বক্স আঁকার ফাংশন
def draw_box(fig, x_start, x_end, y_low, y_high, fill_rgba, border_color, label):
    fig.add_trace(go.Scatter(
        x=[x_start, x_end, x_end, x_start, x_start],
        y=[y_low, y_low, y_high, y_high, y_low],
        fill="toself",
        fillcolor=fill_rgba,
        line=dict(color=border_color, width=1.5),
        mode="lines",
        hoverinfo="skip"
    ))
    fig.add_annotation(
        x=x_end,
        y=(y_low + y_high) / 2,
        text=f"<b>{label}</b>",
        showarrow=False,
        xanchor="right",
        font=dict(color="white", size=11),
        bgcolor=border_color,
        borderpad=3
    )

def draw_line(fig, x_start, x_end, y_val, color, label, dash="dash"):
    fig.add_trace(go.Scatter(
        x=[x_start, x_end],
        y=[y_val, y_val],
        mode="lines",
        line=dict(color=color, width=1.5, dash=dash)
    ))
    fig.add_annotation(
        x=x_start,
        y=y_val,
        text=f"<b>{label}</b>",
        showarrow=False,
        xanchor="left",
        yshift=10,
        font=dict(color=color, size=11)
    )

tab1, tab2 = st.tabs(["📊 প্রাইস অ্যাকশন ও জোন", "🧠 অ্যাডভান্সড SMC অ্যানালাইসিস"])

with tab1:
    c1, c2 = st.columns(2)
    pn = c1.selectbox("পেয়ার", list(pairs.keys()), key="p1")
    tfl = c2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf1")
    if st.button("🔍 চার্ট অ্যানালাইসিস দেখুন", use_container_width=True, type="primary", key="b1"):
        tk = pairs[pn]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        df = get_df(tk, *tfs[tfl])
        dfd = get_df(tk, "5d", "1d")
        if len(df) >= 15:
            c = float(df['Close'].iloc[-1])
            lb = min(32, len(df)-2)
            res, sup = float(df.iloc[-lb:-2]['High'].max()), float(df.iloc[-lb:-2]['Low'].min())
            buf = (res - sup) * 0.05
            tr = trend(df)
            d, en, stp = ("BUY 🟢", sup+buf, sup-buf*0.5) if "Bull" in tr else (("SELL 🔴", res-buf, res+buf*0.5) if "Bear" in tr else ("RANGE 🟡", sup+buf, sup-buf*0.5))
            tp = en + abs(en-stp)*2 if "BUY" in d or "RANGE" in d else en - abs(stp-en)*2
            pdh = round(float(dfd['High'].iloc[-2]), dec) if len(dfd)>=2 else None
            pdl = round(float(dfd['Low'].iloc[-2]), dec) if len(dfd)>=2 else None
            
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
            
            ps1 = df.iloc[-45:]
            fig, xl = make_fig(ps1, 380)
            draw_box(fig, xl[0], xl[-1], res-buf, res, "rgba(255, 165, 0, 0.22)", "#FFA500", "Resistance Zone")
            draw_box(fig, xl[0], xl[-1], sup, sup+buf, "rgba(0, 191, 255, 0.22)", "#00BFFF", "Support Zone")
            draw_line(fig, xl[0], xl[-1], en, "#00FFFF", f"Entry: {round(en,dec)}")
            draw_line(fig, xl[0], xl[-1], stp, "#FF4B4B", f"SL: {round(stp,dec)}", "dot")
            draw_line(fig, xl[0], xl[-1], tp, "#00FF7F", f"TP: {round(tp,dec)}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ ডেটা লোড হয়নি।")

with tab2:
    if "smc_on" not in st.session_state:
        st.session_state.smc_on = False

    s1, s2 = st.columns(2)
    sp = s1.selectbox("পেয়ার", list(pairs.keys()), key="p2")
    stf = s2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf2")
    tool = st.selectbox("SMC উপাদান নির্বাচন করুন:", [
        "১. ফেয়ার ভ্যালু গ্যাপ (FVG & 50% CE)",
        "২. অর্ডার ব্লক (Order Block)",
        "৩. মার্কেট স্ট্রাকচার (BOS / CHoCH)",
        "৪. প্রিমিয়াম / ডিসকাউন্ট ও OTE",
        "৫. লিকুইডিটি পুল (BSL / SSL)"
    ], key="tool")
    
    if st.button("⚡ চার্ট ও SMC অ্যানালাইসিস দেখুন", use_container_width=True, type="primary", key="b2"):
        st.session_state.smc_on = True

    if st.session_state.smc_on:
        tk = pairs[sp]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        dfs = get_df(tk, *tfs[stf])
        if len(dfs) >= 15:
            ps = dfs.iloc[-45:].copy()
            fig, xl = make_fig(ps, 410)
            c = float(ps['Close'].iloc[-1])
            mid = max(2, len(ps) // 2)
            
            h1_p = int(ps.iloc[:mid]['High'].values.argmax())
            h2_p = mid + int(ps.iloc[mid:]['High'].values.argmax())
            l1_p = int(ps.iloc[:mid]['Low'].values.argmin())
            l2_p = mid + int(ps.iloc[mid:]['Low'].values.argmin())
            
            h1, h2 = float(ps['High'].iloc[h1_p]), float(ps['High'].iloc[h2_p])
            l1, l2 = float(ps['Low'].iloc[l1_p]), float(ps['Low'].iloc[l2_p])
            sw_hi, sw_lo = max(h1, h2), min(l1, l2)
            rng, eq = max(sw_hi - sw_lo, 1e-6), (sw_hi + sw_lo) / 2
            
            bf_l = bf_h = sf_l = sf_h = None
            bf_idx = sf_idx = 0
            bob_l = bob_h = sob_l = sob_h = None
            bob_idx = sob_idx = 0
            
            for i in range(len(ps)-1, 1, -1):
                if float(ps['Low'].iloc[i]) > float(ps['High'].iloc[i-2]) and bf_l is None:
                    bf_l, bf_h = round(float(ps['High'].iloc[i-2]), dec), round(float(ps['Low'].iloc[i]), dec)
                    bf_idx = i - 2
                    bob_l, bob_h = round(float(ps['Low'].iloc[i-2]), dec), round(float(ps['High'].iloc[i-2]), dec)
                    bob_idx = i - 2
                if float(ps['High'].iloc[i]) < float(ps['Low'].iloc[i-2]) and sf_l is None:
                    sf_l, sf_h = round(float(ps['High'].iloc[i]), dec), round(float(ps['Low'].iloc[i-2]), dec)
                    sf_idx = i - 2
                    sob_l, sob_h = round(float(ps['Low'].iloc[i-2]), dec), round(float(ps['High'].iloc[i-2]), dec)
                    sob_idx = i - 2

            if "FVG" in tool:
                f1, f2 = st.columns(2)
                f1.metric("Bullish FVG (Buy Gap)", f"{bf_l} - {bf_h}" if bf_l else "পাওয়া যায়নি")
                f2.metric("Bearish FVG (Sell Gap)", f"{sf_l} - {sf_h}" if sf_l else "পাওয়া যায়নি")
                if bf_l:
                    draw_box(fig, xl[bf_idx], xl[-1], bf_l, bf_h, "rgba(0, 255, 127, 0.28)", "#00C853", "Bullish FVG")
                    draw_line(fig, xl[bf_idx], xl[-1], round((bf_l+bf_h)/2, dec), "#00FF7F", "50% CE", "dot")
                if sf_l:
                    draw_box(fig, xl[sf_idx], xl[-1], sf_l, sf_h, "rgba(255, 75, 75, 0.28)", "#FF1744", "Bearish FVG")
                    draw_line(fig, xl[sf_idx], xl[-1], round((sf_l+sf_h)/2, dec), "#FF5252", "50% CE", "dot")
                if not bf_l and not sf_l:
                    st.info("এই ৪৫টি ক্যান্ডেলের ভেতরে কোনো স্পষ্ট FVG গ্যাপ তৈরি হয়নি। অন্য টাইমফ্রেম চেক করুন।")

            elif "OB" in tool:
                o1, o2 = st.columns(2)
                o1.metric("Bullish OB (Demand)", f"{bob_l} - {bob_h}" if bob_l else "পাওয়া যায়নি")
