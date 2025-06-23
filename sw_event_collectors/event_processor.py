"""
イベントデータ処理クラス
複数ソースからのイベントデータをマージ・重複排除
"""

from typing import List, Dict


class EventProcessor:
    """イベントデータ処理クラス"""

    def merge_events(
        self, doorkeeper_events: List[Dict], peatix_events: List[Dict]
    ) -> List[Dict]:
        """DoorkeeperとPeatixのイベントをマージ（重複はPeatix優先）"""
        print("🔄 イベントデータをマージ中...")

        # Peatixイベントをベースにする
        merged_events = peatix_events.copy()

        # Doorkeeperイベントを追加（重複チェック）
        for dk_event in doorkeeper_events:
            is_duplicate = False

            for i, px_event in enumerate(merged_events):
                if self._is_duplicate_event(dk_event, px_event):
                    # 重複発見：Peatix優先なので何もしない
                    print(
                        f"🔄 重複イベントを検出（Peatix優先）: {px_event['イベント名']}"
                    )
                    is_duplicate = True
                    break

            if not is_duplicate:
                merged_events.append(dk_event)

        print(f"✅ マージ完了: 合計 {len(merged_events)} 件のイベント")
        return merged_events

    def _is_duplicate_event(self, event1: Dict, event2: Dict) -> bool:
        """イベント名と開始日時で重複判定"""
        try:
            # イベント名の類似性チェック（簡易版）
            name1 = event1.get("イベント名", "").lower().strip()
            name2 = event2.get("イベント名", "").lower().strip()

            # 開始日時の比較（日付部分のみ）
            date1 = event1.get("開催日", "")[:10]  # YYYY-MM-DD部分
            date2 = event2.get("開催日", "")[:10]

            # 名前が70%以上類似 かつ 開始日が同じ
            name_similarity = self._calculate_similarity(name1, name2)

            return name_similarity > 0.7 and date1 == date2

        except Exception:
            return False

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """文字列の類似度を計算（簡易版）"""
        if not str1 or not str2:
            return 0.0

        # 共通部分の長さ / 長い方の長さ
        common_chars = set(str1) & set(str2)
        max_len = max(len(str1), len(str2))

        return len(common_chars) / max_len if max_len > 0 else 0.0