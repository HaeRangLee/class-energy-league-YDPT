/**
 * 쿠키를 설정합니다.
 * @param {string} name 쿠키 이름
 * @param {string} value 쿠키 값
 * @param {number} days 만료 기간 (일)
 */
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/; SameSite=Lax";
}

/**
 * 이름으로 쿠키 값을 가져옵니다.
 * @param {string} name 쿠키 이름
 * @returns {string|null} 쿠키 값 또는 null
 */
function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

/**
 * '내 반 정하기' 드롭다운 메뉴에 반 목록을 채웁니다.
 * @param {HTMLSelectElement} selectElement - 목록을 채울 select 요소
 * @param {Array} classData - 반 목록 데이터
 */
function populateMyClassSelect(selectElement, classData) {
    if (!selectElement) return;
    // 데이터 이름순으로 정렬하여 옵션 추가
    const sortedData = [...classData].sort((a, b) => a.className.localeCompare(b.className));
    
    let optionsHTML = '<option value="">반 선택</option>';
    sortedData.forEach(team => {
        optionsHTML += `<option value="${team.className}">${team.className}</option>`;
    });
    selectElement.innerHTML = optionsHTML;
}