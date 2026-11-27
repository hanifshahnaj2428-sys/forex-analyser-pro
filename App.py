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
    if len(df) < 15:
        return "N/A"
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

def base_candlestick(df_s, h=390):
    fig = go.Figure(data=[go.Candlestick(
        x=df_s.index,
        open=df_s['Open'],
        high=df_s['High'],
        low=df_s['Low'],
        close=df_s['Close']
    )])
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=h,
        margin=dict(l=5, r=5, t=25, b=5),
        template="plotly_dark",
        xaxis_type="category",
        showlegend=False
    )
    fig.update_xaxes(showticklabels=False)
    return fig

# আগের মতো স্ট্যান্ডার্ড ট্যাব মেনু
tab1, tab2 = st.tabs(["📊 চার্ট ও জোন", "🧠 SMC অ্যানালাইসিস"])

# ==================== TAB 1 ====================
with tab1:
    c1, c2 = st.columns(2)
    pn = c1.selectbox("পেয়ার", list(pairs.keys()), key="p1")
    tfl = c2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf1")
    if st.button("🔍 অ্যানালাইসিস দেখুন", use_container_width=True, type="primary", key="b1"):
        tk = pairs[pn]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        df = get_df(tk, *tfs[tfl])
        dfd = get_df(tk, "5d", "1d")
        if len(df) >= 15:
            c = float(df['Close'].iloc[-1])
            lb = min(32, len(df)-2)
            res = float(df.iloc[-lb:-2]['High'].max())
            sup = float(df.iloc[-lb:-2]['Low'].min())
            buf = (res - sup) * 0.05
            tr = trend(df)
            if "Bull" in tr:
                d, en, stp = "BUY 🟢", sup + buf, sup - buf * 0.5
                tp = en + abs(en - stp) * 2
            elif "Bear" in tr:
                d, en, stp = "SELL 🔴", res - buf, res + buf * 0.5
                tp = en - abs(stp - en) * 2
            else:
                d, en, stp, tp = "RANGE 🟡", sup + buf, sup - buf * 0.5, res - buf

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

            fig = base_candlestick(df.iloc[-45:], 390)
            fig.add_hrect(y0=res - buf, y1=res, fillcolor="orange", opacity=0.22, annotation_text="Res")
            fig.add_hrect(y0=sup, y1=sup + buf, fillcolor="deepskyblue", opacity=0.22, annotation_text="Sup")
            fig.add_hline(y=en, line_dash="dash", line_color="cyan", annotation_text="Entry")
            fig.add_hline(y=stp, line_dash="dot", line_color="red", annotation_text="SL")
            fig.add_hline(y=tp, line_dash="dash", line_color="lime", annotation_text="TP")
            if pdh:
                fig.add_hline(y=pdh, line_dash="dashdot", line_color="gold", annotation_text="PDH")
            if pdl:
                fig.add_hline(y=pdl, line_dash="dashdot", line_color="violet", annotation_text="PDL")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ ডেটা লোড হয়নি, আবার চেষ্টা করুন।")

# ==================== TAB 2: SMC অ্যানালাইসিস ====================
with tab2:
    s1, s2 = st.columns(2)
    sp = s1.selectbox("পেয়ার", list(pairs.keys()), key="p2")
    stf = s2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf2")
    smc_item = st.selectbox("SMC উপাদান নির্বাচন করুন:", [
        "১. ফেয়ার ভ্যালু গ্যাপ (FVG & 50% CE)",
        "২. অর্ডার ব্লক (Order Block)",
        "৩. মার্কেট স্ট্রাকচার (BOS / CHoCH)",
        "৪. প্রিমিয়াম / ডিসকাউন্ট ও OTE",
        "৫. লিকুইডিটি পুল (BSL / SSL)"
    ], key="smc_item")

    if st.button("⚡ ফুল SMC অ্যানালাইসিস দেখুন", use_container_width=True, type="primary", key="b2"):
        tk = pairs[sp]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        dfs = get_df(tk, *tfs[stf])
        if len(dfs) >= 15:
            ps = dfs.iloc[-45:].copy()
            c = float(ps['Close'].iloc[-1])
            mid = max(2, len(ps) // 2)

            h1 = float(ps.iloc[:mid]['High'].max())
            h2 = float(ps.iloc[mid:]['High'].max())
            l1 = float(ps.iloc[:mid]['Low'].min())
            l2 = float(ps.iloc[mid:]['Low'].min())

            sw_hi = max(h1, h2)
            sw_lo = min(l1, l2)
            rng = max(sw_hi - sw_lo, 1e-6)
            eq = (sw_hi + sw_lo) / 2

            # FVG খোঁজা
            bf_l = bf_h = sf_l = sf_h = None
            for i in range(len(ps)-1, 1, -1):
                if float(ps['Low'].iloc[i]) > float(ps['High'].iloc[i-2]) and bf_l is None:
                    bf_l = round(float(ps['High'].iloc[i-2]), dec)
                    bf_h = round(float(ps['Low'].iloc[i]), dec)
                if float(ps['High'].iloc[i]) < float(ps['Low'].iloc[i-2]) and sf_l is None:
                    sf_l = round(float(ps['High'].iloc[i]), dec)
                    sf_h = round(float(ps['Low'].iloc[i-2]), dec)

            # Order Block খোঁজা
            bob_l = bob_h = sob_l = sob_h = None
            avg_b = float((ps['Close'] - ps['Open']).abs().mean())
            for i in range(len(ps)-1, 1, -1):
                mv = float(ps['Close'].iloc[i] - ps['Open'].iloc[i])
                if mv > avg_b * 1.4 and bob_l is None:
                    bob_l = round(float(ps['Low'].iloc[i-1]), dec)
                    bob_h = round(max(float(ps['Open'].iloc[i-1]), float(ps['Close'].iloc[i-1])), dec)
                if mv < -avg_b * 1.4 and sob_l is None:
                    sob_h = round(float(ps['High'].iloc[i-1]), dec)
                    sob_l = round(min(float(ps['Open'].iloc[i-1]), float(ps['Close'].iloc[i-1])), dec)

            if bob_l is None:
                bob_l, bob_h = round(l2, dec), round(l2 + rng * 0.08, dec)
            if sob_l is None:
                sob_h, sob_l = round(h2, dec), round(h2 - rng * 0.08, dec)

            fig_smc = base_candlestick(ps, 390)

            if "FVG" in smc_item:
                f1, f2 = st.columns(2)
                f1.metric("Bullish FVG (Buy Gap)", f"{bf_l} - {bf_h}" if bf_l else "সক্রিয় গ্যাপ নেই")
                f2.metric("Bearish FVG (Sell Gap)", f"{sf_l} - {sf_h}" if sf_l else "সক্রিয় গ্যাপ নেই")
                if bf_l is not None:
                    fig_smc.add_hrect(y0=bf_l, y1=bf_h, fillcolor="lime", opacity=0.25, annotation_text="Bull FVG")
                    fig_smc.add_hline(y=round((bf_l + bf_h) / 2, dec), line_dash="dot", line_color="lime", annotation_text="Bull 50% CE")
                if sf_l is not None:
                    fig_smc.add_hrect(y0=sf_l, y1=sf_h, fillcolor="red", opacity=0.25, annotation_text="Bear FVG")
                    fig_smc.add_hline(y=round((sf_l + sf_h) / 2, dec), line_dash="dot", line_color="red", annotation_text="Bear 50% CE")

            elif "OB" in smc_item:
                o1, o2 = st.columns(2)
                o1.metric("Bullish OB (Demand)", f"{bob_l} - {bob_h}")
                o2.metric("Bearish OB (Supply)", f"{sob_l} - {sob_h}")
                fig_smc.add_hrect(y0=bob_l, y1=bob_h, fillcolor="cyan", opacity=0.25, annotation_text="Bullish OB")
                fig_smc.add_hrect(y0=sob_l, y1=sob_h, fillcolor="magenta", opacity=0.25, annotation_text="Bearish OB")

            elif "BOS" in smc_item:
                h_lbl = "HH" if h2 > h1 else "LH"
                l_lbl = "HL" if l2 > l1 else "LL"
                if c > h2:
                    msg = f"🚀 **Bullish {'BOS' if h2 > h1 else 'CHoCH'}** @ {round(h2, dec)}"
                elif c < l2:
