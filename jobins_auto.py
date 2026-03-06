"""
JoBins（ジョビンズ）自動化スクリプト
自宅Windows PCで実行 - 全レイヤーで本物のWindows Chromeとして動作

アーキテクチャ:
  VPS(律) → Tailscale SSH → 自宅PC → Patchright(本物Windows Chrome) → JoBins
  全TCP/IP, TLS, Canvas, WebGL, フォントが本物のWindowsとして動作

使い方:
  1. 初回: python jobins_auto.py --login
     → ブラウザが開くので手動でログイン → Cookieが保存される
  2. 手動実行: python jobins_auto.py
     → 新着応募を確認・一覧表示
  3. API経由（VPSから制御）: python jobins_auto.py --server
     → HTTPサーバーが起動し、VPSからAPI経由で操作可能
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from patchright.sync_api import sync_playwright

# === 設定 ===
JOBINS_URL = "https://jobins.jp"
DATA_DIR = Path(__file__).parent / "jobins_data"
COOKIE_FILE = DATA_DIR / "cookies.json"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
LOG_FILE = DATA_DIR / "jobins.log"
RESULT_FILE = DATA_DIR / "latest_result.json"
HEADLESS = False  # False = ヘッドフルモード（検出されにくい）

# データディレクトリ作成
DATA_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("jobins")


# === ユーティリティ ===


def human_delay(min_sec=1.5, max_sec=4.0):
    """人間的なランダム待機"""
    time.sleep(random.uniform(min_sec, max_sec))


def human_type(page, selector, text):
    """人間的なタイピング速度で入力"""
    page.click(selector)
    human_delay(0.3, 0.7)
    for char in text:
        page.keyboard.type(char, delay=random.randint(50, 150))
        if random.random() < 0.1:
            time.sleep(random.uniform(0.2, 0.5))


def human_scroll(page, direction="down", amount=None):
    """人間的なスクロール"""
    if amount is None:
        amount = random.randint(200, 600)
    if direction == "down":
        page.mouse.wheel(0, amount)
    else:
        page.mouse.wheel(0, -amount)
    human_delay(0.5, 1.5)


def save_cookies(context):
    """Cookieをファイルに保存"""
    cookies = context.cookies()
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)
    log.info(f"Cookies保存: {COOKIE_FILE}")


def load_cookies(context):
    """保存されたCookieを読み込み"""
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        log.info(f"Cookies読込: {COOKIE_FILE}")
        return True
    return False


def save_result(result):
    """結果をJSONファイルに保存（VPSから読み取り用）"""
    result["timestamp"] = datetime.now().isoformat()
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    log.info(f"結果保存: {RESULT_FILE}")


def take_screenshot(page, name="page"):
    """スクリーンショットを保存"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOT_DIR / f"{name}_{ts}.png"
    page.screenshot(path=str(path))
    log.info(f"スクリーンショット: {path}")
    return str(path)


# === ブラウザ管理 ===


def create_browser(playwright):
    """本物のWindows Chromeとして起動（検出対策済み）"""
    browser = playwright.chromium.launch(
        headless=HEADLESS,
        channel="chrome",  # 本物のGoogle Chromeを使用（Chromiumではなく）
        args=[
            "--disable-blink-features=AutomationControlled",
            "--lang=ja-JP",
            "--disable-features=IsolateOrigins,site-per-process",
            # WebRTCリーク防止
            "--disable-webrtc",
            "--enforce-webrtc-ip-permission-check",
            "--webrtc-ip-handling-policy=disable_non_proxied_udp",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="ja-JP",
        timezone_id="Asia/Tokyo",
        # User-Agentは設定しない → 本物のChromeのUAがそのまま使われる
        # これにより UA/TLS/Canvas の全フィンガープリントが自然に一致する
        color_scheme="light",
        java_script_enabled=True,
        has_touch=False,
        is_mobile=False,
    )

    # WebRTCを完全無効化（IPリーク防止）
    context.add_init_script("""
        // WebRTC IPリーク防止
        if (window.RTCPeerConnection) {
            window.RTCPeerConnection = class extends window.RTCPeerConnection {
                constructor(config) {
                    if (config && config.iceServers) {
                        config.iceServers = [];
                    }
                    super(config);
                }
            };
        }

        // Notification API（ボット検出に使われることがある）
        if (Notification.permission === 'default') {
            Object.defineProperty(Notification, 'permission', {
                get: () => 'default'
            });
        }
    """)

    return browser, context


# === メイン機能 ===


def manual_login():
    """手動ログインモード - Cookieを保存"""
    log.info("=== 手動ログインモード ===")
    log.info("ブラウザが開きます。手動でログインしてください。")

    with sync_playwright() as p:
        browser, context = create_browser(p)
        page = context.new_page()

        page.goto(JOBINS_URL, wait_until="networkidle")
        human_delay(2, 3)

        input("\n>>> ログインが完了したらEnterキーを押してください... ")

        save_cookies(context)
        take_screenshot(page, "after_login")
        log.info("ログイン情報を保存しました。")

        browser.close()


def check_applications(page):
    """新着応募を確認して結果を返す"""
    log.info("=== 新着応募を確認中 ===")

    # まずダッシュボードの情報を取得
    human_delay(1, 2)
    take_screenshot(page, "dashboard")

    # ページのテキストコンテンツを取得
    page_text = page.inner_text("body")
    page_title = page.title()
    current_url = page.url

    log.info(f"ページタイトル: {page_title}")
    log.info(f"URL: {current_url}")

    # 応募関連のリンクやボタンを探す
    application_links = page.query_selector_all(
        'a[href*="application"], a[href*="entry"], a[href*="offer"], '
        'a[href*="message"], a[href*="scout"]'
    )

    links_info = []
    for link in application_links:
        text = link.inner_text().strip()
        href = link.get_attribute("href") or ""
        if text:
            links_info.append({"text": text, "href": href})

    # 通知バッジや未読カウントを探す
    badges = page.query_selector_all(
        '.badge, .notification, .count, [class*="unread"], [class*="new"]'
    )
    badge_texts = []
    for badge in badges:
        text = badge.inner_text().strip()
        if text:
            badge_texts.append(text)

    result = {
        "status": "success",
        "page_title": page_title,
        "url": current_url,
        "links_found": links_info,
        "badges": badge_texts,
        "page_text_preview": page_text[:2000],
    }

    # 応募一覧ページに移動を試みる
    for link in application_links:
        href = link.get_attribute("href") or ""
        text = link.inner_text().strip()
        if any(kw in text for kw in ["応募", "エントリー", "新着", "未対応"]):
            log.info(f"応募関連ページに移動: {text} -> {href}")
            link.click()
            human_delay(2, 4)
            take_screenshot(page, "applications")

            app_text = page.inner_text("body")
            result["applications_page_text"] = app_text[:3000]
            break

    save_result(result)
    return result


def auto_mode():
    """自動モード - Cookie使用して新着確認"""
    if not COOKIE_FILE.exists():
        log.error("Cookieファイルが見つかりません。")
        log.error("まず --login で手動ログインしてください:")
        log.error("  python jobins_auto.py --login")
        save_result({"status": "error", "message": "Cookie未設定。--loginで初回ログイン必要"})
        return

    log.info("=== 自動モード ===")

    with sync_playwright() as p:
        browser, context = create_browser(p)
        load_cookies(context)

        page = context.new_page()

        # JoBinsにアクセス（Cookieで自動ログイン）
        page.goto(JOBINS_URL, wait_until="networkidle")
        human_delay(2, 4)

        # 人間的な動作をシミュレート
        human_scroll(page, "down")
        human_delay(1, 2)

        # ログイン状態を確認
        current_url = page.url
        log.info(f"現在のURL: {current_url}")

        if "login" in current_url.lower() or "signin" in current_url.lower():
            log.warning("セッション切れ。再ログインが必要です。")
            save_result({"status": "error", "message": "セッション切れ。--loginで再ログイン必要"})
            browser.close()
            return

        log.info("ログイン成功！")

        # 新着応募を確認
        result = check_applications(page)

        # Cookie更新して保存
        save_cookies(context)
        browser.close()

        return result


def run_server(port=8585):
    """APIサーバーモード - VPS(律)からHTTP経由で制御"""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class JobinsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self._respond(200, {"status": "ok", "service": "jobins-auto"})

            elif self.path == "/check":
                log.info("API: 新着応募チェック開始")
                try:
                    result = auto_mode()
                    self._respond(200, result or {"status": "error", "message": "結果なし"})
                except Exception as e:
                    log.error(f"チェック失敗: {e}")
                    self._respond(500, {"status": "error", "message": str(e)})

            elif self.path == "/result":
                # 最新の結果を返す（ブラウザ起動なし）
                if RESULT_FILE.exists():
                    with open(RESULT_FILE, "r", encoding="utf-8") as f:
                        result = json.load(f)
                    self._respond(200, result)
                else:
                    self._respond(404, {"status": "error", "message": "結果なし"})

            elif self.path == "/cookies-status":
                exists = COOKIE_FILE.exists()
                age = None
                if exists:
                    age = time.time() - COOKIE_FILE.stat().st_mtime
                self._respond(200, {
                    "cookies_exist": exists,
                    "age_seconds": age,
                    "age_hours": round(age / 3600, 1) if age else None,
                })

            else:
                self._respond(404, {"error": "Not found"})

        def _respond(self, code, data):
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

        def log_message(self, format, *args):
            log.info(f"HTTP: {args[0]}")

    server = HTTPServer(("0.0.0.0", port), JobinsHandler)
    log.info(f"=== JoBins APIサーバー起動: http://0.0.0.0:{port} ===")
    log.info("エンドポイント:")
    log.info("  GET /health       - ヘルスチェック")
    log.info("  GET /check        - 新着応募チェック実行")
    log.info("  GET /result       - 最新結果取得（ブラウザ起動なし）")
    log.info("  GET /cookies-status - Cookie状態確認")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("サーバー停止")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="JoBins自動化ツール")
    parser.add_argument("--login", action="store_true", help="手動ログインモード（初回のみ）")
    parser.add_argument("--server", action="store_true", help="APIサーバーモード（VPSから制御用）")
    parser.add_argument("--port", type=int, default=8585, help="APIサーバーポート（デフォルト: 8585）")
    args = parser.parse_args()

    if args.login:
        manual_login()
    elif args.server:
        run_server(args.port)
    else:
        result = auto_mode()
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
