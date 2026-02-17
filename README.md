# OpenClaw Telegram Bot - VPS Deployment

OpenClaw を VPS にデプロイし、Telegram から AI アシスタントを操作するためのプロジェクトです。

## 🌟 特徴

- **🤖 AI 自動化**: OpenClaw を使用した強力な AI アシスタント
- **💬 Telegram 連携**: Telegram から直接 AI と対話
- **🔒 セキュリティ**: TLS、Fail2ban、ファイアウォールによる保護
- **🐳 Docker**: コンテナ化による簡単なデプロイ
- **🚀 自動デプロイ**: ワンコマンドで VPS にデプロイ

## 📋 前提条件

- VPS (2 CPU, 4GB RAM, 20GB ストレージ推奨)
- SSH アクセス権限
- Telegram アカウント
- Anthropic または OpenAI の API キー

## 🚀 クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/roymatt-too/recruitment-automation.git
cd recruitment-automation
```

### 2. Telegram Bot のセットアップ

```bash
./scripts/setup-telegram-bot.sh
```

このスクリプトが以下を行います:
- Telegram Bot トークンの設定
- ユーザー ID の設定
- AI モデルの選択と API キー設定
- ドメイン設定 (オプション)

### 3. VPS へのデプロイ

```bash
./scripts/deploy-to-vps.sh
```

デプロイスクリプトが自動的に:
- Docker と Docker Compose のインストール
- ファイアウォールの設定
- プロジェクトのアップロード
- サービスの起動

### 4. Telegram Bot のテスト

Telegram で bot を検索し、メッセージを送信してください。

## 📁 プロジェクト構造

```
recruitment-automation/
├── docker-compose.yml          # Docker Compose 設定
├── .env.example                # 環境変数テンプレート
├── .env                        # 環境変数 (自動生成、Git 無視)
├── config/
│   ├── Caddyfile              # Caddy (リバースプロキシ + TLS) 設定
│   └── fail2ban/              # Fail2ban セキュリティ設定
├── scripts/
│   ├── setup-telegram-bot.sh  # Telegram Bot セットアップ
│   ├── deploy-to-vps.sh       # VPS デプロイスクリプト
│   ├── update-vps.sh          # VPS 更新スクリプト
│   └── troubleshoot.sh        # トラブルシューティング
├── data/                      # データディレクトリ (自動生成)
├── logs/                      # ログディレクトリ (自動生成)
└── docs/                      # ドキュメント
```

## 🔧 設定

### 環境変数

`.env` ファイルで以下を設定します:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=123456789,987654321

# AI Model
ANTHROPIC_API_KEY=your_key
DEFAULT_MODEL=claude-sonnet-4-5-20250929

# Domain (HTTPS用)
DOMAIN=your-domain.com
EMAIL=your-email@example.com
```

### Telegram Bot の作成

1. Telegram で [@BotFather](https://t.me/BotFather) を検索
2. `/newbot` コマンドを送信
3. ボット名とユーザー名を設定
4. Bot Token を取得

### ユーザー ID の取得

1. Telegram で [@userinfobot](https://t.me/userinfobot) を検索
2. `/start` を送信
3. User ID をコピー

## 🛠️ 管理コマンド

### ログの確認

```bash
ssh user@vps-ip 'cd /opt/openclaw && docker-compose logs -f'
```

### サービスの再起動

```bash
ssh user@vps-ip 'cd /opt/openclaw && docker-compose restart'
```

### サービスの停止

```bash
ssh user@vps-ip 'cd /opt/openclaw && docker-compose down'
```

### 更新

```bash
./scripts/update-vps.sh
```

### トラブルシューティング

```bash
./scripts/troubleshoot.sh
```

## 🔒 セキュリティ

このプロジェクトには以下のセキュリティ機能が含まれています:

- **TLS/HTTPS**: Caddy による自動 TLS 証明書
- **Fail2ban**: 不正アクセスの自動ブロック
- **ファイアウォール**: UFW による最小限のポート開放
- **ユーザー制限**: Telegram ユーザー ID ホワイトリスト
- **コンテナ分離**: Docker による隔離環境
- **自動アップデート**: セキュリティパッチの自動適用

## 📊 モニタリング

### ヘルスチェック

```bash
curl http://your-vps-ip:3000/health
```

### Docker 統計

```bash
ssh user@vps-ip 'docker stats'
```

## 🐛 トラブルシューティング

### Bot が応答しない

1. `.env` の `TELEGRAM_BOT_TOKEN` を確認
2. @BotFather で bot が有効か確認
3. ログを確認: `docker-compose logs openclaw`

### API エラー

1. API キーが正しいか確認
2. API クレジットが残っているか確認
3. レート制限を確認

### VPS に接続できない

1. ファイアウォールでポート 80, 443 が開いているか確認
2. DNS 設定を確認
3. Caddy の設定を確認

## 📚 参考資料

- [OpenClaw 公式ドキュメント](https://docs.openclaw.ai)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Docker ドキュメント](https://docs.docker.com)
- [Caddy ドキュメント](https://caddyserver.com/docs)

## 🤝 貢献

プルリクエストを歓迎します！

## 📄 ライセンス

MIT License

## ⚡ ベストプラクティス

このプロジェクトは 2026 年の以下のベストプラクティスに従っています:

- ✅ Docker によるコンテナ化
- ✅ 自動 TLS 証明書 (Let's Encrypt)
- ✅ セキュリティ強化 (Fail2ban, Firewall)
- ✅ ログローテーション
- ✅ 自動セキュリティアップデート
- ✅ 最小権限の原則
- ✅ 環境変数による設定管理
- ✅ ヘルスチェック

## 📞 サポート

問題が発生した場合は、Issue を作成してください。

---

**Sources:**
- [OpenClaw AI: Complete Setup and Automation Guide 2026](https://www.digitalapplied.com/blog/openclaw-ai-complete-guide-setup-skills-automation)
- [OpenClaw (Clawd Bot) Telegram integration: A complete guide](https://www.eesel.ai/blog/clawd-bot-telegram-integration)
- [Running OpenClaw in Docker: Secure Local Setup and Practical Workflow Guide](https://aimlapi.com/blog/running-openclaw-in-docker-secure-local-setup-and-practical-workflow-guide)
- [OpenClaw security: Risks, best practices, and a checklist](https://www.hostinger.com/tutorials/openclaw-security)
- [Technical Deep Dive: How we Created a Security-hardened 1-Click Deploy OpenClaw](https://www.digitalocean.com/blog/technical-dive-openclaw-hardened-1-click-app)
