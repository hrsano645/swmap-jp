"""
utilsモジュールのテスト
"""

import pytest
from sw_event_collectors.utils import convert_to_jst, determine_event_type


class TestUtils:
    """utilsのテストクラス"""

    def test_convert_to_jst_utc_format(self):
        """UTC形式の日時変換テスト"""
        utc_time = "2025-07-01T01:00:00Z"
        result = convert_to_jst(utc_time)
        
        # 日本時間（UTC+9）に変換されることを確認
        assert "+09:00" in result or "Asia/Tokyo" in result

    def test_convert_to_jst_local_format(self):
        """ローカル形式の日時変換テスト"""
        local_time = "2025-07-01 10:00:00"
        result = convert_to_jst(local_time)
        
        # 日本時間として扱われることを確認
        assert "2025-07-01" in result

    def test_convert_to_jst_invalid_input(self):
        """不正な入力の処理テスト"""
        invalid_time = "invalid-date"
        result = convert_to_jst(invalid_time)
        
        # エラー時は元の文字列が返されることを確認
        assert result == invalid_time

    def test_determine_event_type_three_days(self):
        """3日間イベントの判定テスト"""
        start_date = "2025-07-01T10:00:00+09:00"
        end_date = "2025-07-03T18:00:00+09:00"
        
        result = determine_event_type(start_date, end_date)
        assert result == "本イベント"

    def test_determine_event_type_one_day(self):
        """1日イベントの判定テスト"""
        start_date = "2025-07-01T10:00:00+09:00"
        end_date = "2025-07-01T18:00:00+09:00"
        
        result = determine_event_type(start_date, end_date)
        assert result == "その他"

    def test_determine_event_type_empty_input(self):
        """空の入力の処理テスト"""
        result = determine_event_type("", "")
        assert result == "その他"

        result = determine_event_type("2025-07-01", "")
        assert result == "その他"

    def test_determine_event_type_invalid_format(self):
        """不正な日付形式の処理テスト"""
        result = determine_event_type("invalid", "invalid")
        assert result == "その他"