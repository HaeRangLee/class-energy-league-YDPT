import cv2
import pytesseract
import numpy as np
import re

# --- 사전 세팅 ---
# OCR 언어 설정 (한글 + 영어)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # OS에 맞게 수정 필요
OCR_LANG = 'kor+eng'

def preprocess_image(image_path):
    """이미지를 전처리 (흑백 변환, 대비 향상, 노이즈 제거)"""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3,3), 0)
    enhanced = cv2.convertScaleAbs(blur, alpha=1.5, beta=0)  # 대비 강화
    return enhanced

def extract_text(image):
    """OCR 수행"""
    config = '--psm 6'  # 문장 단위 인식
    text = pytesseract.image_to_string(image, lang=OCR_LANG, config=config)
    text = text.replace(" ", "").strip()
    return text

def detect_temperature(text):
    """텍스트에서 온도(숫자+도) 인식"""
    match = re.search(r'(\d{1,2})[°도]?', text)
    if match:
        return int(match.group(1))
    return None

def detect_mode(text):
    """냉방 / 난방 / 제습 / 자동 등 모드 인식"""
    modes = ['냉방', '난방', '제습', '자동', '송풍']
    for mode in modes:
        if mode in text:
            return mode
    return "인식 안됨"

def detect_wind_level(text):
    """바람 세기 단어(미약, 약, 중, 강, 파워, AUTO) 인식"""
    wind_keywords = ['미약', '약', '중', '강', '파워', 'AUTO']
    for word in wind_keywords:
        if word in text.upper() or word in text:
            return word
    return "인식 안됨"

def read_controller(image_path):
    """전체 인식 프로세스"""
    img = preprocess_image(image_path)
    text = extract_text(img)

    temperature = detect_temperature(text)
    mode = detect_mode(text)
    wind = detect_wind_level(text)

    result = {
        "온도": temperature,
        "모드": mode,
        "바람세기": wind
    }

    return result


# --- 단독 테스트용 ---
if __name__ == "__main__":
    test_image = "sample_controller.jpg"  # 테스트 이미지 경로
    result = read_controller(test_image)
    print(result)
