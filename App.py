import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

st.set_page_config(page_title="BD Pro Market & SMC", page_icon="📊", layout="centered")
st.title("📊 প্রো মার্কেট ও SMC অ্যানালাইসিস")

bd_tz = pytz.timezone('Asia/Dhaka')
now_bd = datetime.now(bd_tz)
hr = now_bd.hour
ses = [s for s, cond in [("🌏 Asian", 6<=hr<15), ("🇬🇧 London", 13<=hr<22), ("🇺🇸 NY", 18<=hr or hr<3)] if cond]
with st.container(border=True):
    st.markdown(f"**🕒 সময়:** {now_bd.strftime('%I:%M %p (BD)')} | " + ("🔥 **Overlap**" if 18<=hr<22 else (" | ".join(ses) if ses else "💤 অফ-সেশন")))

pairs = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X", "GOLD": "GC=F", "ETH": "ETH-USD"}
tfs = {"5M": ("5d", "5m"), "15M": ("5d", "15m"), "1H": ("1mo", "1h"), "4H": ("2mo", "4h")}

def get_df(sym, p, iv):
    df = yf.download(sym, period=p, interval="1h" if iv=="4h" else iv, progress=False)
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df.resample("4h").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna() if iv=="4h" else df

def trend(df):
    if len(df) < 50: return "N/A"
    e20, e50, c = df['Close'].ewm(span=20).mean().iloc[-1], df['Close'].ewm(span=50).mean().iloc[-1], float(df['Close'].iloc[-1])
    return "🟢 Bullish" if c > e20 > e50 else ("🔴 Bearish" if c < e20 < e50 else "🟡 Ranging")

def analyze(df, dec):
    c, pc = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
    res, sup = float(df.iloc[-32:-2]['High'].max()), float(df.iloc[-32:-2]['Low'].min())
    buf = (res - sup) * 0.05
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
        d, en, stp = "BUY 🟢", dh or (sup+buf), (dl or sup) - buf*0.5
        tp = en + max(abs(en-stp), buf)*2
    elif "Bear" in tr or "Bear" in sig:
        d, en, stp = "SELL 🔴", sl or (res-buf), (sh or res) + buf*0.5
        tp = en - max(abs(stp-en), buf)*2
    else:
        d, en, stp, tp = "RANGE 🟡", sup+buf, sup-buf*0.5, res-buf
    return {"p":round(c,dec), "res":(res-buf,res), "sup":(sup,sup+buf), "dem":(dl,dh) if dl else None, "sup_z":(sl,sh) if sl else None, "sig":sig, "dir":d, "en":round(en,dec), "sl":round(stp,dec), "tp":round(tp,dec)}

tab1, tab2 = st.tabs(["📊 চার্ট ও জোন", "🧠 SMC অ্যানালাইসিস"])

with tab1:
    c1, c2 = st.columns(2)
    pn, tfl = c1.selectbox("পেয়ার", list(pairs.keys())), c2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2)
    if st.button("🔍 অ্যানালাইসিস দেখুন", use_container_width=True, type="primary"):
        tk = pairs[pn]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        df = get_df(tk, *tfs[tfl])
        dfd = get_df(tk, "5d", "1d")
        pdh = round(float(dfd['High'].iloc[-2]), dec) if len(dfd)>=2 else None
        pdl = round(float(dfd['Low'].iloc[-2]), dec) if len(dfd)>=2 else None
        if not df.empty:
            z = analyze(df, dec)
            m1, m2, m3 = st.columns(3)
            m1.metric("প্রাইস", z["p"]); m2.metric("Prev High", pdh); m3.metric("Prev Low", pdl)
            st.info(f"**ট্রেন্ড:** {trend(df)} | **স্ট্যাটাস:** {z['sig']}")
            t1, t2, t3 = st.columns(3)
            t1.metric(f"Entry ({z['dir']})", z["en"]); t2.metric("Stop Loss", z["sl"]); t3.metric("Exit (TP)", z["tp"])
            pdf = df.iloc[-45:]
            fig = go.Figure(data=[go.Candlestick(x=pdf.index, open=pdf['Open'], high=pdf['High'], low=pdf['Low'], close=pdf['Close'])])
            fig.add_hrect(y0=z["res"], y1=z["res"], fillcolor="orange", opacity=0.2, annotation_text="Res")
            fig.add_hrect(y0=z["sup"], y1=z["sup"], fillcolor="deepskyblue", opacity=0.2, annotation_text="Sup")
            if z["dem"]: fig.add_hrect(y0=z["dem"], y1=z["dem"], fillcolor="green", opacity=0.25, annotation_text="Demand")
            if z["sup_z"]: fig.add_hrect(y0=z["sup_z"], y1=z["sup_z"], fillcolor="red", opacity=0.25, annotation_text="Supply")
            fig.add_hline(y=z["en"], line_dash="dash", line_color="cyan", annotation_text="Entry")
            fig.add_hline(y=z["sl"], line_dash="dot", line_color="red", annotation_text="SL")
            fig.add_hline(y=z["tp"], line_dash="dash", line_color="lime", annotation_text="Exit")
            if pdh: fig.add_hline(y=pdh, line_dash="dashdot", line_color="gold", annotation_text="PDH")
            if pdl: fig.add_hline(y=pdl, line_dash="dashdot", line_color="violet", annotation_text="PDL")
            fig.update_layout(xaxis_rangeslider_visible=False, height=380, margin=dict(l=5,r=5,t=20,b=5), template="plotly_dark", xaxis_type="category")
            fig.update_xaxes(showticklabels=False)
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    s1, s2 = st.columns(2)
    sp, stf = s1.selectbox("পেয়ার", list(pairs.keys()), key="sp"), s2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="stf")
    if st.button("⚡ ফুল SMC অ্যানালাইসিস দেখুন", use_container_width=True, type="primary"):
        tk = pairs[sp]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        dfs = get_df(tk, *tfs[stf])
        if len(dfs) >= 40:
            ps = dfs.iloc[-40:].copy()
            c = float(ps['Close'].iloc[-1])
            
            h1, h2 = float(ps.iloc[-40:-20]['High'].max()), float(ps.iloc[-20:-2]['High'].max())
            l1, l2 = float(ps.iloc[-40:-20]['Low'].min()), float(ps.iloc[-20:-2]['Low'].min())
            idx_h1, idx_h2 = ps.iloc[-40:-20]['High'].idxmax(), ps.iloc[-20:-2]['High'].idxmax()
            idx_l1, idx_l2 = ps.iloc[-40:-20]['Low'].idxmin(), ps.iloc[-20:-2]['Low'].idxmin()

            h_lbl = "HH" if h2 > h1 else "LH"
            l_lbl = "HL" if l2 > l1 else "LL"
            ms_text = f"Uptrend ({h_lbl} & {l_lbl})" if (h2 > h1 and l2 > l1) else (f"Downtrend ({h_lbl} & {l_lbl})" if (h2 < h1 and l2 < l1) else f"Transition ({h_lbl} / {l_lbl})")

            if c > h2:
                bos_choch = f"🚀 {'BOS (Trend Continuation)' if h2 > h1 else 'CHoCH (Reversal Signal)'} @ {round(h2, dec)}"
            elif c < l2:
                bos_choch = f"🔻 {'BOS (Trend Continuation)' if l2 < l1 else 'CHoCH (Reversal Signal)'} @ {round(l2, dec)}"
            else:
                bos_choch = f"🟡 Ranging Structure ({round(l2, dec)} - {round(h2, dec)})"

            sw_hi, sw_lo = max(h1, h2), min(l1, l2)
            eq = (sw_hi + sw_lo) / 2
            pd_zone = "🔴 Premium Zone (Sell Area)" if c > eq else "🟢 Discount Zone (Buy Area)"

            bsl, ssl = round(sw_hi, dec), round(sw_lo, dec)

            bfvg_l = bfvg_h = sfvg_l = sfvg_h = None
            bob_l = bob_h = sob_l = sob_h = None
            for i in range(len(dfs)-2, max(len(dfs)-25, 2), -1):
                if dfs['Low'].iloc[i] > dfs['High'].iloc[i-2] and bfvg_l is None:
                    bfvg_l, bfvg_h = round(float(dfs['High'].iloc[i-2]),dec), round(float(dfs['Low'].iloc[i]),dec)
                    bob_l, bob_h = round(float(dfs['Low'].iloc[i-2]),dec), round(float(dfs['High'].iloc[i-2]),dec)
                if dfs['High'].iloc[i] < dfs['Low'].iloc[i-2] and sfvg_l is None:
                    sfvg_l, sfvg_h = round(float(dfs['High'].iloc[i]),dec), round(float(dfs['Low'].iloc[i-2]),dec)
                    sob_l, sob_h = round(float(dfs['Low'].iloc[i-2]),dec), round(float(dfs['High'].iloc[i-2]),dec)

            buf = (sw_hi - sw_lo) * 0.05
            if c <= eq and bob_l is not None:
                s_dir = "BUY (Discount OB) 🟢"
                s_en = bob_h
                s_sl = round(bob_l - buf*0.5, dec)
                s_tp = round(s_en + max(abs(s_en - s_sl), buf)*2, dec)
            elif c > eq and sob_l is not None:
                s_dir = "SELL (Premium OB) 🔴"
                s_en = sob_l
                s_sl = round(sob_h + buf*0.5, dec)
                s_tp = round(s_en - max(abs(s_sl - s_en), buf)*2, dec)
            else:
                if c <= eq:
                    s_dir, s_en, s_sl, s_tp = "BUY 🟢", round(ssl+buf, dec), round(ssl-buf*0.5, dec), round(bsl, dec)
                else:
                    s_dir, s_en, s_sl, s_tp = "SELL 🔴", round(bsl-buf, dec), round(bsl+buf*0.5, dec), round(ssl, dec)

            st.info(f"**Structure:** {ms_text} | **Signal:** {bos_choch}")
            m1, m2 = st.columns(2)
            m1.metric("বর্তমান জোন (50% EQ)", pd_zone)
            m2.metric("Liquidity (BSL / SSL)", f"{bsl} / {ssl}")

            t1, t2, t3 = st.columns(3)
            t1.metric(f"SMC Entry ({s_dir})", s_en); t2.metric("Stop Loss", s_sl); t3.metric("Exit (TP)", s_tp)

            figs = go.Figure(data=[go.Candlestick(x=ps.index, open=ps['Open'], high=ps['High'], low=ps['Low'], close=ps['Close'], name="Price")])
            
            figs.add_hrect(y0=eq, y1=sw_hi, fillcolor="rgba(255,82,82,0.08)", line_width=0, annotation_text="PREMIUM (Sell)", annotation_position="top right")
            figs.add_hrect(y0=sw_lo, y1=eq, fillcolor="rgba(0,230,118,0.08)", line_width=0, annotation_text="DISCOUNT (Buy)", annotation_position="bottom right")
