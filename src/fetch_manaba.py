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
        # 動作確認完了後は headless=True にしてOKです（今回はFalseのまま）
        browser = await p.chromium.launch(headless=True)
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
        target_button = page.locator("img[alt='未提出の課題一覧']")
        
        tasks = []
        if await target_button.count() > 0:
            print("🚀 未提出一覧ページへ移動します...")
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

                    # 締切がない場合はスキップ（または無期限として扱う）
                    if not deadline_text:
                        continue

                    # 過去の課題を除外するロジック（YYYY-MM-DD HH:MM 形式を想定）
                    try:
                        deadline_dt = datetime.strptime(deadline_text, "%Y-%m-%d %H:%M")
                        if deadline_dt < datetime.now():
                            # 期限切れはスキップ
                            continue
                        
                        # Google Tasks用にISO形式文字列に変換
                        deadline_iso = deadline_dt.isoformat()
                    except ValueError:
                        # 日付形式が違う場合はそのまま入れるか、エラーにする
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
        
        else:
            print("✅ 未提出課題はありません！")

        # --- 結果出力 ---
        print("\n" + "="*30)
        print(f"🎉 抽出された有効な課題: {len(tasks)} 件")
        # JSON形式で綺麗に出力（これを次のステップでGoogle APIに投げます）
        print(json.dumps(tasks, indent=4, ensure_ascii=False))
        print("="*30)

        # --- ★追加: ファイルに保存しておく（開発用）★ ---
        output_path = current_dir.parent / "tasks.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
        print(f"💾 データを保存しました: {output_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())