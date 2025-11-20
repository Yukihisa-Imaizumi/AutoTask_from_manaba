import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# .envファイルからログイン情報を読み込む
load_dotenv()
USERNAME = os.getenv("MANABA_USERNAME")
PASSWORD = os.getenv("MANABA_PASSWORD")

if not USERNAME or not PASSWORD:
    print("エラー: .envファイルに MANABA_USERNAME と MANABA_PASSWORD を設定してください")
    exit()

async def run():
    async with async_playwright() as p:
        # headless=False にするとブラウザが立ち上がるのが見えます（デバッグ用）
        # GitHub Actionsでは True にします
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()

        print("🔄 manabaにアクセス中...")
        # 筑波大manabaのトップページへ
        await page.goto("https://manaba.tsukuba.ac.jp/")

        # 「ログイン」ボタンがある場合をクリック（manabaのトップにある場合）
        # 既にログイン済みや、直接IdPに飛ぶ場合を考慮してtry-exceptにするか、
        # ページ遷移を待ちます。通常は統一認証へリダイレクトされます。
        
        # 統一認証システムの画面か確認 (URLやタイトルで判定)
        try:
            # ページが完全に読み込まれるまで待機
            await page.wait_for_load_state("networkidle")
            
            print(f"TITLE: {await page.title()}")

            # 統一認証の入力フォームを探して入力
            # ※セレクタ（HTMLのIDやClass）は変更される可能性があります
            # 一般的なname属性を探します
            if "idp" in page.url or "auth" in page.url:
                print("🔑 統一認証画面を検出。ログインを試みます...")
                
                # ユーザー名入力 (name="j_username" などを想定)
                # 多くのIdPで共通のセレクタ、もしくは placeholder や label から探す
                await page.get_by_label("User ID").or_(page.locator("input[type='text']").first).fill(USERNAME)
                
                # パスワード入力
                await page.get_by_label("Password").or_(page.locator("input[type='password']")).fill(PASSWORD)
                
                # ログインボタン押下 (type="submit" を探す)
                await page.locator("button[type='submit'], input[type='submit']").click()
                
                # ログイン後の遷移を待機
                await page.wait_for_load_state("networkidle")

        except Exception as e:
            print(f"⚠️ ログイン処理中にエラーまたは既にログイン済み: {e}")

        # ログイン成功の確認（マイページにいるか？）
        if "home" in page.url or "コース一覧" in await page.content():
            print("✅ ログイン成功！マイページに到達しました。")
            
            # --- ここで課題情報の取得テスト ---
            # manabaのマイページ右側などにある「未提出課題（リマインダ）」を取得してみる
            # ※デザインによってセレクタが異なるため、まずはコース名一覧を取得して検証
            
            print("\n--- 履修コース一覧 (テスト取得) ---")
            # コース名のリンクを取得 (一般的なmanabaの構造: .course-title a)
            courses = page.locator(".course-title a")
            count = await courses.count()
            
            for i in range(count):
                course_name = await courses.nth(i).inner_text()
                print(f"- {course_name}")
                
            # スクリーンショットを撮って保存（動作確認用）
            await page.screenshot(path="manaba_result.png")
            print("\n📷 スクリーンショットを保存しました: manaba_result.png")

        else:
            print("❌ ログインに失敗したか、ページ構造が想定と異なります。")
            print(f"現在のURL: {page.url}")
            await page.screenshot(path="error.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())