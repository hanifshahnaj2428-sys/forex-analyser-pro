
    
df.columns = df.columns.get_level_values(0)
    return df.dropna()

def check_trend(df):
    if len(df) < 50:
        return "ডেটা কম ⚪"
    ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ].iloc[-2])
    
    /রিটেস্ট (1H):** {res_1h['breakout']}")
