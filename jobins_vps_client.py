"""
JoBins VPS側クライアント - 律(Ritsu)がTailscale経由で自宅PCを制御

VPS(律) → Tailscale → 自宅PC(jobins_auto.py --server) → JoBins

このスクリプトをVPSに配置し、律から呼び出す。
使い方:
  python jobins_vps_client.py check     # 新着応募をチェック
  python jobins_vps_client.py result    # 最新結果を取得
  python jobins_vps_client.py status    # Cookie状態確認
  python jobins_vps_client.py health    # ヘルスチェック
"""

import json
import sys
import urllib.request
import urllib.error

# === 設定 ===
# 自宅PCのTailscale IP（Tailscale管理画面で確認）
# tailscale status コマンドでも確認可能
HOME_PC_TAILSCALE_IP = "100.114.36.33"  # ewg2405-04 (自宅Windows PC)
JOBINS_API_PORT = 8585
BASE_URL = f"http://{HOME_PC_TAILSCALE_IP}:{JOBINS_API_PORT}"

# タイムアウト設定（ブラウザ起動を含むので長め）
CHECK_TIMEOUT = 120  # /check は最大2分
DEFAULT_TIMEOUT = 15  # その他は15秒


def api_call(endpoint, timeout=DEFAULT_TIMEOUT):
    """自宅PCのJoBins APIを呼び出す"""
    url = f"{BASE_URL}{endpoint}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.URLError as e:
        return {
            "status": "error",
            "message": f"自宅PCに接続できません: {e}",
            "hint": "自宅PCでjobins_auto.py --serverが起動しているか確認してください",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_check():
    """新着応募チェック"""
    print("JoBins新着応募チェック中（自宅PC経由）...")
    result = api_call("/check", timeout=CHECK_TIMEOUT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_result():
    """最新結果取得"""
    result = api_call("/result")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_status():
    """Cookie状態確認"""
    result = api_call("/cookies-status")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_health():
    """ヘルスチェック"""
    result = api_call("/health")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def format_for_telegram(result):
    """律のTelegram応答用にフォーマット"""
    if not result or result.get("status") == "error":
        msg = result.get("message", "不明なエラー") if result else "結果なし"
        return f"❌ JoBinsエラー: {msg}"

    lines = ["📋 JoBins 新着応募チェック結果\n"]

    if result.get("page_title"):
        lines.append(f"📄 {result['page_title']}")

    if result.get("badges"):
        lines.append(f"🔔 通知: {', '.join(result['badges'])}")

    if result.get("links_found"):
        lines.append("\n📌 関連リンク:")
        for link in result["links_found"][:10]:
            lines.append(f"  • {link['text']}")

    if result.get("timestamp"):
        lines.append(f"\n⏰ 確認時刻: {result['timestamp']}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("使い方: python jobins_vps_client.py [check|result|status|health]")
        sys.exit(1)

    if HOME_PC_TAILSCALE_IP == "CHANGE_ME":
        print("エラー: HOME_PC_TAILSCALE_IPを設定してください")
        print("tailscale status で自宅PCのIPを確認し、スクリプトを編集してください")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "check":
        result = cmd_check()
    elif cmd == "result":
        result = cmd_result()
    elif cmd == "status":
        result = cmd_status()
    elif cmd == "health":
        result = cmd_health()
    elif cmd == "telegram":
        # Telegram用フォーマットで出力
        result = api_call("/result")
        print(format_for_telegram(result))
    else:
        print(f"不明なコマンド: {cmd}")
        print("使い方: python jobins_vps_client.py [check|result|status|health|telegram]")
        sys.exit(1)


if __name__ == "__main__":
    main()
