# -*- coding: utf-8 -*-
with open(r'D:\Industry\InvestmentPortal\frontend\src\App.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

history_code = """
  // 뒤로가기(Back) 버튼 핸들러
  useEffect(() => {
    const handlePopState = (e) => {
      setViewMode('research');
      setSelectedCompany(null);
      setSidebarOpen(false);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const isHome = viewMode === 'research' && selectedCompany === null;
  const isHomeRef = useRef(isHome);
  useEffect(() => {
    if (isHomeRef.current && !isHome) {
      window.history.pushState({ detail: true }, '');
    }
    isHomeRef.current = isHome;
  }, [isHome]);
"""

# Insert history_code right before the existing PWA useEffect
if '  // PWA 설치 프롬프트 캡처' in text:
    text = text.replace('  // PWA 설치 프롬프트 캡처', history_code + '\n  // PWA 설치 프롬프트 캡처')

with open(r'D:\Industry\InvestmentPortal\frontend\src\App.jsx', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully injected history logic.")
