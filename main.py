import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import gspread
import datetime
import os
import shutil
from google.oauth2.service_account import Credentials

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
            print("Nenhum pop-up foi encontrado. Tentando fechar com ESC.")
            await page.keyboard.press("Escape")
    except Exception as e:
        print(f"[LOGIN] Erro no login: {e}")
        raise

async def get_data(page, download_dir):
    try:
        os.makedirs(download_dir, exist_ok=True)

        # Navega para a lista outbound
        await page.goto("https://spx.shopee.com.br/#/staging-area-management/list/outbound")
        await page.wait_for_load_state("networkidle", timeout=10000)

        # Clica no botão de exportar
        await page.locator('xpath=/html/body/div[1]/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div/div/span/span/button').click()
        await page.wait_for_timeout(5000)

        # Seleciona a primeira opção
        await page.wait_for_selector('xpath=//div[@class="ssc-react-tooltip-reference"]//span[contains(text(),"Exportar")]', timeout=15000)
        await page.click('xpath=//div[@class="ssc-react-tooltip-reference"]//span[contains(text(),"Exportar")')

        # Vai para o Task Center
        await page.goto("https://spx.shopee.com.br/#/taskCenter/exportTaskCenter")
        await page.wait_for_load_state("networkidle", timeout=10000)

        # Botão de download
        download_button = page.locator('xpath=//*[@id="fms-container"]/div[2]/div[2]/div/div/div/div[1]/div[8]/div/div[1]/div/div[2]/div[1]/div[1]/div[2]/div/div/div/table/tbody[2]/tr[1]/td[7]/div/div/button')
        if await download_button.count() == 0:
            raise ValueError("[DOWNLOAD] Botão de download não encontrado")

        # Espera e captura o download
        async with page.expect_download() as download_info:
            await download_button.click()
        download = await download_info.value

        # Salva o arquivo
        file_path = os.path.join(download_dir, download.suggested_filename)
        await download.save_as(file_path)

        # Renomeia com base na hora
        current_hour = datetime.datetime.now().strftime("%H")
        new_file_name = f"EXP-{current_hour}.csv"
        new_file_path = os.path.join(download_dir, new_file_name)

        if os.path.exists(new_file_path):
            os.remove(new_file_path)

        shutil.move(file_path, new_file_path)
        print(f"[DOWNLOAD] Arquivo salvo como: {new_file_path}")
        return new_file_path

    except PlaywrightTimeoutError as e:
        print(f"[TIMEOUT] Erro de timeout em get_data: {e}")
        raise
    except Exception as e:
        print(f"[ERRO] Falha ao coletar dados: {e}")
        raise

def update_packing_google_sheets(download_dir):
    try:
        current_hour = datetime.datetime.now().strftime("%H")
        csv_file_name = f"EXP-{current_hour}.csv"
        csv_file_path = os.path.join(download_dir, csv_file_name)
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"[ARQUIVO] Arquivo não encontrado: {csv_file_path}")

        # Autenticação com Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("hxh.json", scopes=scope)
        client = gspread.authorize(creds)

        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1hoXYiyuArtbd2pxMECteTFSE75LdgvA2Vlb6gPpGJ-g/edit?gid=0#gid=0")
        worksheet = sheet.worksheet("Base SPX")

        # Carrega CSV e envia
        df = pd.read_csv(csv_file_path)
        df.fillna("", inplace=True)
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())

        print(f"[GOOGLE SHEETS] Upload do arquivo {csv_file_name} concluído com sucesso.")

    except FileNotFoundError as e:
        print(f"[ERRO] Arquivo não encontrado: {e}")
        raise
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar o Google Sheets: {e}")
        raise

async def main():
    download_dir = "/tmp"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            #await login(page)
            #await get_data(page, download_dir)
            print("Chamando Selenium...")
            subprocess.run(["python", "download.py"])
            update_packing_google_sheets()
            print("Dados atualizados com sucesso.")
            await browser.close()
    except Exception as e:
        print(f"Erro durante o processo: {e}")

if __name__ == "__main__":
    asyncio.run(main())
