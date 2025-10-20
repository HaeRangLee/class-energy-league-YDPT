import time
import datetime
# import cv2 # 실제 카메라 안 쓰므로 주석 처리
# import requests # 실제 서버 전송 안 하므로 주석 처리
import logging
# from controller_reader import generate as read_controller # 실제 API 호출 안 함
from calculate_usageIndex import UsageIndexCalculator

# --- (기본 설정) ---
# SERVER_URL = "http://your-server-address/api/upload" # 주석 처리
CLASS_ID = "1반"
# CAPTURE_PATH = "/home/pi/controller_image.jpg" # 실제 저장 안 함
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- 가짜 함수 정의 ---
def capture_image():
    """(가짜) 사진 촬영 성공했다고 가정하고 임시 파일 경로 반환"""
    logging.info("(가짜) 사진 촬영 시뮬레이션")
    return "dummy_image.jpg" # 실제 파일 없어도 됨

def read_controller(image_path: str) -> dict:
    """(가짜) Gemini API 호출 대신 미리 정의된 결과 반환"""
    
    logging.info("(가짜) Gemini 분석 시뮬레이션")
    # 테스트하고 싶은 다양한 케이스를 여기서 바꿔가며 테스트 가능
    return {'mode': '냉방', 'isOn': True, 'temperature': 18, 'fanSpeed': '강'}
    # return {'mode': 'OFF', 'isOn': False, 'temperature': 'Po', 'fanSpeed': None} # 꺼짐/결측치 테스트

def read_outdoor_sensor():
    """(가짜) 외부 온도 센서 값 반환"""
    logging.info("(가짜) 외부 온도 센서 시뮬레이션")
    return 26.0 # 테스트하고 싶은 외부 온도 설정

def send_to_server(data):
    """(가짜) 서버로 전송 대신 payload 내용 출력"""
    logging.info("(가짜) 서버 전송 시뮬레이션")
    # Firestore에 저장될 최종 데이터 형태를 확인
    payload = {
        "classId": CLASS_ID,
        "timestamp": datetime.datetime.now().isoformat(), # 실제로는 서버 타임스탬프 권장
        "temperature": data.get("temperature"),
        "mode": data.get("mode"),
        "fanSpeed": data.get("fanSpeed"),
        "isOn": data.get("isOn"),
        "usageIndex": data.get("usageIndex") # usageIndex 포함 확인
    }
    print("\n--- 서버로 전송될 Payload ---")
    print(payload)
    print("--------------------------\n")

# --- (is_operating_time 함수는 그대로 둠) ---
# def is_operating_time(): ...

def main():
    """메인 루프 (시뮬레이션)"""
    logging.info("===== IoT 시스템 시뮬레이션 시작 =====")
    calculator = UsageIndexCalculator()

    # 테스트를 위해 while True 대신 한 번만 실행하도록 변경 (또는 몇 번만 반복)
    for _ in range(2): # 예: 2번만 실행하고 종료
        logging.info("작업 주기 시작.")
        image_path = capture_image()
        outdoor_temp = read_outdoor_sensor()

        if image_path:
            data = read_controller(image_path)
            if data:
                temp_str = data.get("temperature", "Po")
                try:
                    indoor_temp = float(temp_str) if temp_str != "Po" else float('nan')
                except (ValueError, TypeError):
                    indoor_temp = float('nan')

                usage_index = calculator.calculate_usage_index(
                    mode=data.get("mode"),
                    indoor_temp_setting=indoor_temp,
                    fan_speed=data.get("fanSpeed"),
                    outdoor_temp=outdoor_temp,
                    isOn=data.get("isOn")
                )
                data['usageIndex'] = usage_index

                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                      f"상태: {'켜짐' if data.get('isOn') else '꺼짐'} | "
                      f"온도: {data.get('temperature', 'N/A')} | 모드: {data.get('mode', 'N/A')} | "
                      f"풍량: {data.get('fanSpeed', 'N/A')} | 지수: {usage_index}")

                send_to_server(data)
                logging.info("데이터 처리 완료.")
            else:
                logging.warning("컨트롤러 데이터 읽기 실패.")
        else:
            logging.warning("이미지 캡처 실패.")

        # 테스트 시에는 대기 시간 짧게 설정
        time.sleep(5) # 5초만 대기

    logging.info("===== 시뮬레이션 종료 =====")

if __name__ == "__main__":
    main()