# ============================================================
# ちょるこ式スイングトレード判定 STEP3版
# ZAi 2026年9月号掲載手法
# ※STEP4は試験後にStreamlitで復活予定
# ============================================================

!pip install yfinance pandas numpy openpyxl -q

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import io
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# 都築さんの保有銘柄（重複なし・21銘柄）
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

def get_prime_codes():
    """JPXから東証プライム全銘柄コードを取得"""
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        df = pd.read_excel(io.BytesIO(r.content), header=0, engine="xlrd")
        prime = df[df.iloc[:,2] == "プライム"]
        codes = prime.iloc[:,1].astype(str).str.zfill(4).tolist()
        print(f"東証プライム {len(codes)}銘柄を取得しました")
        return codes
    except Exception as e:
        print(f"銘柄一覧取得失敗: {e}")
        return []

THRESHOLDS = {
    "1": ("10兆円以上", 10_000_000_000_000),
    "2": ("5兆円以上",   5_000_000_000_000),
    "3": ("1兆円以上",   1_000_000_000_000),
}

def calc_rci(series, period=9):
    if len(series) < period:
        return 0.0
    recent = series.iloc[-period:].values
    n = period
    date_rank  = np.arange(1, n + 1)
    price_rank = pd.Series(recent).rank(ascending=True).values
    d_sq = np.sum((date_rank - price_rank) ** 2)
    return round((1 - 6 * d_sq / (n * (n**2 - 1))) * 100, 1)

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
        "sell_bb":    bb_sigma > 3.0,
        "sell_rci":   rci > 80,
    }

def judge(s3):
    s3n = sum([
        s3["change_pct"] <= -2.5,
        s3["ma25_dev"]   <  0,
        s3["bb_sigma"]   <= -3.0,
        s3["rci"]        <= -80,
    ])
    if s3["sell_bb"] or s3["sell_rci"]: return "🔔 売りサイン", s3n
    if s3n >= 3:                        return "🟢 買い候補",   s3n
    if s3n >= 2:                        return "🟡 監視継続",   s3n
    return "🔴 様子見", s3n

def print_result(d):
    cap_str = ""
    if d.get("market_cap"):
        cap = d["market_cap"]/1_000_000_000_000
        cap_str = f"\n時価総額: {cap:.1f}兆円"
    print(f"\n{'─'*40}")
    print(d["judge"])
    print(f"{d['name']} ({d['code']})")
    print(f"株価: {d['price']:,}円{cap_str}")
    print(f"前日比: {d['change_pct']:+.1f}%")
    print(f"\nSTEP3 ({d['s3n']}/4クリア)")
    print(f"{'✅' if d['change_pct']<=-2.5 else '❌'} 前日比: {d['change_pct']:+.1f}%")
    print(f"{'✅' if d['ma25_dev']<0 else '❌'} MA乖離: {d['ma25_dev']:+.1f}%")
    print(f"{'✅' if d['bb_sigma']<=-3.0 else '❌'} BB: {d['bb_sigma']:.2f}σ")
    print(f"{'✅' if d['rci']<=-80 else '❌'} RCI: {d['rci']:.0f}%")
    if d["sell_bb"] or d["sell_rci"]:
        print("⚠️ 売りサイン")
        if d["sell_bb"]:  print("🔔 BB +3σ到達")
        if d["sell_rci"]: print("🔔 RCI 買われすぎ")

def scan_holdings():
    print("="*40)
    print("保有銘柄 STEP3判定")
    print(f"全{len(HOLDINGS)}銘柄")
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("="*40)
    all_data = []
    for code, name in HOLDINGS:
        print(f"[{code}] {name}...", end=" ", flush=True)
        try:
            ticker = yf.Ticker(f"{code}.T")
            df = ticker.history(period="60d")
            if len(df) < 30:
                print("スキップ"); continue
            s3 = calc_step3(df)
            j, s3n = judge(s3)
            all_data.append({"code":code,"name":name,"market_cap":0,"judge":j,"s3n":s3n,**s3})
            print(j)
        except:
            print("失敗")
    if not all_data:
        print("データ取得失敗"); return
    order = {"🟢 買い候補":0,"🟡 監視継続":1,"🔔 売りサイン":2,"🔴 様子見":3}
    all_data.sort(key=lambda x: order.get(x["judge"],9))
    print(f"\n{'='*40}")
    print("保有銘柄 判定結果")
    print("="*40)
    for d in all_data:
        print_result(d)
    print(f"\n{'='*40}")
    print("⚠️ 投資判断はご自身の責任で")
    print("="*40)

def scan_market():
    print("="*40)
    print("時価総額フィルタースキャン")
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("="*40)
    print("\n時価総額を選んでください")
    print("1. 10兆円以上")
    print("2. 5兆円以上")
    print("3. 1兆円以上")
    choice = input("\n番号(1/2/3) → ").strip()
    tier_label, threshold = THRESHOLDS.get(choice, THRESHOLDS["3"])
    holding_codes = {code for code, _ in HOLDINGS}

    codes = get_prime_codes()
    if not codes:
        print("銘柄一覧取得失敗。終了します。")
        return

    print(f"\n▶ {tier_label} をスキャン中...\n")

    all_data = []
    for code in codes:
        if code in holding_codes:
            continue
        try:
            ticker = yf.Ticker(f"{code}.T")
            info = ticker.fast_info
            market_cap = getattr(info, 'market_cap', 0) or 0
            if market_cap < threshold:
                continue
            name = ticker.info.get("longName") or ticker.info.get("shortName") or code
            df = ticker.history(period="60d")
            if len(df) < 30:
                continue
            s3 = calc_step3(df)
            j, s3n = judge(s3)
            cap = market_cap/1_000_000_000_000
            print(f"[{code}] {name[:12]} {cap:.1f}兆 → {j}")
            all_data.append({"code":code,"name":name,"market_cap":market_cap,"judge":j,"s3n":s3n,**s3})
        except:
            continue

    if not all_data:
        print("該当銘柄なし"); return

    order = {"🟢 買い候補":0,"🟡 監視継続":1,"🔔 売りサイン":2,"🔴 様子見":3}
    all_data.sort(key=lambda x: order.get(x["judge"],9))
    print(f"\n{'='*40}")
    print(f"判定結果 / {tier_label} / {len(all_data)}銘柄")
    print("="*40)
    for d in all_data:
        print_result(d)
    print(f"\n{'='*40}")
    print("⚠️ 投資判断はご自身の責任で")
    print("="*40)

# ── 実行 ──
print("\n実行モードを選んでください")
print("1. 保有銘柄スキャン（21銘柄）")
print("2. 時価総額フィルター（東証プライム全銘柄）")
mode = input("\n番号(1/2) → ").strip()
if mode == "1":
    scan_holdings()
else:
    scan_market()
