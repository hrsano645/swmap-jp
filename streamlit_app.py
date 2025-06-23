import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path
from urllib.parse import quote, urlencode
from datetime import datetime, timezone
import uuid
import base64
import re


# CSVファイルのパスを設定
csv_path = Path("./startup_weekend_events.csv")
last_run_time_path = Path("./last_run_time.txt")


def generate_google_calendar_url(event_name, start_date, end_date, location, description, event_url):
    """Google Calendarに追加するためのURLを生成"""
    try:
        # 日付文字列をdatetimeオブジェクトに変換
        start_dt = pd.to_datetime(start_date).strftime('%Y%m%dT%H%M%S')
        end_dt = pd.to_datetime(end_date).strftime('%Y%m%dT%H%M%S')
        
        # イベント詳細を作成
        details = f"{description}\n\nイベントページ: {event_url}"
        
        # Google CalendarのURL生成
        params = {
            'action': 'TEMPLATE',
            'text': event_name,
            'dates': f"{start_dt}/{end_dt}",
            'location': location,
            'details': details
        }
        
        base_url = "https://calendar.google.com/calendar/render?"
        return base_url + urlencode(params)
    except Exception as e:
        st.error(f"Google Calendar URL生成エラー: {e}")
        return None


def generate_ical_content(event_name, start_date, end_date, location, description, event_url):
    """iCal形式のコンテンツを生成"""
    try:
        # 日付文字列をdatetimeオブジェクトに変換（UTC）
        start_dt = pd.to_datetime(start_date).strftime('%Y%m%dT%H%M%SZ')
        end_dt = pd.to_datetime(end_date).strftime('%Y%m%dT%H%M%SZ')
        
        # ユニークなUID生成
        event_uid = str(uuid.uuid4())
        
        # 現在時刻（作成日時）
        now = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        
        # iCalコンテンツ生成
        ical_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Startup Weekend Map Japan//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{event_uid}@swmap-jp.com
DTSTART:{start_dt}
DTEND:{end_dt}
DTSTAMP:{now}
CREATED:{now}
LAST-MODIFIED:{now}
SUMMARY:{event_name}
LOCATION:{location}
DESCRIPTION:{description}\\n\\nイベントページ: {event_url}
URL:{event_url}
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""
        
        return ical_content
    except Exception as e:
        st.error(f"iCal生成エラー: {e}")
        return None


def extract_event_id_from_url(event_url):
    """URLからイベントIDとプラットフォームを抽出"""
    try:
        # Peatixのパターン: https://peatix.com/event/12345678
        peatix_match = re.search(r'peatix\.com/event/(\d+)', event_url)
        if peatix_match:
            return 'peatix', peatix_match.group(1)
        
        # Doorkeeperのパターン: https://doorkeeper.jp/events/abcd1234
        doorkeeper_match = re.search(r'doorkeeper\.jp/events/([a-zA-Z0-9]+)', event_url)
        if doorkeeper_match:
            return 'doorkeeper', doorkeeper_match.group(1)
        
        # その他のURLの場合はNoneを返す
        return None, None
    except Exception:
        return None, None


def generate_ical_filename(start_date, end_date, event_url):
    """iCalファイル名を生成"""
    try:
        # 開始日をフォーマット
        start_dt = pd.to_datetime(start_date).strftime('%Y%m%d%H%M')
        
        # URLからイベントIDを抽出
        platform, event_id = extract_event_id_from_url(event_url)
        
        if platform and event_id:
            # プラットフォーム+ID形式
            filename = f"swevent_{start_dt}_{platform}_{event_id}.ics"
        else:
            # フォールバック: 開始日+終了日形式
            end_dt = pd.to_datetime(end_date).strftime('%Y%m%d%H%M')
            filename = f"swevent_{start_dt}_{end_dt}.ics"
        
        return filename
    except Exception:
        # エラー時のフォールバック
        return f"swevent_{datetime.now().strftime('%Y%m%d%H%M')}.ics"


def generate_ical_download_link(event_name, start_date, end_date, location, description, event_url):
    """iCalファイルのdata URIダウンロードリンクを生成"""
    try:
        ical_content = generate_ical_content(event_name, start_date, end_date, location, description, event_url)
        if ical_content:
            # Base64エンコード
            b64_ical = base64.b64encode(ical_content.encode('utf-8')).decode('utf-8')
            # ファイル名を生成
            filename = generate_ical_filename(start_date, end_date, event_url)
            # data URIを生成
            data_uri = f"data:text/calendar;base64,{b64_ical}"
            return data_uri, filename
        return None, None
    except Exception as e:
        st.error(f"iCalリンク生成エラー: {e}")
        return None, None

st.set_page_config(
    layout="wide",
    page_title="Startup Weekend Map for Japan",
)

st.markdown(
    "<h3 style='text-align: center;'>Startup Weekend Map for Japan</h3>",
    unsafe_allow_html=True,
)

# サイドバーにアプリの概要を表示
with st.sidebar:
    with st.expander("このサイトは？", expanded=True):
        st.markdown(
            """
            Startup Weekendのイベント情報と開催地をマップで表示します。ただいまベータバージョンとして公開中です。
            
            ### 注意事項

            * Peatixのイベント情報を収集し、一覧を作成しています。一部Doorkeeperでの公開イベントも収集しています。
            * このサービスはStartup Weekend オーガナイザーの個人プロジェクトです。不備などがありましたら以下の連絡先までお知らせください。
            * ソースコードはGitHubにて公開しています。修正提案は歓迎しています。issueからお気軽にお知らせください。→ [GitHub](https://github.com/hrsano645/swmap-jp)

            ### 作成者

            * Hiroshi Sano: [X](https://x.com/hrs_sano645), [FB](https://www.facebook.com/hrs.sano645)
            """
        )

    if last_run_time_path.exists():
        with open(last_run_time_path, "r") as file:
            last_run_time = file.read().strip()
            last_run_time = pd.to_datetime(last_run_time).tz_convert("Asia/Tokyo")
            formatted_last_run_time = last_run_time.strftime("%Y-%m-%d %H:%M")
            st.info(f"最終更新日: **{formatted_last_run_time}**")
    else:
        st.warning("最終更新が確認できませんでした")

if csv_path.exists():
    try:

        @st.cache_data
        def load_data_from_file(path):
            data = pd.read_csv(path)
            return data

        data = load_data_from_file(csv_path)

        # urlパラメーターを取得して、表示種類を選択する
        url_params = st.query_params

        # 選択済みの主催者を取得
        query_params_organizer = "全て"
        if "organizer" in url_params:
            query_params_organizer = url_params["organizer"]
        organizers = data["主催者"].dropna().unique().tolist()
        selectlist_organizer: list = ["全て"] + organizers

        # 選択済みのイベント種類を取得
        query_params_event_type = "全て"
        if "event_type" in url_params:
            query_params_event_type = url_params["event_type"]
        selectlist_event_type: list = ["全て", "本イベント", "その他"]

        # 横並びにするためのカラムを作成
        col1, col2 = st.columns(2)

        with col1:
            selected_organizer = st.selectbox(
                "主催者",
                selectlist_organizer,
                index=selectlist_organizer.index(query_params_organizer)
                if query_params_organizer in selectlist_organizer
                else 0,
            )

        with col2:
            selected_event_type = st.selectbox(
                "イベント種類",
                selectlist_event_type,
                index=selectlist_event_type.index(query_params_event_type)
                if query_params_event_type in selectlist_event_type
                else 0,
            )

        # フィルタリングの適用、urlパラメーターも更新
        # 主催者が選択された場合
        if selected_organizer != "全て":
            data = data[data["主催者"] == selected_organizer]
            st.query_params["organizer"] = selected_organizer
        else:
            # 主催者が全ての場合はパラメーターを削除
            if "organizer" in st.query_params:
                del st.query_params["organizer"]

        # イベント種類が選択された場合
        if selected_event_type == "本イベント":
            # イベント種類が本イベントの場合
            data = data[data["イベント種類"] == "本イベント"]
            st.query_params["event_type"] = "本イベント"
        elif selected_event_type == "その他":
            # イベント種類がその他の場合
            data = data[data["イベント種類"] == "その他"]
            st.query_params["event_type"] = "その他"
        else:
            # イベント種類が全ての場合はパラメーターを削除
            if "event_type" in st.query_params:
                del st.query_params["event_type"]

        # イベントの数が0の場合はメッセージを表示
        if len(data) == 0:
            st.warning(
                "該当するイベントが見つかりませんでした。条件を変更してください。"
            )
            st.stop()

        # イベントの見つかった件数を表示
        st.info(f"見つかったイベントの件数: **{len(data)}件**")

        # デフォルトの列インデックスを設定
        lat_column = data.columns[4]  # 緯度列
        lon_column = data.columns[5]  # 経度列
        event_name_column = data.columns[0]  # イベント名列
        start_date_column = data.columns[1]  # 開催日時列
        end_date_column = data.columns[2]  # 終了日時列
        place_column = data.columns[3]  # 開催場所列
        url_column = data.columns[6]  # URL列
        address_column = data.columns[7]  # 住所列
        organizer_column = data.columns[8]  # 主催者列
        event_type_column = data.columns[9]  # イベント種類列

        # 日付列を日本向け表記変換
        data[start_date_column] = pd.to_datetime(data[start_date_column]).dt.tz_convert(
            "Asia/Tokyo"
        )
        data[start_date_column] = data[start_date_column].dt.strftime("%Y-%m-%d %H:%M")
        data[end_date_column] = pd.to_datetime(data[end_date_column]).dt.tz_convert(
            "Asia/Tokyo"
        )
        data[end_date_column] = data[end_date_column].dt.strftime("%Y-%m-%d %H:%M")

        if lat_column and lon_column:
            # イベント一覧用のデータフレーム
            event_data = data.copy()
            # 緯度と経度の列を削除
            event_data = event_data.drop(columns=[lat_column, lon_column])

            # マップ用のデータフレーム
            map_data = data.copy()
            # データ前処理
            # Nanを削除: 緯度と経度が欠損している行を削除してマップには出さない
            map_data = map_data.dropna(subset=[lat_column, lon_column])
            # インデックスを文字列に変換
            map_data["index"] = map_data.index.astype(str)

            # 同一地点のイベントをグループ化
            def group_events_by_location(df):
                """緯度・経度でイベントをグループ化"""
                grouped = df.groupby([lat_column, lon_column])
                location_groups = []
                
                for (lat, lon), group in grouped:
                    events = []
                    for _, row in group.iterrows():
                        events.append({
                            'name': row[event_name_column],
                            'organizer': row[organizer_column],
                            'start_date': row[start_date_column],
                            'end_date': row[end_date_column],
                            'place': row[place_column],
                            'url': row[url_column],
                            'event_type': row[event_type_column]
                        })
                    
                    location_groups.append({
                        'lat': lat,
                        'lon': lon,
                        'events': events,
                        'count': len(events)
                    })
                
                return location_groups
            
            location_groups = group_events_by_location(map_data)
            
            def create_popup_html(events, lat, lon):
                """装飾されたポップアップHTMLを生成"""
                
                # CSSスタイル定義
                css_style = """
                <style>
                .popup-container {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    max-width: 400px;
                    margin: 0;
                    padding: 0;
                }
                .popup-header {
                    background: #f8f9fa;
                    color: #495057;
                    padding: 12px 16px;
                    border-radius: 8px 8px 0 0;
                    font-weight: bold;
                    font-size: 14px;
                    text-align: center;
                    border-bottom: 1px solid #dee2e6;
                }
                .event-item {
                    background: #fafafa;
                    border: 1px solid #e1e5e9;
                    margin: 8px 0;
                    border-radius: 8px;
                    overflow: hidden;
                }
                .event-item.main-event {
                    border-left: 4px solid #dc3545;
                }
                .event-item.other-event {
                    border-left: 4px solid #28a745;
                }
                .event-content {
                    padding: 12px 16px;
                }
                .event-title {
                    font-size: 15px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 8px;
                    line-height: 1.3;
                }
                .event-detail {
                    font-size: 12px;
                    color: #5a6c7d;
                    margin: 4px 0;
                    display: flex;
                    align-items: center;
                }
                .event-icon {
                    margin-right: 6px;
                    font-size: 12px;
                    width: 14px;
                    text-align: center;
                }
                .event-links {
                    margin-top: 10px;
                    padding-top: 8px;
                    border-top: 1px solid #f0f2f5;
                }
                .event-link {
                    display: inline-block;
                    background: #f8f9fa;
                    color: #495057;
                    padding: 4px 8px;
                    border-radius: 12px;
                    text-decoration: none;
                    font-size: 11px;
                    margin: 2px 4px 2px 0;
                    border: 1px solid #dee2e6;
                    transition: all 0.2s ease;
                }
                .event-link:hover {
                    background: #e9ecef;
                    text-decoration: none;
                    color: #495057;
                }
                .map-link {
                    background: #e2e3e5;
                    border-color: #ced4da;
                    color: #6c757d;
                }
                .map-link:hover {
                    background: #d1ecf1;
                    color: #0c5460;
                }
                .popup-footer {
                    background: #f8f9fa;
                    padding: 8px 16px;
                    border-radius: 0 0 8px 8px;
                    border-top: 1px solid #e9ecef;
                    text-align: center;
                }
                </style>
                """
                
                # ヘッダー部分
                event_count_text = f"{len(events)}件のイベント" if len(events) > 1 else "1件のイベント"
                html_content = f"""
                {css_style}
                <div class="popup-container">
                    <div class="popup-header">
                        📍 {event_count_text}
                    </div>
                """
                
                # 各イベントの情報を追加
                for event in events:
                    event_class = "main-event" if event['event_type'] == "本イベント" else "other-event"
                    
                    html_content += f"""
                    <div class="event-item {event_class}">
                        <div class="event-content">
                            <div class="event-title">{event['name']}</div>
                            <div class="event-detail">
                                <span class="event-icon">👥</span>
                                {event['organizer']}
                            </div>
                            <div class="event-detail">
                                <span class="event-icon">📅</span>
                                {event['start_date']}
                            </div>
                            <div class="event-detail">
                                <span class="event-icon">📍</span>
                                {event['place']}
                            </div>
                            <div class="event-links">
                                <a href="{event['url']}" target="_blank" class="event-link">📝 詳細</a>
                            </div>
                        </div>
                    </div>
                    """
                
                # フッター部分
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                html_content += f"""
                    <div class="popup-footer">
                        <a href="{google_maps_url}" target="_blank" class="event-link map-link">🗺️ Googleマップで開く</a>
                    </div>
                </div>
                """
                
                return html_content

            # Foliumマップを作成
            m = folium.Map(
                location=[map_data[lat_column].mean(), map_data[lon_column].mean()],
                zoom_start=5,
            )

            # 新しいグループベースのマーカー生成
            for location_group in location_groups:
                lat = location_group['lat']
                lon = location_group['lon']
                events = location_group['events']
                count = location_group['count']
                
                # ポップアップHTMLを生成
                popup_html = create_popup_html(events, lat, lon)
                
                # マーカーのアイコンを決定（複数イベントの場合は数字付き）
                if count > 1:
                    # 複数イベントの場合
                    icon_color = "blue"
                    icon_symbol = "info-sign"
                    # 複数イベント用のアイコン（数字付き）
                    icon = folium.Icon(
                        color=icon_color, 
                        icon=icon_symbol,
                        prefix='fa'
                    )
                else:
                    # 単一イベントの場合
                    event_type = events[0]['event_type']
                    if event_type == "本イベント":
                        icon_color = "red"
                    else:
                        icon_color = "green"
                    icon = folium.Icon(color=icon_color, icon="info-sign")
                
                # マーカーを地図に追加
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=450),
                    icon=icon,
                    tooltip=f"{count}件のStartup Weekend イベント" if count > 1 else events[0]['name'][:30] + "..."
                ).add_to(m)

            # タブを作成
            tab1, tab2, tab3 = st.tabs(["マップ", "リスト", "データ"])

            with tab1:
                st_folium(m, height=600, use_container_width=True)

            with tab2:
                # カードリスト表示
                # カード用のCSS
                st.markdown(
                    """
                <style>
                .event-card {
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    border-radius: 15px;
                    padding: 20px;
                    margin: 10px 0;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    border-left: 5px solid #4CAF50;
                    transition: transform 0.2s ease;
                }
                .event-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.15);
                }
                .event-card.main-event {
                    border-left-color: #FF6B6B;
                    background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%);
                }
                .event-card.other-event {
                    border-left-color: #4ECDC4;
                    background: linear-gradient(135deg, #f0fdfc 0%, #e0f7f5 100%);
                }
                .event-title {
                    font-size: 18px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 10px;
                    line-height: 1.3;
                }
                .event-info {
                    color: #34495e;
                    font-size: 14px;
                    margin: 5px 0;
                    display: flex;
                    align-items: center;
                }
                .event-icon {
                    margin-right: 8px;
                    font-size: 16px;
                }
                .event-link {
                    background-color: #e3f2fd;
                    color: #333;
                    padding: 8px 16px;
                    border-radius: 20px;
                    text-decoration: none;
                    font-size: 12px;
                    display: inline-block;
                    margin: 5px 5px 0 0;
                    transition: background-color 0.2s;
                    border: 1px solid #90caf9;
                }
                .event-link:hover {
                    background-color: #bbdefb;
                    color: #333;
                    text-decoration: none;
                }
                .map-link {
                    background-color: #ffebee;
                    border: 1px solid #ef9a9a;
                }
                .map-link:hover {
                    background-color: #ffcdd2;
                }
                .calendar-dropdown {
                    position: relative;
                    display: inline-block;
                }
                .calendar-button {
                    background-color: #f3e5f5;
                    color: #333;
                    padding: 8px 16px;
                    border-radius: 20px;
                    text-decoration: none;
                    font-size: 12px;
                    display: inline-block;
                    margin: 5px 5px 0 0;
                    transition: background-color 0.2s;
                    border: 1px solid #ce93d8;
                    cursor: pointer;
                }
                .calendar-button:hover {
                    background-color: #e1bee7;
                    color: #333;
                    text-decoration: none;
                }
                .calendar-dropdown-content {
                    display: none;
                    position: absolute;
                    background-color: white;
                    min-width: 200px;
                    box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
                    z-index: 1;
                    border-radius: 8px;
                    padding: 8px 0;
                    top: 100%;
                    left: 0;
                }
                .calendar-dropdown:hover .calendar-dropdown-content {
                    display: block;
                }
                .calendar-option {
                    color: #333;
                    padding: 8px 16px;
                    text-decoration: none;
                    display: block;
                    font-size: 12px;
                    transition: background-color 0.2s;
                }
                .calendar-option:hover {
                    background-color: #f5f5f5;
                    text-decoration: none;
                    color: #333;
                }
                </style>
                """,
                    unsafe_allow_html=True,
                )

                # カード表示用のデータ準備
                card_data = data.copy()

                # 列数を設定（画面幅に応じて調整）
                cols = st.columns(2)

                for idx, (_, row) in enumerate(card_data.iterrows()):
                    col_idx = idx % 2

                    # イベント種類による色分け
                    card_class = (
                        "main-event"
                        if row[event_type_column] == "本イベント"
                        else "other-event"
                    )

                    # Googleマップリンクの作成
                    if pd.notna(row[lat_column]) and pd.notna(row[lon_column]):
                        map_link = f"https://www.google.com/maps/search/?api=1&query={row[lat_column]},{row[lon_column]}"
                    else:
                        map_link = f"https://www.google.com/maps/search/?api=1&query={row[address_column]}"

                    with cols[col_idx]:
                        # カレンダー用のURLとコンテンツ生成
                        google_calendar_url = generate_google_calendar_url(
                            row[event_name_column],
                            row[start_date_column],
                            row[end_date_column],
                            row[place_column],
                            f"主催者: {row[organizer_column]}",
                            row[url_column]
                        )
                        ical_data_uri, ical_filename = generate_ical_download_link(
                            row[event_name_column],
                            row[start_date_column],
                            row[end_date_column],
                            row[place_column],
                            f"主催者: {row[organizer_column]}",
                            row[url_column]
                        )
                        
                        # カレンダーリンクのHTML生成
                        calendar_links = ""
                        if google_calendar_url:
                            calendar_links += f'<a href="{google_calendar_url}" target="_blank" class="event-link" style="background-color: #e3f2fd; border: 1px solid #90caf9; color: #333;">📅 Google Calendar</a>'
                        if ical_data_uri and ical_filename:
                            calendar_links += f'<a href="{ical_data_uri}" download="{ical_filename}" class="event-link" style="background-color: #f3e5f5; border: 1px solid #ce93d8; color: #333;">📅 iCal</a>'
                        
                        # カードのHTMLコンテンツ
                        st.markdown(
                            f"""
                        <div class="event-card {card_class}">
                            <div class="event-title">{row[event_name_column]}</div>
                            <div class="event-info">
                                <span class="event-icon">📅</span>
                                {row[start_date_column]}
                            </div>
                            <div class="event-info">
                                <span class="event-icon">📍</span>
                                {row[place_column]}
                            </div>
                            <div class="event-info">
                                <span class="event-icon">🏠</span>
                                {row[address_column]}
                            </div>
                            <div style="margin-top: 15px;">
                                <a href="{row[url_column]}" target="_blank" class="event-link">イベント詳細</a>
                                <a href="{map_link}" target="_blank" class="event-link map-link">地図で見る</a>
                                {calendar_links}
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

            with tab3:
                st.info(
                    """イベントの詳細情報を表形式で表示します。URLをクリックすると、イベントページへ移動します。  
                    表を選択中、右上にCSVファイルのダウンロードボタンが現れます。データとして利用したい場合にご利用ください"""
                )
                st.dataframe(
                    event_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={url_column: st.column_config.LinkColumn()},
                )

    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
else:
    st.error(
        "何らかの問題でCSVファイルが読み込めませんでした。製作者へご連絡いただけましたら助かります🙏"
    )
