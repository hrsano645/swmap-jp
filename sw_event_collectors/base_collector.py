"""
基底コレクタークラス
各イベント収集クラスの共通処理を定義
"""

from abc import ABC, abstractmethod
from typing import List, Dict

from .config import Config
from .utils import convert_to_jst, determine_event_type


class BaseCollector(ABC):
    """イベント収集基底クラス"""

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def collect_events(self) -> List[Dict]:
        """イベント収集の抽象メソッド"""
        pass

    def convert_to_jst(self, utc_time: str) -> str:
        """UTC時間を日本時間に変換する"""
        return convert_to_jst(utc_time)

    def _determine_event_type(self, start_date: str, end_date: str) -> str:
        """開催日時からイベント種類を判定"""
        return determine_event_type(start_date, end_date)

    def _is_startup_weekend_related(
        self, event_title: str, event_description: str, organizer_name: str
    ) -> bool:
        """イベントがStartup Weekend関連かどうかを判定"""
        # 検索対象テキストを結合
        search_text = f"{event_title} {event_description} {organizer_name}".lower()

        # キーワードマッチング
        for keyword in self.config.startup_weekend_keywords:
            if keyword.lower() in search_text:
                print(
                    f"✓ キーワードマッチ: '{keyword}' in '{event_title[:50]}...'"
                )
                return True

        print(f"✗ キーワード不一致: {event_title[:30]}...")
        return False