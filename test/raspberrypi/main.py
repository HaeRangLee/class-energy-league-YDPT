import time
import logging
from firebase_handler import FirebaseHandler
import controller_reader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 설정 파일 로드 ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    # config 딕셔너리에서 각 설정값을 변수로 저장
    CLASS_ID = config['CLASS_ID']
    KEY_PATH = config['KEY_PATH']
    NORMAL_INTERVAL = config['NORMAL_INTERVAL_SECONDS']
    RETRY_INTERVAL = config['RETRY_INTERVAL_SECONDS']

except FileNotFoundError:
    print("오류: config.json 파일을 찾을 수 없습니다. 프로그램을 종료합니다.")
    exit() # 설정 파일이 없으면 실행이 불가능하므로 종료
except KeyError as e:
    print(f"오류: config.json 파일에 필요한 설정값({e})이 없습니다. 프로그램을 종료합니다.")
    exit()
# --------------------


def main():
    fb_handler = FirebaseHandler(KEY_PATH)
    logging.info(f"[{CLASS_ID}반] 데이터 수집을 시작합니다.")

    while True:
        try: 
            
            ac_data = controller_reader.read_ac_status()

            if ac_data:
                logging.info("컨트롤러 데이터 읽기 성공.")
                ac_data['classId'] = CLASS_ID
                fb_handler.send_ac_data(ac_data)
                
                logging.info(f"다음 작업을 위해 {NORMAL_INTERVAL}초 대기합니다.")
                time.sleep(NORMAL_INTERVAL)
            else:
                logging.warning(f"컨트롤러 데이터 읽기 실패. {RETRY_INTERVAL}초 후 재시도합니다.")
                time.sleep(RETRY_INTERVAL)

        except Exception as e:
            logging.critical(f"메인 루프에서 예측 불가능한 에러 발생: {e}")
            logging.critical(f"프로그램을 계속 실행하기 위해 {RETRY_INTERVAL}초 후 재시도합니다.")
            time.sleep(RETRY_INTERVAL)


if __name__ == "__main__":
    main()