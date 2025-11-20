import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- 設定読み込み ---
current_dir = Path(__file__).resolve().parent
base_dir = current_dir.parent
env_path = base_dir / "setting.env"
load_dotenv(dotenv_path=env_path)

# 定数
SCOPES = ['https://www.googleapis.com/auth/tasks']
CREDENTIALS_FILE = base_dir / 'credentials.json'
TOKEN_FILE = base_dir / 'token.json'
TASKS_DATA_FILE = base_dir / 'tasks.json'
TASK_LIST_ID = os.getenv("GOOGLE_TASK_LIST_ID")

def get_service():
    """Google API 認証サービス"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                print("トークン期限切れ。再認証が必要です（ローカルで実行してください）")
                return None
        else:
            print("トークンが見つかりません（ローカルで実行してください）")
            return None

    return build('tasks', 'v1', credentials=creds)

def convert_to_rfc3339(date_str):
    """
    manabaの日時文字列 (YYYY-MM-DDTHH:MM:SS) を
    Google Tasks用のRFC3339形式 (UTC) に変換する
    """
    try:
        # manabaは日本時間 (JST) なので、Timezone情報を付与してUTCに変換
        dt_jst = datetime.fromisoformat(date_str)
        # JST (+09:00) を設定
        jst = timezone(timedelta(hours=9))
        dt_jst = dt_jst.replace(tzinfo=jst)
        
        # UTCに変換して文字列化 (Zをつける)
        dt_utc = dt_jst.astimezone(timezone.utc)
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    except ValueError:
        return None

def main():
    if not TASK_LIST_ID:
        print("エラー: setting.env に GOOGLE_TASK_LIST_ID が設定されていません。")
        return

    # 1. tasks.json の読み込み
    if not os.path.exists(TASKS_DATA_FILE):
        print("tasks.json が見つかりません。先に fetch_manaba.py を実行してください。")
        return
    
    with open(TASKS_DATA_FILE, "r", encoding="utf-8") as f:
        new_tasks = json.load(f)
    
    print(f"📂 tasks.json から {len(new_tasks)} 件のデータを読み込みました。")

    # 2. Google API 接続
    service = get_service()
    if not service:
        return

    # 3. 既存タスクの取得 (重複チェック用)
    print("🔍 既存のタスクを確認中...")
    existing_tasks = []
    page_token = None
    while True:
        results = service.tasks().list(
            tasklist=TASK_LIST_ID,
            showCompleted=True,
            showHidden=True,
            maxResults=100,
            pageToken=page_token
        ).execute()
        
        items = results.get('items', [])
        for item in items:
            existing_tasks.append(item['title'])
            
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    print(f"✅ 現在登録済みのタスク数: {len(existing_tasks)}")

    # 4. 新規タスクの登録
    added_count = 0
    for item in new_tasks:
        # タイトルを整形: [コース名] 課題名
        task_title = f"[{item['course']}] {item['title']}"
        
        # 重複チェック
        if task_title in existing_tasks:
            print(f"  skip: {task_title} (登録済み)")
            continue

        # 期限の変換
        due_date = convert_to_rfc3339(item['deadline'])
        
        # API用ボディ作成
        task_body = {
            'title': task_title,
            'notes': f"{item['url']}\n(Auto added from manaba)",
        }
        
        if due_date:
            task_body['due'] = due_date

        # APIリクエスト実行
        try:
            service.tasks().insert(tasklist=TASK_LIST_ID, body=task_body).execute()
            print(f"  🆕 ADD: {task_title}")
            added_count += 1
        except Exception as e:
            print(f"  ❌ Error adding {task_title}: {e}")

    print("="*30)
    print(f"🎉 処理完了！ {added_count} 件のタスクを新規追加しました。")
    print("Google Calendar (Tasksカレンダー) を確認してください。")

if __name__ == '__main__':
    main()