import requests
from bs4 import BeautifulSoup

def fetch_pilot_data():
    url = "http://www.ulsanpilot.co.kr/main/pilot_forecast.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'

    if response.status_code != 200:
        raise Exception(f"❌ 요청 실패: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "table_list"})

    if table is None:
        raise Exception("❌ 테이블을 찾을 수 없습니다.")

    rows = table.find_all("tr")[1:]  # 첫 번째 tr은 헤더이므로 제외
    ships = []

    for idx, row in enumerate(rows):
        cols = row.find_all("td")
        if len(cols) < 6:
            continue  # 데이터가 부족한 경우 스킵

        ship_data = {
            "id": str(idx + 1),
            "status": cols[0].text.strip(),
            "time": cols[1].text.strip(),
            "ship_name": cols[2].text.strip(),
            "from": cols[3].text.strip(),
            "to": cols[4].text.strip(),
            "remark": cols[5].text.strip()
        }
        ships.append(ship_data)

    return ships

# ✅ 확인용 출력
if __name__ == "__main__":
    ships = fetch_pilot_data()
    for ship in ships:
        print(ship)
