import time
import datetime
import cv2
import requests
import logging
from controller_reader import read_controller
from calculate_usageIndex import UsageIndexCalculator
from raspberry_pi_firebase_init import initialize_firebase_admin_sdk
from firebase_admin import firestore,credentials 

# -------------------------------
# 기본 설정
# -------------------------------
CLASS_ID = "1반"                                       # 🔸 반 이름 또는 ID 수정 가능
CAPTURE_PATH = "/home/pi/controller_image.jpg"          # 🔸 이미지 임시 저장 경로 (라즈베리파이 환경에 맞게 수정)
# 로그 설정
logging.basicConfig(
    filename="controller_log.txt",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -------------------------------
# 1. Firebase 초기화 및 db 객체 생성 (전역 스코프)
# -------------------------------
db = initialize_firebase_admin_sdk() # 👈 함수를 호출하여 db 객체를 바로 받음

if db is None:
    logging.critical("Firebase 초기화 실패. 애플리케이션 종료.")
    print("Firebase 초기화 실패. 애플리케이션을 시작할 수 없습니다.")
    exit()
else:
    logging.info("Firebase Admin SDK 초기화 및 db 객체 생성 성공.")
# -------------------------------
# 2. 함수 정의
# -------------------------------

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
    
def send_to_server(data: dict):
    """분석된 데이터를 Firestore 'ac_logs' 컬렉션에 저장합니다."""
    try:
        # Firestore 문서 스키마에 맞게 최종 payload 구성
        payload = {
            "classId": CLASS_ID,
            "timestamp": firestore.SERVER_TIMESTAMP, 
            "isOn": data.get("isOn"),
            "mode": data.get("mode"),
            "temperature": data.get("temperature"),
            "fanSpeed": data.get("fanSpeed"),
            "usageIndex": data.get("usageIndex")
        }

        # ac_logs 컬렉션에 문서 추가 (자동 ID 생성)
        db.collection("ac_logs").add(payload)
        logging.info(f"Firestore 저장 성공: {payload.get('usageIndex')}")

    except Exception as e:
        logging.error(f"Firestore 저장 오류: {e}")

def read_outdoor_sensor():
    """야외 온도 센서에서 온도 읽기 (가상 함수)"""
    # 실제 센서 읽기 로직 필요
    outdoor_temp = 25.0  # 예시 값
    logging.info(f"야외 온도 읽기: {outdoor_temp}°C")
    return outdoor_temp

def main():
    logging.info("===== IoT 에어컨 추적 시스템 시작 =====")

    # 1. 루프 시작 *전*에 계산기 인스턴스를 생성합니다
    calculator = UsageIndexCalculator()

    if True:
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
               
                # 서버 전송
                send_to_server(data)
                logging.info("데이터 처리 완료.")

            else:
                logging.warning("이미지 캡처 실패로 이번 주기 건너뜀")

if __name__ == "__main__":
    if db:
        logging.info("Firebase Admin SDK가 준비되었습니다. 메인 작업을 시작합니다.")
        main()
    else :
        logging.critical("db 객체가 초기화되지 않았습니다. 작업을 시작할 수 없습니다.")