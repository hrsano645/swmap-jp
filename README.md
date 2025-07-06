# swmap-jp: Startup Weekend Map in Japan

## これは何？

日本国内のStartup Weekendのイベント情報を地図上に表示するためのアプリケーションです。

## 使い方

以下のURLからアクセスできます。

[Startup Weekend Map in Japan](https://hrsano645.github.io/swmap-jp/)

![swmap-jp screenshot](./app_screenshot.png)

* イベント一覧には、イベント名、開催日時、開催場所、主催者、URLが表示されます。
* マップには上記情報が表示され、イベントページのリンクやGoogleマップへのリンクがあります。
* 主催者や開催形式（オンライン/物理開催）でフィルタリングできます。

## 今後やりたいこと

* SWのコミュニティ情報も載せる（コミュニティの紹介文とか）

## コントリビュート

* issueから問題などお知らせください。
* このリポジトリをforkして、プルリクエストを送ってください。

## 開発環境

[Streamlit](https://streamlit.io/)を利用しています。公開先では[stlite](https://edit.share.stlite.net)を利用しています。

Pythonは3.11を推奨です（stliteを利用するため）

### 環境構築

* このリポジトリをクローンします。
* pythonのvenvを作成し、activateします。
* `pip install -r requirements.txt`で必要なライブラリをインストールします。

## セットアップ方法

### 1. アプリケーションの表示設定

本アプリケーションは`stlite`を用いて、`index.html`から直接Streamlitアプリケーションを読み込んで表示します。

イベント情報が格納された公開Googleスプレッドシートの情報を`index.html`に設定する必要があります。

`index.html`を開き、以下の変数をあなたのGoogleスプレッドシートの情報に書き換えてください。

```javascript
// index.html内の<script>タグにあります
let sheet_id = '[YOUR_GOOGLE_SHEET_ID]'
let sheet_data_gid = '[YOUR_SHEET_DATA_GID]'
let sheet_last_run_time_gid = '[YOUR_SHEET_LAST_RUN_TIME_GID]'
```

設定後、ローカルサーバを起動して表示を確認できます。

```bash
python -m http.server
```

`http://localhost:8000` にアクセスしてください。

### 2. イベント一覧の更新スクリプト設定

イベント一覧は`update_sw_eventlist.py`スクリプトを実行して更新します。このスクリプトは、DoorkeeperやPeatixからイベント情報を収集し、指定のGoogleスプレッドシートに保存します。

#### GoogleスプレッドシートとAPIの準備

1. **Googleスプレッドシートの用意**:
    * イベント一覧を保存するシートと、スクリプトの最終更新日時を記録するシートの2つを作成します。
    * スプレッドシートのURLから`[sheet_id]`を、各シートのURLから`[gid]`を取得します。
        * `https://docs.google.com/spreadsheets/d/[sheet_id]/edit#gid=[gid]`

2. **Google Cloudの設定**:
    * Google Cloud ConsoleでGoogle Sheets APIを有効にします。
    * サービスアカウントを作成し、認証用のJSONキーファイルをダウンロードして`service_account.json`としてプロジェクトルートに配置します。
    * サービスアカウントのメールアドレスを、書き込み権限（編集者）でGoogleスプレッドシートに共有します。

#### 環境変数の設定

プロジェクトルートに`.env`ファイルを作成し、以下の情報を設定します。

```bash
# Doorkeeper APIキー (任意)
DOORKEEPER_API_KEY="your_doorkeeper_api_key"

# Googleスプレッドシート情報 (必須)
GOOGLE_SHEET_ID="your_google_sheet_id"
GOOGLE_SHEET_DATA_GID="your_sheet_data_gid"
GOOGLE_SHEET_LAST_RUN_TIME_GID="your_sheet_last_run_time_gid"
```

設定完了後、以下のコマンドでイベント一覧を更新できます。

```bash
python update_sw_eventlist.py
```

## イベント一覧の自動更新 (Docker利用)

Dockerfileを利用して、イベント更新処理を定期的に自動実行できます。

1. **Dockerイメージのビルド**

    ```bash
    docker build -t swmap-jp-update-eventlist .
    ```

2. **crontabでの定期実行**
    `crontab -e`でcronジョブを編集し、以下の行を追加します。
    (以下の例は、毎日午前3時に更新スクリ-プトを実行します)

    ```bash
    0 3 * * * docker run --rm --env-file /[path_to_your_project]/.env swmap-jp-update-eventlist
    ```

    **Note:** `[path_to_your_project]`は、このプロジェクトの絶対パスに書き換えてください。

## ライセンス

[MIT License](./LICENSE)
