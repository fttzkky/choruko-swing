import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")
 
st.set_page_config(page_title="ちょるこ式スイングトレード判定", layout="wide")
st.title("ちょるこ式スイングトレード判定")
st.caption("ZAi 2026年9月号掲載手法 STEP3版")
 
HOLDINGS = [
    ("1332", "ニッスイ"),
    ("2282", "日本ハム"),
    ("2432", "ディーエヌエー"),
    ("2914", "JT"),
    ("3167", "TOKAIホールディングス"),
    ("3968", "セグエ"),
    ("4503", "アステラス製薬"),
    ("4765", "SBIアセットM"),
    ("5261", "リソル"),
    ("6758", "ソニーグループ"),
    ("6803", "ティアック"),
    ("8304", "あおぞら銀行"),
    ("8410", "セブン銀行"),
    ("8473", "SBI"),
    ("8729", "ソニーFG"),
    ("9101", "日本郵船"),
    ("9432", "NTT"),
    ("9433", "KDDI"),
    ("9434", "ソフトバンク"),
    ("9531", "東京ガス"),
    ("9672", "東京都競馬"),
]
 
def calc_rci(series, period=9):
    if len(series) < period:
        return 0.0
    recent = series.iloc[-period:].values
    n = period
    dr = np.arange(1, n+1)
    pr = pd.Series(recent).rank(ascending=True).values
    dsq = np.sum((dr-pr)**2)
    return round((1 - 6*dsq/(n*(n**2-1)))*100, 1)
 
def calc_step3(df):
    close = df["Close"]
    ma25  = close.rolling(25).mean()
    bb_std = close.rolling(25).std()
    bb_sigma = (close.iloc[-1] - ma25.iloc[-1]) / bb_std.iloc[-1]
    rci = calc_rci(close, 9)
    change = (close.iloc[-1]-close.iloc[-2])/close.iloc[-2]*100
    ma25_dev = (close.iloc[-1]-ma25.iloc[-1])/ma25.iloc[-1]*100
    return {
        "price":      round(close.iloc[-1]),
        "change_pct": round(change, 2),
        "ma25_dev":   round(ma25_dev, 2),
        "bb_sigma":   round(bb_sigma, 2),
        "rci":        round(rci, 1),
    }
 
mode = st.radio("スキャン対象", ["保有銘柄（21銘柄）", "時価総額フィルター"])
 
if mode == "時価総額フィルター":
    tier = st.selectbox("時価総額", ["10兆円以上", "5兆円以上", "1兆円以上"])
    tier_map = {"10兆円以上": 10_000_000_000_000, "5兆円以上": 5_000_000_000_000, "1兆円以上": 1_000_000_000_000}
    threshold = tier_map[tier]
else:
    threshold = 0
 
if st.button("スキャン開始", type="primary"):
    results = []
    progress = st.progress(0)
    status = st.empty()
 
    targets = HOLDINGS if mode == "保有銘柄（21銘柄）" else HOLDINGS
 
    for i, (code, name) in enumerate(targets):
        status.text(f"取得中: {name}...")
        progress.progress((i+1)/len(targets))
        try:
            ticker = yf.Ticker(f"{code}.T")
            if threshold > 0:
                mc = getattr(ticker.fast_info, 'market_cap', 0) or 0
                if mc < threshold:
                    continue
            df = ticker.history(period="60d")
            if len(df) < 30:
                continue
            s3 = calc_step3(df)
            s3n = sum([
                s3["change_pct"] <= -2.5,
                s3["ma25_dev"]   <  0,
                s3["bb_sigma"]   <= -3.0,
                s3["rci"]        <= -80,
            ])
            results.append({"code":code,"name":name,"s3n":s3n,**s3})
        except:
            continue
 
    status.empty()
    progress.empty()
 
    results.sort(key=lambda x: -x["s3n"])
 
    st.subheader(f"判定結果 / {len(results)}銘柄")
 
    for d in results:
        if d["s3n"] >= 3:
            color = "🟢"
        elif d["s3n"] >= 2:
            color = "🟡"
        else:
            color = "🔴"
 
        with st.expander(f"{color} {d['name']} ({d['code']})　STEP3: {d['s3n']}/4クリア　株価: ¥{d['price']:,}　前日比: {d['change_pct']:+.1f}%"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("✅" if d["change_pct"] <= -2.5 else "❌", f"前日比: {d['change_pct']:+.1f}%")
                st.write("✅" if d["ma25_dev"] < 0 else "❌", f"MA乖離: {d['ma25_dev']:+.1f}%")
            with col2:
                st.write("✅" if d["bb_sigma"] <= -3.0 else "❌", f"BB: {d['bb_sigma']:.2f}σ")
                st.write("✅" if d["rci"] <= -80 else "❌", f"RCI: {d['rci']:.0f}%")
 
st.caption("⚠️ 投資判断はご自身の責任で")
