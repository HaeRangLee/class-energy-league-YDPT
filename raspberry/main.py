import time
import datetime
import cv2
import requests
import logging
from controller_reader import read_controller
from calculate_usageIndex import UsageIndexCalculator
from raspberry_pi_firebase_init import initialize_firebase_admin_sdk
from firebase_admin import firestore

# -------------------------------
# 기본 설정
# -------------------------------
SERVER_URL = "http://your-server-address/api/upload"   # 🔸 서버 주소 직접 수정
CLASS_ID = "1반"                                       # 🔸 반 이름 또는 ID 수정 가능
CAPTURE_PATH = "/home/pi/controller_image.jpg"          # 🔸 이미지 임시 저장 경로 (라즈베리파이 환경에 맞게 수정)

# 로그 설정
logging.basicConfig(
    filename="controller_log.txt",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def capture_image():
    """라즈베리파이 카메라로 컨트롤러 사진 촬영"""
    try:
        cam = cv2.VideoCapture(0)
        time.sleep(2)  # 카메라 초기화 대기
        ret, frame = cam.read()
        if not ret:
            raise Exception("카메라에서 영상을 읽을 수 없습니다.")
        cv2.imwrite(CAPTURE_PATH, frame)
        cam.release()
        logging.info("사진 촬영 완료")
        return CAPTURE_PATH
    except Exception as e:
        logging.error(f"사진 촬영 실패: {e}")
        return None
    

def send_to_server(data):
    """서버로 인식 결과 전송"""
    try:
        payload = {
            "classId": CLASS_ID,
            "timestamp": datetime.datetime.now().isoformat(),
            "temperature": data.get("온도"),
            "mode": data.get("모드"),
            "fanSpeed": data.get("바람세기"),
            "usageIndex": data.get("사용량지수", 8)
        }

        response = requests.post(SERVER_URL, json=payload)
        if response.status_code == 200:
            logging.info(f"서버 전송 성공: {payload}")
        else:
            logging.warning(f"서버 전송 실패: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"서버 전송 오류: {e}")

def read_outdoor_sensor():
    """야외 온도 센서에서 온도 읽기 (가상 함수)"""
    # 실제 센서 읽기 로직 필요
    outdoor_temp = 25.0  # 예시 값
    logging.info(f"야외 온도 읽기: {outdoor_temp}°C")
    return outdoor_temp


def is_operating_time():
    """현재 시간이 작동해야 하는 시간인지 확인하는 함수"""
    now = datetime.datetime.now()
    weekday = now.weekday() # 월요일=0, 화요일=1, ..., 금요일=4, 토요일=5, 일요일=6
    current_hour = now.hour

    # 평일(월~금)인지 확인
    if 0 <= weekday <= 4:
        # 시작 시간(오전 8시) 확인
        if current_hour >= 8:
            # 월/수/금 종료 시간(15시 미만) 확인
            if weekday in [0, 2, 4] and current_hour < 15: # 월(0), 수(2), 금(4)
                return True
            # 화/목 종료 시간(16시 미만) 확인
            elif weekday in [1, 3] and current_hour < 16: # 화(1), 목(3)
                return True
    # 그 외의 경우는 작동 시간 아님
    return False

def main():
    """메인 루프"""
    logging.info("===== IoT 에어컨 추적 시스템 시작 =====")

    # 1. 루프 시작 *전*에 계산기 인스턴스를 생성합니다
    calculator = UsageIndexCalculator()

    while True:
        # 작동 시간인지 확인 (필요 없으면 확인 로직 제거)
        # if is_operating_time():
        logging.info("작동 시간 확인됨. 작업 시작.")
        image_path = capture_image()
        outdoor_temp = read_outdoor_sensor() # 외부 온도 가져오기

        if image_path:
            # 2. OCR/Gemini로부터 데이터 딕셔너리를 받습니다
            data = read_controller(image_path)

            # 계속 진행하기 전에 data가 비어있지 않은지 확인
            if data:
                # 3. 'Po' 온도 값 처리 - NaN 또는 기본값으로 취급
                temp_str = data.get("temperature", "Po")
                try:
                    # 'Po'가 아니면 float으로 변환, 'Po'면 NaN으로 변환
                    indoor_temp = float(temp_str) if temp_str != "Po" else float('nan')
                except (ValueError, TypeError):
                    indoor_temp = float('nan') # 변환 실패 시 NaN으로 처리

                # 4. *인스턴스*에서 calculate_usage_index 메서드를 호출합니다
                usage_index = calculator.calculate_usage_index(
                    mode=data.get("mode"), # 키가 없으면 None 전달
                    indoor_temp_setting=indoor_temp,
                    fan_speed=data.get("fanSpeed"), # 키가 없으면 None 전달
                    outdoor_temp=outdoor_temp,
                    is_on=data.get("isOn") # 키가 없으면 None 전달
                )
                # 5. 계산된 지수를 데이터 딕셔너리에 추가합니다
                data['usageIndex'] = usage_index           
               
                # 콘솔 출력 (키 이름은 Gemini 결과에 맞게)
                # print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                #       f"상태: {'켜짐' if data.get('isOn') else '꺼짐'} | "
                #       f"온도: {data.get('temperature', 'N/A')} | 모드: {data.get('mode', 'N/A')} | 바람세기: {data.get('fanSpeed', 'N/A')}")

                # 서버 전송 (실제 서버 URL 및 로직 필요)
                send_to_server(data)
                logging.info("데이터 처리 완료.")

            else:
                logging.warning("이미지 캡처 실패로 이번 주기 건너뜀")

            # 다음 작업까지 5분 대기
            sleep_duration = 300

        else:
            # 작동 시간이 아니면 로그 남기고 잠시 대기 후 다시 확인
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"{now_str} - 작동 시간 아님. 대기 중...")
            # 1분(60초)마다 시간 체크
            sleep_duration = 60

        time.sleep(sleep_duration)

if __name__ == "__main__":
    if initialize_firebase_admin_sdk():
        logging.info("Firebase Admin SDK 초기화 성공. 메인 애플리케이션 시작.")
        #main()
        camera_path = capture_image
    else :
        logging.critical("Firebase Admin SDK 초기화 실패. 애플리케이션 종료.")
        print("Firebase Admin SDK 초기화 실패. 애플리케이션을 시작할 수 없습니다.")