"""
EventProcessorクラスのテスト
"""

import pytest
from sw_event_collectors.event_processor import EventProcessor


class TestEventProcessor:
    """EventProcessorのテストクラス"""

    def setup_method(self):
        """各テストの前に実行"""
        self.processor = EventProcessor()

    def test_merge_events_no_duplicates(self):
        """重複なしのマージテスト"""
        doorkeeper_events = [
            {
                "イベント名": "Startup Weekend Tokyo",
                "開催日": "2025-07-01T10:00:00+09:00",
                "開催場所": "東京",
            }
        ]
        peatix_events = [
            {
                "イベント名": "Startup Weekend Osaka",
                "開催日": "2025-07-08T10:00:00+09:00",
                "開催場所": "大阪",
            }
        ]

        result = self.processor.merge_events(doorkeeper_events, peatix_events)

        assert len(result) == 2
        assert result[0]["イベント名"] == "Startup Weekend Osaka"  # Peatix優先
        assert result[1]["イベント名"] == "Startup Weekend Tokyo"

    def test_merge_events_with_duplicates(self):
        """重複ありのマージテスト"""
        doorkeeper_events = [
            {
                "イベント名": "Startup Weekend Tokyo 2025",
                "開催日": "2025-07-01T10:00:00+09:00",
                "開催場所": "東京",
            }
        ]
        peatix_events = [
            {
                "イベント名": "Startup Weekend Tokyo 2025",
                "開催日": "2025-07-01T18:00:00+09:00",  # 同日
                "開催場所": "東京",
            }
        ]

        result = self.processor.merge_events(doorkeeper_events, peatix_events)

        # 重複のため、Peatixのみが残る
        assert len(result) == 1
        assert result[0]["開催日"] == "2025-07-01T18:00:00+09:00"  # Peatix版

    def test_merge_events_empty_lists(self):
        """空リストのマージテスト"""
        result = self.processor.merge_events([], [])
        assert len(result) == 0

    def test_calculate_similarity(self):
        """文字列類似度計算のテスト"""
        # 完全一致
        assert self.processor._calculate_similarity("test", "test") == 1.0

        # 部分一致
        similarity = self.processor._calculate_similarity("startup weekend", "startup")
        assert 0 < similarity < 1

        # 不一致
        assert self.processor._calculate_similarity("abc", "xyz") >= 0

        # 空文字列
        assert self.processor._calculate_similarity("", "test") == 0.0
        assert self.processor._calculate_similarity("test", "") == 0.0

    def test_is_duplicate_event(self):
        """重複判定のテスト"""
        event1 = {
            "イベント名": "Startup Weekend Tokyo",
            "開催日": "2025-07-01T10:00:00+09:00",
        }
        event2 = {
            "イベント名": "Startup Weekend Tokyo 2025",
            "開催日": "2025-07-01T18:00:00+09:00",  # 同日
        }
        event3 = {
            "イベント名": "Startup Weekend Osaka",
            "開催日": "2025-07-08T10:00:00+09:00",  # 別日
        }

        # 同日で類似名前の場合は重複
        assert self.processor._is_duplicate_event(event1, event2)

        # 別日の場合は重複でない
        assert not self.processor._is_duplicate_event(event1, event3)

        # 不正なデータでエラーにならない
        invalid_event = {"不正": "データ"}
        assert not self.processor._is_duplicate_event(event1, invalid_event)