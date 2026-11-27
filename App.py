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
