"""
Peatixイベント収集クラス
PeatixからStartup Weekendイベント情報をスクレイピング
"""

import re
import time
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
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

from .base_collector import BaseCollector
from .config import Config


class PeatixCollector(BaseCollector):
    """Peatixイベント収集クラス"""

    def __init__(self, config: Config):
        super().__init__(config)
        self.driver = None

    def collect_events(self) -> List[Dict]:
        """PeatixからStartup Weekendイベントを収集"""
        peatix_events = []

        try:
            if not self.setup_driver():
                print(
                    "⚠️ Seleniumドライバーの初期化に失敗しました。Peatixのデータ収集をスキップします。"
                )
                return peatix_events

            print("📡 Peatixからイベント情報を取得中...")

            collected_urls = set()

            for keyword in self.config.peatix_search_keywords:
                print(f"🔍 キーワード '{keyword}' で検索中...")
                event_urls = self.search_events(keyword)

                for url in event_urls:
                    if url not in collected_urls:
                        collected_urls.add(url)
                        event_details = self.extract_event_details(url)
                        if event_details:
                            peatix_events.append(event_details)

            print(f"✅ Peatixから {len(peatix_events)} 件のイベントを取得しました")

        except Exception as e:
            print(f"❌ Peatixからのデータ取得でエラーが発生しました: {e}")
        finally:
            if self.driver:
                self.driver.quit()

        return peatix_events

    def setup_driver(self) -> bool:
        """Seleniumドライバーの設定"""
        try:
            options = Options()
            for option in self.config.chrome_options:
                options.add_argument(option)

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

    def search_events(self, keyword: str) -> List[str]:
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

    def extract_event_details(self, event_url: str) -> Optional[Dict]:
        """PeatixイベントページからJSONデータを抽出"""
        try:
            print(f"📄 詳細取得中: {event_url}")
            self.driver.get(event_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

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