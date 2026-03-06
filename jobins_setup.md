# JoBins 自動化セットアップガイド

## アーキテクチャ

```
[VPS - 律(Ritsu)]                    [自宅Windows PC]
  Telegram受信                         Patchright実行
      ↓                                   ↓
  jobins_vps_client.py  ──Tailscale──►  jobins_auto.py --server
      ↓                                   ↓
  結果をTelegramで返信               本物のChrome → JoBins
```

**ポイント**: ブラウザは自宅PCで実行。TCP/IP、TLS、Canvas全てが本物のWindowsとして動作。

## セットアップ手順

### 1. 自宅PC側

```bash
# Patchrightインストール（既にインストール済みなら不要）
pip install patchright
patchright install chromium

# Google Chrome がインストールされている必要あり
# （channel="chrome" で本物のChromeを使うため）

# 初回ログイン（手動）
cd C:\Users\2\Documents\recruitment-automation
python jobins_auto.py --login
# → ブラウザが開く → JoBinsに手動ログイン → Enterキー

# APIサーバー起動（常駐）
python jobins_auto.py --server
# → http://0.0.0.0:8585 で待機
```

### 2. 自宅PCのAPIサーバーを自動起動（Windows Task Scheduler）

1. Win+R → `taskschd.msc`
2. 「タスクの作成」
3. 全般: 名前「JoBins API Server」、「ユーザーがログオンしているかどうかにかかわらず実行」
4. トリガー: 「スタートアップ時」
5. 操作: プログラム `python`、引数 `C:\Users\2\Documents\recruitment-automation\jobins_auto.py --server`
6. 条件: 「AC電源のみ」のチェックを外す

### 3. VPS側

```bash
# Tailscaleで自宅PCのIPを確認
tailscale status

# jobins_vps_client.py をVPSに配置
scp -i ~/.ssh/xserver_recruitment jobins_vps_client.py root@220.158.18.159:/opt/openclaw/scripts/

# VPSにSSH接続
ssh -i ~/.ssh/xserver_recruitment root@220.158.18.159

# HOME_PC_TAILSCALE_IP を編集
nano /opt/openclaw/scripts/jobins_vps_client.py
# → CHANGE_ME を自宅PCのTailscale IPに変更

# テスト
python3 /opt/openclaw/scripts/jobins_vps_client.py health
python3 /opt/openclaw/scripts/jobins_vps_client.py check
```

### 4. 律から使えるようにする

律（Telegram Bot）に以下のように指示：
```
JoBinsの新着を確認して
→ 律が /opt/openclaw/scripts/jobins_vps_client.py check を実行
→ 結果をTelegramで返信
```

## APIエンドポイント

| エンドポイント | 説明 |
|------------|------|
| GET /health | サーバー稼働確認 |
| GET /check | 新着応募チェック（ブラウザ起動） |
| GET /result | 最新結果取得（キャッシュ） |
| GET /cookies-status | ログイン状態確認 |

## IPブロック解除

自宅IPがブロックされている場合:
1. ルーターを再起動（動的IPなら新しいIPが割り当てられる可能性）
2. 数日待つ（通常24h-7日で解除）
3. ISPに連絡してIP変更を依頼

## トラブルシューティング

- **Cookie切れ**: `python jobins_auto.py --login` で再ログイン
- **自宅PC接続不可**: `tailscale status` でPCがオンラインか確認
- **ブロック再発**: ブラウザ実行間隔を長くする、human_delayの値を増やす
