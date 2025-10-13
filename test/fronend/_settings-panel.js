/**
 * 공통 '더보기' 패널을 초기화하는 함수
 * @param {object} realtimedata - 전체 데이터 객체
 * @param {function} [onMyClassChange] - '내 반'이 변경되었을 때 호출할 콜백 함수
 * @param {object} [additionalMenuItems] - 패널에 추가할 메뉴 아이템 배열 { text, href, id, onClick }
 */
async function initializeSettingsPanel(realtimedata, onMyClassChange, additionalMenuItems = []) {
    // 1. HTML 템플릿 로드 및 삽입
    try {
        const response = await fetch('_settings-panel.html');
        if (!response.ok) throw new Error('Could not load settings panel HTML.');
        const panelHTML = await response.text();
        const placeholder = document.getElementById('settings-panel-placeholder');
        if (placeholder) {
            placeholder.innerHTML = panelHTML;
        } else {
            console.error('Settings panel placeholder not found.');
            return;
        }
    } catch (error) {
        console.error('Failed to initialize settings panel:', error);
        return;
    }

    // 2. DOM 요소 참조
    const settingsPanel = document.getElementById('settings-panel');
    const overlay = document.getElementById('overlay');
    const settingsBtn = document.getElementById('settings-btn');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const themeSelect = document.getElementById('theme-select');
    const myClassSelect = document.getElementById('my-class-select');

    if (!settingsPanel || !overlay || !settingsBtn || !closeSettingsBtn || !themeSelect || !myClassSelect) {
        console.error('One or more settings panel elements are missing.');
        return;
    }

    // 3. 함수 정의
    const toggleSettingsPanel = () => {
        const isOpen = settingsPanel.classList.toggle('open');
        overlay.classList.toggle('active');
        settingsPanel.setAttribute('aria-hidden', !isOpen);
    };

    const applyTheme = (theme, saveCookie = true) => {
        let effectiveTheme = theme;
        if (theme === 'auto') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            effectiveTheme = prefersDark ? 'dark' : 'light';
        }
        document.body.setAttribute('data-theme', effectiveTheme);

        // 차트가 있는 페이지를 위한 색상 업데이트 (Chart.js가 로드되었을 경우에만 실행)
        if (typeof Chart !== 'undefined') {
            if (effectiveTheme === 'dark') {
                Chart.defaults.color = '#ecf0f1'; // 전역 글자 색 (범례 등)
                Chart.defaults.borderColor = '#34495e'; // 차트 테두리
                Chart.defaults.scale.ticks.color = '#bdc3c7'; // 축 글자 색
                Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.1)'; // 축 격자선 색
            } else {
                Chart.defaults.color = '#555';
                Chart.defaults.borderColor = '#dceddc';
                Chart.defaults.scale.ticks.color = '#555';
                Chart.defaults.scale.grid.color = 'rgba(0, 0, 0, 0.1)';
            }
        }

        if (saveCookie) setCookie('theme', theme, 365);
        themeSelect.value = theme;
    };

    // 4. 이벤트 리스너 연결
    settingsBtn.addEventListener('click', toggleSettingsPanel);
    closeSettingsBtn.addEventListener('click', toggleSettingsPanel);
    overlay.addEventListener('click', toggleSettingsPanel);

    themeSelect.addEventListener('change', (e) => {
        applyTheme(e.target.value);
        // 테마 변경 시 차트 색상 등을 다시 그려야 할 수 있으므로, 페이지를 새로고침하는 것이 간단하고 안정적일 수 있습니다.
        // 필요에 따라 이 부분은 주석 처리하거나, 차트만 다시 그리는 로직으로 변경할 수 있습니다.
        window.location.reload();
    });

    myClassSelect.addEventListener('change', (e) => {
        const myClass = e.target.value;
        setCookie('myClass', myClass, 365);
        if (typeof onMyClassChange === 'function') {
            onMyClassChange(myClass); // 각 페이지별 콜백 함수 실행
        }
    });

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if ((getCookie('theme') || 'auto') === 'auto') {
            applyTheme('auto', false);
            window.location.reload();
        }
    });

    // 아코디언 메뉴
    document.querySelectorAll('.accordion-header').forEach(button => {
        if (button.tagName === 'BUTTON') {
            button.addEventListener('click', () => {
                const content = button.nextElementSibling;
                const isExpanded = content.style.maxHeight;
                button.setAttribute('aria-expanded', !isExpanded);
                content.style.maxHeight = isExpanded ? null : content.scrollHeight + "px";
            });
        }
    });

    // 5. 초기화 로직 실행
    // 테마 적용
    applyTheme(getCookie('theme') || 'auto');

    // '내 반' 드롭다운 채우기 및 선택
    populateMyClassSelect(myClassSelect, realtimedata.mainPage.monthlyRanking);
    const savedMyClass = getCookie('myClass');
    if (savedMyClass) {
        myClassSelect.value = savedMyClass;
    }

    // '반별 페이지' 링크 생성
    const classLinksContent = document.getElementById('class-links-content');
    const grid = document.createElement('div');
    grid.className = 'class-link-grid';
    const sortedRanking = [...realtimedata.mainPage.monthlyRanking].sort((a, b) => a.className.localeCompare(b.className));
    sortedRanking.forEach(team => {
        grid.innerHTML += `<a href="info.html?classId=${encodeURIComponent(team.classId)}">${team.className}</a>`;
    });
    classLinksContent.appendChild(grid);
}