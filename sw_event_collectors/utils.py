"""
共通ユーティリティ関数
各モジュールで共通して使用される機能を提供
"""

from datetime import datetime
from zoneinfo import ZoneInfo


def convert_to_jst(utc_time: str) -> str:
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
    except (ValueError, TypeError) as e:
        # 具体的な例外をキャッチして、予期しないエラーを隠さない
        print(f"日時変換エラー: {e}, 入力値: {utc_time}")
        return str(utc_time)


def determine_event_type(start_date: str, end_date: str) -> str:
    """開催日時からイベント種類を判定"""
    try:
        if not start_date or not end_date:
            return "その他"  # デフォルト

        # 日付部分のみを比較
        start_date_only = start_date[:10]  # YYYY-MM-DD
        end_date_only = end_date[:10]  # YYYY-MM-DD

        # 日付をdatetimeオブジェクトに変換
        start_dt = datetime.fromisoformat(start_date_only)
        end_dt = datetime.fromisoformat(end_date_only)

        # 日数を計算（終了日 - 開始日 + 1）
        duration_days = (end_dt - start_dt).days + 1

        if duration_days == 3:
            return "本イベント"  # 3日間開催
        else:
            return "その他"  # 3日間以外
    except (ValueError, TypeError) as e:
        print(f"イベント種類判定エラー: {e}")
        return "その他"  # エラー時はデフォルト