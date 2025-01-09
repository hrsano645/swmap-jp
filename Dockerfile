# update_sw_eventlist.pyを実行する。Python3.12でビルドをした上でスクリプトの実行。

# ビルドステージ
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 実行ステージ
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH

CMD ["python", "update_sw_eventlist.py"]
