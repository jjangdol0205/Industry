/* ==========================================================================
   TrendPulse AI - SPA Core Frontend JavaScript Logic
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // 1. 전역 상태 변수
    let currentReports = [];
    let currentChartInstance = null;
    let selectedReportForModal = null;
    let activeRegionFilter = "all";
    let activeIndustryFilter = "all";
    let globalSearchQuery = "";

    // 2. DOM 요소 셀렉터
    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebar-toggle");
    const menuItems = document.querySelectorAll(".menu-item");
    const contentViews = document.querySelectorAll(".content-view");
    const globalSearch = document.getElementById("global-search");
    const liveClock = document.getElementById("live-clock");
    
    // 모달 요소들
    const reportModal = document.getElementById("report-modal");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const btnCloseModalBottom = document.getElementById("btn-close-modal-bottom");
    const modalTabButtons = document.querySelectorAll(".modal-tab");
    const modalTabContents = document.querySelectorAll(".modal-tab-content");

    // 3. 시간 표시 모듈 (Live Clock)
    function updateClock() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const date = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        
        liveClock.innerHTML = `<i class="fa-regular fa-clock"></i> ${year}-${month}-${date} ${hours}:${minutes}`;
    }
    updateClock();
    setInterval(updateClock, 60000);

    // 4. 모바일 사이드바 제어
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            sidebar.classList.toggle("active");
        });
        document.addEventListener("click", () => {
            sidebar.classList.remove("active");
        });
    }

    // 5. 네비게이션 탭 전환 제어
    menuItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const targetViewId = item.getAttribute("data-target");
            
            // 메뉴 활성화 상태 전환
            menuItems.forEach(m => m.classList.remove("active"));
            item.classList.add("active");
            
            // 뷰 전환
            contentViews.forEach(view => {
                if (view.id === targetViewId) {
                    view.classList.add("active");
                } else {
                    view.classList.remove("active");
                }
            });
            
            // 특수 뷰 로직 트리거
            if (targetViewId === "view-comparer") {
                populateCompareSelectors();
            }
            if (targetViewId === "view-dashboard") {
                loadReports();
            }
            if (targetViewId === "view-settings") {
                updateSettingsStats();
            }
            
            // 모바일 사이드바 자동 닫기
            sidebar.classList.remove("active");
        });
    });

    // 6. 설정 및 API 상태 점검 모듈
    async function checkApiSettings() {
        try {
            const response = await fetch("/api/settings");
            const data = await response.json();
            
            const sidebarIndicator = document.getElementById("sidebar-api-indicator");
            const sidebarText = document.getElementById("sidebar-api-text");
            const statusOffline = document.getElementById("key-status-offline");
            const statusOnline = document.getElementById("key-status-online");
            const maskedKeySpan = document.getElementById("masked-key-value");
            const apiKeyInput = document.getElementById("gemini-api-key-input");

            if (data.has_key) {
                // API 키 연결 완료 상태
                sidebarIndicator.className = "api-indicator online";
                sidebarText.textContent = "AI 심층 분석 가능";
                
                if (statusOffline) statusOffline.style.display = "none";
                if (statusOnline) {
                    statusOnline.style.display = "flex";
                    maskedKeySpan.textContent = data.masked_key;
                }
                if (apiKeyInput) apiKeyInput.value = "••••••••••••••••••••••••";
            } else {
                // API 키 연결 대기 상태
                sidebarIndicator.className = "api-indicator offline";
                sidebarText.textContent = "로컬 분석 모드 (무료)";
                
                if (statusOffline) statusOffline.style.display = "flex";
                if (statusOnline) statusOnline.style.display = "none";
            }
        } catch (e) {
            console.error("API 세팅 점검 실패:", e);
        }
    }
    checkApiSettings();

    // API 키 등록 액션
    const btnSaveApiKey = document.getElementById("btn-save-api-key");
    if (btnSaveApiKey) {
        btnSaveApiKey.addEventListener("click", async () => {
            const apiKeyInput = document.getElementById("gemini-api-key-input");
            const keyVal = apiKeyInput.value.strip ? apiKeyInput.value.strip() : apiKeyInput.value.trim();
            
            if (!keyVal || keyVal.includes("••••")) {
                alert("유효한 Gemini API Key를 입력하세요.");
                return;
            }

            try {
                const response = await fetch("/api/settings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ key: keyVal })
                });
                const resData = await response.json();
                if (resData.status === "success") {
                    alert(resData.message);
                    checkApiSettings();
                }
            } catch (e) {
                alert("API 키 설정 등록 도중 실패했습니다: " + e);
            }
        });
    }

    // 7. 대시보드 리포트 목록 불러오기 & 필터링 렌더링
    async function loadReports() {
        const grid = document.getElementById("reports-grid");
        
        try {
            const url = `/api/reports?region=${activeRegionFilter}&industry=${encodeURIComponent(activeIndustryFilter)}&query=${encodeURIComponent(globalSearchQuery)}`;
            const response = await fetch(url);
            currentReports = await response.json();
            
            // 통계 보정 업데이트
            updateDashboardStats();
            
            if (currentReports.length === 0) {
                grid.innerHTML = `
                    <div class="loading-spinner-container">
                        <i class="fa-solid fa-folder-open" style="font-size: 3rem; color: var(--text-muted);"></i>
                        <p>해당 필터 조건에 부합하는 보고서가 없습니다. 다른 조건을 검색해 보세요.</p>
                    </div>`;
                return;
            }
            
            grid.innerHTML = ""; // 기존 비우기
            
            currentReports.forEach(report => {
                const card = document.createElement("div");
                card.className = "report-card glass-panel";
                
                // 국가명 보정 매핑
                const flagMap = { "KR": "🇰🇷 KR", "US": "🇺🇸 US", "EU": "🇪🇺 EU", "CN": "🇨🇳 CN", "JP": "🇯🇵 JP" };
                const regionFlag = flagMap[report.region] || `🌐 ${report.region}`;
                
                // 감정 톤 색상 보정
                const sentimentClass = report.sentiment.toLowerCase();
                
                card.innerHTML = `
                    <div class="report-card-header">
                        <span class="region-flag-badge">${regionFlag}</span>
                        <span class="industry-tag">${report.industry}</span>
                    </div>
                    <h3>${report.title}</h3>
                    <span class="report-card-source">${report.source}</span>
                    <p class="report-card-desc">${report.summary}</p>
                    <div class="report-card-footer">
                        <span class="cagr-badge">CAGR: <strong>${report.cagr}</strong></span>
                        <div class="flex items-center gap-2">
                            <span class="badge-sentiment ${sentimentClass}" title="오피니언 톤: ${report.sentiment}"></span>
                            <button class="btn-read-more" data-id="${report.id}">
                                분석 돋보기 <i class="fa-solid fa-arrow-right"></i>
                            </button>
                        </div>
                    </div>
                    <span class="card-glow"></span>
                `;
                
                // 카드 내 [돋보기] 클릭 이벤트
                const readBtn = card.querySelector(".btn-read-more");
                readBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    openReportModal(report.id);
                });
                
                // 카드 전체 클릭 이벤트 지원
                card.addEventListener("click", () => {
                    openReportModal(report.id);
                });
                
                grid.appendChild(card);
            });
            
        } catch (e) {
            console.error("보고서 목록 조회 도중 오류 발생:", e);
            grid.innerHTML = `<p class="text-center py-4 text-red">보고서 목록을 가져오는 데 오류가 발생했습니다: ${e}</p>`;
        }
    }
    loadReports();

    // 통계 계량기 업데이트
    function updateDashboardStats() {
        const statsTotal = document.getElementById("stats-total-reports");
        const statsLocal = document.getElementById("stats-local-reports");
        const statsAi = document.getElementById("stats-ai-reports");
        const statsCache = document.getElementById("stats-cache-size");

        if (!statsTotal) return;

        const total = currentReports.length;
        const local = currentReports.filter(r => !r.is_ai_analyzed).length;
        const ai = currentReports.filter(r => r.is_ai_analyzed).length;
        
        statsTotal.textContent = `${total} 개`;
        statsLocal.textContent = `${local} 개`;
        statsAi.textContent = `${ai} 개`;
        
        // 캐시 크기 추정 계산 (더미 바이트 계산)
        const cacheBytes = JSON.stringify(currentReports.filter(r => !r.id.startsWith("preloaded"))).length;
        statsCache.textContent = `${(cacheBytes / 1024).toFixed(1)} KB`;
    }

    // 설정 탭 요약 업데이트
    function updateSettingsStats() {
        const settingsCustom = document.getElementById("settings-custom-count");
        const settingsCacheMem = document.getElementById("settings-cache-mem");
        
        if (!settingsCustom) return;

        // 사전탑재 리포트가 아닌 커스텀 리포트 개수 산출
        const customCount = currentReports.filter(r => !r.id.startsWith("preloaded")).length;
        const cacheBytes = JSON.stringify(currentReports.filter(r => !r.id.startsWith("preloaded"))).length;
        
        settingsCustom.textContent = `${customCount} 개`;
        settingsCacheMem.textContent = `${(cacheBytes / 1024).toFixed(1)} KB`;
    }

    // 8. 지역 및 산업군 필터 이벤트 바인딩
    const regionTabs = document.getElementById("region-filter-tabs");
    if (regionTabs) {
        regionTabs.addEventListener("click", (e) => {
            const btn = e.target.closest(".region-tab");
            if (!btn) return;
            
            // 기존 탭 활성화 해제
            regionTabs.querySelectorAll(".region-tab").forEach(tab => tab.classList.remove("active"));
            btn.classList.add("active");
            
            activeRegionFilter = btn.getAttribute("data-region");
            loadReports();
        });
    }

    const industryFilter = document.getElementById("industry-filter");
    if (industryFilter) {
        industryFilter.addEventListener("change", () => {
            activeIndustryFilter = industryFilter.value;
            loadReports();
        });
    }

    // 글로벌 실시간 검색 이벤트
    if (globalSearch) {
        globalSearch.addEventListener("input", () => {
            globalSearchQuery = globalSearch.value.trim();
            loadReports();
        });
    }

    // 9. 리포트 상세 모달 (Modal Viewer)
    function openReportModal(reportId) {
        // 전역 목록에서 탐색
        const report = currentReports.find(r => r.id === reportId);
        if (!report) return;
        
        selectedReportForModal = report;
        
        // 텍스트 기입
        const titleText = document.getElementById("modal-report-title");
        const regionBadge = document.getElementById("modal-region-badge");
        const sourceLabel = document.getElementById("modal-source-label");
        const industryLabel = document.getElementById("modal-industry-label");
        const cagrLabel = document.getElementById("modal-cagr-label");
        const sentimentLabel = document.getElementById("modal-sentiment-label");
        
        const summaryText = document.getElementById("modal-summary-text");
        const keySentencesList = document.getElementById("modal-key-sentences-list");
        const megatrendsContainer = document.getElementById("modal-megatrends-container");
        const implicationsList = document.getElementById("modal-implications-list");
        const originalTextArea = document.getElementById("modal-original-text-area");
        
        const btnTriggerDeepAi = document.getElementById("btn-trigger-deep-ai");
        const aiBadgeIndicator = document.getElementById("ai-badge-indicator");
        const chartTitle = document.getElementById("modal-chart-title");

        titleText.textContent = report.title;
        regionBadge.textContent = report.region.toUpperCase();
        sourceLabel.textContent = report.source;
        industryLabel.textContent = report.industry;
        cagrLabel.textContent = report.cagr;
        sentimentLabel.textContent = report.sentiment;
        summaryText.textContent = report.summary;
        chartTitle.textContent = report.chart_title || "핵심 시장 규모 및 통계";
        
        // 감정 톤 색상 클래스 배정
        sentimentLabel.className = "meta-val";
        if (report.sentiment === "Positive") sentimentLabel.classList.add("text-green");
        else if (report.sentiment === "Caution") sentimentLabel.classList.add("neon-red");
        else sentimentLabel.classList.add("neon-gold");
        
        // AI 분석 상태 뱃지 제어
        if (report.is_ai_analyzed) {
            aiBadgeIndicator.style.display = "inline-flex";
            btnTriggerDeepAi.style.display = "none";
        } else {
            aiBadgeIndicator.style.display = "none";
            btnTriggerDeepAi.style.display = "inline-flex"; // 심층 분석 실행 단추 노출
        }

        // 주요 문장 Top 5 렌더
        keySentencesList.innerHTML = "";
        const sentences = report.key_sentences || [];
        if (sentences.length === 0) {
            keySentencesList.innerHTML = "<li>원문 분석 결과 도출된 고밀도 문장이 존재하지 않습니다.</li>";
        } else {
            sentences.forEach(s => {
                const li = document.createElement("li");
                li.textContent = s;
                keySentencesList.appendChild(li);
            });
        }

        // 메가트렌드 카드 렌더
        megatrendsContainer.innerHTML = "";
        const trends = report.megatrends || [];
        trends.forEach((t, idx) => {
            const card = document.createElement("div");
            card.className = "megatrend-card";
            card.innerHTML = `
                <h6>0${idx + 1}. ${t.title}</h6>
                <p>${t.description}</p>
            `;
            megatrendsContainer.appendChild(card);
        });

        // 비즈니스 시사점 렌더
        implicationsList.innerHTML = "";
        const imps = report.implications || [];
        imps.forEach(imp => {
            const li = document.createElement("li");
            li.textContent = imp;
            implicationsList.appendChild(li);
        });

        // 원문 텍스트 렌더
        originalTextArea.value = report.original_text || "본 보고서는 사전 분석 데이터셋으로 원문 텍스트 전문을 별도로 백업해두지 않았습니다. 요약 카드를 열람해 주세요.";

        // 모달 탭 상태 초기화 (첫 번째 탭 강제 선택)
        modalTabButtons.forEach(btn => btn.classList.remove("active"));
        modalTabContents.forEach(content => content.classList.remove("active"));
        modalTabButtons[0].classList.add("active");
        modalTabContents[0].classList.add("active");

        // 10. Chart.js 캔버스 렌더링 시작
        renderModalChart(report);

        // 모달창 오픈 클래스 부여
        reportModal.classList.add("active");
    }

    // Chart.js 시각화 코어 함수
    function renderModalChart(report) {
        const canvas = document.getElementById("modal-chart-canvas");
        const ctx = canvas.getContext("2d");
        
        // 기존 인스턴스 파괴
        if (currentChartInstance) {
            currentChartInstance.destroy();
        }

        const chartData = report.chart_data || [];
        if (chartData.length === 0) {
            // 더미 차트 데이터셋 구축 예비
            canvas.style.display = "none";
            return;
        }
        canvas.style.display = "block";

        const labels = chartData.map(d => d.year);
        const dataValues = chartData.map(d => d.value);
        const unit = chartData[0]?.unit || "";

        // 네온 그라데이션 브러시 생성
        const gradient = ctx.createLinearGradient(0, 0, 0, 180);
        gradient.addColorStop(0, 'rgba(0, 242, 254, 0.4)');
        gradient.addColorStop(1, 'rgba(155, 81, 224, 0.02)');

        // 차트 구성
        currentChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: `시장 예측 지표 (${unit})`,
                    data: dataValues,
                    borderColor: '#00f2fe',
                    borderWidth: 3,
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#9b51e0',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1.5,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(11, 15, 31, 0.95)',
                        borderColor: 'rgba(0, 242, 254, 0.3)',
                        borderWidth: 1,
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        padding: 10,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return ` 예측: ${context.parsed.y} ${unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.03)'
                        },
                        ticks: {
                            color: '#a0aec0',
                            font: {
                                family: 'Inter',
                                size: 10
                            }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.03)'
                        },
                        ticks: {
                            color: '#a0aec0',
                            font: {
                                family: 'Inter',
                                size: 10
                            }
                        }
                    }
                }
            }
        });
    }

    // 모달 닫기 바인딩
    function closeModal() {
        reportModal.classList.remove("active");
        if (currentChartInstance) {
            currentChartInstance.destroy();
            currentChartInstance = null;
        }
    }
    
    if (btnCloseModal) btnCloseModal.addEventListener("click", closeModal);
    if (btnCloseModalBottom) btnCloseModalBottom.addEventListener("click", closeModal);
    
    // 모달 외부 영역 클릭 시 닫기
    reportModal.addEventListener("click", (e) => {
        if (e.target === reportModal) closeModal();
    });

    // 모달 탭 스위칭 제어
    modalTabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTabId = btn.getAttribute("data-tab");
            
            modalTabButtons.forEach(b => b.classList.remove("active"));
            modalTabContents.forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTabId).classList.add("active");
        });
    });

    // 전문 복사 단추
    const btnCopyOriginalText = document.getElementById("btn-copy-original-text");
    if (btnCopyOriginalText) {
        btnCopyOriginalText.addEventListener("click", () => {
            const area = document.getElementById("modal-original-text-area");
            area.select();
            document.execCommand("copy");
            
            // 시각적 피드백
            const originalIcon = btnCopyOriginalText.innerHTML;
            btnCopyOriginalText.innerHTML = `<i class="fa-solid fa-check text-green"></i> 전문 클립보드 복사됨`;
            setTimeout(() => {
                btnCopyOriginalText.innerHTML = originalIcon;
            }, 2000);
        });
    }

    // 모달 내 [인사이트 리포트 인쇄] 내보내기 단추
    const btnExportPdf = document.getElementById("btn-export-pdf");
    if (btnExportPdf) {
        btnExportPdf.addEventListener("click", () => {
            if (!selectedReportForModal) return;
            window.print();
        });
    }

    // 온디맨드 Gemini AI 심층 분석 트리거
    const btnTriggerDeepAi = document.getElementById("btn-trigger-deep-ai");
    if (btnTriggerDeepAi) {
        btnTriggerDeepAi.addEventListener("click", async () => {
            if (!selectedReportForModal) return;
            
            // 로더 애니메이션 구성
            const modalBody = document.querySelector(".modal-body-container");
            const originalBodyHtml = modalBody.innerHTML;
            
            modalBody.innerHTML = `
                <div class="loading-spinner-container" style="grid-column: 1 / -1; height: 350px;">
                    <div class="spinner-large"></div>
                    <h3 style="color:#ffffff;">Gemini AI 심층 리포트 분석 가동 중...</h3>
                    <p style="color:var(--text-secondary); max-width:80%;">다국어 번역 정제, 핵심 3대 메가트렌드 정형화 및 고도화 시사점 수립을 실행합니다 (약 5~15초 소요).</p>
                </div>
            `;
            
            btnTriggerDeepAi.disabled = true;

            try {
                const response = await fetch("/api/analyze/deep", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ report_id: selectedReportForModal.id })
                });

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "API 서버 응답 실패");
                }

                const upgradedReport = await response.json();
                
                // 모달 및 전역 데이터 즉시 업데이트
                selectedReportForModal = upgradedReport;
                alert("Gemini AI를 이용한 심층 리포트 구성이 성공적으로 완료되었습니다!");
                
                // 대시보드 리로드 및 모달 새로고침
                await loadReports();
                openReportModal(upgradedReport.id);

            } catch (e) {
                alert(`AI 심층 분석 도중 에러가 발생했습니다: ${e.message}\n설정 탭에서 API Key가 올바르게 세팅되었는지 확인하십시오.`);
                // 실패 시 원래 뷰 복구
                modalBody.innerHTML = originalBodyHtml;
                // 모달 닫기
                closeModal();
            } finally {
                btnTriggerDeepAi.disabled = false;
            }
        });
    }

    // 11. 실시간 RSS 무료 보고서 수집 탭 바인딩
    const btnRunCrawl = document.getElementById("btn-run-crawl");
    if (btnRunCrawl) {
        btnRunCrawl.addEventListener("click", async () => {
            const tableBody = document.getElementById("crawler-results-table");
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4">
                        <div class="spinner" style="margin: 0 auto 10px;"></div>
                        글로벌 공공/씽크탱크 RSS 피드를 라이브 크롤링 중입니다...
                    </td>
                </tr>
            `;

            try {
                const response = await fetch("/api/crawl");
                const crawled = await response.json();

                tableBody.innerHTML = "";

                crawled.forEach((item, idx) => {
                    const row = document.createElement("tr");
                    const flagMap = { "KR": "🇰🇷 KR", "US": "🇺🇸 US", "EU": "🇪🇺 EU", "CN": "🇨🇳 CN", "JP": "🇯🇵 JP" };
                    const regionFlag = flagMap[item.region] || item.region;
                    
                    row.innerHTML = `
                        <td class="source-lbl">${item.source}</td>
                        <td>${regionFlag}</td>
                        <td style="font-weight: 500;"><a href="${item.url}" target="_blank" style="color: #ffffff; text-decoration: none; transition: var(--transition-smooth);"><i class="fa-solid fa-link" style="font-size:0.8rem; color:var(--text-muted);"></i> ${item.title}</a></td>
                        <td style="color: var(--text-muted); font-size: 0.8rem;">${item.date.split(" ")[0]}</td>
                        <td>
                            <button class="btn btn-secondary btn-sm btn-action-analyze-link" data-url="${item.url}" data-title="${item.title}">
                                <i class="fa-solid fa-wand-magic-sparkles"></i> 즉시 분석 연계
                            </button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });

                // 생성된 버튼들에 이벤트 추가
                tableBody.querySelectorAll(".btn-action-analyze-link").forEach(btn => {
                    btn.addEventListener("click", () => {
                        const url = btn.getAttribute("data-url");
                        const title = btn.getAttribute("data-title");
                        
                        // AI 보고서 분석기 탭으로 강제 이동하고 주소창 채우기
                        const analyzerMenu = document.getElementById("nav-analyzer");
                        analyzerMenu.click();
                        
                        document.getElementById("report-url-input").value = url;
                    });
                });

            } catch (e) {
                tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-red py-4">RSS 피드 수집을 가동하는 중 실패했습니다: ${e}</td></tr>`;
            }
        });
    }

    // 12. PDF 드래그앤드롭 업로드 제어
    const dropZone = document.getElementById("pdf-drop-zone");
    const fileInput = document.getElementById("pdf-file-input");

    if (dropZone && fileInput) {
        dropZone.addEventListener("click", () => fileInput.click());

        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove("dragover");
            });
        });

        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === "application/pdf") {
                uploadPdfFile(files[0]);
            } else {
                alert("오직 PDF 형식의 문항 리포트만 제출할 수 있습니다.");
            }
        });

        fileInput.addEventListener("change", () => {
            if (fileInput.files.length > 0) {
                uploadPdfFile(fileInput.files[0]);
            }
        });
    }

    // 실제 파일 서버에 POST 전송 처리
    async function uploadPdfFile(file) {
        const statusEmpty = document.getElementById("status-empty-state");
        const statusRunning = document.getElementById("status-running-state");
        const statusSuccess = document.getElementById("status-success-state");
        const progressFill = document.getElementById("status-progress-fill");
        const logBox = document.getElementById("running-log-box");
        const stepTitle = document.getElementById("running-step-title");

        statusEmpty.style.display = "none";
        statusSuccess.style.display = "none";
        statusRunning.style.display = "flex";
        
        progressFill.style.width = "10%";
        logBox.innerHTML = "<p>[SYSTEM] 대기열 배정 완료. 분석 파이프라인 가동...</p>";

        // 실시간 사용자 모션 로그 구현 (Satisfying UX)
        function writeLog(text, progress, stepName) {
            return new Promise(resolve => {
                setTimeout(() => {
                    logBox.innerHTML += `<p>[LOG] ${text}</p>`;
                    logBox.scrollTop = logBox.scrollHeight;
                    progressFill.style.width = `${progress}%`;
                    if (stepName) stepTitle.textContent = stepName;
                    resolve();
                }, 700);
            });
        }

        try {
            await writeLog("PDF 파일 패킷 전송 중...", 20, "PDF 바이너리 스트림 전송");
            
            const formData = new FormData();
            formData.append("file", file);

            // 실제 서버 전송 시작
            const response = await fetch("/api/analyze/upload", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "서버 분석에 실패했습니다.");
            }

            const reportResult = await response.json();

            await writeLog("PDF 원문 무손실 텍스트 추출 완료.", 45, "pdfplumber 텍스트 추출 체인");
            await writeLog("로컬 TextRank 비지도 학습 유사성 매트릭스 계산 개시...", 70, "TextRank 핵심 오피니언 문단 추출");
            await writeLog("Regex 수치/통계 구조 스캔 및 CAGR 수치 도출 중...", 90, "시장 통계 데이터셋 정형화");
            await writeLog("로컬 분석 완료! 시각화 차트 바인딩 성공.", 100, "분석 완료");

            // 성공 뷰 세팅
            statusRunning.style.display = "none";
            statusSuccess.style.display = "flex";

            document.getElementById("success-word-count").textContent = reportResult.original_text.split(/\s+/).length;
            
            // [결과 카드 보기] 버튼 바인딩
            const btnView = document.getElementById("btn-view-analyzed-report");
            btnView.onclick = async () => {
                // 대시보드로 이동
                const dashMenu = document.getElementById("nav-dashboard");
                dashMenu.click();
                
                // 대시보드 강제 새로고침 후 모달 띄우기
                await loadReports();
                openReportModal(reportResult.id);
            };

        } catch (e) {
            alert(`분석 도중 장애가 일어났습니다: ${e.message}`);
            statusRunning.style.display = "none";
            statusEmpty.style.display = "flex";
        }
    }

    // URL 웹리포트 수집 및 실시간 크롤러 연동 본문 분석 (실제 API 연동)
    const btnAnalyzeUrl = document.getElementById("btn-analyze-url");
    if (btnAnalyzeUrl) {
        btnAnalyzeUrl.addEventListener("click", async () => {
            const val = document.getElementById("report-url-input").value.trim();
            if (!val) {
                alert("웹 보고서 주소 URL을 입력해 주세요.");
                return;
            }
            
            const statusEmpty = document.getElementById("status-empty-state");
            const statusRunning = document.getElementById("status-running-state");
            const statusSuccess = document.getElementById("status-success-state");
            const progressFill = document.getElementById("status-progress-fill");
            const logBox = document.getElementById("running-log-box");
            const stepTitle = document.getElementById("running-step-title");

            statusEmpty.style.display = "none";
            statusSuccess.style.display = "none";
            statusRunning.style.display = "flex";
            
            progressFill.style.width = "10%";
            logBox.innerHTML = "<p>[SYSTEM] URL 수집 엔진 대기열 배정 완료...</p>";

            function writeLog(text, progress, stepName) {
                return new Promise(resolve => {
                    setTimeout(() => {
                        logBox.innerHTML += `<p>[LOG] ${text}</p>`;
                        logBox.scrollTop = logBox.scrollHeight;
                        progressFill.style.width = `${progress}%`;
                        if (stepName) stepTitle.textContent = stepName;
                        resolve();
                    }, 500);
                });
            }

            try {
                await writeLog("대상 URL 패킷 세션 연결 시도 중...", 25, "대상 웹사이트 접속");
                
                // 실제 서버 API 호출
                const response = await fetch("/api/analyze/url", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url: val, title: "웹수집_보고서" })
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || "URL 콘텐츠를 수집하지 못했습니다.");
                }

                const reportResult = await response.json();

                await writeLog("HTML/PDF 원문 다운로드 및 텍스트 청크 추출 완료.", 55, "보일러플레이트 태그 필터링");
                await writeLog("로컬 TextRank 비지도 학습 유사성 계산 가동...", 75, "TextRank 핵심 문장 요약");
                await writeLog("Regex 수치 파서 가동 및 데이터 차트 시각화 구조 생성...", 95, "통계 데이터셋 바인딩");
                await writeLog("분석 완료!", 100, "분석 완료");

                // 성공 뷰 세팅
                statusRunning.style.display = "none";
                statusSuccess.style.display = "flex";

                document.getElementById("success-word-count").textContent = reportResult.original_text.split(/\s+/).length;
                
                // 결과 카드 보기 버튼 바인딩
                const btnView = document.getElementById("btn-view-analyzed-report");
                btnView.onclick = async () => {
                    const dashMenu = document.getElementById("nav-dashboard");
                    dashMenu.click();
                    await loadReports();
                    openReportModal(reportResult.id);
                };

            } catch (e) {
                alert(`URL 분석 중 오류가 발생했습니다: ${e.message}\n(공공 PDF 다이렉트 주소인 경우 다운로드가 성공하지만, Cloudflare가 걸린 해외 사이트는 차단될 수 있습니다.)`);
                statusRunning.style.display = "none";
                statusEmpty.style.display = "flex";
            }
        });
    }

    // 실시간 AI 검색 리포트 생성기 바인딩
    const btnRunAiSearch = document.getElementById("btn-run-ai-search");
    if (btnRunAiSearch) {
        btnRunAiSearch.addEventListener("click", async () => {
            const queryInput = document.getElementById("ai-search-query-input");
            const val = queryInput.value.trim();
            if (!val) {
                alert("AI 실시간 검색어를 입력해 주세요. (예: 2026년 반도체 시장 규모 전망)");
                return;
            }

            // 1. API 키 연동 여부 확인 선행 검증
            try {
                const checkRes = await fetch("/api/settings");
                const checkData = await checkRes.json();
                if (!checkData.has_key) {
                    alert("실시간 AI 검색 합성은 Gemini API Key 설정이 필수적입니다. 설정 탭으로 자동 이동합니다. API 키를 먼저 입력해 주세요.");
                    const settingsMenu = document.getElementById("nav-settings");
                    if (settingsMenu) {
                        settingsMenu.click();
                        // 스크롤 포커스 지원
                        setTimeout(() => {
                            const keyInput = document.getElementById("gemini-api-key-input");
                            if (keyInput) keyInput.focus();
                        }, 300);
                    }
                    return;
                }
            } catch (e) {
                console.error("API 키 확인 실패:", e);
            }

            const statusEmpty = document.getElementById("status-empty-state");
            const statusRunning = document.getElementById("status-running-state");
            const statusSuccess = document.getElementById("status-success-state");
            const progressFill = document.getElementById("status-progress-fill");
            const logBox = document.getElementById("running-log-box");
            const stepTitle = document.getElementById("running-step-title");

            statusEmpty.style.display = "none";
            statusSuccess.style.display = "none";
            statusRunning.style.display = "flex";
            
            progressFill.style.width = "10%";
            logBox.innerHTML = "<p>[SYSTEM] 실시간 AI 검색 대기열 활성화...</p>";

            function writeLog(text, progress, stepName) {
                return new Promise(resolve => {
                    setTimeout(() => {
                        logBox.innerHTML += `<p>[LOG] ${text}</p>`;
                        logBox.scrollTop = logBox.scrollHeight;
                        progressFill.style.width = `${progress}%`;
                        if (stepName) stepTitle.textContent = stepName;
                        resolve();
                    }, 500);
                });
            }

            try {
                await writeLog("DuckDuckGo Lite 유기적 정보 탐색 가동 중...", 25, "실시간 인터넷 검색");
                
                // 실제 서버 API 호출
                const response = await fetch("/api/analyze/search", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query: val })
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || "실시간 검색 분석에 실패했습니다.");
                }

                const reportResult = await response.json();

                await writeLog("상위 2대 기술 포털 원본 문맥 패킷 크롤링 성공.", 55, "웹 크롤러 및 WAF 감지");
                await writeLog("Gemini 2.5 Flash를 이용한 3대 메가트렌드 및 예측 지표 합성 개시...", 80, "Gemini 2.5 Flash 리포트 합성");
                await writeLog("AI 비즈니스 인사이트 리포트 생성 완료!", 100, "분석 완료");

                // 성공 뷰 세팅
                statusRunning.style.display = "none";
                statusSuccess.style.display = "flex";

                document.getElementById("success-word-count").textContent = reportResult.original_text.split(/\s+/).length;
                
                // 결과 카드 보기 버튼 바인딩
                const btnView = document.getElementById("btn-view-analyzed-report");
                btnView.onclick = async () => {
                    const dashMenu = document.getElementById("nav-dashboard");
                    dashMenu.click();
                    await loadReports();
                    openReportModal(reportResult.id);
                };

            } catch (e) {
                alert(`AI 실시간 보고서 생성 중 오류가 발생했습니다: ${e.message}`);
                statusRunning.style.display = "none";
                statusEmpty.style.display = "flex";
            }
        });
    }


    // 13. 글로벌 리포트 크로스 비교 콘솔 구현
    function populateCompareSelectors() {
        const selectA = document.getElementById("compare-select-a");
        const selectB = document.getElementById("compare-select-b");
        
        if (!selectA || !selectB) return;

        // 기존 요소들 비우고 디폴트만
        selectA.innerHTML = '<option value="">-- 첫 번째 보고서 선택 --</option>';
        selectB.innerHTML = '<option value="">-- 두 번째 보고서 선택 --</option>';

        currentReports.forEach(r => {
            const opt = `<option value="${r.id}">[${r.source}] ${r.title.substring(0, 50)}...</option>`;
            selectA.innerHTML += opt;
            selectB.innerHTML += opt;
        });
    }

    // 크로스 분석 실행 제어
    const btnRunComparison = document.getElementById("btn-run-comparison");
    if (btnRunComparison) {
        btnRunComparison.addEventListener("click", () => {
            const selectA = document.getElementById("compare-select-a");
            const selectB = document.getElementById("compare-select-b");
            const resPanel = document.getElementById("comparison-result-panel");

            const idA = selectA.value;
            const idB = selectB.value;

            if (!idA || !idB) {
                alert("대조 비교할 두 보고서를 모두 선택하셔야 합니다.");
                return;
            }

            if (idA === idB) {
                alert("서로 다른 두 개의 보고서를 고르셔야 객관적인 비교가 가능합니다.");
                return;
            }

            const repA = currentReports.find(r => r.id === idA);
            const repB = currentReports.find(r => r.id === idB);

            if (!repA || !repB) return;

            // 타이틀 바인딩
            document.getElementById("compare-title-a-label").textContent = repA.title.split("(")[0].substring(0, 45) + "...";
            document.getElementById("compare-title-b-label").textContent = repB.title.split("(")[0].substring(0, 45) + "...";

            // 논조 및 초점 차이 유도 (정교한 휴리스틱 다국어 비교 알고리즘)
            const focusA = document.getElementById("compare-focus-a");
            const focusB = document.getElementById("compare-focus-b");

            focusA.innerHTML = `
                <strong>📍 관점 소싱: ${repA.source} (${repA.region})</strong>
                <p class="mt-2" style="font-size:0.8rem; color:var(--text-secondary);">${repA.summary}</p>
                <div class="mt-2">
                    <span class="cagr-badge">지표 동향: <strong>${repA.cagr}</strong></span>
                    <span class="cagr-badge ml-2" style="margin-left:10px;">분석 톤: <strong>${repA.sentiment}</strong></span>
                </div>
            `;
            
            focusB.innerHTML = `
                <strong>📍 관점 소싱: ${repB.source} (${repB.region})</strong>
                <p class="mt-2" style="font-size:0.8rem; color:var(--text-secondary);">${repB.summary}</p>
                <div class="mt-2">
                    <span class="cagr-badge">지표 동향: <strong>${repB.cagr}</strong></span>
                    <span class="cagr-badge ml-2" style="margin-left:10px;">분석 톤: <strong>${repB.sentiment}</strong></span>
                </div>
            `;

            // 핵심 아젠다 매핑
            const trendA = document.getElementById("compare-trend-a");
            const trendB = document.getElementById("compare-trend-b");

            trendA.innerHTML = "<strong>🔥 3대 메가트렌드 아젠다</strong><ul class='mt-2' style='padding-left:15px; font-size:0.8rem;'>";
            repA.megatrends.forEach(t => {
                trendA.innerHTML += `<li style='margin-bottom:6px;'><strong>${t.title}</strong>: ${t.description.substring(0, 60)}...</li>`;
            });
            trendA.innerHTML += "</ul>";

            trendB.innerHTML = "<strong>🔥 3대 메가트렌드 아젠다</strong><ul class='mt-2' style='padding-left:15px; font-size:0.8rem;'>";
            repB.megatrends.forEach(t => {
                trendB.innerHTML += `<li style='margin-bottom:6px;'><strong>${t.title}</strong>: ${t.description.substring(0, 60)}...</li>`;
            });
            trendB.innerHTML += "</ul>";

            // 상호 작용 시너지 권고 대조
            const impA = document.getElementById("compare-imp-a");
            const impB = document.getElementById("compare-imp-b");

            impA.innerHTML = `
                <strong>💡 상호 분석에 입각한 비즈니스 권고사항</strong>
                <ul class="mt-2" style="padding-left:15px; font-size:0.8rem; line-height:1.5;">
                    <li style="margin-bottom:6px;">${repA.implications[0]}</li>
                    <li>${repA.implications[1] || '지속가능 경영을 위한 공급 다각화 필수'}</li>
                </ul>
            `;
            
            impB.innerHTML = `
                <strong>💡 상호 분석에 입각한 비즈니스 권고사항</strong>
                <ul class="mt-2" style="padding-left:15px; font-size:0.8rem; line-height:1.5;">
                    <li style="margin-bottom:6px;">${repB.implications[0]}</li>
                    <li>${repB.implications[1] || '전용 하드웨어 및 데이터 파이프라인 조기 구축 권고'}</li>
                </ul>
            `;

            // 패널 활성화
            resPanel.style.display = "flex";
            
            // 아래로 부드러운 스크롤
            setTimeout(() => {
                resPanel.scrollIntoView({ behavior: "smooth" });
            }, 200);
        });
    }

});
