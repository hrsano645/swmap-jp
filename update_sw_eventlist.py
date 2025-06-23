"""
Startup Weekend Event Collector (Main Entry Point)
DoorkeeperとPeatixからStartup Weekendイベント情報を収集し、Google Sheetsに統合保存するシステム

リファクタリング後のメインエントリーポイント
各機能は sw_event_collectors/ モジュールに分離
"""

from sw_event_collectors.config import Config
from sw_event_collectors.doorkeeper_collector import DoorkeeperCollector
from sw_event_collectors.peatix_collector import PeatixCollector
from sw_event_collectors.event_processor import EventProcessor
from sw_event_collectors.google_sheets_storage import GoogleSheetsStorage


class StartupWeekendEventCollector:
    """Startup Weekendイベント収集の統合クラス（リファクタリング後）"""

    def __init__(self):
        self.config = Config()
        self.doorkeeper_collector = DoorkeeperCollector(self.config)
        self.peatix_collector = PeatixCollector(self.config)
        self.event_processor = EventProcessor()
        self.storage = GoogleSheetsStorage(self.config)

    def collect_all_events(self):
        """全イベント収集の実行（リファクタリング後）"""
        print("🚀 Startup Weekend イベント収集を開始します")
        print("=" * 50)

        # 1. Doorkeeperからデータ収集
        doorkeeper_events = self.doorkeeper_collector.collect_events()

        # 2. Peatixからデータ収集
        peatix_events = self.peatix_collector.collect_events()

        # 3. データマージ
        if doorkeeper_events or peatix_events:
            merged_events = self.event_processor.merge_events(doorkeeper_events, peatix_events)

            # 4. Google Sheetsに保存
            self.storage.save_events(merged_events)
        else:
            print("⚠️ 収集できたイベントがありません")

        print("=" * 50)
        print("🏁 イベント収集が完了しました")


def main():
    """メイン実行関数"""
    try:
        collector = StartupWeekendEventCollector()
        collector.collect_all_events()
    except Exception as e:
        print(f"❌ プログラム実行中にエラーが発生しました: {e}")


if __name__ == "__main__":
    main()