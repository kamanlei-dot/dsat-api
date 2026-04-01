from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, List
from playwright.async_api import async_playwright
import asyncio
import time
import uvicorn   # ← 這一行必須加上！

app = FastAPI(title="DSAT 學時查詢 API")

class QueryRequest(BaseModel):
    編號: str
    身份證號碼: str


async def query_dsat_hours(編號: str, 身份證號碼: str) -> Dict[str, Any]:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, slow_mo=400)
            page = await browser.new_page()

            print(f"[INFO] 開始查詢 → 編號: {編號}")

            await page.goto('https://www.dsat.gov.mo/car_new/exam.aspx?language=c',
                            wait_until='networkidle', timeout=60000)

            await page.wait_for_selector("input[name='ExamTypeD']", timeout=30000)
            await page.click("input[name='ExamTypeD']")
            await page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(2)

            clean_id = ''.join(c for c in 身份證號碼 if c.isalnum())

            await page.wait_for_selector("input[name='RegisterNO']", timeout=30000)
            await page.fill("input[name='RegisterNO']", 編號.strip())

            await page.wait_for_selector("input[name='IDNo']", timeout=30000)
            await page.fill("input[name='IDNo']", clean_id)

            await page.click("input[name='btnSearch02']")
            await page.wait_for_load_state('networkidle', timeout=45000)
            await asyncio.sleep(3)

            await page.wait_for_selector('#gvDrivingPracticeSummary', timeout=30000)

            summary = {}
            summary_table = page.locator("#gvDrivingPracticeSummary")
            if await summary_table.count() > 0:
                rows = await summary_table.locator("tr").all()
                if len(rows) > 1:
                    cells = await rows[1].locator("td").all()
                    if len(cells) >= 5:
                        summary = {
                            "場內": (await cells[0].inner_text()).strip(),
                            "場外": (await cells[1].inner_text()).strip(),
                            "累計實習學時": (await cells[2].inner_text()).strip(),
                            "最低學時要求": (await cells[3].inner_text()).strip(),
                            "是否符合最低學時要求": (await cells[4].inner_text()).strip()
                        }

            details: List[Dict] = []
            detail_table = page.locator("#gvDrivingPracticeRecord")
            if await detail_table.count() > 0:
                rows = await detail_table.locator("tr").all()
                for row in rows[1:]:
                    cells = await row.locator("td").all()
                    if len(cells) >= 8:
                        end_cell = cells[4]
                        end_time = (await end_cell.inner_text()).strip()
                        span = end_cell.locator("span")
                        if await span.count() > 0:
                            end_time = (await span.inner_text()).strip()

                        details.append({
                            "登錄日期": (await cells[0].inner_text()).strip(),
                            "教學單位": (await cells[1].inner_text()).strip(),
                            "教練員": (await cells[2].inner_text()).strip(),
                            "開始時間": (await cells[3].inner_text()).strip(),
                            "結束時間": end_time,
                            "場內": (await cells[5].inner_text()).strip(),
                            "場外": (await cells[6].inner_text()).strip(),
                            "備註": (await cells[7].inner_text()).strip() or "—"
                        })

            await browser.close()

            return {
                "success": True,
                "編號": 編號,
                "身份證號碼": 身份證號碼,
                "總結": summary,
                "詳細記錄": details,
                "達標": "是" if summary.get("是否符合最低學時要求") == "符合" else "否",
                "查詢時間": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    except Exception as e:
        print(f"[ERROR] 查詢失敗: {e}")
        return {
            "success": False,
            "error": str(e),
            "編號": 編號,
            "身份證號碼": 身份證號碼
        }


@app.post("/query")
async def query_dsat(req: QueryRequest):
    result = await query_dsat_hours(req.編號, req.身份證號碼)
    return result


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
