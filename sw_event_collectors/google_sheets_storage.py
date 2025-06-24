"""
Google Sheetsストレージクラス
Google Sheetsへのイベントデータ保存処理
"""

import pandas as pd
import gspread
from datetime import datetime
from typing import List, Dict

from .config import Config
from .utils import convert_to_jst


class GoogleSheetsStorage:
    """Google Sheetsストレージクラス"""

    def __init__(self, config: Config):
        self.config = config
        # Google Sheetsクライアントを一度だけ初期化
        self.gc = gspread.service_account(filename="service_account.json")

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

            # Google Sheetsクライアントを使用
            spreadsheet = self.gc.open_by_key(self.config.google_sheet_id)
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
            last_run_time_jst = convert_to_jst(datetime.now().isoformat())
            
            # Google Sheetsクライアントを使用
            spreadsheet = self.gc.open_by_key(self.config.google_sheet_id)
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

