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
    # 1. ローカルファイルの確認
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    # 2. 環境変数 (GitHub Secrets) の確認
    elif os.getenv("GOOGLE_TOKEN_JSON"):
        try:
            info = json.loads(os.getenv("GOOGLE_TOKEN_JSON"))
            creds = Credentials.from_authorized_user_info(info, SCOPES)
        except Exception as e:
            print(f"環境変数の読み込みエラー: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                return None
        else:
            return None
    return build('tasks', 'v1', credentials=creds)

def convert_to_rfc3339(date_str):
    """manabaの日時文字列をGoogle Tasks用の形式に変換"""
    try:
        dt_jst = datetime.fromisoformat(date_str)
        jst = timezone(timedelta(hours=9))
        dt_jst = dt_jst.replace(tzinfo=jst)
        dt_utc = dt_jst.astimezone(timezone.utc)
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    except ValueError:
        return None

def format_time_str(date_str):
    """日時文字列から時間部分(HH:MM)だけを抜き出す"""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%H:%M")
    except ValueError:
        return None

def main():
    print(f"DEBUG: TASK_LIST_ID Status = {'OK' if TASK_LIST_ID else 'None'}")

    if not TASK_LIST_ID:
        print("エラー: GOOGLE_TASK_LIST_ID が設定されていません。")
        return

    if not os.path.exists(TASKS_DATA_FILE):
        print("tasks.json が見つかりません。先に fetch_manaba.py を実行してください。")
        return
    
    with open(TASKS_DATA_FILE, "r", encoding="utf-8") as f:
        new_tasks = json.load(f)
    
    print(f"📂 tasks.json から {len(new_tasks)} 件のデータを読み込みました。")

    service = get_service()
    if not service:
        print("Google Tasks APIへの接続に失敗しました。")
        return

    # 既存タスク取得
    print("🔍 既存のタスクを確認中...")
    existing_tasks = []
    page_token = None
    while True:
        results = service.tasks().list(tasklist=TASK_LIST_ID, showCompleted=True, showHidden=True, maxResults=100, pageToken=page_token).execute()
        items = results.get('items', [])
        for item in items:
            existing_tasks.append(item['title'])
        page_token = results.get('nextPageToken')
        if not page_token: break
            
    print(f"✅ 現在登録済みのタスク数: {len(existing_tasks)}")

    # 新規登録
    added_count = 0
    for item in new_tasks:
        # 時間文字列を取得 (例: "18:00")
        time_str = format_time_str(item['deadline'])
        
        # タイトルに時間を含める: "[18:00] [コース名] 課題名"
        if time_str:
            task_title = f"[{time_str}] [{item['course']}] {item['title']}"
        else:
            task_title = f"[{item['course']}] {item['title']}"
        
        if task_title in existing_tasks:
            print(f"  skip: {task_title} (登録済み)")
            continue

        due_date = convert_to_rfc3339(item['deadline'])
        
        task_body = {
            'title': task_title,
            'notes': f"{item['url']}\n(Auto added from manaba)"
        }
        
        # 期限日も設定
        if due_date:
            task_body['due'] = due_date

        try:
            service.tasks().insert(tasklist=TASK_LIST_ID, body=task_body).execute()
            print(f"  🆕 ADD: {task_title}")
            added_count += 1
        except Exception as e:
            print(f"  ❌ Error adding {task_title}: {e}")

    print("="*30)
    print(f"🎉 処理完了！ {added_count} 件のタスクを新規追加しました。")

if __name__ == '__main__':
    main()