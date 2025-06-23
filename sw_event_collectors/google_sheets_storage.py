"""
Google Sheetsストレージクラス
Google Sheetsへのイベントデータ保存処理
"""

import pandas as pd
import gspread
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict

from .config import Config


class GoogleSheetsStorage:
    """Google Sheetsストレージクラス"""

    def __init__(self, config: Config):
        self.config = config

    def save_events(self, events: List[Dict]):
        """Google Sheetsにイベントデータを保存"""
        try:
            print("💾 Google Sheetsにデータを保存中...")

            # DataFrameに変換
            df = pd.DataFrame(events)

            if df.empty:
                print("⚠️ 保存するデータがありません")
                return

            # 開催日でソート（文字列のままでも日時順になるISO形式を想定）
            try:
                # 開催日が存在する場合のみソート
                if "開催日" in df.columns and not df["開催日"].empty:
                    # 空の値を最後に持ってくるためにna_position='last'を指定
                    df = df.sort_values(by="開催日", ascending=True, na_position="last")
                    print("📅 開催日順にソートしました")
            except (KeyError, TypeError) as sort_error:
                print(
                    f"⚠️ ソート処理でエラーが発生しましたが、処理を続行します: {sort_error}"
                )

            # データ型を統一
            df = df.astype(str)
            df.fillna("", inplace=True)

            # Google Sheets APIの認証
            gc = gspread.service_account(filename="service_account.json")
            spreadsheet = gc.open_by_key(self.config.google_sheet_id)
            data_worksheet = spreadsheet.get_worksheet_by_id(
                int(self.config.google_sheet_data_gid)
            )

            # データを書き込み
            data_worksheet.clear()
            data_worksheet.update([df.columns.values.tolist()] + df.values.tolist())

            # 実行時刻を記録
            self.update_last_run_time()

            print(f"✅ {len(events)} 件のイベント情報をGoogle Sheetsに保存しました")
            print(f"📊 シート ID: {self.config.google_sheet_id}")

        except Exception as e:
            print(f"❌ Google Sheetsへの保存でエラーが発生しました: {e}")

    def update_last_run_time(self):
        """実行時刻を記録"""
        try:
            last_run_time_jst = self._convert_to_jst(datetime.now().isoformat())
            
            # Google Sheets APIの認証
            gc = gspread.service_account(filename="service_account.json")
            spreadsheet = gc.open_by_key(self.config.google_sheet_id)
            last_run_time_worksheet = spreadsheet.get_worksheet_by_id(
                int(self.config.google_sheet_last_run_time_gid)
            )
            
            last_run_time_worksheet.clear()
            last_run_time_worksheet.update(
                values=[[last_run_time_jst]], range_name="A1"
            )

            print(f"⏱️ 実行完了時間の記録を行いました 実行完了時間: {last_run_time_jst}")
            
        except Exception as e:
            print(f"❌ 実行時刻の記録でエラーが発生しました: {e}")

    def _convert_to_jst(self, utc_time: str) -> str:
        """UTC時間を日本時間に変換する"""
        try:
            if isinstance(utc_time, str):
                # Peatixの日時データ（既に日本時間、タイムゾーン情報なし）の場合
                if "T" not in utc_time and " " in utc_time:
                    # "2025-06-13 18:00:00" 形式の場合、日本時間として扱う
                    dt = datetime.fromisoformat(utc_time)
                    # 日本時間のタイムゾーン情報を付与
                    jst_dt = dt.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
                    return jst_dt.isoformat()
                elif utc_time.endswith("Z"):
                    utc = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
                else:
                    utc = datetime.fromisoformat(utc_time)
            else:
                utc = utc_time

            jst = utc.astimezone(ZoneInfo("Asia/Tokyo"))
            return jst.isoformat()
        except Exception:
            return str(utc_time)