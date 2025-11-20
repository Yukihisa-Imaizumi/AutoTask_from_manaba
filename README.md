# AutoTask from manaba 📚➡️✅

筑波大学のLMS「manaba」の未提出課題を自動で取得し、Google Tasks（ToDoリスト）に同期するツールです。
毎朝自動で実行され、新しい課題があれば自動的にタスクに追加されます。

## 🌟 機能

**自動ログイン**: 統一認証システム経由でmanabaにアクセスします。

**未提出チェック**: 「未提出の課題一覧」から情報を取得します。

**Google Tasks同期**:

[コース名] 課題名 の形式でタスクを追加。

締切日時も自動設定。

課題のURLをメモ欄に追加。

**重複防止**: すでに追加済みの課題は追加しません。

## 🛠 前提条件

GitHubアカウント

Googleアカウント

Python環境（初期設定でのみ使用）

## 🚀 セットアップ手順

### Step 1: リポジトリの準備

このリポジトリを自分のGitHubアカウントに Fork（コピー）してください。
その後、自分のPCにクローンします。

git clone [https://github.com/Yukihisa-Imaizumi/AutoTask_from_manaba.git](https://github.com/YOUR_USERNAME/AutoTask_from_manaba.git)
cd AutoTask_from_manaba
pip install -r requirements.txt
playwright install


(※ requirements.txt がない場合は手動インストール: pip install playwright python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib requests)

### Step 2: Google Cloudの設定

Google Tasks APIを使えるようにします。

Google Cloud Console にアクセスし、新しいプロジェクトを作成。

「APIとサービス」 > 「ライブラリ」 から 「Google Tasks API」 を検索して有効化。

「OAuth同意画面」 を作成（User Typeは「外部」、テストユーザーに自分のGmailを追加）。

「認証情報」 から 「OAuthクライアントID」 (デスクトップアプリ) を作成。

JSONファイルをダウンロードして credentials.json にリネームし、プロジェクトのルートフォルダに置く。

### Step 3: 認証トークンの生成 (ローカル実行)

一度自分のPCで実行して、Googleへのログイン認証を行います。

プロジェクト直下に setting.env ファイルを作成。

MANABA_USERNAME=202XXXXXX
MANABA_PASSWORD=your_password
GOOGLE_TASK_LIST_ID=（Step 4で取得するので一旦空でOK）


以下のコマンドを実行して認証。

python src/register_tasks.py


ブラウザが開くのでログインして許可。成功すると token.json が生成されます。
(この際、コンソールにタスクリストの一覧とIDが表示されるので、追加したいリストのIDを控えてください)

### Step 4: GitHub Secretsの設定

GitHubリポジトリの Settings > Secrets and variables > Actions に行き、以下の5つを登録します。

Name

Value

MANABA_USERNAME

学籍番号 (例: 202XXXXXX)

MANABA_PASSWORD

統一認証パスワード

GOOGLE_TASK_LIST_ID

追加先のタスクリストID (例: clZn...)

GOOGLE_CREDENTIALS_JSON

credentials.json の中身すべて

GOOGLE_TOKEN_JSON

token.json の中身すべて

### Step 5: 自動実行の開始

GitHub Actionsタブを開き、ワークフローが有効になっているか確認してください。
設定完了後、毎日 日本時間の朝7時 に自動実行されます。

## ⚠️ 注意事項

大学のパスワードやAPIトークンは、必ず GitHub Secrets に登録してください。コードに直接書いたり、.envファイルをGitHubにアップロードしないでください。

manabaの仕様変更により動かなくなる可能性があります。

## 🐛 トラブルシューティング

ログインエラー: 大学のパスワード変更時は、Secretsの MANABA_PASSWORD も更新してください。

トークン期限切れ: まれに token.json の期限が切れます。その場合はStep 3を再実行して新しいトークンをSecretsに登録し直してください。