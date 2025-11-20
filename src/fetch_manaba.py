import asyncio
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# --- 設定読み込み ---
current_dir = Path(__file__).resolve().parent
env_path = current_dir.parent / "setting.env"
load_dotenv(dotenv_path=env_path)

USERNAME = os.getenv("MANABA_USERNAME")
PASSWORD = os.getenv("MANABA_PASSWORD")

async def run():
    async with async_playwright() as p:
        # 動作確認のため headless=True (本番設定)
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        print("🔄 manabaにログイン中...")
        await page.goto("https://manaba.tsukuba.ac.jp/")

        # --- ログイン処理 ---
        try:
            if "idp" in page.url or "auth" in page.url:
                await page.get_by_label("User ID").or_(page.locator("input[type='text']").first).fill(USERNAME)
                await page.get_by_label("Password").or_(page.locator("input[type='password']")).fill(PASSWORD)
                await page.locator("button[type='submit'], input[type='submit']").click()
                await page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"⚠️ ログイン処理: {e}")

        # --- 未提出課題一覧へ ---
        print("🚀 「未提出の課題一覧」ボタンを探しています...")
        
        tasks = []
        
        button_selector = "img[alt='未提出の課題一覧']"
        target_button = page.locator(button_selector)
        
        try:
            # ボタンが表示されるまで最大15秒待つ
            await page.wait_for_selector(button_selector, state="visible", timeout=15000)
            
            print("✅ ボタンを発見！クリックして一覧ページへ飛びます。")
            await target_button.click()
            await page.wait_for_load_state("domcontentloaded")

            # テーブル行を取得
            rows = await page.locator(".stdlist tr").all()
            print(f"📊 {len(rows)-1} 件の行を解析中...")

            for row in rows[1:]: # ヘッダー行スキップ
                cells = await row.locator("td").all()
                
                # 列数が足りない場合はスキップ
                if len(cells) < 5:
                    continue

                try:
                    # 1列目: 種別（不要なら無視）
                    # 2列目: 課題名とURL
                    title_cell = cells[1]
                    assignment_title = await title_cell.inner_text()
                    assignment_title = assignment_title.strip()
                    
                    link = title_cell.locator("a").first
                    url = await link.get_attribute("href") if await link.count() > 0 else ""

                    # 3列目: コース名
                    course_name = await cells[2].inner_text()
                    course_name = course_name.strip()

                    # 5列目: 締切日時
                    deadline_text = await cells[4].inner_text()
                    deadline_text = deadline_text.strip()

                    # 締切がない場合はスキップ
                    if not deadline_text:
                        continue

                    # 過去の課題を除外するロジック
                    try:
                        deadline_dt = datetime.strptime(deadline_text, "%Y-%m-%d %H:%M")
                        if deadline_dt < datetime.now():
                            continue
                        deadline_iso = deadline_dt.isoformat()
                    except ValueError:
                        deadline_iso = deadline_text

                    # データの整形
                    tasks.append({
                        "course": course_name,
                        "title": assignment_title,
                        "deadline": deadline_iso,
                        "url": url
                    })

                except Exception as e:
                    print(f"行解析エラー: {e}")

        except Exception as e:
            print(f"❌ エラー: ボタンが見つからないか、タイムアウトしました: {e}")
            # エラー時はtasksは空のまま進む

        # --- 結果出力 ---
        print("\n" + "="*30)
        print(f"🎉 抽出された有効な課題: {len(tasks)} 件")
        print(json.dumps(tasks, indent=4, ensure_ascii=False))
        print("="*30)

        # --- ファイル保存 ---
        output_path = current_dir.parent / "tasks.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
        print(f"💾 データを保存しました: {output_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())