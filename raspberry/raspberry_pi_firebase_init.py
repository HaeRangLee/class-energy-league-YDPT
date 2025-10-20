import firebase_admin
from firebase_admin import credentials
import os
import logging # logging import 추가

def initialize_firebase_admin_sdk():
    """
    Firebase Admin SDK를 초기화하고 성공 여부를 반환합니다.
    초기화 실패 시 프로그램이 정상적으로 Firebase 서비스를 사용하지 못합니다.
    """
    SERVICE_ACCOUNT_KEY_FILE = '/home/pi/class-energy-league-firebase-adminsdk-fbsvc-48fc2c76fe.json'
    SERVICE_ACCOUNT_KEY_PATH = os.path.join(os.path.dirname(__file__), SERVICE_ACCOUNT_KEY_FILE)

    if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        logging.error(f"오류: 서비스 계정 키 파일 '{SERVICE_ACCOUNT_KEY_FILE}'을(를) 찾을 수 없습니다.")
        print(f"오류: 서비스 계정 키 파일 '{SERVICE_ACCOUNT_KEY_FILE}'을(를) 찾을 수 없습니다.")
        print(f"경로: {SERVICE_ACCOUNT_KEY_PATH}")
        print("파일이 이 스크립트와 같은 디렉토리에 있는지 확인하거나, 정확한 경로로 수정해주세요.")
        return False

    try:
        if not firebase_admin._apps: # 이미 초기화되었는지 확인 (중복 초기화 방지)
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            # Firestore만 사용할 경우, databaseURL은 필요 없거나 생략 가능
            firebase_admin.initialize_app(cred)
            logging.info("Firebase Admin SDK가 성공적으로 초기화되었습니다.")
        else:
            logging.info("Firebase Admin SDK는 이미 초기화되었습니다.")
        return True
    except Exception as e:
        logging.error(f"Firebase Admin SDK 초기화 중 오류 발생: {e}")
        print(f"Firebase Admin SDK 초기화 중 오류 발생: {e}")
        return False

# main 함수 
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    if initialize_firebase_admin_sdk():
        logging.info("\nFirebase Admin SDK 초기화 성공. 이제 관리자 권한으로 Firebase 서비스 사용 가능.")
    else:
        logging.error("\nFirebase Admin SDK 초기화 실패. Firebase 관련 작업 수행 불가.")