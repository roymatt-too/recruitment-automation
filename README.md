# Claude Code Telegram Bot - VPS Deployment

VPS上でClaude Codeを実行し、Telegramから操作するためのプロジェクトです。

**🎉 特徴: APIキー不要！Claude Codeサブスクリプションだけで動作します！**

## 🌟 主な機能

- **💬 Telegram連携**: Telegramから直接Claude Codeを操作
- **🔒 サブスクリプション使用**: 追加のAPI料金不要
- **🐍 Python環境**: Poetry + systemdで安定動作
- **🚀 自動デプロイ**: ワンコマンドでVPSにデプロイ
- **🔐 セキュリティ**: ユーザーIDホワイトリストで保護

## 📋 前提条件

- VPS (2 CPU, 4GB RAM, 20GB ストレージ推奨)
- SSH アクセス権限
- Telegram アカウント
- **Claude Code サブスクリプション** (Max, Team, または Enterprise)

## 🚀 クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/roymatt-too/recruitment-automation.git
cd recruitment-automation
```

### 2. Telegram Botのセットアップ

```bash
chmod +x scripts/*.sh
./scripts/setup-telegram-bot.sh
```

このスクリプトで設定する項目:
- Telegram Bot Token (@BotFather から取得)
- Bot Username
- 許可するユーザーID (@userinfobot から取得)
- プロジェクトディレクトリ

**重要: APIキーは不要です！**

### 3. VPSへのデプロイ

```bash
./scripts/deploy-to-vps.sh
```

デプロイスクリプトが自動的に:
1. ✅ システム依存関係のインストール (Python, Poetry, Node.js, Claude CLI)
2. ✅ claude-code-telegramリポジトリのクローン
3. ✅ Python依存関係のインストール
4. ✅ 設定ファイルのアップロード
5. ✅ Claude CLI認証（ブラウザで認証）
6. ✅ systemdサービスの設定と起動

### 4. Claude CLI認証

デプロイ中に、以下の指示が表示されます:

1. VPSにSSH接続
2. `claude auth login` を実行
3. ブラウザで認証フローを完了
4. デプロイスクリプトに戻って続行

### 5. Telegram Botのテスト

Telegramでbotを検索し、メッセージを送信してください。

## 📁 プロジェクト構造

```
recruitment-automation/
├── .env.example                # 環境変数テンプレート
├── .env                        # 環境変数 (自動生成、Git無視)
├── scripts/
│   ├── setup-telegram-bot.sh  # Telegram Bot セットアップ
│   ├── deploy-to-vps.sh       # VPS デプロイスクリプト
│   ├── update-vps.sh          # VPS 更新スクリプト
│   └── troubleshoot.sh        # トラブルシューティング
└── docs/                      # ドキュメント
```

## 🔧 環境変数

`.env`ファイルで設定します:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username
ALLOWED_USERS=123456789

# プロジェクトディレクトリ
APPROVED_DIRECTORY=/opt/openclaw/projects

# Claude設定
USE_SDK=true
ANTHROPIC_API_KEY=  # 空でOK！Claude CLI認証を使用

# 環境設定
ENVIRONMENT=production
DEBUG=false
DEVELOPMENT_MODE=false
```

## 🛠️ 管理コマンド

### ログの確認

```bash
ssh user@vps-ip 'journalctl --user -u claude-telegram-bot -f'
```

### サービスの再起動

```bash
ssh user@vps-ip 'systemctl --user restart claude-telegram-bot'
```

### サービスの停止

```bash
ssh user@vps-ip 'systemctl --user stop claude-telegram-bot'
```

### サービスの状態確認

```bash
ssh user@vps-ip 'systemctl --user status claude-telegram-bot'
```

## 🔒 セキュリティ

- **ユーザー制限**: Telegram ユーザー ID ホワイトリスト
- **プロジェクト分離**: サンドボックス化されたプロジェクトディレクトリ
- **レート制限**: トークンバケットアルゴリズムによる制限
- **監査ログ**: 全操作のログ記録
- **自動再起動**: systemdによる自動復旧

## 🐛 トラブルシューティング

### Botが応答しない

1. サービス状態を確認: `systemctl --user status claude-telegram-bot`
2. ログを確認: `journalctl --user -u claude-telegram-bot -n 50`
3. `.env`の`TELEGRAM_BOT_TOKEN`を確認
4. `ALLOWED_USERS`にあなたのUser IDが含まれているか確認

### Claude CLI認証エラー

1. VPSにSSH接続
2. `claude auth status`で認証状態を確認
3. 未認証の場合: `claude auth login`を実行

### サービスが起動しない

```bash
# 手動でbotを起動してエラーを確認
cd /opt/openclaw/claude-code-telegram
poetry run claude-telegram-bot
```

## 📚 参考資料

- [claude-code-telegram GitHub](https://github.com/RichardAtCT/claude-code-telegram)
- [Claude Code Documentation](https://claude.ai/code)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Poetry Documentation](https://python-poetry.org/docs/)

## 🤝 貢献

プルリクエストを歓迎します！

## 📄 ライセンス

MIT License

## ⚡ 技術スタック

このプロジェクトは以下の技術を使用しています:

- ✅ Python 3.10+ + Poetry
- ✅ Claude Agent SDK
- ✅ python-telegram-bot
- ✅ systemd (サービス管理)
- ✅ Claude CLI (認証)
- ✅ SQLite (セッション永続化)

## 💰 コスト

- **VPS**: 月額 $6-40 (プロバイダーとスペックによる)
- **Claude Code サブスクリプション**: 既存のサブスクリプションを使用
- **追加のAPI料金**: なし！

## 📞 サポート

問題が発生した場合は、Issueを作成してください。

---

**Based on:**
- [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)
- Claude Code CLI integration
