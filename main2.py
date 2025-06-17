import asyncio
from playwright.async_api import async_playwright
import time
import datetime
import os
import shutil
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

DOWNLOAD_DIR = "/tmp"

def rename_downloaded_file(download_dir, download_path):
    try:
        current_hour = datetime.datetime.now().strftime("%H")
        new_file_name = f"EXP-{current_hour}.csv"
        new_file_path = os.path.join(download_dir, new_file_name)
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
        shutil.move(download_path, new_file_path)
        print(f"Arquivo salvo como: {new_file_path}")
        return new_file_path
    except Exception as e:
        print(f"Erro ao renomear o arquivo: {e}")
        return None

def update_packing_google_sheets(csv_file_path):
    try:
        if not os.path.exists(csv_file_path):
            print(f"Arquivo {csv_file_path} não encontrado.")
            return
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("hxh.json", scope)
        client = gspread.authorize(creds)
        sheet1 = client.open_by_url("https://docs.google.com/spreadsheets/d/1hoXYiyuArtbd2pxMECteTFSE75LdgvA2Vlb6gPpGJ-g/edit?gid=0#gid=0")
        worksheet1 = sheet1.worksheet("Base SPX")
        df = pd.read_csv(csv_file_path)
        df = df.fillna("")
        worksheet1.clear()
        worksheet1.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"Arquivo enviado com sucesso para a aba 'EXP'.")
        time.sleep(5)
    except Exception as e:
        print(f"Erro durante o processo: {e}")

async def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"])
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        try:
            # LOGIN
            await page.goto("https://spx.shopee.com.br/")
            await page.wait_for_selector('xpath=//*[@placeholder="Ops ID"]', timeout=15000)
            await page.locator('xpath=//*[@placeholder="Ops ID"]').fill('Ops35683')
            await page.locator('xpath=//*[@placeholder="Senha"]').fill('@Shopee123')
            await page.locator('xpath=/html/body/div[1]/div/div[2]/div/div/div[1]/div[3]/form/div/div/button').click()
            await page.wait_for_timeout(15000)
            try:
                await page.locator('.ssc-dialog-close').click(timeout=5000)
            except:
                print("Nenhum pop-up foi encontrado.")
                await page.keyboard.press("Escape")
            
            # NAVEGAÇÃO E DOWNLOAD
            await page.goto("https://spx.shopee.com.br/#/staging-area-management/list/outbound")
            await page.wait_for_timeout(8000)
            await page.locator('xpath=/html/body/div[1]/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div/div/span/span/button').click()
            await page.wait_for_timeout(8000)
            await page.locator('xpath=/html[1]/body[1]/div[3]/ul[1]/li[1]/span[1]/div[1]/div[1]/span[1]').click()
            await page.wait_for_timeout(8000)
            await page.goto("https://spx.shopee.com.br/#/taskCenter/exportTaskCenter")
            await page.wait_for_timeout(15000)


            
            # Use async with para download
            async with page.expect_download() as download_info:
                await page.locator('xpath=/html[1]/body[1]/div[1]/div[1]/div[2]/div[2]/div[1]/div[1]/div[1]/div[1]/div[8]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/table[1]/tbody[2]/tr[1]/td[7]/div[1]/div[1]/button[1]/span[1]/span[1]', timeout=30000).click()
            download = await download_info.value
            download_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
            await download.save_as(download_path)
            new_file_path = rename_downloaded_file(DOWNLOAD_DIR, download_path)
            

            """
            # Clica no primeiro <span> com texto "Download"
            await page.wait_for_selector('button.ssc-button.action-link', timeout=60000)
            buttons = await page.locator('button.ssc-button.action-link').all()
            print("Quantidade de botões encontrados:", len(buttons))
            # Opcional: iterar e clicar no que tem "Download"
            for i in range(len(buttons)):
                btn = page.locator('button.ssc-button.action-link').nth(i)
                span_text = await btn.inner_text()
                print(f"Botão {i}: {span_text}")
                if "Download" in span_text:
                    async with page.expect_download() as download_info:
                        await btn.click()
                    download = await download_info.value
                    download_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
                    await download.save_as(download_path)
                    print("Download concluído!")
                    break
            """

            # Atualizar Google Sheets (opcional)
            if new_file_path:
                update_packing_google_sheets(new_file_path)
                print("Dados atualizados com sucesso.")
        except Exception as e:
            print(f"Erro durante o processo: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
