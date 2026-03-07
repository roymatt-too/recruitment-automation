"""
JoBins（ジョビンズ）自動化スクリプト
自宅Windows PCで実行 - Patchright(本物Windows Chrome)で動作

アーキテクチャ:
  VPS(律) → Tailscale → 自宅PC:8585 → Patchright → JoBins

使い方:
  python jobins_auto.py --server   # APIサーバーモード（推奨）
  python jobins_auto.py --login    # 手動ログインモード

注意:
  - browser.new_page() はDNSエラー → launch_persistent_context() を使う
  - channel="chrome" もDNSエラー → 使わない

安全機構:
  - グローバルレートリミッター: JoBinsへの全gotoに最低30秒間隔を強制
  - /checkクールダウン: 最低5分間隔
  - サーキットブレーカー: 連続3回失敗で自動停止（手動復旧が必要）
  - get_page()再起動制限: 10分に1回まで
  - 1日のアクセス上限: 100回/日（超えたらサーバー停止）
  - 起動時にloginページにアクセスしない（既存セッションを確認するだけ）
"""

import argparse
import json
import logging
import random
import sys
import io
import time
import os
import atexit
from datetime import datetime, date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from patchright.sync_api import sync_playwright

# Windows コンソール文字化け対策
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# === 設定 ===
JOBINS_BASE = "https://jobins.jp"
JOBINS_TOP = "https://agent.jobins.com/"
DATA_DIR = Path(__file__).parent / "jobins_data"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
LOG_FILE = DATA_DIR / "jobins.log"
RESULT_FILE = DATA_DIR / "latest_result.json"

# URL定義
URLS = {
    "login": f"{JOBINS_BASE}/agent/login",
    "selection_supplier": f"{JOBINS_BASE}/agent/selection-management#/supplier",
    "selection_seeker": f"{JOBINS_BASE}/agent/selection-management#/seeker",
    "notifications": f"{JOBINS_BASE}/agent/notifications",
    "job_search": f"{JOBINS_BASE}/agent/job/search_1#/",
}

# === 安全設定（絶対に緩めない） ===
MIN_GOTO_INTERVAL_SEC = 60      # 全gotoの最低間隔（秒）= 1分
MIN_CHECK_INTERVAL_SEC = 600    # /checkの最低間隔（秒）= 10分
MAX_CONSECUTIVE_FAILURES = 3    # 連続失敗でサーキットブレーカー発動
MAX_DAILY_NAVIGATIONS = 50      # 1日のgoto上限（checkは3回消費 → 最大16回/日）
RESTART_COOLDOWN_SEC = 600      # get_page()の再起動間隔（秒）= 10分

# ロックファイル（多重起動防止）
LOCK_FILE = DATA_DIR / "jobins.lock"

# ディレクトリ作成
DATA_DIR.mkdir(exist_ok=True)
BROWSER_PROFILE_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)


# === ロックファイル ===

def acquire_lock():
    """ロックファイルを取得。既に別プロセスが動いていたら即終了する。"""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                print(f"エラー: 既に別のjobins_auto.pyが実行中です (PID: {pid})")
                print(f"強制解除するには {LOCK_FILE} を削除してください")
                sys.exit(1)
            except OSError:
                pass
        except (ValueError, FileNotFoundError):
            pass

    LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(release_lock)


def release_lock():
    try:
        if LOCK_FILE.exists():
            pid = int(LOCK_FILE.read_text().strip())
            if pid == os.getpid():
                LOCK_FILE.unlink()
    except Exception:
        pass


# === レートリミッター & サーキットブレーカー（ディスク永続化） ===
#
# 設計根拠（2026-03-07 調査に基づく）:
#   - JoBinsはAWS上(43.206.72.223)。AWS WAFのデフォルト: 100req/5min, ブロック最低6分
#   - 固定間隔はbot検知シグナル → 全待機にランダムジッター必須
#   - サーキットブレーカーは3状態(CLOSED/OPEN/HALF_OPEN)が業界標準
#   - OPEN時はプログレッシブバックオフ(2分→5分→15分→30分)
#   - goto成功後もページ内容をチェックしブロック兆候を検知

SAFETY_STATE_FILE = DATA_DIR / "safety_state.json"

# サーキットブレーカー状態
CB_CLOSED = "closed"       # 正常: アクセス許可
CB_OPEN = "open"           # 異常: 全アクセス拒否（クールダウン中）
CB_HALF_OPEN = "half_open" # 回復試行: 1回だけプローブ許可


class SafetyGuard:
    """JoBinsへのアクセスを制御する安全機構。
    全てのpage.goto()はこのクラスを通して実行する。
    状態はディスクに永続化される。プロセス再起動しても制限は引き継がれる。
    """

    def __init__(self):
        self._load_state()

    def _load_state(self):
        """ディスクから状態を読み込む。ファイルがなければ初期値。"""
        if SAFETY_STATE_FILE.exists():
            try:
                with open(SAFETY_STATE_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
                self._last_goto_time = s.get("last_goto_time", 0.0)
                self._last_check_time = s.get("last_check_time", 0.0)
                self._last_restart_time = s.get("last_restart_time", 0.0)
                self._consecutive_failures = s.get("consecutive_failures", 0)
                self._circuit_state = s.get("circuit_state", CB_CLOSED)
                self._circuit_trip_count = s.get("circuit_trip_count", 0)
                self._circuit_opened_at = s.get("circuit_opened_at", 0.0)
                self._half_open_successes = s.get("half_open_successes", 0)
                self._daily_count = s.get("daily_count", 0)
                self._daily_date = s.get("daily_date", str(date.today()))
                self._all_goto_timestamps = s.get("all_goto_timestamps", [])
                return
            except Exception:
                pass
        self._init_defaults()

    def _init_defaults(self):
        self._last_goto_time = 0.0
        self._last_check_time = 0.0
        self._last_restart_time = 0.0
        self._consecutive_failures = 0
        self._circuit_state = CB_CLOSED
        self._circuit_trip_count = 0       # OPENになった回数（バックオフ計算用）
        self._circuit_opened_at = 0.0      # 最後にOPENになった時刻
        self._half_open_successes = 0      # HALF_OPENでの連続成功数
        self._daily_count = 0
        self._daily_date = str(date.today())
        self._all_goto_timestamps = []

    def _save_state(self):
        """状態をディスクに書き出す。全ての状態変更後に呼ぶ。"""
        s = {
            "last_goto_time": self._last_goto_time,
            "last_check_time": self._last_check_time,
            "last_restart_time": self._last_restart_time,
            "consecutive_failures": self._consecutive_failures,
            "circuit_state": self._circuit_state,
            "circuit_trip_count": self._circuit_trip_count,
            "circuit_opened_at": self._circuit_opened_at,
            "half_open_successes": self._half_open_successes,
            "daily_count": self._daily_count,
            "daily_date": self._daily_date,
            "all_goto_timestamps": self._all_goto_timestamps[-200:],
            "saved_at": datetime.now().isoformat(),
        }
        try:
            with open(SAFETY_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _reset_daily_if_needed(self):
        today = str(date.today())
        if today != self._daily_date:
            self._daily_date = today
            self._daily_count = 0
            self._save_state()

    def _count_recent_accesses(self, window_sec):
        """直近N秒間のアクセス数を返す"""
        now = time.time()
        cutoff = now - window_sec
        return sum(1 for t in self._all_goto_timestamps if t > cutoff)

    def _get_circuit_cooldown(self):
        """サーキットブレーカーのクールダウン時間（プログレッシブバックオフ）"""
        # trip回数に応じて: 2分 → 5分 → 15分 → 30分（上限）
        cooldowns = [120, 300, 900, 1800]
        idx = min(self._circuit_trip_count - 1, len(cooldowns) - 1)
        if idx < 0:
            idx = 0
        return cooldowns[idx]

    def _check_circuit_recovery(self):
        """OPEN状態のサーキットブレーカーがクールダウン完了したらHALF_OPENに遷移"""
        if self._circuit_state != CB_OPEN:
            return
        cooldown = self._get_circuit_cooldown()
        elapsed = time.time() - self._circuit_opened_at
        if elapsed >= cooldown:
            self._circuit_state = CB_HALF_OPEN
            self._half_open_successes = 0
            log.info(f"サーキットブレーカー: OPEN → HALF_OPEN（{cooldown}秒経過、プローブ許可）")
            self._save_state()

    def _trip_circuit(self):
        """サーキットブレーカーをOPENにする"""
        self._circuit_state = CB_OPEN
        self._circuit_trip_count += 1
        self._circuit_opened_at = time.time()
        self._half_open_successes = 0
        cooldown = self._get_circuit_cooldown()
        log.critical(
            f"サーキットブレーカー発動！(第{self._circuit_trip_count}回) "
            f"全アクセスを{cooldown}秒間停止します。"
        )
        self._save_state()

    def _jitter(self, base_sec):
        """ランダムジッターを加える（±30%）。固定間隔はbot検知シグナルになる"""
        return base_sec * random.uniform(0.7, 1.3)

    def can_goto(self):
        """gotoが許可されるか確認。"""
        self._reset_daily_if_needed()
        self._check_circuit_recovery()

        if self._circuit_state == CB_OPEN:
            cooldown = self._get_circuit_cooldown()
            remaining = cooldown - (time.time() - self._circuit_opened_at)
            return False, f"サーキットブレーカーOPEN（第{self._circuit_trip_count}回）。あと{remaining:.0f}秒で自動回復試行"

        if self._daily_count >= MAX_DAILY_NAVIGATIONS:
            return False, f"1日のアクセス上限({MAX_DAILY_NAVIGATIONS}回)に達しました。明日まで停止"

        # 直近10分間に6回以上 → 異常
        recent_10min = self._count_recent_accesses(600)
        if recent_10min >= 6:
            return False, f"異常検知: 直近10分間に{recent_10min}回アクセス。冷却期間が必要です"

        elapsed = time.time() - self._last_goto_time
        if elapsed < MIN_GOTO_INTERVAL_SEC:
            wait = MIN_GOTO_INTERVAL_SEC - elapsed
            return False, f"レートリミット: あと{wait:.0f}秒待ってください（最低{MIN_GOTO_INTERVAL_SEC}秒間隔）"

        return True, "ok"

    def can_check(self):
        ok, reason = self.can_goto()
        if not ok:
            return False, reason
        elapsed = time.time() - self._last_check_time
        if elapsed < MIN_CHECK_INTERVAL_SEC:
            wait = MIN_CHECK_INTERVAL_SEC - elapsed
            return False, f"/checkクールダウン: あと{wait:.0f}秒待ってください（最低{MIN_CHECK_INTERVAL_SEC}秒間隔）"
        return True, "ok"

    def can_restart(self):
        elapsed = time.time() - self._last_restart_time
        if elapsed < RESTART_COOLDOWN_SEC:
            wait = RESTART_COOLDOWN_SEC - elapsed
            return False, f"再起動クールダウン: あと{wait:.0f}秒待ってください（最低{RESTART_COOLDOWN_SEC}秒間隔）"
        return True, "ok"

    def safe_goto(self, page, url, **kwargs):
        """安全なpage.goto()。全ての防御を通す。
        SPAリダイレクト対策でwait_until=domcontentloadedをデフォルトに。"""
        kwargs.setdefault("wait_until", "domcontentloaded")
        ok, reason = self.can_goto()
        if not ok:
            log.warning(f"goto拒否: {reason}")
            self._save_state()
            raise RuntimeError(reason)

        now = time.time()
        self._last_goto_time = now
        self._daily_count += 1
        self._all_goto_timestamps.append(now)
        self._all_goto_timestamps = [t for t in self._all_goto_timestamps if t > now - 3600]
        self._save_state()

        log.info(f"goto実行 [{self._daily_count}/{MAX_DAILY_NAVIGATIONS}] "
                 f"[CB:{self._circuit_state}]: {url}")

        try:
            result = page.goto(url, **kwargs)
            # goto成功後: ページ内容をチェックしブロック兆候を検知
            self._check_for_block_signals(page)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def _check_for_block_signals(self, page):
        """ページ読み込み後にブロック/CAPTCHA/403の兆候をチェック"""
        try:
            title = page.title().lower()
            url = page.url.lower()
            # ブロック/CAPTCHA/エラーの兆候
            block_signals = [
                "access denied", "403 forbidden", "blocked",
                "captcha", "robot", "bot detection",
                "rate limit", "too many requests",
                "security check", "please verify",
            ]
            for signal in block_signals:
                if signal in title or signal in url:
                    log.critical(f"ブロック兆候検知！ title='{page.title()}' url='{page.url}'")
                    self._trip_circuit()
                    raise RuntimeError(f"ブロック兆候検知: '{signal}' in page. サーキットブレーカー発動。")
        except RuntimeError:
            raise
        except Exception:
            pass  # チェック自体の失敗は無視

    def _record_success(self):
        """goto成功を記録"""
        self._consecutive_failures = 0
        if self._circuit_state == CB_HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= 2:
                # HALF_OPEN中に2回連続成功 → CLOSED（正常復帰）
                self._circuit_state = CB_CLOSED
                self._circuit_trip_count = 0
                log.info("サーキットブレーカー: HALF_OPEN → CLOSED（正常復帰）")
            else:
                log.info(f"サーキットブレーカー: HALF_OPENプローブ成功 ({self._half_open_successes}/2)")
        self._save_state()

    def _record_failure(self, error):
        """goto失敗を記録"""
        self._consecutive_failures += 1
        log.error(f"goto失敗 ({self._consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {error}")

        if self._circuit_state == CB_HALF_OPEN:
            # HALF_OPENでの失敗は即OPEN（バックオフ増加）
            log.warning("HALF_OPENプローブ失敗 → OPENに戻る（バックオフ増加）")
            self._trip_circuit()
        elif self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            self._trip_circuit()
        self._save_state()

    def record_check(self):
        self._last_check_time = time.time()
        self._save_state()

    def record_restart(self):
        self._last_restart_time = time.time()
        self._save_state()

    def reset_circuit(self):
        """サーキットブレーカーを手動リセット（緊急時のみ）"""
        self._circuit_state = CB_CLOSED
        self._consecutive_failures = 0
        self._circuit_trip_count = 0
        self._half_open_successes = 0
        self._save_state()
        log.info("サーキットブレーカーを手動リセットしました")

    def status(self):
        self._reset_daily_if_needed()
        self._check_circuit_recovery()
        now = time.time()
        result = {
            "circuit_state": self._circuit_state,
            "circuit_trip_count": self._circuit_trip_count,
            "consecutive_failures": self._consecutive_failures,
            "daily_navigations": f"{self._daily_count}/{MAX_DAILY_NAVIGATIONS}",
            "recent_10min": self._count_recent_accesses(600),
            "last_goto_ago": f"{now - self._last_goto_time:.0f}s" if self._last_goto_time else "never",
            "last_check_ago": f"{now - self._last_check_time:.0f}s" if self._last_check_time else "never",
            "last_restart_ago": f"{now - self._last_restart_time:.0f}s" if self._last_restart_time else "never",
        }
        if self._circuit_state == CB_OPEN:
            cooldown = self._get_circuit_cooldown()
            remaining = cooldown - (now - self._circuit_opened_at)
            result["circuit_remaining"] = f"{max(0, remaining):.0f}s"
        if self._circuit_state == CB_HALF_OPEN:
            result["half_open_successes"] = f"{self._half_open_successes}/2"
        return result


# グローバルインスタンス
guard = SafetyGuard()


# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("jobins")


# === ユーティリティ ===

def human_delay(min_sec=2.0, max_sec=6.0):
    """人間らしいランダム遅延。固定間隔を避けるため範囲を広くとる"""
    time.sleep(random.uniform(min_sec, max_sec))


def take_screenshot(page, name="page"):
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOT_DIR / f"{name}_{ts}.png"
        page.screenshot(path=str(path))
        log.info(f"スクリーンショット: {path}")
        return str(path)
    except Exception as e:
        log.warning(f"スクリーンショット失敗（無視）: {e}")
        return None


def save_result(result):
    result["timestamp"] = datetime.now().isoformat()
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def launch_browser(pw, headless=False):
    """Patchright ブラウザを起動（persistent context）
    headless=False: headlessだとログインセッションが無効になるため常にheadful
    """
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(BROWSER_PROFILE_DIR),
        headless=headless,
        viewport={"width": 1920, "height": 1080},
        locale="ja-JP",
        timezone_id="Asia/Tokyo",
    )
    page = context.pages[0] if context.pages else context.new_page()
    return context, page


# === データ取得 ===

def extract_selection_counts(page):
    """選考管理ページからステータスカウントを抽出"""
    return page.evaluate(r"""() => {
        const result = {};
        const body = document.body.innerText;
        const patterns = [
            ['選考中', /選考中\s*(\d+)件/],
            ['内定', /(?<!承諾以降.{0,5})内定\s*(\d+)件/],
            ['内定承諾以降', /内定承諾以降\s*(\d+)件/],
            ['辞退不合格', /辞退\/不合格\s*(\d+)件/],
        ];
        for (const [key, regex] of patterns) {
            const m = body.match(regex);
            if (m) result[key] = parseInt(m[1]);
        }
        return result;
    }""")


def extract_notifications(page, limit=10):
    """通知ページから通知リストを抽出（DOM + テキスト解析）"""
    return page.evaluate("""(limit) => {
        const items = [];

        // Method 1: DOM - .notification-wrap 要素から抽出
        const wraps = document.querySelectorAll('.notification-wrap');
        for (const wrap of wraps) {
            const text = wrap.innerText.trim();
            const isUnread = wrap.classList.contains('new');
            const titleEl = wrap.querySelector('.main-text span');
            const title = titleEl ? titleEl.innerText.trim() : '';
            const dateMatch = text.match(/(\\d{4}\\/\\d{2}\\/\\d{2}\\s+\\d{2}:\\d{2})/);

            if (title) {
                items.push({
                    title: title.substring(0, 100),
                    unread: isUnread,
                    date: dateMatch ? dateMatch[1] : '',
                });
            }
            if (items.length >= limit) break;
        }

        // Method 2: テキスト解析（DOM方式が失敗した場合）
        if (items.length === 0) {
            const body = document.body.innerText;
            const lines = body.split('\\n').map(l => l.trim()).filter(l => l);
            let current = null;
            for (const line of lines) {
                if (line.startsWith('ご推薦') || line.startsWith('【JoBins】') || line.startsWith('【')) {
                    if (current) items.push(current);
                    current = { title: line.substring(0, 100) };
                }
                if (current && (line === '未読' || line === '既読')) {
                    current.unread = (line === '未読');
                }
                if (current && line.includes('受信日時')) {
                    const m = line.match(/(\\d{4}\\/\\d{2}\\/\\d{2}\\s+\\d{2}:\\d{2})/);
                    if (m) current.date = m[1];
                }
                if (items.length >= limit) break;
            }
            if (current && items.length < limit) items.push(current);
        }

        return items;
    }""", limit)


def check_login_status(page):
    """ログイン状態を確認（ネットワークアクセスなし、現在のページ状態のみ確認）"""
    try:
        url = page.url
        title = page.title()
        is_login_page = "login" in url or "エージェント登録" in title
        is_logged_in = any(kw in url for kw in ["/agent/job", "/agent/selection", "/agent/candidate", "/agent/notification"])
        return {
            "logged_in": is_logged_in and not is_login_page,
            "url": url,
            "title": title,
        }
    except Exception as e:
        return {"logged_in": False, "error": str(e)}


def do_check(page):
    """メインチェック: 通知 + 選考状況を取得
    3ページ遷移するため、全てguard.safe_goto()を通す。
    """
    # /checkクールダウン確認
    ok, reason = guard.can_check()
    if not ok:
        return {"status": "rate_limited", "message": reason}

    guard.record_check()
    log.info("=== チェック開始 ===")
    result = {"status": "success"}

    # 1. 通知ページで新着確認
    log.info("通知ページを確認中...")
    guard.safe_goto(page, URLS["notifications"])
    human_delay(3, 5)
    take_screenshot(page, "notifications")

    notifications = extract_notifications(page, limit=10)
    unread_count = sum(1 for n in notifications if n.get("unread"))
    result["notifications"] = notifications
    result["unread_count"] = unread_count
    log.info(f"通知: {len(notifications)}件取得, 未読{unread_count}件")

    # 2. 選考管理 - 自社推薦タブ（60秒制限 + 30秒バッファ + ジッター）
    wait1 = guard._jitter(MIN_GOTO_INTERVAL_SEC + 30)
    log.info(f"選考管理（自社推薦）を確認中...（{wait1:.0f}秒待機）")
    time.sleep(wait1)
    guard.safe_goto(page, URLS["selection_supplier"])
    human_delay(3, 5)
    result["tab1_自社推薦"] = extract_selection_counts(page)
    log.info(f"  自社推薦: {result['tab1_自社推薦']}")

    # 3. 選考管理 - 被推薦タブ（60秒制限 + 30秒バッファ + ジッター）
    wait2 = guard._jitter(MIN_GOTO_INTERVAL_SEC + 30)
    log.info(f"選考管理（被推薦）を確認中...（{wait2:.0f}秒待機）")
    time.sleep(wait2)
    guard.safe_goto(page, URLS["selection_seeker"])
    human_delay(3, 5)
    result["tab2_被推薦"] = extract_selection_counts(page)
    take_screenshot(page, "selection")
    log.info(f"  被推薦: {result['tab2_被推薦']}")

    save_result(result)
    log.info("=== チェック完了 ===")
    return result


# === サーバーモード ===

def run_server(port=8585):
    """APIサーバーモード - ブラウザ常駐 + HTTP API"""
    acquire_lock()
    log.info("=== ブラウザ起動中 ===")

    pw = sync_playwright().start()
    context, page = launch_browser(pw)

    # 起動時: loginページにアクセスしない。既存セッションの状態だけ確認する。
    login_status = check_login_status(page)
    if login_status.get("logged_in"):
        log.info(f"ログイン済み: {login_status['url']}")
    else:
        current_url = login_status.get("url", "unknown")
        log.info(f"未ログイン状態（現在: {current_url}）。ブラウザで手動ログインしてください。")

    def get_page():
        """ページが死んでいたらcontext/ブラウザごと再起動する（制限付き）"""
        nonlocal context, page
        need_restart = False
        try:
            page.evaluate("1+1")
        except Exception:
            need_restart = True

        if need_restart:
            ok, reason = guard.can_restart()
            if not ok:
                log.warning(f"ブラウザ再起動を拒否: {reason}")
                raise RuntimeError(f"ブラウザが死んでいますが再起動できません: {reason}")

            log.warning("ページが閉じられました。ブラウザを再起動します。")
            guard.record_restart()
            try:
                context.close()
            except Exception:
                pass
            context, page = launch_browser(pw)
            # 再起動後もloginページにはアクセスしない
            log.info("ブラウザ再起動完了。loginページへの自動アクセスはしません。")
        return page

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?")[0]

            # /health と /result と /safety はブラウザアクセス不要
            if path == "/health":
                try:
                    p = get_page()
                    self._ok({"status": "ok", "browser": "alive", **check_login_status(p), "safety": guard.status()})
                except RuntimeError as e:
                    self._ok({"status": "degraded", "browser": "dead", "error": str(e), "safety": guard.status()})

            elif path == "/result":
                if RESULT_FILE.exists():
                    with open(RESULT_FILE, "r", encoding="utf-8") as f:
                        self._ok(json.load(f))
                else:
                    self._ok({"status": "no_data"})

            elif path == "/safety":
                self._ok(guard.status())

            elif path == "/reset-circuit":
                guard.reset_circuit()
                self._ok({"status": "ok", "message": "サーキットブレーカーをリセットしました", "safety": guard.status()})

            elif path == "/check":
                log.info("API: /check")
                try:
                    p = get_page()
                    result = do_check(p)
                    self._ok(result)
                except RuntimeError as e:
                    self._err(str(e))
                except Exception as e:
                    log.error(f"チェック失敗: {e}")
                    self._err(str(e))

            elif path == "/notifications":
                log.info("API: /notifications")
                try:
                    p = get_page()
                    ok, reason = guard.can_goto()
                    if not ok:
                        self._err(reason)
                        return
                    guard.safe_goto(p, URLS["notifications"])
                    human_delay(3, 5)
                    notifs = extract_notifications(p, limit=20)
                    self._ok({"notifications": notifs, "unread": sum(1 for n in notifs if n.get("unread"))})
                except Exception as e:
                    self._err(str(e))

            elif path == "/screenshot":
                log.info("API: /screenshot")
                try:
                    p = get_page()
                    path_str = take_screenshot(p, "api")
                    self._ok({"status": "ok", "path": path_str})
                except Exception as e:
                    self._err(str(e))

            elif path == "/goto":
                from urllib.parse import parse_qs
                qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
                url = qs.get("url", [JOBINS_TOP])[0]
                log.info(f"API: /goto -> {url}")
                try:
                    p = get_page()
                    guard.safe_goto(p, url)
                    human_delay(2, 3)
                    self._ok({"url": p.url, "title": p.title()})
                except Exception as e:
                    self._err(str(e))

            else:
                self._ok({
                    "endpoints": [
                        "GET /health        - ブラウザ状態 + 安全機構状態",
                        "GET /check         - 全チェック（通知+選考）※5分間隔制限",
                        "GET /notifications - 通知一覧 ※30秒間隔制限",
                        "GET /screenshot    - スクリーンショット",
                        "GET /result        - 最新結果取得（アクセスなし）",
                        "GET /goto?url=...  - ブラウザ移動 ※30秒間隔制限",
                        "GET /safety        - 安全機構の状態確認",
                        "GET /reset-circuit - サーキットブレーカーリセット",
                    ]
                })

        def _ok(self, data):
            self._respond(200, data)

        def _err(self, msg):
            self._respond(500, {"status": "error", "message": msg})

        def _respond(self, code, data):
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

        def log_message(self, fmt, *args):
            log.info(f"HTTP: {args[0] if args else fmt}")

    server = HTTPServer(("0.0.0.0", port), Handler)
    log.info(f"=== JoBins APIサーバー起動: http://0.0.0.0:{port} ===")
    log.info("エンドポイント: /health /check /notifications /screenshot /result /goto /safety /reset-circuit")
    log.info(f"安全設定: goto間隔{MIN_GOTO_INTERVAL_SEC}秒, check間隔{MIN_CHECK_INTERVAL_SEC}秒, "
             f"日上限{MAX_DAILY_NAVIGATIONS}回, 連続失敗{MAX_CONSECUTIVE_FAILURES}回で停止")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("サーバー停止")
        server.shutdown()
    finally:
        context.close()
        pw.stop()


# === 手動ログインモード ===

def manual_login():
    acquire_lock()
    log.info("=== 手動ログインモード ===")
    with sync_playwright() as p:
        context, page = launch_browser(p, headless=False)
        # 手動ログインでもSafetyGuardを通す
        guard.safe_goto(page, URLS["login"])
        human_delay(2, 3)

        status = check_login_status(page)
        if status["logged_in"]:
            log.info("既にログイン済みです。")
        else:
            log.info("ブラウザで手動ログインしてください。")
            input("\n>>> ログイン完了後Enterを押してください... ")

        take_screenshot(page, "login_result")
        log.info(f"状態: {check_login_status(page)}")
        context.close()


# === エントリポイント ===

def main():
    parser = argparse.ArgumentParser(description="JoBins自動化ツール")
    parser.add_argument("--login", action="store_true", help="手動ログインモード")
    parser.add_argument("--server", action="store_true", help="APIサーバーモード")
    parser.add_argument("--port", type=int, default=8585, help="ポート（デフォルト: 8585）")
    args = parser.parse_args()

    if args.login:
        manual_login()
    elif args.server:
        run_server(args.port)
    else:
        parser.print_help()
        print("\n使い方:")
        print("  python jobins_auto.py --server   # サーバーモード（推奨）")
        print("  python jobins_auto.py --login    # 手動ログイン")


if __name__ == "__main__":
    main()
