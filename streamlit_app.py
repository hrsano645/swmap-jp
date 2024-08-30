import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path

st.set_page_config(layout="wide")

st.title("[beta]Startup Weekend Map for Japan")

# サイドバーにアプリの概要を表示
with st.sidebar.expander("このサイトは？", expanded=True):
    st.markdown(
        """
        Startup Weekendのイベント情報と開催地をマップで表示します。

        ソースコードはGitHubにて公開しています。修正提案は歓迎しています。

        → [GitHub](https://github.com/hrsano645/swmap-jp)
        
        ### 注意事項

        * Doorkeeper APIを使い、１日に２回程度情報の更新をします。公開イベントのみを収集しています。
        * Startup Weekend オーガナイザーの個人プロジェクトです。不備がありましたら以下の連絡先までお知らせください。

        ### 作成者

        * Hiroshi Sano: [X](https://x.com/hrs_sano645), [FB](https://www.facebook.com/hrs.sano645)
        """
    )

# CSVファイルのパスを設定
csv_path = Path("./startup_weekend_events.csv")
last_run_time_path = Path("./last_run_time.txt")

if csv_path.exists():
    try:

        @st.cache_data
        def load_data_from_file(path):
            data = pd.read_csv(path)
            return data

        data = load_data_from_file(csv_path)

        # 都道府県のセレクトボックスを追加
        prefectures = data["都道府県"].dropna().unique().tolist()
        selected_prefecture = st.selectbox(
            "都道府県でフィルター", ["全て", "未分類"] + prefectures
        )

        # フィルタリングの適用
        if selected_prefecture == "未分類":
            data = data[data["都道府県"].isnull()]
        elif selected_prefecture != "全て":
            data = data[data["都道府県"] == selected_prefecture]

        # イベントの見つかった件数を表示
        st.info(f"見つかったイベントの件数: **{len(data)}件**")

        if last_run_time_path.exists():
            with open(last_run_time_path, "r") as file:
                last_run_time = file.read().strip()
                last_run_time = pd.to_datetime(last_run_time).tz_convert("Asia/Tokyo")
                formatted_last_run_time = last_run_time.strftime("%Y-%m-%d %H:%M")
                st.info(f"最終更新日: **{formatted_last_run_time}**")
        else:
            st.warning("最終更新が確認できませんでした")

        # デフォルトの列インデックスを設定
        lat_column = data.columns[3]  # 緯度列
        lon_column = data.columns[4]  # 経度列
        event_name_column = data.columns[0]  # イベント名列
        date_column = data.columns[1]  # 開催日時列
        place_column = data.columns[2]  # 開催場所列
        url_column = data.columns[5]  # URL列

        if lat_column and lon_column:
            # イベント一覧用のデータフレーム
            event_data = data.copy()
            # 緯度と経度の列を削除
            event_data = event_data.drop(columns=[lat_column, lon_column])

            # 日時の表示を日本国内向けに変更
            event_data[date_column] = pd.to_datetime(
                event_data[date_column]
            ).dt.tz_convert("Asia/Tokyo")
            event_data[date_column] = event_data[date_column].dt.strftime(
                "%Y-%m-%d %H:%M"
            )

            # マップ用のデータフレーム
            map_data = data.copy()
            # データ前処理
            # Nanを削除: 緯度と経度が欠損している行を削除してマップには出さない
            map_data = map_data.dropna(subset=[lat_column, lon_column])
            # インデックスを文字列に変換
            map_data["index"] = map_data.index.astype(str)
            # 日時の表示を日本国内向けに変更
            map_data[date_column] = pd.to_datetime(map_data[date_column]).dt.tz_convert(
                "Asia/Tokyo"
            )
            map_data[date_column] = map_data[date_column].dt.strftime("%Y-%m-%d %H:%M")

            # 詳細情報を含むカラムを作成
            map_data["info"] = (
                "イベント名: "
                + map_data[event_name_column]
                + "<br>"
                + "開催日時: "
                + map_data[date_column]
                + "<br>"
                + "開催場所: "
                + map_data[place_column]
                + "<br>"
                + '<a href="'
                + map_data[url_column]
                + '" target="_blank">イベントページ</a>'
            )

            # Foliumマップを作成
            m = folium.Map(
                location=[map_data[lat_column].mean(), map_data[lon_column].mean()],
                zoom_start=5,
            )

            for i, row in map_data.iterrows():
                folium.Marker(
                    location=[row[lat_column], row[lon_column]],
                    popup=folium.Popup(row["info"], max_width=600),
                    icon=folium.Icon(color="gray", icon="info-sign"),
                ).add_to(m)

            # 横並びにするためのカラムを作成
            col1, col2 = st.columns([1, 1])

            with col1:
                st.dataframe(
                    event_data,
                    use_container_width=True,
                    hide_index=True,
                )

            with col2:
                st_folium(m, height=600, use_container_width=True)

    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
else:
    st.error(
        "何らかの問題でCSVファイルが読み込めませんでした。製作者へご連絡いただけましたら助かります🙏"
    )
