from flask import Flask, Response, request, jsonify
import json, os, time, threading
from alert_generator import generate_alert_messages
from compare_data import check_for_updates
from bs4 import BeautifulSoup

import firebase_admin
from firebase_admin import credentials, messaging

# Firebase 초기화
if not firebase_admin._apps:
    firebase_credentials_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if firebase_credentials_json:
        cred_dict = json.loads(firebase_credentials_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        raise RuntimeError("❌ 환경 변수 FIREBASE_CREDENTIALS_JSON이 설정되지 않았습니다.")

app = Flask(__name__)

# 파일 경로 상수
DATA_FILE = 'previous_data.json'
FAVORITES_FILE = 'favorites.json'
ALARM_MODE_FILE = 'alarm_modes.json'
HTML_FILE = 'ulsanpilot.html'

# HTML 기반 선박 데이터 파싱 함수
def fetch_pilot_data():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    data_list = []

    for table_id in ["cz_or_assign_s01", "cz_or_assign_s02"]:
        table = soup.find("tbody", {"id": table_id})
        if not table:
            continue

        rows = table.find_all("tr")
        for idx, row in enumerate(rows):
            cells = row.find_all("td")
            if len(cells) < 12:
                continue

            data = {
                "id": str(idx + 1),
                "status": cells[1].get_text(strip=True),
                "time": cells[3].get_text(strip=True),
                "ship_name": cells[4].get_text(strip=True),
                "from": cells[10].get_text(strip=True),
                "to": cells[11].get_text(strip=True),
                "remark": cells[19].get_text(strip=True) if len(cells) > 19 else ""
            }
            data_list.append(data)

    return data_list

# JSON 파일 로드 및 저장 관련 함수들
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default
        except json.JSONDecodeError:
            print(f"❌ {path} JSON 파싱 실패. 초기화됨.")
    return default

def save_to_file(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_previous_data():
    return load_json(DATA_FILE, [])

def load_favorites():
    return load_json(FAVORITES_FILE, {})

def load_alarm_modes():
    return load_json(ALARM_MODE_FILE, {})

def save_current_data(data):
    save_to_file(DATA_FILE, data)

def remove_token_from_storage(token):
    for file_path in [FAVORITES_FILE, ALARM_MODE_FILE]:
        data = load_json(file_path, {})
        if token in data:
            del data[token]
            save_to_file(file_path, data)
            print(f"🗑️ {file_path}에서 제거됨: {token}")

def remove_unlisted_ships_from_favorites(latest_ships):
    current_ship_names = {ship['ship_name'].strip().lower() for ship in latest_ships if ship.get('ship_name')}
    favorites = load_favorites()
    modified = False

    for token, ships in favorites.items():
        filtered = [name for name in ships if name.strip().lower() in current_ship_names]
        if len(filtered) != len(ships):
            favorites[token] = filtered
            modified = True
            print(f"🥹 즐겨창기 정리됨 ({token}): {len(ships)} → {len(filtered)}")

    if modified:
        save_to_file(FAVORITES_FILE, favorites)

# FCM 알림 전송
def send_fcm_notification(token, alert_messages, alarm_mode=False):
    print(f"📨 전송 대상 토큰: {token} / 알람 모드: {'ON' if alarm_mode else 'OFF'}")

    sound = "boat_horn" if alarm_mode else "soft_bell"

    message = messaging.Message(
        data={
            "title": "🚨 도선 선발 알림",
            "body": "\n".join(alert_messages[:3]),
            "alarm_mode": "on" if alarm_mode else "off",
            "sound": sound
        },
        android=messaging.AndroidConfig(priority='high'),
        token=token
    )

    try:
        print(f"📤 메시지 전송 시작...")
        response = messaging.send(message)
        print(f"✅ FCM 전송 성공: {response}")
    except Exception as e:
        print(f"❌ FCM 전송 실패: {e}")
        if "Requested entity was not found" in str(e):
            print(f"🗑️ 유효하지 않은 토큰 제거: {token}")
            remove_token_from_storage(token)

def send_notifications_to_users(changes, alerts):
    favorites_map = load_favorites()
    alarm_modes = load_alarm_modes()

    for token, ship_list in favorites_map.items():
        matched_alerts = [alert for alert in alerts if any(name in alert for name in ship_list)]
        if matched_alerts:
            alarm_mode = alarm_modes.get(token, False)
            send_fcm_notification(token, matched_alerts, alarm_mode)

# API 엔드포인트
@app.route('/api/pilotships')
def get_pilot_ships():
    try:
        data = fetch_pilot_data()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/checkupdates')
def check_updates():
    try:
        old = load_previous_data()
        new = fetch_pilot_data()
        changes = check_for_updates(old, new)
        alerts = generate_alert_messages(changes)
        save_current_data(new)
        remove_unlisted_ships_from_favorites(new)
        return jsonify({"status": "success", "changes": changes, "alerts": alerts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test-alert')
def test_alert():
    test_changes = {
        "status_added": [{"id": "1", "ship_name": "BLUE KINGDOM", "status": "Heavy Weather"}],
        "status_removed": [{"id": "2", "ship_name": "TP ENDEAVOUR", "status": "Dense Fog"}],
        "time_changes": [{"id": "3", "ship_name": "BELSOUTH", "before": "10:00", "after": "11:00"}],
        "removed_ships": [{"id": "4", "ship_name": "HYODONG CHEMI"}]
    }
    alerts = generate_alert_messages(test_changes)
    favorites_map = load_favorites()
    alarm_modes = load_alarm_modes()

    for token, ships in favorites_map.items():
        filtered = [a for a in alerts if any(s in a for s in ships)]
        if filtered:
            alarm_mode = alarm_modes.get(token, False)
            send_fcm_notification(token, filtered, alarm_mode)

    return jsonify({"status": "success", "alerts": alerts})

@app.route('/api/register_token', methods=['POST'])
def register_token():
    data = request.get_json()
    token = data.get("token")
    if not token:
        return jsonify({"status": "error", "message": "Missing token"}), 400
    print(f"✅ 토큰 등록됨: {token}")
    return jsonify({"status": "success"})

@app.route('/api/register_favorites', methods=['POST'])
def register_favorites():
    data = request.get_json()
    token = data.get('token')
    favorites = data.get('favorites', [])
    if not token or not isinstance(favorites, list):
        return jsonify({"status": "error", "message": "Invalid request"}), 400
    all_favorites = load_favorites()
    all_favorites[token] = favorites
    save_to_file(FAVORITES_FILE, all_favorites)
    print(f"✅ 즐겨창기 저장: {token} → {favorites}")
    return jsonify({"status": "success"})

@app.route('/api/alarm_mode', methods=['POST'])
def set_alarm_mode():
    data = request.get_json()
    token = data.get("token")
    mode = data.get("alarm_mode")
    if not token or not isinstance(mode, bool):
        return jsonify({"status": "error", "message": "Invalid request"}), 400
    modes = load_alarm_modes()
    modes[token] = mode
    save_to_file(ALARM_MODE_FILE, modes)
    print(f"✅ 알람 모드 저장: {token} → {'ON' if mode else 'OFF'}")
    return jsonify({"status": "success"})

# 백그라운드 주기 확인
def background_scheduler():
    while True:
        try:
            print("⏰ 도선 데이터 변경 확인 중...")
            old = load_previous_data()
            new = fetch_pilot_data()
            changes = check_for_updates(old, new)
            if any(changes.values()):
                alerts = generate_alert_messages(changes)
                send_notifications_to_users(changes, alerts)
                save_current_data(new)
                remove_unlisted_ships_from_favorites(new)
        except Exception as e:
            print(f"❌ 스케줄러 오류: {e}")
        time.sleep(60)

# ✅ Railway 호환을 위한 실행부
if __name__ == "__main__":
    try:
        print("🚀 초기 데이터 정리 중...")
        latest = fetch_pilot_data()
        remove_unlisted_ships_from_favorites(latest)
    except Exception as e:
        print(f"❌ 초기 처리 실패: {e}")

    threading.Thread(target=background_scheduler, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))  # Railway가 제공하는 포트 사용
    app.run(host="0.0.0.0", port=port, debug=True)
