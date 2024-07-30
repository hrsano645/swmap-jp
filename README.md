# swmap-jp: Startup Weekend Map in Japan

## これは何？

日本国内のStartup Weekendのイベント情報を地図上に表示するためのアプリケーションです。

## 使い方

以下のURLからアクセスできます。

<!-- [Startup Weekend Map in Japan](https://[pathを載せる]) -->

<!-- <TODO: 2024-07-30 表示されるサイトの画像を入れる> -->

* イベント一覧には、イベント名、開催日時、開催場所、URLが表示されます。
* マップには上記情報が表示され、イベントページのリンクがあります。

## 今後やりたいこと

* 地域選択で絞る機能の実装
* SWのコミュニティ情報も載せる（コミュニティの紹介文とか）

## コントリビュート

* このリポジトリをforkして、プルリクエストを送ってください。

## 開発環境

[Streamlit](https://streamlit.io/)を利用しています。公開先では[stlite](https://share.stlite.net)を利用しています。

Pythonは3.11を推奨です（stliteを利用するため）

### 環境構築

* このリポジトリをクローンします。
* pythonのvenvを作成し、activateします。
* `pip install -r requirements.txt`で必要なライブラリをインストールします。

### イベント情報の更新

`update_sw_eventlist.py`を実行することで、イベント情報を更新できます。

* .envファイルを作成し、以下の環境変数を設定してください。
  * `DOORKEEPER_API_KEY`: Doorkeeper APIを利用する際のAPIキー (必須)
  Doorkeeper APIの取得方法はヘルプを参考にください。<https://www.doorkeeper.jp/developer/api?locale=en>

### アプリケーションの起動

* Streamlit: `streamlit run streamlit_app.py`でアプリケーションを起動します。
* stlite: `python -m http.server` でローカルサーバーを立ち上げ、ブラウザで `http://localhost:8000/` にアクセスすると確認できます。

## ライセンス

[MIT License](./LICENSE)
