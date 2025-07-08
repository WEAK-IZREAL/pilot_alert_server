from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def fetch_pilot_data():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(executable_path='C:/Users/leeja/chromedriver-win64/chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=options)

    driver.get('http://www.ulsanpilot.co.kr/main/pilot_forecast.php')

    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.comm_table tbody#cz_or_assign_s01 tr')))

    rows = driver.find_elements(By.CSS_SELECTOR, 'table.comm_table tbody#cz_or_assign_s01 tr')
    data_list = []

    for row in rows:
        cells = row.find_elements(By.TAG_NAME, 'td')
        if len(cells) < 5:
            continue
        data = {
            "id": cells[0].text.strip(),
            "status": cells[1].text.strip(),
            "time": cells[3].text.strip(),
            "ship_name": cells[4].text.strip(),
            "from": cells[10].text.strip() if len(cells) > 10 else "",
            "to": cells[11].text.strip() if len(cells) > 11 else "",
            "remark": cells[19].text.strip() if len(cells) > 19 else ""
        }
        data_list.append(data)

    driver.quit()
    return data_list