import time
import datetime
import cv2
import requests
import logging
from controller_reader import read_controller

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
            "class_id": CLASS_ID,
            "timestamp": datetime.datetime.now().isoformat(),
            "temperature": data.get("온도"),
            "mode": data.get("모드"),
            "fan_speed": data.get("바람세기")
        }

        response = requests.post(SERVER_URL, json=payload)
        if response.status_code == 200:
            logging.info(f"서버 전송 성공: {payload}")
        else:
            logging.warning(f"서버 전송 실패: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"서버 전송 오류: {e}")

def main():
    """메인 루프 (5분 주기 촬영 및 전송)"""
    logging.info("===== IoT 에어컨 사용량 추적 시스템 시작 =====")

    while True:
        image_path = capture_image()
        if image_path:
            data = read_controller(image_path)

            # 콘솔 출력
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                  f"온도: {data['온도']}°C | 모드: {data['모드']} | 바람세기: {data['바람세기']}")

            # 서버 전송
            send_to_server(data)

        else:
            logging.warning("이미지 캡처 실패로 이번 주기 건너뜀")

        # 5분 대기 (300초)
        time.sleep(300)

if __name__ == "__main__":
    main()
