"""
Startup Weekend Event Collector
DoorkeeperとPeatixからStartup Weekendイベント情報を収集し、Google Sheetsに統合保存するシステム
"""

import os
import re
import httpx
import pandas as pd
import gspread
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote_plus, urlparse, urlunparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


class StartupWeekendEventCollector:
    """Startup Weekendイベント収集の統合クラス"""

    def __init__(self):
        # 環境変数の読み込み
        load_dotenv()
        self._load_environment_variables()

        # データ格納用
        self.collected_events = []
        self.driver = None

        # 日本の都道府県をカバーする正規表現パターン
        self.prefecture_pattern = r"(東京都|北海道|京都府|大阪府|.{2,3}県)"

    def _load_environment_variables(self):
        """環境変数の読み込みと検証"""
        # Doorkeeper API設定
        self.doorkeeper_api_key = os.getenv("DOORKEEPER_API_KEY")

        # Google Sheets設定
        self.google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.google_sheet_data_gid = os.getenv("GOOGLE_SHEET_DATA_GID")
        self.google_sheet_last_run_time_gid = os.getenv(
            "GOOGLE_SHEET_LAST_RUN_TIME_GID"
        )

        # 必須環境変数の検証
        if not all(
            [
                self.google_sheet_id,
                self.google_sheet_data_gid,
                self.google_sheet_last_run_time_gid,
            ]
        ):
            raise ValueError("必須のGoogle Sheets環境変数が設定されていません")

    def convert_to_jst(self, utc_time: str) -> str:
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

    def get_doorkeeper_group_info(self, group_id: int) -> Optional[str]:
        """Doorkeeper Groups APIからグループ名を取得"""
        try:
            if not self.doorkeeper_api_key or not group_id:
                return None

            api_url = f"https://api.doorkeeper.jp/groups/{group_id}"
            headers = {"Authorization": f"Bearer {self.doorkeeper_api_key}"}

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

    def collect_doorkeeper_events(self) -> List[Dict]:
        """DoorkeeperからStartup Weekendイベントを収集"""
        doorkeeper_events = []

        if not self.doorkeeper_api_key:
            print(
                "⚠️ Doorkeeper API KEYが設定されていません。Doorkeeperのデータ収集をスキップします。"
            )
            return doorkeeper_events

        try:
            print("📡 Doorkeeperからイベント情報を取得中...")

            # APIリクエスト設定
            api_url = "https://api.doorkeeper.jp/events"
            params = {"q": "Startup Weekend", "per_page": 100, "sort": "starts_at"}
            headers = {"Authorization": f"Bearer {self.doorkeeper_api_key}"}

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
                    group_name = self.get_doorkeeper_group_info(group_id)
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

    def _is_startup_weekend_related(
        self, event_title: str, event_description: str, organizer_name: str
    ) -> bool:
        """DoorkeeperイベントがStartup Weekend関連かどうかを判定"""
        # キーワードリスト
        startup_keywords = [
            "startup weekend",
            "startupweekend",
            # "sw",
            # "スタートアップウィークエンド",
            # "スタートアップ ウィークエンド",
        ]

        # 検索対象テキストを結合
        search_text = f"{event_title} {event_description} {organizer_name}".lower()

        # キーワードマッチング
        for keyword in startup_keywords:
            if keyword.lower() in search_text:
                print(
                    f"✓ Doorkeeperキーワードマッチ: '{keyword}' in '{event_title[:50]}...'"
                )
                return True

        print(f"✗ Doorkeeperキーワード不一致: {event_title[:30]}...")
        return False

    def setup_driver(self):
        """Seleniumドライバーの設定"""
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except Exception as e:
            print(f"❌ Seleniumドライバーの初期化に失敗しました: {e}")
            return False

    def clean_url(self, url: str) -> str:
        """URLをクリーンアップ"""
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    def search_peatix_events(self, keyword: str) -> List[str]:
        """Peatixでキーワード検索してイベントURLを取得"""
        event_urls = []
        page = 1

        while True:
            try:
                # 元のスクリプトと同じ詳細な検索パラメーターを使用
                encoded_keyword = quote_plus(keyword)
                search_url = f"https://peatix.com/search?q={encoded_keyword}&country=JP&l.text=%E3%81%99%E3%81%B9%E3%81%A6%E3%81%AE%E5%A0%B4%E6%89%80&p={page}&size=20&v=3.4&tag_ids=&dr="

                print(f"🔍 検索URL: {search_url}")
                self.driver.get(search_url)

                # ページの読み込み待機
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # 追加の待機時間
                import time

                time.sleep(3)

                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                # イベントリストを取得
                event_list = soup.find("ul", class_="event-list")

                if not event_list:
                    print(f"ページ {page}: イベントリストが見つかりません")
                    break

                # 各イベントのURLを抽出
                events = event_list.find_all("li")
                if not events:
                    print(f"ページ {page}: イベントが見つかりません")
                    break

                page_urls = []
                for event in events:
                    # event-thumb_linkクラスのリンクを探す
                    link = event.find("a", class_="event-thumb_link")
                    if link and link.get("href"):
                        full_url = urljoin("https://peatix.com", link["href"])
                        clean_url = self.clean_url(full_url)
                        if clean_url not in event_urls:
                            page_urls.append(clean_url)
                            event_urls.append(clean_url)

                if not page_urls:
                    print(f"ページ {page}: 新しいイベントURLが見つかりません")
                    break

                print(f"ページ {page}: {len(page_urls)}件のイベントを発見")

                # 次のページがあるかチェック
                pagination = soup.find("ul", class_="pagination")
                if not pagination:
                    break

                next_button = pagination.find("a", string="次")
                if not next_button:
                    break

                page += 1
                time.sleep(2)  # ページ間の待機

                # 安全のため最大5ページまでに制限
                if page > 5:
                    break

            except Exception as e:
                print(f"❌ Peatix検索でエラーが発生しました (ページ {page}): {e}")
                break

        print(f"キーワード '{keyword}' で合計 {len(event_urls)} 件のイベントを発見")
        return event_urls

    def extract_peatix_event_details(self, event_url: str) -> Optional[Dict]:
        """PeatixイベントページからJSONデータを抽出"""
        try:
            print(f"📄 詳細取得中: {event_url}")
            self.driver.get(event_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            import time

            time.sleep(3)

            page_source = self.driver.page_source

            # view-event URLを取得
            view_event_url = self._extract_view_event_url(page_source)

            if view_event_url:
                print(f"🔗 JSON API URL発見: {view_event_url}")
                json_data = self._fetch_event_json_data(view_event_url)
                if json_data:
                    result, status = self._extract_event_details_from_json(
                        json_data, event_url
                    )

                    if status == "success":
                        return result
                    elif status in ["duplicate", "no_keyword_match"]:
                        print(f"⏭️ スキップ ({status}): {event_url}")
                        return None

            # JSON APIで取得できない場合のフォールバック処理
            print("📄 フォールバック: HTMLから直接抽出")
            return self._extract_from_html_fallback(page_source, event_url)

        except Exception as e:
            print(
                f"❌ Peatixイベント詳細の取得でエラーが発生しました ({event_url}): {e}"
            )
            return None

    def _extract_view_event_url(self, page_source: str) -> Optional[str]:
        """ページソースからviewEventURLを抽出"""
        try:
            # w.viewEventURL = "https://peatix.com/event/[eventid]/get_view_data"; のパターンを検索
            pattern = r'w\.viewEventURL\s*=\s*["\']([^"\']+)["\']'
            match = re.search(pattern, page_source)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            print(f"viewEventURL抽出エラー: {e}")
            return None

    def _fetch_event_json_data(self, view_event_url: str) -> Optional[Dict]:
        """viewEventURLからJSONデータを取得"""
        try:
            import httpx

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = httpx.get(view_event_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"JSONデータ取得エラー ({view_event_url}): {e}")
            return None

    def _extract_event_details_from_json(
        self, json_data: Dict, event_url: str
    ) -> tuple[Optional[Dict], str]:
        """JSONデータからイベント詳細を抽出"""
        try:
            event_data = json_data.get("json_data", {}).get("event", {})
            if not event_data:
                return None, "error"

            # イベント名
            event_name = event_data.get("name", "")

            # 主催者情報（podから取得）
            pod_data = event_data.get("pod", {})
            organizer_name = pod_data.get("name", "") if pod_data else ""

            # キーワードフィルタリング
            if not self._matches_startup_weekend_keywords(
                event_name, event_data.get("description", ""), organizer_name
            ):
                return None, "no_keyword_match"

            # 開催日時
            start_datetime = event_data.get("datetime", "")
            end_datetime = event_data.get("datetimeEnd", "")

            # 開催場所の情報
            venue_name = event_data.get("venueName", "")
            venue_address = event_data.get("venueAddress", "")
            is_online = event_data.get("isOnline", False)

            # 緯度経度
            latlng = event_data.get("latlng", "")
            latitude, longitude = "", ""
            if latlng and "," in latlng:
                lat_lon_parts = latlng.split(",")
                if len(lat_lon_parts) == 2:
                    latitude = lat_lon_parts[0].strip()
                    longitude = lat_lon_parts[1].strip()

            # イベント種別の判定
            if is_online or venue_name.lower() in [
                "online",
                "オンライン",
                "xxxonlineeventxxx",
            ]:
                # オンラインイベント
                location = ""  # Doorkeeperに合わせて空文字列
                address = ""  # Doorkeeperに合わせて空文字列
                latitude = ""  # オンラインの場合は緯度経度も空文字列
                longitude = ""  # オンラインの場合は緯度経度も空文字列
            else:
                # 物理開催イベント
                location = venue_name
                address = venue_address

            # イベント種類を判定
            event_type_category = self._determine_event_type(
                self._format_datetime(start_datetime),
                self._format_datetime(end_datetime),
            )

            return {
                "イベント名": event_name,
                "開催日": self._format_datetime(start_datetime),
                "終了日": self._format_datetime(end_datetime),
                "開催場所": location,
                "緯度": latitude,
                "経度": longitude,
                "イベントURL": self.clean_url(event_url),
                "住所": address,
                "主催者": organizer_name,
                "イベント種類": event_type_category,
            }, "success"

        except Exception as e:
            print(f"JSONからのイベント詳細抽出エラー: {e}")
            return None, "error"

    def _format_datetime(self, datetime_str: str) -> str:
        """日時文字列をフォーマット"""
        try:
            if not datetime_str:
                return ""

            # Peatixの日時データ（既に日本時間、タイムゾーン情報なし）の場合
            if "T" not in datetime_str and " " in datetime_str:
                # "2025-06-13 18:00:00" 形式の場合、日本時間として扱う
                dt = datetime.fromisoformat(datetime_str)
                # 日本時間のタイムゾーン情報を付与
                jst_dt = dt.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
                return jst_dt.isoformat()
            else:
                # DoorkeeperのUTC時間データの場合
                dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                # 日本時間に変換
                jst_dt = dt.astimezone(ZoneInfo("Asia/Tokyo"))
                return jst_dt.isoformat()
        except Exception:
            return str(datetime_str)

    def _matches_startup_weekend_keywords(
        self, event_name: str, description: str, organizer_name: str
    ) -> bool:
        """Startup Weekendキーワードマッチング（強化版）"""
        # 主催者名に直接キーワードが含まれているかチェック（最優先）
        organizer_text = organizer_name.lower()
        startup_keywords = [
            "startup weekend",
            "startupweekend",
            "startup",
            # "スタートアップウィークエンド",
            # "スタートアップ",
        ]

        for keyword in startup_keywords:
            if keyword in organizer_text:
                print(
                    f"✓ 主催者名 '{organizer_name}' にキーワード '{keyword}' がマッチしました"
                )
                return True

        # イベント名に直接キーワードが含まれているかチェック
        event_name_text = event_name.lower()
        for keyword in startup_keywords:
            if keyword in event_name_text:
                print(
                    f"✓ イベント名 '{event_name[:50]}...' にキーワード '{keyword}' がマッチしました"
                )
                return True

        print(
            f"✗ キーワードマッチせず - イベント名: {event_name[:30]}..., 主催者: {organizer_name}"
        )
        return False

    def _extract_from_html_fallback(
        self, page_source: str, event_url: str
    ) -> Optional[Dict]:
        """HTMLから直接情報を抽出するフォールバック処理"""
        try:
            soup = BeautifulSoup(page_source, "html.parser")

            # 基本情報の抽出（簡易版）
            title_elem = soup.find("h1", class_="event-summary__title")
            event_name = title_elem.get_text(strip=True) if title_elem else ""

            if not event_name:
                return None

            # 簡易的なキーワードチェック
            if not self._matches_startup_weekend_keywords(event_name, "", ""):
                return None

            return {
                "イベント名": event_name,
                "開催日": "",
                "終了日": "",
                "開催場所": "",
                "緯度": "",
                "経度": "",
                "イベントURL": self.clean_url(event_url),
                "住所": "",
                "主催者": "",
                "イベント種類": "本イベント",  # デフォルト値
            }

        except Exception as e:
            print(f"HTMLフォールバック処理エラー: {e}")
            return None

    def collect_peatix_events(self) -> List[Dict]:
        """PeatixからStartup Weekendイベントを収集"""
        peatix_events = []

        try:
            if not self.setup_driver():
                print(
                    "⚠️ Seleniumドライバーの初期化に失敗しました。Peatixのデータ収集をスキップします。"
                )
                return peatix_events

            print("📡 Peatixからイベント情報を取得中...")

            # 検索キーワード
            keywords = ["Startup Weekend", "StartupWeekend"]

            collected_urls = set()

            for keyword in keywords:
                print(f"🔍 キーワード '{keyword}' で検索中...")
                event_urls = self.search_peatix_events(keyword)

                for url in event_urls:
                    if url not in collected_urls:
                        collected_urls.add(url)
                        event_details = self.extract_peatix_event_details(url)
                        if event_details:
                            peatix_events.append(event_details)

            print(f"✅ Peatixから {len(peatix_events)} 件のイベントを取得しました")

        except Exception as e:
            print(f"❌ Peatixからのデータ取得でエラーが発生しました: {e}")
        finally:
            if self.driver:
                self.driver.quit()

        return peatix_events

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

    def save_to_google_sheets(self, events: List[Dict]):
        """Google Sheetsにデータを保存"""
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
            spreadsheet = gc.open_by_key(self.google_sheet_id)
            data_worksheet = spreadsheet.get_worksheet_by_id(
                int(self.google_sheet_data_gid)
            )

            # データを書き込み
            data_worksheet.clear()
            data_worksheet.update([df.columns.values.tolist()] + df.values.tolist())

            # 実行時刻を記録
            last_run_time_jst = self.convert_to_jst(datetime.now().isoformat())
            last_run_time_worksheet = spreadsheet.get_worksheet_by_id(
                int(self.google_sheet_last_run_time_gid)
            )
            last_run_time_worksheet.clear()
            last_run_time_worksheet.update(
                values=[[last_run_time_jst]], range_name="A1"
            )

            print(f"✅ {len(events)} 件のイベント情報をGoogle Sheetsに保存しました")
            print(f"📊 シート ID: {self.google_sheet_id}")

            # 実行時刻についてもログを出す
            print(f"⏱️ 実行完了時間の記録を行いました 実行完了時間: {last_run_time_jst}")
        except Exception as e:
            print(f"❌ Google Sheetsへの保存でエラーが発生しました: {e}")

    def _determine_event_type(self, start_date: str, end_date: str) -> str:
        """開催日時からイベント種類を判定"""
        try:
            if not start_date or not end_date:
                return "本イベント"  # デフォルト

            # 日付部分のみを比較
            start_date_only = start_date[:10]  # YYYY-MM-DD
            end_date_only = end_date[:10]  # YYYY-MM-DD

            if start_date_only == end_date_only:
                return "プレイベント"  # 同日開催
            else:
                return "本イベント"  # 複数日開催
        except Exception:
            return "本イベント"  # エラー時はデフォルト

    def collect_all_events(self):
        """全イベント収集の実行"""
        print("🚀 Startup Weekend イベント収集を開始します")
        print("=" * 50)

        # 1. Doorkeeperからデータ収集
        doorkeeper_events = self.collect_doorkeeper_events()

        # 2. Peatixからデータ収集
        peatix_events = self.collect_peatix_events()

        # 3. データマージ
        if doorkeeper_events or peatix_events:
            merged_events = self.merge_events(doorkeeper_events, peatix_events)

            # 4. Google Sheetsに保存
            self.save_to_google_sheets(merged_events)
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
