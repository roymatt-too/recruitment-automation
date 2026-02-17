# よくある質問 (FAQ)

## 一般的な質問

### Q: OpenClaw とは何ですか？

A: OpenClaw は、オープンソースの AI エージェント/アシスタントです。Telegram、Discord、WhatsApp などのメッセージングプラットフォームと統合して、AI を簡単に操作できます。

### Q: なぜ VPS が必要なのですか？

A: VPS で実行することで、24/7 稼働が可能になり、複数のユーザーが同時にアクセスできます。また、データとプライバシーを完全にコントロールできます。

### Q: 費用はどのくらいかかりますか？

A:
- **VPS**: 月額 $6-40 (プロバイダーとスペックによる)
- **AI API**: 使用量に応じて課金
  - Claude Sonnet: $3 / 1M トークン
  - GPT-4: $10 / 1M トークン
- 平均的な使用 (月間 100万トークン): $10-15/月

### Q: ドメインは必須ですか？

A: いいえ、ドメインはオプションです。HTTPS を使用したい場合にのみ必要です。IP アドレスだけでも動作します。

## インストールとセットアップ

### Q: どの VPS プロバイダーを選べばいいですか？

A: 以下を推奨します:
- **初心者**: DigitalOcean (1クリックデプロイ対応)
- **コスパ重視**: Contabo
- **日本拠点**: X Server、Conoha VPS
- **ヨーロッパ**: Hetzner

### Q: Docker の経験がなくても大丈夫ですか？

A: はい。このプロジェクトのスクリプトが Docker のインストールと設定を自動で行います。

### Q: Windows でも使用できますか？

A: はい。以下の2つの方法があります:
1. WSL2 (Windows Subsystem for Linux) を使用
2. Git Bash を使用してスクリプトを実行

### Q: Mac でも使用できますか？

A: はい、完全に対応しています。ターミナルからスクリプトを実行できます。

## Telegram

### Q: Bot が応答しません

A: 以下を確認してください:
1. `.env` の `TELEGRAM_BOT_TOKEN` が正しいか
2. @BotFather で bot が有効になっているか
3. `TELEGRAM_ALLOWED_USERS` にあなたの User ID が含まれているか
4. ログを確認: `docker-compose logs openclaw`

### Q: グループチャットで bot を使用できますか？

A: はい。プライバシーモードを有効にすることを推奨します:

```bash
TELEGRAM_PRIVACY_MODE=true
TELEGRAM_REQUIRE_MENTION=true
```

これにより、bot は @mention された時のみ反応します。

### Q: 複数のユーザーに bot へのアクセスを許可するには？

A: `.env` ファイルで複数の User ID をカンマ区切りで指定します:

```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321,456789123
```

### Q: 誰でも bot を使えるようにするには？

A: `.env` で `TELEGRAM_ALLOWED_USERS` を空にします:

```bash
TELEGRAM_ALLOWED_USERS=
```

⚠️ セキュリティリスクがあるため、推奨しません。

## AI モデル

### Q: Claude と GPT-4 のどちらを選べばいいですか？

A:
- **Claude Sonnet**: コスト効率が良く、長文処理に優れている
- **GPT-4**: 汎用性が高く、コーディングに強い

両方設定して、用途に応じて切り替えることも可能です。

### Q: 複数の AI モデルを使用できますか？

A: はい。`.env` で両方の API キーを設定します:

```bash
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
DEFAULT_MODEL=claude-sonnet-4-5-20250929
```

Bot にコマンドでモデルを切り替える機能を追加することもできます。

### Q: ローカルモデル (Ollama など) を使用できますか？

A: はい、可能です。`docker-compose.yml` を編集して Ollama コンテナを追加し、OpenClaw の設定を変更する必要があります。

## セキュリティ

### Q: データはどこに保存されますか？

A: 全てのデータは VPS 上の `/opt/openclaw/data` ディレクトリに保存されます。サードパーティのクラウドには保存されません。

### Q: API キーは安全ですか？

A: はい。API キーは `.env` ファイルに保存され、Git にはコミットされません (`.gitignore` で除外)。

### Q: HTTPS は必須ですか？

A: Telegram Bot API は暗号化されているため必須ではありませんが、Web インターフェースを使用する場合は HTTPS を推奨します。

### Q: Fail2ban とは何ですか？

A: Fail2ban は、不正なログイン試行を検出して自動的にブロックするセキュリティツールです。このプロジェクトではデフォルトで有効になっています。

## パフォーマンスとメンテナンス

### Q: どのくらいの頻度で更新すべきですか？

A: 月に一度、以下を実行することを推奨します:

```bash
./scripts/update-vps.sh
```

セキュリティアップデートは自動で適用されます。

### Q: ログはどのくらい保存されますか？

A: デフォルトで14日間保存され、自動的にローテーションされます。

### Q: バックアップは自動で行われますか？

A: 更新時に自動バックアップが作成されます (`/tmp` ディレクトリ)。定期的なバックアップは手動で設定する必要があります。

### Q: メモリ使用量を減らすには？

A: `docker-compose.yml` でメモリ制限を設定します:

```yaml
services:
  openclaw:
    mem_limit: 2g
```

また、ログレベルを `info` または `warn` に設定します。

## トラブルシューティング

### Q: "Permission denied" エラーが出ます

A: スクリプトに実行権限を付与します:

```bash
chmod +x scripts/*.sh
```

### Q: "Port already in use" エラーが出ます

A: ポート 80 または 443 が既に使用されています。他のサービスを停止するか、`docker-compose.yml` でポートを変更します。

### Q: Docker イメージのダウンロードが遅いです

A: Docker レジストリミラーを設定するか、別の VPS プロバイダーを検討してください。

### Q: Bot が時々応答しなくなります

A: 以下を確認:
1. VPS のメモリとディスク容量
2. API レート制限
3. ログでエラーを確認

メモリ不足の場合は、VPS のアップグレードを検討してください。

### Q: SSL 証明書のエラーが出ます

A:
1. ドメインの DNS 設定が正しいか確認
2. ポート 80, 443 が開いているか確認
3. Caddy のログを確認: `docker-compose logs caddy`

## コスト最適化

### Q: API コストを削減するには？

A:
1. レート制限を設定 (`.env` の `RATE_LIMIT_MAX_REQUESTS`)
2. `TELEGRAM_ALLOWED_USERS` でユーザーを制限
3. 安価なモデルを使用 (Claude Haiku など)
4. メッセージ長を制限 (`MAX_MESSAGE_LENGTH`)

### Q: VPS コストを削減するには？

A:
1. 小さいインスタンスから始める (1 CPU, 2GB RAM でも可)
2. 年間契約で割引を受ける
3. 複数のプロジェクトで同じ VPS を共有

## 高度な質問

### Q: カスタムコマンドを追加できますか？

A: はい。OpenClaw の設定ファイルを編集してカスタムコマンドを追加できます。詳細は OpenClaw のドキュメントを参照してください。

### Q: データベースを統合できますか？

A: はい。`docker-compose.yml` に PostgreSQL コンテナを追加し、`.env` で `DATABASE_URL` を設定します。

### Q: 複数の bot を同じ VPS で実行できますか？

A: はい。異なるポートを使用して複数のインスタンスを実行できます。各インスタンス用に別の `docker-compose.yml` を作成してください。

### Q: Webhook を使用できますか？

A: はい。Telegram は Webhook をサポートしています。`.env` で `TELEGRAM_USE_WEBHOOK=true` を設定し、Webhook URL を設定します。

## サポート

### Q: 問題が解決しない場合は？

A: 以下の手順を試してください:

1. トラブルシューティングスクリプトを実行:
   ```bash
   ./scripts/troubleshoot.sh
   ```

2. ログを確認:
   ```bash
   docker-compose logs -f
   ```

3. GitHub で Issue を作成:
   - リポジトリの Issues タブ
   - エラーメッセージとログを含める

4. コミュニティに質問:
   - GitHub Discussions
   - OpenClaw の公式コミュニティ

### Q: 機能リクエストはどこで行えますか？

A: GitHub の Issues または Discussions で Feature Request として投稿してください。

### Q: このプロジェクトに貢献できますか？

A: はい！プルリクエストを歓迎します。貢献する前に、既存の Issues を確認してください。

---

質問がここに載っていない場合は、GitHub で Issue を作成してください！
