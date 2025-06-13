import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import gspread
import time
import datetime
import os
import shutil
import subprocess
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

async def login(page):
    await page.goto("https://spx.shopee.com.br/")
    try:
        await page.wait_for_selector('input[placeholder="Ops ID"]', timeout=15000)
        await page.fill('input[placeholder="Ops ID"]', 'Ops35683')
        await page.fill('input[placeholder="Senha"]', '@Shopee123')
        await page.click('._tYDNB')
        await page.wait_for_timeout(15000)
        try:
            await page.click('.ssc-dialog-close', timeout=20000)
        except:
            print("Nenhum pop-up foi encontrado.")
            await page.keyboard.press("Escape")
    except Exception as e:
        print(f"Erro no login: {e}")
        raise

python

Recolher

Encapsular

Executar

Copiar
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import time
import datetime
import shutil
from dotenv import load_dotenv

# Load environment variables for credentials
load_dotenv()

async def login(page):
    try:
        await page.goto("https://spx.shopee.com.br/")
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Fill login form
        await page.wait_for_selector('input[placeholder="Ops ID"]', timeout=15000)
        await page.fill('input[placeholder="Ops ID"]', os.getenv("SHOPEE_OPS_ID", "Ops35683"))
        await page.fill('input[placeholder="Senha"]', os.getenv("SHOPEE_PASSWORD", "@Shopee123"))
        await page.click('._tYDNB')  # Keep original class selector
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Handle potential pop-up
        try:
            await page.wait_for_selector('.ssc-dialog-close', timeout=10000)
            await page.click('.ssc-dialog-close')
        except PlaywrightTimeoutError:
            print("No pop-up found, attempting Escape key.")
            await page.keyboard.press("Escape")

        print("Login successful.")
    except PlaywrightTimeoutError as e:
        print(f"Timeout during login: {e}")
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise

async def get_data(page, download_dir):
    try:
        os.makedirs(download_dir, exist_ok=True)

        # Navigate to outbound list
        await page.goto("https://spx.shopee.com.br/#/staging-area-management/list/outbound")
        await page.wait_for_load_state("networkidle", timeout=10000)

        # Click export button (original XPath)
        await page.locator('/html/body/div[1]/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div/div/span/span/button').click()
        await page.wait_for_timeout(5000)  # Kept due to XPath dependency, but minimized

        # Select first option (original XPath)
        await page.wait_for_selector('/html/body/div[4]/ul/li[1]/span/div/div/span', timeout=5000)
        await page.click('/html/body/div[4]/ul/li[1]/span/div/div/span')

        # Navigate to task center
        await page.goto("https://spx.shopee.com.br/#/taskCenter/exportTaskCenter")
        await page.wait_for_load_state("networkidle", timeout=10000)

        # Click download button (original XPath)
        download_button = page.locator('//*[@id="fms-container"]/div[2]/div[2]/div/div/div/div[1]/div[8]/div/div[1]/div/div[2]/div[1]/div[1]/div[2]/div/div/div/table/tbody[2]/tr[1]/td[7]/div/div/button')
        if await download_button.count() == 0:
            raise ValueError("Download button not found")

        # Handle download
        async with page.expect_download() as download_info:
            await download_button.click()
        download = await download_info.value

        # Save and rename file
        file_path = os.path.join(download_dir, download.suggested_filename)
        await download.save_as(file_path)
        current_hour = datetime.datetime.now().strftime("%H")
        new_file_name = f"EXP-{current_hour}.csv"
        new_file_path = os.path.join(download_dir, new_file_name)
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
        shutil.move(file_path, new_file_path)
        print(f"File saved as: {new_file_path}")
        return new_file_path

    except PlaywrightTimeoutError as e:
        print(f"Timeout error in get_data: {e}")
        raise
    except Exception as e:
        print(f"Error collecting data: {e}")
        raise

def update_packing_google_sheets(download_dir):
    try:
        current_hour = datetime.datetime.now().strftime("%H")
        csv_file_name = f"EXP-{current_hour}.csv"
        csv_file_path = os.path.join(download_dir, csv_file_name)
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"File {csv_file_path} not found")

        # Google Sheets authentication
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("hxh.json", scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1hoXYiyuArtbd2pxMECteTFSE75LdgvA2Vlb6gPpGJ-g/edit?gid=0#gid=0"
        )
        worksheet = sheet.worksheet("Base SPX")

        # Read and upload CSV
        df = pd.read_csv(csv_file_path)
        df = df.fillna("")
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"File {csv_file_name} uploaded to Google Sheets successfully.")

    except FileNotFoundError as e:
        print(f"File error: {e}")
        raise
    except Exception as e:
        print(f"Error updating Google Sheets: {e}")
        raise

async def main():
    download_dir = "/tmp"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=not bool(os.getenv("DEBUG_MODE", False)))
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            await login(page)
            file_path = await get_data(page, download_dir)
            update_packing_google_sheets(download_dir)
            print("Data updated successfully.")
            await browser.close()
    except Exception as e:
        print(f"Main process error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
