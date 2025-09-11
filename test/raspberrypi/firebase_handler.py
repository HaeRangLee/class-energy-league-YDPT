# firebase_handler.py (개선된 버전)

import firebase_admin
from firebase_admin import credentials, firestore
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FirebaseHandler:
    def __init__(self, service_account_key_path, collection_name='ac_logs'):
        self.key_path = service_account_key_path
        self.collection_name = collection_name
        self.db = None
        self._connect() # 최초 연결 시도

    def _connect(self):
        """Firebase에 연결을 시도하고, 이미 연결되어 있으면 통과합니다."""
        if firebase_admin._apps:
            self.db = firestore.client()
            return

        try:
            cred = credentials.Certificate(self.key_path)
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            logging.info("Firebase 앱이 성공적으로 초기화 및 연결되었습니다.")
        except Exception as e:
            logging.error(f"Firebase 연결 실패: {e}")
            self.db = None

    def send_ac_data(self, ac_data):
        """에어컨 상태 데이터를 받아 Firestore에 전송합니다."""
        # 1. DB 연결이 끊겼는지 확인하고, 끊겼다면 재연결 시도
        if not self.db:
            logging.warning("Firestore 연결이 끊겼습니다. 재연결을 시도합니다.")
            self._connect()
            # 재연결 후에도 실패했다면 함수 종료
            if not self.db:
                logging.error("재연결 실패. 데이터 전송을 건너뜁니다.")
                return

        try:
            # 2. 데이터 구조에 서버 타임스탬프 추가
            ac_data['timestamp'] = firestore.FieldValue.serverTimestamp()
            
            collection_ref = self.db.collection(self.collection_name)
            update_time, doc_ref = collection_ref.add(ac_data)

            logging.info(f"✅ [{ac_data.get('classId', 'N/A')}반] 데이터 전송 성공!")
            
        except Exception as e:
            logging.error(f"데이터 전송 중 에러 발생: {e}")
            # 여기서 에러가 나면 다음 사이클에서 다시 시도하게 됨