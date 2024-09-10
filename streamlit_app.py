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

        # urlパラメーターを取得して、表示種類を選択する
        url_params = st.query_params

        # 選択済みの都道府県を取得
        query_params_prefecture = "全て"
        if "prefecture" in url_params:
            query_params_prefecture = url_params["prefecture"]
        prefectures = data["都道府県"].dropna().unique().tolist()
        selectlist_prefecture: list = ["全て", "未分類"] + prefectures

        # 選択済みのイベント種別を取得
        query_params_event_type = "全て"
        if "event_type" in url_params:
            query_params_event_type = url_params["event_type"]
        event_types = data["イベント種別"].dropna().unique().tolist()
        selectlist_event_type: list = ["全て"] + event_types

        # 横並びにするためのカラムを作成
        col1, col2 = st.columns(2)

        with col1:
            selected_prefecture = st.selectbox(
                "都道府県",
                selectlist_prefecture,
                index=selectlist_prefecture.index(query_params_prefecture)
                if query_params_prefecture in selectlist_prefecture
                else 0,
            )

        with col2:
            selected_event_type = st.selectbox(
                "イベント種別",
                selectlist_event_type,
                index=selectlist_event_type.index(query_params_event_type)
                if query_params_event_type in selectlist_event_type
                else 0,
            )

        # フィルタリングの適用、urlパラメーターも更新
        # 都道府県が選択された場合
        if selected_prefecture == "未分類":
            data = data[data["都道府県"].isnull()]
            st.query_params["prefecture"] = "未分類"
        elif selected_prefecture != "全て":
            data = data[data["都道府県"] == selected_prefecture]
            st.query_params["prefecture"] = selected_prefecture
        else:
            # 都道府県が全ての場合はパラメーターを削除
            if "prefecture" in st.query_params:
                del st.query_params["prefecture"]
        # イベント種別が選択された場合
        if selected_event_type != "全て":
            data = data[data["イベント種別"] == selected_event_type]
            st.query_params["event_type"] = selected_event_type
        else:
            # イベント種別が全ての場合はパラメーターを削除
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

        if last_run_time_path.exists():
            with open(last_run_time_path, "r") as file:
                last_run_time = file.read().strip()
                last_run_time = pd.to_datetime(last_run_time).tz_convert("Asia/Tokyo")
                formatted_last_run_time = last_run_time.strftime("%Y-%m-%d %H:%M")
                st.info(f"最終更新日: **{formatted_last_run_time}**")
        else:
            st.warning("最終更新が確認できませんでした")

        # デフォルトの列インデックスを設定
        lat_column = data.columns[4]  # 緯度列
        lon_column = data.columns[5]  # 経度列
        event_name_column = data.columns[0]  # イベント名列
        start_date_column = data.columns[1]  # 開催日時列
        end_date_column = data.columns[2]  # 終了日時列
        place_column = data.columns[3]  # 開催場所列
        url_column = data.columns[6]  # URL列
        event_type_column = data.columns[9]  # イベント種別列

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

            # 詳細情報を含むカラムを作成
            map_data["info"] = (
                "イベント名: "
                + map_data[event_name_column]
                + "<br>"
                + "イベント種別: "
                + map_data[event_type_column]
                + "<br>"
                + "開催日時: "
                + map_data[start_date_column]
                + " ~ "
                + map_data[end_date_column]
                + "<br>"
                + "開催場所: "
                + map_data[place_column]
                + "<br>"
                + '<a href="'
                + map_data[url_column]
                + '" target="_blank">イベントページ</a>'
                + "<br>"
                + "<a href='https://www.google.com/maps/search/?api=1&query="
                + map_data[lat_column].astype(str)
                + ","
                + map_data[lon_column].astype(str)
                + "' target='_blank'>Googleマップで開く</a>"
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
                    column_config={url_column: st.column_config.LinkColumn()},
                )

            with col2:
                st_folium(m, height=600, use_container_width=True)

    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
else:
    st.error(
        "何らかの問題でCSVファイルが読み込めませんでした。製作者へご連絡いただけましたら助かります🙏"
    )
