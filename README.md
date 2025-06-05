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

## イベント一覧の更新方法

`update_sw_eventlist.py`を実行することで、イベント情報を更新できます。Googleスプレッドシート + Google Sheet APIを利用します。

Dockerfileを元に、コンテナ経由で更新スクリプトを動かすことも可能です。

### Googleスプレッドシートの準備

Googleスプレッドシートの用意を行い、Google_Sheet_IDを取得してください。URLは`https://docs.google.com/spreadsheets/d/[sheet_id]/edit`のようになっています。

次にGoogle Cloud ConsoleでGoogle Sheet APIを有効にしてください。

Google Cloudの認証にはサービスアカウントを作成しjsonファイルを利用してください。`service_account.json`にて保存します。

サービスアカウントのメールアドレスを、Googleスプレッドシートの共有設定で共有します。権限は編集者にしてください。

Googleスプレッドシート内に最低２つのシートを作成してください。シート名は適切なものであれば何でも構いません。

* イベント一覧のシート
* 最終更新日時のシート

それぞれのシートを選択時にURLに記載されるgid=の値をGoogle_Sheet_DATA_GIDとGoogle_Sheet_LAST_RUN_TIME_GIDに設定してください。

例：`https://docs.google.com/spreadsheets/d/[sheet_id]/edit#gid=[gid]`

### 生成されるデータの例

|イベント名|開催日|終了日|開催場所|緯度|経度|イベントURL|住所|主催者|
|---|---|---|---|---|---|---|---|---|
|Startup Weekend 長崎佐世保 vol.6|2025-06-13T18:00:00+09:00|2025-06-15T20:00:00+09:00|大村市 中央公民館|32.900511|129.957181|<https://peatix.com/event/4401622>|大村市幸町２５−３３|Startup Weekend 長崎佐世保|
|Startup Weekend 多摩4th プレイベント 初夏の体験・交流会 |2025-06-21T14:00:00+09:00|2025-06-21T17:00:00+09:00|Musashino Valley|35.703873|139.554209|<https://peatix.com/event/4361784>|三鷹市上連雀１丁目１２−１７ 三鷹ビジネスパーク B1F|Startup Weekend 多摩|
|［第四回］Startup Weekend 高知|2025-06-20T18:30:00+09:00|2025-06-22T20:00:00+09:00|オビヤギルド|33.5606|133.538369|<https://peatix.com/event/4348102>|高知市帯屋町１丁目１４−９|Startup Weekend 高知|
|［初開催］Startup Weekend 青森|2025-07-04T18:00:00+09:00|2025-07-06T19:30:00+09:00|AOMORI STARTUP CENTER|40.826906|140.734931|<https://peatix.com/event/4385826>|青森市新町１丁目２−１８ 青森商工会議所会館1階|Startup Weekend 青森|
|Startup WeekendでChatGPT活用するために［オンライン開催］|2025-07-05T21:00:00+09:00|2025-07-05T22:00:00+09:00||||<https://peatix.com/event/4369983>||Startup Weekend 多摩|
|Startup Weekend 守山 vol.10|2025-06-20T19:00:00+09:00|2025-06-22T19:00:00+09:00|日本、滋賀県守山市勝部１丁目１３−１ あまが池プラザ（守山市中心市街地活性化交流プラザ）(あまが池親水緑地公園)あまがいけ|35.053048|135.991008|<https://peatix.com/event/4370679>|滋賀県守山市勝部１丁目１３−１ |Startup Weekend 守山|
|Startup Weekend 彦根 Vol.3 in 台中科技大学|2025-06-06T17:00:00+09:00|2025-06-08T20:00:00+09:00|国立台中科技大学|24.151197|120.682176|<https://peatix.com/event/4348789>|台湾台中市北区三民路三段129番|Startup Weekend 彦根|

### 環境準備

`.env`ファイルに以下の環境変数を設定してください。

```bash
DOORKEEPER_API_KEY=""
GOOGLE_SHEET_ID=""
GOOGLE_SHEET_DATA_GID=""
GOOGLE_SHEET_LAST_RUN_TIME_GID=""
```

* .envファイルを作成し、以下の環境変数を設定してください。
  * `DOORKEEPER_API_KEY`: Doorkeeper APIを利用する際のAPIキー (必須)
  Doorkeeper APIの取得方法はヘルプを参考にください。<https://www.doorkeeper.jp/developer/api?locale=en>
* Google_Sheet_ID: GoogleスプレッドシートのID (必須)
* Google_Sheet_DATA_GID: イベント一覧のGID (必須)
* Google_Sheet_LAST_RUN_TIME_GID: 最終更新日時のGID (必須)

index.htmlには、scriptタグ（javascript）の中に環境変数と同等の変数が設定されています。こちらの値を環境変数で設定したGOOGHE_SHEETのID,GIDと同等のものを設定してください。

```javascript
// javascript上の変数と環境変数の対応
let sheet_id = '[GOOGLE_SHEET_ID]'
let sheet_data_gid = '[GOOGLE_SHEET_DATA_GID]'
let sheet_last_run_time_gid = '[GOOGLE_SHEET_LAST_RUN_TIME_GID]'
```

## イベント一覧の更新処理

`update_sw_eventlist.py`を実行することで、イベント一覧の更新が行われます。

Dockerfileでも実行可能です。crontabを使いDockerfileで実行する際は、以下のようにしてください。Dockerfileのイメージ名は`swmap-jp-update-eventlist`としていますが自由に変更可能です。

```bash
# crontabに以下を追加
# 毎日午前3時に実行する例
0 3 * * * docker build -t swmap-jp-update-eventlist /[swmap-jpのディレクトリ]/ && docker run --rm swmap-jp-update-eventlist
```

## アプリケーションの起動

* stlite: `python -m http.server` でローカルサーバーを立ち上げ、ブラウザで `http://localhost:8000/` にアクセスすると確認できます。

## ライセンス

[MIT License](./LICENSE)
