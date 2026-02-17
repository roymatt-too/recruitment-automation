# OpenClaw VPS デプロイガイド

このガイドでは、OpenClaw を VPS に段階的にデプロイする方法を説明します。

## 📝 目次

1. [事前準備](#事前準備)
2. [Telegram Bot の作成](#telegram-bot-の作成)
3. [API キーの取得](#api-キーの取得)
4. [ローカルセットアップ](#ローカルセットアップ)
5. [VPS へのデプロイ](#vps-へのデプロイ)
6. [ドメイン設定 (HTTPS)](#ドメイン設定-https)
7. [動作確認](#動作確認)

## 🎯 事前準備

### 必要なもの

- [ ] VPS サーバー (推奨スペック: 2 CPU, 4GB RAM, 20GB SSD)
- [ ] SSH アクセス権限
- [ ] Telegram アカウント
- [ ] Anthropic または OpenAI の API キー
- [ ] ドメイン名 (HTTPS 用、オプション)

### VPS プロバイダー推奨

- **DigitalOcean**: 月額 $6~ (1クリックデプロイ対応)
- **Contabo**: 月額 $6~ (OpenClaw 専用プラン)
- **Hetzner**: 月額 €4~ (ヨーロッパ拠点)
- **X Server**: 日本のプロバイダー

## 🤖 Telegram Bot の作成

### ステップ 1: BotFather でボットを作成

1. Telegram を開く
2. [@BotFather](https://t.me/BotFather) を検索
3. 以下のコマンドを送信:

```
/newbot
```

4. ボット名を入力 (例: "My OpenClaw Bot")
5. ユーザー名を入力 (例: "my_openclaw_bot")
   - 必ず `_bot` または `Bot` で終わる必要があります
6. Bot Token を保存

**Bot Token の例:**
```
123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### ステップ 2: ユーザー ID を取得

1. [@userinfobot](https://t.me/userinfobot) を検索
2. `/start` を送信
3. User ID をコピー (例: `123456789`)

### ステップ 3: Bot の設定 (オプション)

BotFather でボットのプロフィールを設定:

```
/setdescription - ボットの説明を設定
/setabouttext - About テキストを設定
/setuserpic - プロフィール画像を設定
```

## 🔑 API キーの取得

### Anthropic Claude (推奨)

1. [Anthropic Console](https://console.anthropic.com/) にアクセス
2. アカウントを作成
3. API Keys セクションに移動
4. "Create Key" をクリック
5. API キーをコピー

**料金:**
- Claude Sonnet: $3 / 1M トークン
- 無料クレジット: $5 (新規アカウント)

### OpenAI GPT

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. アカウントを作成
3. API Keys セクションに移動
4. "Create new secret key" をクリック
5. API キーをコピー

**料金:**
- GPT-4: $10 / 1M トークン
- 無料クレジット: $5 (新規アカウント)

## 💻 ローカルセットアップ

### ステップ 1: リポジトリをクローン

```bash
git clone https://github.com/roymatt-too/recruitment-automation.git
cd recruitment-automation
```

### ステップ 2: セットアップスクリプトを実行

```bash
chmod +x scripts/*.sh
./scripts/setup-telegram-bot.sh
```

スクリプトが以下を質問します:

1. **Telegram Bot Token**: 上記で取得したトークンを入力
2. **Telegram User ID**: あなたの User ID を入力 (複数の場合はカンマ区切り)
3. **AI Provider**: Anthropic、OpenAI、または両方を選択
4. **API Key**: 選択したプロバイダーの API キーを入力
5. **Domain**: ドメイン名 (HTTPS 用、なければ skip)

### ステップ 3: 設定の確認

`.env` ファイルが作成されます:

```bash
cat .env
```

以下が設定されているか確認:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USERS`
- `ANTHROPIC_API_KEY` または `OPENAI_API_KEY`

## 🚀 VPS へのデプロイ

### ステップ 1: SSH アクセスの確認

VPS に SSH 接続できることを確認:

```bash
ssh root@your-vps-ip
```

### ステップ 2: デプロイスクリプトを実行

```bash
./scripts/deploy-to-vps.sh
```

スクリプトが以下を実行します:

1. ✅ SSH 接続テスト
2. ✅ Docker インストール
3. ✅ Docker Compose インストール
4. ✅ ファイアウォール設定 (UFW)
5. ✅ プロジェクトファイルのアップロード
6. ✅ コンテナの起動

**所要時間:** 約 5-10 分

### ステップ 3: デプロイの確認

SSH で VPS に接続し、コンテナの状態を確認:

```bash
ssh root@your-vps-ip
cd /opt/openclaw
docker-compose ps
```

全てのサービスが `Up` 状態であることを確認。

## 🌐 ドメイン設定 (HTTPS)

### ステップ 1: DNS 設定

ドメインの DNS 設定で A レコードを追加:

```
Type: A
Name: @ (またはサブドメイン、例: bot)
Value: your-vps-ip
TTL: 3600
```

### ステップ 2: .env ファイルを更新

ローカルの `.env` ファイルを編集:

```bash
DOMAIN=your-domain.com
EMAIL=your-email@example.com
```

### ステップ 3: VPS を更新

```bash
./scripts/update-vps.sh
```

Caddy が自動的に Let's Encrypt から TLS 証明書を取得します。

### ステップ 4: HTTPS の確認

ブラウザで `https://your-domain.com` にアクセスして、証明書が有効か確認。

## ✅ 動作確認

### 1. Bot に Hello メッセージを送信

Telegram で bot を検索し、メッセージを送信:

```
Hello!
```

Bot が応答すれば成功です。

### 2. ログの確認

VPS でログを確認:

```bash
ssh root@your-vps-ip 'cd /opt/openclaw && docker-compose logs -f openclaw'
```

エラーがないことを確認。

### 3. ヘルスチェック

```bash
curl http://your-vps-ip:3000/health
```

または HTTPS の場合:

```bash
curl https://your-domain.com/health
```

`{"status":"ok"}` のような応答があれば OK。

## 🎨 高度な設定

### プライバシーモード

グループチャットでボットを使用する場合、`.env` に追加:

```bash
TELEGRAM_PRIVACY_MODE=true
TELEGRAM_REQUIRE_MENTION=true
```

これにより、bot は @mention された時のみ反応します。

### 複数のユーザー許可

複数のユーザーに bot へのアクセスを許可:

```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321,456789123
```

### レート制限の調整

`.env` でレート制限を調整:

```bash
RATE_LIMIT_WINDOW=60000  # 1分
RATE_LIMIT_MAX_REQUESTS=20  # 1分間に20リクエストまで
```

### ログレベルの変更

デバッグ時はログレベルを変更:

```bash
LOG_LEVEL=debug  # debug, info, warn, error
```

## 🔄 メンテナンス

### 定期的な更新

月に一度、以下を実行:

```bash
./scripts/update-vps.sh
```

### バックアップ

自動バックアップは `/tmp` に作成されます。定期的にダウンロード:

```bash
scp root@your-vps-ip:/tmp/openclaw-backup-*.tar.gz ./backups/
```

### ログのローテーション

ログは自動的にローテーションされます (14日保持)。

## 🆘 トラブルシューティング

問題が発生した場合は、トラブルシューティングスクリプトを実行:

```bash
./scripts/troubleshoot.sh
```

詳細は [README.md](../README.md#-トラブルシューティング) を参照。

## 📊 パフォーマンス最適化

### メモリ制限の設定

`docker-compose.yml` にメモリ制限を追加:

```yaml
services:
  openclaw:
    mem_limit: 2g
    mem_reservation: 1g
```

### ログサイズの制限

```yaml
services:
  openclaw:
    logging:
      options:
        max-size: "10m"
        max-file: "3"
```

## 🎓 次のステップ

- [ ] Bot のカスタマイズ
- [ ] 追加のチャンネル統合 (Discord, WhatsApp)
- [ ] カスタムコマンドの追加
- [ ] データベース統合 (会話履歴の保存)

## 📚 参考資料

- [OpenClaw Documentation](https://docs.openclaw.ai)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Caddy Documentation](https://caddyserver.com/docs/)

---

デプロイに成功しましたら、Issue またはディスカッションでお知らせください！
