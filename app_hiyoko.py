import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="ひよこ式レバ投信シグナル", layout="wide")
st.title("ひよこ式レバ投信シグナル")
st.caption("日経平均 シグナル判定ツール（ZAi 2026年11月号掲載手法）")

# ── サイドバー：パラメータ設定 ──────────────────────────────
st.sidebar.header("⚙️ パラメータ設定")

mode = st.sidebar.radio(
    "判定モード",
    ["円モード（ひよこさん原著）", "%モード（価格水準補正）"],
    index=0
)

if mode == "円モード（ひよこさん原著）":
    threshold_yen = st.sidebar.slider(
        "シグナル閾値（円）",
        min_value=500, max_value=3000, value=1000, step=100,
        help="この円以上の下落で買いシグナル、この円以上の上昇で売りシグナル"
    )
    threshold_pct = None
else:
    threshold_pct = st.sidebar.slider(
        "シグナル閾値（前日比 %）",
        min_value=0.5, max_value=5.0, value=1.5, step=0.1,
        help="この%以上の下落で買いシグナル、この%以上の上昇で売りシグナル"
    )
    threshold_yen = None

start_year = st.sidebar.slider(
    "集計開始年",
    min_value=2010, max_value=2024, value=2020, step=1
)
start_date = f"{start_year}-01-01"

st.sidebar.markdown("---")
st.sidebar.markdown("**現在の設定**")
if threshold_yen:
    st.sidebar.markdown(f"- 閾値: **±{threshold_yen:,}円**")
else:
    st.sidebar.markdown(f"- 閾値: **±{threshold_pct:.1f}%**")
st.sidebar.markdown(f"- 開始: **{start_year}年〜**")
st.sidebar.markdown("---")
st.sidebar.markdown("⚠️ 投資判断はご自身の責任で")

# ── データ取得 ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="日経平均データ取得中...")
def get_nikkei(start):
    df = yf.Ticker("^N225").history(start=start)
    df.index = df.index.tz_localize(None)
    df["change"]     = df["Close"].diff()
    df["change_pct"] = df["Close"].pct_change() * 100
    return df

df = get_nikkei(start_date)

# ── シグナル判定 ─────────────────────────────────────────────
if threshold_yen:
    buy_days  = df[df["change"] <= -threshold_yen].copy()
    sell_days = df[df["change"] >=  threshold_yen].copy()
    label = f"±{threshold_yen:,}円"
else:
    buy_days  = df[df["change_pct"] <= -threshold_pct].copy()
    sell_days = df[df["change_pct"] >=  threshold_pct].copy()
    label = f"±{threshold_pct:.1f}%"

# ── 本日シグナル ─────────────────────────────────────────────
latest       = df.iloc[-1]
today_change = latest["change"]
today_pct    = latest["change_pct"]
today_close  = latest["Close"]

st.subheader("📡 本日のシグナル")
col1, col2, col3 = st.columns(3)
col1.metric(
    "日経平均",
    f"¥{today_close:,.0f}",
    f"{today_change:+,.0f}円 ({today_pct:+.2f}%)"
)

if threshold_yen:
    is_buy  = today_change <= -threshold_yen
    is_sell = today_change >=  threshold_yen
    detail  = f"{today_change:+,.0f}円"
else:
    is_buy  = today_pct <= -threshold_pct
    is_sell = today_pct >=  threshold_pct
    detail  = f"{today_pct:+.2f}%"

if is_buy:
    col2.success(f"🟢 買いシグナル（{detail}）")
elif is_sell:
    col2.error(f"🔴 売りシグナル（{detail}）")
else:
    col2.info(f"⬜ 待機（{detail}）")

col3.info(f"判定閾値: {label}")

st.divider()

# ── 集計 ────────────────────────────────────────────────────
st.subheader(f"📊 過去の{label}超え集計（{start_year}年〜）")

col1, col2 = st.columns(2)
col1.metric(f"🟢 買いシグナル", f"{len(buy_days)}回")
col2.metric(f"🔴 売りシグナル", f"{len(sell_days)}回")

# 年別集計
st.subheader("📅 年別シグナル回数")
buy_by_year  = buy_days.groupby(buy_days.index.year).size().rename("🟢 買い")
sell_by_year = sell_days.groupby(sell_days.index.year).size().rename("🔴 売り")
year_df = pd.concat([buy_by_year, sell_by_year], axis=1).fillna(0).astype(int)
year_df.index.name = "年"
st.dataframe(year_df, use_container_width=True)

st.divider()

# ── 一覧タブ ─────────────────────────────────────────────────
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
