import os
import httpx
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

# 環境変数の読み込み
load_dotenv()
API_KEY = os.getenv("DOORKEEPER_API_KEY")
if API_KEY is None:
    raise ValueError("環境変数 DOORKEEPER_API_KEY が設定されていません")

# APIのエンドポイントとパラメータ
API_URL = "https://api.doorkeeper.jp/events"
params = {"q": "Startup Weekend", "per_page": 100, "sort": "starts_at"}
headers = {"Authorization": f"Bearer {API_KEY}"}

# APIからデータを取得
response = httpx.get(API_URL, params=params, headers=headers)
response.raise_for_status()  # ステータスコードがエラーの場合、例外を発生させる

# JSONデータを解析
events = response.json()

# 必要な情報を抽出
event_data = []
for event in events:
    event_info = {
        "イベント名": event["event"]["title"],
        "開催日": event["event"]["starts_at"],
        "開催場所": event["event"]["venue_name"],
        "緯度": event["event"]["lat"],
        "経度": event["event"]["long"],
        "イベントURL": event["event"]["public_url"],
    }
    event_data.append(event_info)

# DataFrameに変換
df = pd.DataFrame(event_data)

# CSVファイルに保存
csv_file = "startup_weekend_events.csv"
df.to_csv(csv_file, index=False, encoding="utf-8-sig")

# 実行日時を記録する
now = datetime.now(ZoneInfo("Asia/Tokyo"))
last_run_time_file = "last_run_time.txt"

with open(last_run_time_file, "w", encoding="utf-8") as f:
    f.write(now.isoformat())

print(f"イベント情報を {csv_file} に保存しました")
print(f"実行日時を {last_run_time_file} に保存しました")
