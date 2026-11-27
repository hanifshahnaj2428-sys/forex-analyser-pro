import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

st.set_page_config(page_title="Pro Trader", page_icon="📈", layout="centered")
st.title("📈 Pro Trader")

# বাংলাদেশ সময় ও সেশন
bd_tz = pytz.timezone('Asia/Dhaka')
now_bd = datetime.now(bd_tz)
hr = now_bd.hour
ses = [s for s, cond in [("🌏 Asian", 6<=hr<15), ("🇬🇧 London", 13<=hr<22), ("🇺🇸 NY", 18<=hr or hr<3)] if cond]
with st.container(border=True):
    st.markdown(f"**🕒 সময়:** {now_bd.strftime('%I:%M %p (BD)')} | " + ("🔥 **Overlap (NY Killzone)**" if 18<=hr<22 else (" | ".join(ses) if ses else "💤 অফ-সেশন")))

pairs = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X", "GOLD": "GC=F", "ETH": "ETH-USD"}
tfs = {"5M": ("2d", "5m"), "15M": ("5d", "15m"), "1H": ("1mo", "1h"), "4H": ("2mo", "4h")}

@st.cache_data(ttl=60)
def get_df(sym, p, iv):
    try:
        df = yf.download(sym, period=p, interval="1h" if iv=="4h" else iv, progress=False)
        if df is None or df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close']].dropna()
        return df.resample("4h").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna() if iv=="4h" else df
    except Exception:
        return pd.DataFrame()

def trend(df):
    if len(df) < 30: return "N/A"
    e20 = float(df['Close'].ewm(span=20).mean().iloc[-1])
    e50 = float(df['Close'].ewm(span=50).mean().iloc[-1])
    c = float(df['Close'].iloc[-1])
    return "🟢 Bullish" if c > e20 > e50 else ("🔴 Bearish" if c < e20 < e50 else "🟡 Ranging")

def get_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1) if not pd.isna(rsi.iloc[-1]) else 50.0

def analyze(df, dec):
    c, pc = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
    lb = min(32, len(df)-2)
    res, sup = float(df.iloc[-lb:-2]['High'].max()), float(df.iloc[-lb:-2]['Low'].min())
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

def base_chart(df_slice, h=380):
    fig = go.Figure(data=[go.Candlestick(
        x=list(range(len(df_slice))),
        open=df_slice['Open'].tolist(),
        high=df_slice['High'].tolist(),
        low=df_slice['Low'].tolist(),
        close=df_slice['Close'].tolist(),
        name="Price"
    )])
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=h,
        margin=dict(l=5, r=5, t=25, b=5),
        template="plotly_dark",
        showlegend=False
    )
    fig.update_xaxes(showticklabels=False)
    return fig

tab1, tab2 = st.tabs(["📊 প্রাইস অ্যাকশন ও জোন", "🧠 অ্যাডভান্সড SMC অ্যানালাইসিস"])

# ==================== TAB 1 ====================
with tab1:
    c1, c2 = st.columns(2)
    pn = c1.selectbox("পেয়ার", list(pairs.keys()), key="p1")
    tfl = c2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf1")
    if st.button("🔍 চার্ট অ্যানালাইসিস দেখুন", use_container_width=True, type="primary", key="b1"):
        tk = pairs[pn]
        dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
        df = get_df(tk, *tfs[tfl])
        dfd = get_df(tk, "5d", "1d")
        pdh = round(float(dfd['High'].iloc[-2]), dec) if len(dfd)>=2 else None
        pdl = round(float(dfd['Low'].iloc[-2]), dec) if len(dfd)>=2 else None
        if len(df) >= 20:
            z = analyze(df, dec)
            rsi_v = get_rsi(df)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("প্রাইস", z["p"])
            m2.metric("RSI (14)", rsi_v)
            m3.metric("Prev High", pdh)
            m4.metric("Prev Low", pdl)
            st.info(f"**ট্রেন্ড:** {trend(df)} | **স্ট্যাটাস:** {z['sig']}")
            t1, t2, t3 = st.columns(3)
            t1.metric(f"Entry ({z['dir']})", z["en"])
            t2.metric("Stop Loss", z["sl"])
            t3.metric("Exit (TP)", z["tp"])
            
            pdf = df.iloc[-45:]
            fig = base_chart(pdf, h=380)
            fig.add_hrect(y0=z["res"], y1=z["res"], fillcolor="orange", opacity=0.2, annotation_text="Res")
            fig.add_hrect(y0=z["sup"], y1=z["sup"], fillcolor="deepskyblue", opacity=0.2, annotation_text="Sup")
            if z["dem"]: fig.add_hrect(y0=z["dem"], y1=z["dem"], fillcolor="green", opacity=0.25, annotation_text="Demand")
            if z["sup_z"]: fig.add_hrect(y0=z["sup_z"], y1=z["sup_z"], fillcolor="red", opacity=0.25, annotation_text="Supply")
            fig.add_hline(y=z["en"], line_dash="dash", line_color="cyan", annotation_text="Entry")
            fig.add_hline(y=z["sl"], line_dash="dot", line_color="red", annotation_text="SL")
            fig.add_hline(y=z["tp"], line_dash="dash", line_color="lime", annotation_text="Exit")
            if pdh: fig.add_hline(y=pdh, line_dash="dashdot", line_color="gold", annotation_text="PDH")
            if pdl: fig.add_hline(y=pdl, line_dash="dashdot", line_color="violet", annotation_text="PDL")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ ডেটা লোড হয়নি, কিছুক্ষণ পর আবার চেষ্টা করুন।")

# ==================== TAB 2: ADVANCED VISUAL SMC ====================
with tab2:
    s1, s2 = st.columns(2)
    sp = s1.selectbox("পেয়ার", list(pairs.keys()), key="p2")
    stf = s2.selectbox("টাইমফ্রেম", list(tfs.keys()), index=2, key="tf2")
    
    smc_tool = st.selectbox(
        "SMC উপাদান নির্বাচন করুন (ছবি ও অ্যানালাইসিস):",
        [
            "১. ফেয়ার ভ্যালু গ্যাপ (Fair Value Gap & 50% CE)",
            "২. অর্ডার ব্লক (Institutional Order Blocks)",
            "৩. মার্কেট স্ট্রাকচার (BOS ও CHoCH)",
            "৪. প্রিমিয়াম, ডিসকাউন্ট ও OTE জোন",
            "৫. লিকুইডিটি পুল (BSL ও SSL Sweep)"
        ],
        key="smc_tool"
    )
    
    tk = pairs[sp]
    dec = 2 if tk in ["GC=F","USDJPY=X","ETH-USD"] else 5
    dfs = get_df(tk, *tfs[stf])
    
    if len(dfs) >= 35:
        ps = dfs.iloc[-45:].copy().reset_index(drop=True)
        c = float(ps['Close'].iloc[-1])
        mid = len(ps) // 2
        
        h1_idx = int(ps.iloc[:mid]['High'].idxmax())
        h2_idx = int(ps.iloc[mid:-1]['High'].idxmax())
        l1_idx = int(ps.iloc[:mid]['Low'].idxmin())
        l2_idx = int(ps.iloc[mid:-1]['Low'].idxmin())
        
        h1, h2 = float(ps['High'].iloc[h1_idx]), float(ps['High'].iloc[h2_idx])
        l1, l2 = float(ps['Low'].iloc[l1_idx]), float(ps['Low'].iloc[l2_idx])
        
        h_lbl = "HH" if h2 > h1 else "LH"
        l_lbl = "HL" if l2 > l1 else "LL"
        sw_hi, sw_lo = max(h1, h2), min(l1, l2)
        rng = sw_hi - sw_lo
        eq = (sw_hi + sw_lo) / 2
        
        # FVG & OB খোঁজা
        bfvg_l = bfvg_h = sfvg_l = sfvg_h = None
        bfvg_idx = sfvg_idx = None
        bob_l = bob_h = sob_l = sob_h = None
        
        for i in range(len(ps)-2, 2, -1):
            if float(ps['Low'].iloc[i]) > float(ps['High'].iloc[i-2]) and bfvg_l is None:
                bfvg_l, bfvg_h = round(float(ps['High'].iloc[i-2]),dec), round(float(ps['Low'].iloc[i]),dec)
                bfvg_idx = i
                bob_l, bob_h = round(float(ps['Low'].iloc[i-2]),dec), round(float(ps['High'].iloc[i-2]),dec)
            if float(ps['High'].iloc[i]) < float(ps['Low'].iloc[i-2]) and sfvg_l is None:
                sfvg_l, sfvg_h = round(float(ps['High'].iloc[i]),dec), round(float(ps['Low'].iloc[i-2]),dec)
                sfvg_idx = i
                sob_l, sob_h = round(float(ps['Low'].iloc[i-2]),dec), round(float(ps['High'].iloc[i-2]),dec)

        # ১. ফেয়ার ভ্যালু গ্যাপ
        if "ফেয়ার ভ্যালু গ্যাপ" in smc_tool:
            b_fvg_status = "N/A"
            b_ce = None
            if bfvg_l and bfvg_h and bfvg_idx is not None:
                b_ce = round((bfvg_l + bfvg_h) / 2, dec)
                sub_low = float(ps.iloc[bfvg_idx+1:]['Low'].min()) if bfvg_idx+1 < len(ps) else c
                b_fvg_status = "✅ Unmitigated (Active)" if sub_low > bfvg_l else "⚪ Mitigated (Filled)"

            s_fvg_status = "N/A"
            s_ce = None
            if sfvg_l and sfvg_h and sfvg_idx is not None:
                s_ce = round((sfvg_l + sfvg_h) / 2, dec)
                sub_high = float(ps.iloc[sfvg_idx+1:]['High'].max()) if sfvg_idx+1 < len(ps) else c
                s_fvg_status = "✅ Unmitigated (Active)" if sub_high < sfvg_h else "⚪ Mitigated (Filled)"

