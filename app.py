import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="ちょるこ式スイングトレード判定", layout="wide")
st.title("ちょるこ式スイングトレード判定")
st.caption("ZAi 2026年9月号掲載手法 STEP3版")

HOLDINGS = [
    ("1332", "ニッスイ"), ("2282", "日本ハム"), ("2432", "ディーエヌエー"),
    ("2914", "JT"), ("3167", "TOKAIホールディングス"), ("3968", "セグエ"),
    ("4503", "アステラス製薬"), ("4765", "SBIアセットM"), ("5261", "リソル"),
    ("6758", "ソニーグループ"), ("6803", "ティアック"), ("8304", "あおぞら銀行"),
    ("8410", "セブン銀行"), ("8473", "SBI"), ("8729", "ソニーFG"),
    ("9101", "日本郵船"), ("9432", "NTT"), ("9433", "KDDI"),
    ("9434", "ソフトバンク"), ("9531", "東京ガス"), ("9672", "東京都競馬"),
]

# 時価総額を事前にティア別に整理（APIコール不要）
TIER_STOCKS = {
    "10兆円以上": [
        ("7203", "トヨタ自動車"), ("9984", "ソフトバンクグループ"),
        ("6861", "キーエンス"), ("6758", "ソニーグループ"),
        ("9432", "NTT"), ("8306", "三菱UFJ"), ("7974", "任天堂"),
        ("4063", "信越化学工業"), ("9433", "KDDI"), ("8058", "三菱商事"),
    ],
    "5兆円以上": [
        ("7203", "トヨタ自動車"), ("9984", "ソフトバンクグループ"),
        ("6861", "キーエンス"), ("6758", "ソニーグループ"),
        ("9432", "NTT"), ("8306", "三菱UFJ"), ("7974", "任天堂"),
        ("4063", "信越化学工業"), ("9433", "KDDI"), ("8058", "三菱商事"),
        ("6954", "ファナック"), ("4519", "中外製薬"), ("2914", "JT"),
        ("6902", "デンソー"), ("9101", "日本郵船"), ("4503", "アステラス製薬"),
        ("8766", "東京海上HD"), ("7267", "本田技研工業"), ("4502", "武田薬品工業"),
        ("9020", "JR東日本"), ("6367", "ダイキン工業"), ("8316", "三井住友FG"),
        ("6501", "日立製作所"), ("4568", "第一三共"), ("7741", "HOYA"),
        ("9983", "ファーストリテイリング"), ("8001", "伊藤忠商事"), ("8031", "三井物産"),
        ("6857", "アドバンテスト"), ("6981", "村田製作所"),
    ],
    "1兆円以上": [
        ("7203", "トヨタ自動車"), ("9984", "ソフトバンクグループ"),
        ("6861", "キーエンス"), ("6758", "ソニーグループ"),
        ("9432", "NTT"), ("8306", "三菱UFJ"), ("7974", "任天堂"),
        ("4063", "信越化学工業"), ("9433", "KDDI"), ("8058", "三菱商事"),
        ("6954", "ファナック"), ("4519", "中外製薬"), ("2914", "JT"),
        ("6902", "デンソー"), ("9101", "日本郵船"), ("4503", "アステラス製薬"),
        ("8766", "東京海上HD"), ("7267", "本田技研工業"), ("4502", "武田薬品工業"),
        ("9020", "JR東日本"), ("6367", "ダイキン工業"), ("8316", "三井住友FG"),
        ("6501", "日立製作所"), ("4568", "第一三共"), ("7741", "HOYA"),
        ("9983", "ファーストリテイリング"), ("8001", "伊藤忠商事"), ("8031", "三井物産"),
        ("6857", "アドバンテスト"), ("6981", "村田製作所"), ("6146", "ディスコ"),
        ("4661", "オリエンタルランド"), ("6723", "ルネサスエレクトロニクス"),
        ("8802", "三菱地所"), ("3382", "セブン&アイ"), ("6594", "ニデック"),
        ("6273", "SMC"), ("8604", "野村HD"), ("7270", "SUBARU"),
        ("1925", "大和ハウス工業"), ("9531", "東京ガス"), ("2802", "味の素"),
        ("4523", "エーザイ"), ("6301", "小松製作所"), ("6702", "富士通"),
        ("4911", "資生堂"), ("9022", "JR東海"), ("8630", "SOMPO HD"),
        ("6098", "リクルートHD"), ("7832", "バンダイナムコ"), ("8750", "第一生命HD"),
        ("8411", "みずほFG"), ("4543", "テルモ"), ("6762", "TDK"),
        ("7751", "キヤノン"), ("6971", "京セラ"), ("2502", "アサヒグループ"),
        ("2503", "キリンHD"), ("4452", "花王"), ("6326", "クボタ"),
        ("5401", "日本製鉄"), ("5020", "ENEOS HD"), ("1605", "INPEX"),
        ("7011", "三菱重工業"), ("9202", "ANA HD"), ("9201", "JAL"),
        ("9104", "商船三井"), ("9107", "川崎汽船"),
        ("4188", "三菱ケミカルグループ"), ("7013", "IHI"),
    ],
}

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

@st.cache_data(ttl=3600)
def fetch_stock(code):
    ticker = yf.Ticker(f"{code}.T")
    df = ticker.history(period="60d")
    return df

mode = st.radio("スキャン対象", ["保有銘柄（21銘柄）", "時価総額フィルター"], index=1)

if mode == "時価総額フィルター":
    tier = st.selectbox("時価総額", ["10兆円以上", "5兆円以上", "1兆円以上"])
    targets = TIER_STOCKS[tier]
else:
    targets = HOLDINGS

st.caption(f"対象: {len(targets)}銘柄")

if st.button("スキャン開始", type="primary"):
    results = []
    progress = st.progress(0)
    status = st.empty()

    for i, (code, name) in enumerate(targets):
        status.text(f"取得中: {name}...")
        progress.progress((i+1)/len(targets))
        try:
            df = fetch_stock(code)
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
        color = "🟢" if d["s3n"] >= 3 else ("🟡" if d["s3n"] >= 2 else "🔴")
        with st.expander(f"{color} {d['name']} ({d['code']})　STEP3: {d['s3n']}/4クリア　株価: ¥{d['price']:,}　前日比: {d['change_pct']:+.1f}%"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("✅" if d["change_pct"] <= -2.5 else "❌", f"前日比: {d['change_pct']:+.1f}%")
                st.write("✅" if d["ma25_dev"] < 0 else "❌", f"MA乖離: {d['ma25_dev']:+.1f}%")
            with col2:
                st.write("✅" if d["bb_sigma"] <= -3.0 else "❌", f"BB: {d['bb_sigma']:.2f}σ")
                st.write("✅" if d["rci"] <= -80 else "❌", f"RCI: {d['rci']:.0f}%")

st.caption("⚠️ 投資判断はご自身の責任で")
