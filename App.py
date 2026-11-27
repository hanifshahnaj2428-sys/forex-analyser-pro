import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os

st.set_page_config(page_title="BD Pro Market & SMC", page_icon="📊", layout="centered")
st.title("📊 প্রো মার্কেট, SMC ও জার্নাল")

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

tab1, tab2, tab3, tab4 = st.tabs(["📊 চার্ট ও জোন", "🧠 SMC", "🚀 স্ক্যানার", "📒 জার্নাল"])

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
    if st.button("⚡ SMC ও FVG দেখুন", use_container_width=True, type="primary"):
        tk = pairs[sp]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        dfs = get_df(tk, *tfs[stf])
        if not dfs.empty:
            c, sh, sl = float(dfs['Close'].iloc[-1]), float(dfs.iloc[-25:-3]['High'].max()), float(dfs.iloc[-25:-3]['Low'].min())
            st.success(f"**BOS / CHoCH:** {'🟢 Bullish Break' if c>sh else ('🔴 Bearish Break' if c<sl else '🟡 Internal Range')} ({round(sl,dec)} - {round(sh,dec)})")
            bfvg = sfvg = bob = sob = None
            for i in range(len(dfs)-2, max(len(dfs)-25, 2), -1):
                if dfs['Low'].iloc[i] > dfs['High'].iloc[i-2] and not bfvg:
                    bfvg = (round(float(dfs['High'].iloc[i-2]),dec), round(float(dfs['Low'].iloc[i]),dec))
                    bob = (round(float(dfs['Low'].iloc[i-2]),dec), round(float(dfs['High'].iloc[i-2]),dec))
                if dfs['High'].iloc[i] < dfs['Low'].iloc[i-2] and not sfvg:
                    sfvg = (round(float(dfs['High'].iloc[i]),dec), round(float(dfs['Low'].iloc[i-2]),dec))
                    sob = (round(float(dfs['Low'].iloc[i-2]),dec), round(float(dfs['High'].iloc[i-2]),dec))
            c1, c2 = st.columns(2)
            c1.info(f"**🟢 Bull OB:** {bob}\n\n**🟢 Bull FVG:** {bfvg}")
            c2.error(f"**🔴 Bear OB:** {sob}\n\n**🔴 Bear FVG:** {sfvg}")
            ps = dfs.iloc[-40:]
            figs = go.Figure(data=[go.Candlestick(x=ps.index, open=ps['Open'], high=ps['High'], low=ps['Low'], close=ps['Close'])])
            if bfvg: figs.add_hrect(y0=bfvg, y1=bfvg, fillcolor="lime", opacity=0.25, annotation_text="Bull FVG")
            if sfvg: figs.add_hrect(y0=sfvg, y1=sfvg, fillcolor="red", opacity=0.25, annotation_text="Bear FVG")
            figs.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=5,r=5,t=20,b=5), template="plotly_dark", xaxis_type="category")
            figs.update_xaxes(showticklabels=False)
            st.plotly_chart(figs, use_container_width=True)

with tab3:
    sctf = st.selectbox("স্ক্যান টাইমফ্রেম", list(tfs.keys()), index=2, key="sctf")
    if st.button("🔄 অল-পেয়ার স্ক্যান করুন", use_container_width=True, type="primary"):
        rows = []
        for nm, tk in pairs.items():
            dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
            df = get_df(tk, *tfs[sctf])
            if not df.empty:
                z = analyze(df, dec)
                rows.append({"Pair":nm, "Price":z["p"], "Setup":z["dir"], "Entry":z["en"], "SL":z["sl"], "Exit":z["tp"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab4:
    jf = "journal.csv"
    with st.form("jf", clear_on_submit=True):
        c1, c2 = st.columns(2)
        jp, jt = c1.selectbox("পেয়ার", list(pairs.keys())), c2.selectbox("পজিশন", ["BUY 🟢", "SELL 🔴"])
        c3, c4 = st.columns(2)
        jr, jpnl = c3.selectbox("রেজাল্ট", ["Win ✅", "Loss ❌"]), c4.number_input("PnL ($)", value=0.0)
        if st.form_submit_button("💾 সেভ করুন", use_container_width=True):
            row = pd.DataFrame([{"Time":now_bd.strftime("%d-%b %I:%M%p"), "Pair":jp, "Type":jt, "Result":jr, "PnL":jpnl}])
            pd.concat([row, pd.read_csv(jf) if os.path.exists(jf) else pd.DataFrame()], ignore_index=True).to_csv(jf, index=False)
            st.success("✅ সেভ হয়েছে!")
    if os.path.exists(jf):
        df_j = pd.read_csv(jf)
        st.metric("মোট PnL ($)", f"${df_j['PnL'].sum():.2f}")
        st.dataframe(df_j, use_container_width=True, hide_index=True)
