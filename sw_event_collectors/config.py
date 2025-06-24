"""
設定管理クラス
環境変数の読み込みと検証を行う
"""

import os
from dotenv import load_dotenv


class Config:
    """アプリケーション設定管理クラス"""

    def __init__(self):
        load_dotenv()
        self._load_environment_variables()

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

    @property
    def has_doorkeeper_api_key(self) -> bool:
        """Doorkeeper API KEYが設定されているかチェック"""
        return bool(self.doorkeeper_api_key)

    @property
    def startup_weekend_keywords(self) -> list[str]:
        """Startup Weekendキーワードリスト"""
        return [
            "startup weekend",
            "startupweekend",
        ]

    @property
    def peatix_search_keywords(self) -> list[str]:
        """Peatix検索キーワードリスト"""
        return ["Startup Weekend", "StartupWeekend"]

    @property
    def chrome_options(self) -> list[str]:
        """Chrome WebDriverオプション"""
        return [
            "--headless",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        ]