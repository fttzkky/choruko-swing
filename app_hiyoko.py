import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="ひよこ式レバ投信シグナル", layout="wide")
st.title("ひよこ式レバ投信シグナル")
st.caption("日経平均 ±1,000円ルール（ZAi 2026年11月号掲載手法）")

@st.cache_data(ttl=3600, show_spinner="日経平均データ取得中...")
def get_nikkei(start="2020-03-01"):
    df = yf.Ticker("^N225").history(start=start)
    df.index = df.index.tz_localize(None)
    df["change"] = df["Close"].diff()
    df["change_pct"] = df["Close"].pct_change() * 100
    return df

df = get_nikkei()

latest = df.iloc[-1]
today_change = latest["change"]
today_close  = latest["Close"]

st.subheader("📡 本日のシグナル")
col1, col2, col3 = st.columns(3)
col1.metric("日経平均", f"¥{today_close:,.0f}", f"{today_change:+,.0f}円")

if today_change <= -1000:
    col2.success("🟢 買いシグナル（-1,000円以下）")
elif today_change >= 1000:
    col2.error("🔴 売りシグナル（+1,000円以上）")
else:
    col2.info(f"⬜ 待機（{today_change:+,.0f}円）")

st.divider()

st.subheader("📊 過去の±1,000円超え集計（2020年3月〜）")

buy_days  = df[df["change"] <= -1000].copy()
sell_days = df[df["change"] >=  1000].copy()

col1, col2 = st.columns(2)
col1.metric("🟢 買いシグナル（-1,000円以下）", f"{len(buy_days)}回")
col2.metric("🔴 売りシグナル（+1,000円以上）", f"{len(sell_days)}回")

st.divider()

tab1, tab2 = st.tabs(["🟢 買いシグナル一覧", "🔴 売りシグナル一覧"])

def fmt_table(d):
    t = d[["Close", "change", "change_pct"]].copy()
    t.columns = ["日経平均終値", "前日差(円)", "前日比(%)"]
    t["日経平均終値"] = t["日経平均終値"].round(0).astype(int)
    t["前日差(円)"]   = t["前日差(円)"].round(0).astype(int)
    t["前日比(%)"]    = t["前日比(%)"].round(2)
    t.index = t.index.strftime("%Y-%m-%d")
    return t.sort_index(ascending=False)

with tab1:
    st.dataframe(fmt_table(buy_days), use_container_width=True)

with tab2:
    st.dataframe(fmt_table(sell_days), use_container_width=True)

st.caption("⚠️ 投資判断はご自身の責任で")
