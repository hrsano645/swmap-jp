"""
Doorkeeperイベント収集クラス
Doorkeeper APIからStartup Weekendイベント情報を取得
"""

import httpx
from typing import List, Dict, Optional

from .base_collector import BaseCollector
from .config import Config


class DoorkeeperCollector(BaseCollector):
    """Doorkeeperイベント収集クラス"""

    def __init__(self, config: Config):
        super().__init__(config)

    def collect_events(self) -> List[Dict]:
        """DoorkeeperからStartup Weekendイベントを収集"""
        doorkeeper_events = []

        if not self.config.has_doorkeeper_api_key:
            print(
                "⚠️ Doorkeeper API KEYが設定されていません。Doorkeeperのデータ収集をスキップします。"
            )
            return doorkeeper_events

        try:
            print("📡 Doorkeeperからイベント情報を取得中...")

            # APIリクエスト設定
            api_url = "https://api.doorkeeper.jp/events"
            params = {"q": "Startup Weekend", "per_page": 100, "sort": "starts_at"}
            headers = {"Authorization": f"Bearer {self.config.doorkeeper_api_key}"}

            print(f"🔗 リクエストURL: {api_url}")
            print(f"🔍 検索パラメータ: {params}")

            # APIからデータを取得
            response = httpx.get(api_url, params=params, headers=headers)
            print(f"📡 HTTP ステータス: {response.status_code}")

            response.raise_for_status()

            events_data = response.json()
            print(f"🔍 Doorkeeper API応答: {len(events_data)} 件のイベントを受信")

            # デバッグ: 最初の数件のイベント構造を確認
            if events_data and len(events_data) > 0:
                print(
                    f"📋 最初のイベントの構造例: {list(events_data[0].keys()) if events_data[0] else 'Empty'}"
                )

            for i, event_wrapper in enumerate(events_data):
                # 元のスクリプトと同じ構造: event["event"] でアクセス
                event = event_wrapper.get("event", {})
                if not event:
                    print(
                        f"📋 [{i + 1}/{len(events_data)}] 空のイベントデータをスキップ"
                    )
                    continue

                print(
                    f"📋 [{i + 1}/{len(events_data)}] 処理中イベント: {event.get('title', 'タイトル不明')}"
                )

                # 場所情報の処理（元のスクリプトと同じフィールド名を使用）
                venue_name = event.get("venue_name", "") or ""
                latitude = (
                    str(event.get("lat", "")) if event.get("lat") is not None else ""
                )
                longitude = (
                    str(event.get("long", "")) if event.get("long") is not None else ""
                )  # 元のスクリプトでは"long"を使用
                address = event.get("address", "") or ""

                # オンラインイベントの判定（Peatixに合わせて統一）
                is_online = (
                    venue_name == ""
                    or venue_name is None
                    or venue_name.lower()
                    in ["online", "オンライン", "xxxonlineeventxxx"]
                )

                # オンラインイベントの場合、開催場所、住所、緯度、経度を空文字列に統一
                if is_online:
                    venue_name = ""
                    address = ""
                    latitude = ""
                    longitude = ""

                # 開始・終了日時の変換
                start_date = self.convert_to_jst(event.get("starts_at", ""))
                end_date = self.convert_to_jst(event.get("ends_at", ""))

                # 主催者情報の取得
                group_id = event.get("group")
                organizer_name = "未取得"
                if group_id:
                    group_name = self.get_group_info(group_id)
                    if group_name:
                        organizer_name = group_name

                # Startup Weekendに関連するイベントかチェック
                event_title = event.get("title", "")
                event_description = event.get("description", "")

                if self._is_startup_weekend_related(
                    event_title, event_description, organizer_name
                ):
                    # イベント種類を判定
                    event_type = self._determine_event_type(start_date, end_date)

                    event_info = {
                        "イベント名": event_title,
                        "開催日": start_date,
                        "終了日": end_date,
                        "開催場所": venue_name,
                        "緯度": latitude,
                        "経度": longitude,
                        "イベントURL": event.get("public_url", ""),
                        "住所": address,
                        "主催者": organizer_name,
                        "イベント種類": event_type,
                    }

                    doorkeeper_events.append(event_info)
                    print(f"✓ Startup Weekendイベントとして追加: {event_title}")
                else:
                    print(
                        f"⏭️ Startup Weekend以外のイベントとしてスキップ: {event_title}"
                    )

            print(
                f"✅ Doorkeeperから {len(doorkeeper_events)} 件のStartup Weekendイベントを取得しました"
            )

        except Exception as e:
            print(f"❌ Doorkeeperからのデータ取得でエラーが発生しました: {e}")
            import traceback

            print(f"詳細エラー: {traceback.format_exc()}")

        return doorkeeper_events

    def get_group_info(self, group_id: int) -> Optional[str]:
        """Doorkeeper Groups APIからグループ名を取得"""
        try:
            if not self.config.doorkeeper_api_key or not group_id:
                return None

            api_url = f"https://api.doorkeeper.jp/groups/{group_id}"
            headers = {"Authorization": f"Bearer {self.config.doorkeeper_api_key}"}

            print(f"🏢 グループ情報取得中: Group ID {group_id}")

            response = httpx.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()

            group_data = response.json()
            group_name = group_data.get("group", {}).get("name", "")

            if group_name:
                print(f"✓ グループ名取得成功: {group_name}")
                return group_name
            else:
                print(f"⚠️ グループ名が見つかりません: Group ID {group_id}")
                return None

        except Exception as e:
            print(f"❌ グループ情報取得エラー (Group ID {group_id}): {e}")
            return None