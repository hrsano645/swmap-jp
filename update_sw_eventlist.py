import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
import httpx
import pandas as pd
from dotenv import load_dotenv

# 日本の都道府県をカバーする正規表現パターン
prefecture_pattern = r"(東京都|北海道|京都府|大阪府|.{2,3}県)"


# 環境変数の読み込み
load_dotenv()
API_KEY = os.getenv("DOORKEEPER_API_KEY")
if API_KEY is None:
    raise ValueError("環境変数 DOORKEEPER_API_KEY が設定されていません")

# gsheetのIDとGIDを設定。環境変数から読み込み
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEET_DATA_GID = os.getenv("GOOGLE_SHEET_DATA_GID")
GOOGLE_SHEET_LAST_RUN_TIME_GID = os.getenv("GOOGLE_SHEET_LAST_RUN_TIME_GID")
if (
    GOOGLE_SHEET_ID is None
    or GOOGLE_SHEET_DATA_GID is None
    or GOOGLE_SHEET_LAST_RUN_TIME_GID is None
):
    raise ValueError(
        "環境変数 GOOGLE_SHEET_ID または GOOGLE_SHEET_DATA_GID または GOOGLE_SHEET_LAST_RUN_TIME_GID が設定されていません"
    )

# APIのエンドポイントとパラメータ
API_URL = "https://api.doorkeeper.jp/events"
params = {"q": "Startup Weekend", "per_page": 100, "sort": "starts_at"}
headers = {"Authorization": f"Bearer {API_KEY}"}

# APIからデータを取得
response = httpx.get(API_URL, params=params, headers=headers)
response.raise_for_status()  # ステータスコードがエラーの場合、例外を発生させる

# JSONデータを解析
events = response.json()


def convert_to_jst(utc_time: str) -> str:
    """UTC時間を日本時間に変換する"""
    utc = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
    jst = utc.astimezone(ZoneInfo("Asia/Tokyo"))
    return jst.isoformat()


# 必要な情報を抽出
event_data = []
for event in events:
    # 開催日、終了日のUTC時間を日本時間に変換
    starts_at_jst = convert_to_jst(event["event"]["starts_at"])
    ends_at_jst = convert_to_jst(event["event"]["ends_at"])

    # 住所から都道府県を抽出。都道府県が見つからない場合は空文字列
    prefecture = ""
    address = event["event"].get("address", "")
    if address:
        match = re.search(prefecture_pattern, address)
        prefecture = match.group(0).strip() if match else ""

    # 開催日と終了日の長さで本イベントかプレイベントかを判定
    # 本イベントは 2 日間以上、プレイベントは 1 日のイベント
    event_length = (
        datetime.fromisoformat(ends_at_jst) - datetime.fromisoformat(starts_at_jst)
    ).days
    event_type = "本イベント" if event_length >= 2 else "プレイベント"

    event_info = {
        "イベント名": event["event"]["title"],
        "開催日": starts_at_jst,
        "終了日": ends_at_jst,
        "開催場所": event["event"]["venue_name"],
        "緯度": event["event"]["lat"],
        "経度": event["event"]["long"],
        "イベントURL": event["event"]["public_url"],
        "住所": address,
        "都道府県": prefecture,
        "イベント種別": event_type,
    }
    event_data.append(event_info)

# DataFrameに変換
df = pd.DataFrame(event_data)

# NaNを空文字列に置き換える前に、データ型を明示的に設定
df = df.astype(str)  # すべての列を文字列型に変換
df.fillna("", inplace=True)  # ここでNaNを空文字列に置き換え

# スプレッドシートに保存
# Google Sheets APIの認証
gc = gspread.service_account(filename="service_account.json")
spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
data_worksheet = spreadsheet.get_worksheet_by_id(int(GOOGLE_SHEET_DATA_GID))

# DataFrameをリストに変換してスプレッドシートに書き込み
data_worksheet.clear()  # 既存のデータをクリア
data_worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# 実行時刻を記録する
last_run_time_jst = convert_to_jst(datetime.now().isoformat())

# 実行日時をスプレッドシートに書き込み
last_run_time_worksheet = spreadsheet.get_worksheet_by_id(
    int(GOOGLE_SHEET_LAST_RUN_TIME_GID)
)
last_run_time_worksheet.clear()  # 既存のデータをクリア

# worksheet.update() メソッドの引数の順序を修正
last_run_time_worksheet.update(
    values=[[last_run_time_jst]], range_name="A1"
)  # A1セルに日本時間を記入

print(f"イベント情報を {GOOGLE_SHEET_ID=} {GOOGLE_SHEET_DATA_GID=} に保存しました")
print(f"実行日時を {GOOGLE_SHEET_ID=} {GOOGLE_SHEET_LAST_RUN_TIME_GID=} に保存しました")
