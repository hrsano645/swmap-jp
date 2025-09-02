# update_sw_eventlist.pyを実行する。Python3.12でビルドをした上でスクリプトの実行。

# ビルドステージ
FROM python:3.12-bookworm AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt


# 実行ステージ
FROM python:3.12-bookworm

# Google Chrome と関連パッケージのインストール
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    # Google ChromeのGPGキーをダウンロードし、キーリングに追加
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    # Google Chromeのリポジトリを追加（signed-byオプションでキーを指定）
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    # パッケージリストを更新して、Google Chromeをインストール
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    # キャッシュをクリーンアップ
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH

CMD ["python", "update_sw_eventlist.py"]
