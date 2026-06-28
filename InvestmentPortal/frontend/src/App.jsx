import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend,
  ResponsiveContainer, LineChart, Line, ComposedChart, Area,
  PieChart, Pie, Cell, Tooltip
} from 'recharts';
import { 
  TrendingUp, Database, FileText, ArrowLeft, Activity, DollarSign, Target,
  BookOpen, BarChart2, BarChart3, Shield, Zap, RefreshCw, ExternalLink, Users, Globe,
  FolderOpen, ChevronDown, ChevronRight, Package, Layers, AlertTriangle, Star
} from 'lucide-react';
import './index.css';

const BACKEND_HOST = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://industry-l08j.onrender.com';
const API_BASE = `${BACKEND_HOST}/api`;

// ── 포맷 유틸 ──────────────────────────────────────────
const fB  = (n) => n == null ? '-' : `$${(n/1e9).toFixed(2)}B`;          // 십억 달러
const fM  = (n) => n == null ? '-' : `$${(n/1e6).toFixed(0)}M`;          // 백만 달러
const fP  = (n) => n == null ? '-' : `${(n*100).toFixed(1)}%`;            // 비율(0~1) → %
const fP2 = (n) => n == null ? '-' : `${n.toFixed(1)}%`;                  // 이미 % 값
const fX  = (n) => n == null ? '-' : `${n.toFixed(2)}x`;                  // 배수
const fN  = (n) => n == null ? '-' : n.toFixed(2);                        // 소수
const fK  = (n) => n == null ? '-' : n.toLocaleString();                  // 정수
const fDollar = (n) => n == null ? '-' : `$${n.toFixed(2)}`;              // 달러 단위

const color = (v, good, bad) => {
  if (v == null) return 'var(--text-secondary)';
  return v >= good ? 'var(--accent-green)' : v <= bad ? '#ff6b6b' : 'var(--text-primary)';
};

// ── 메인 앱 ─────────────────────────────────────────────
function App() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [companyProfile, setCompanyProfile] = useState(null);
  const [companyFinancials, setCompanyFinancials] = useState(null);
  const [companyAiAnalysis, setCompanyAiAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMsg, setLoadingMsg] = useState('서버에 연결 중...');
  const [loadingDot, setLoadingDot] = useState(0);
  const [retryCount, setRetryCount] = useState(0);
  const [viewMode, setViewMode] = useState('research');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [installPrompt, setInstallPrompt] = useState(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingPhase, setLoadingPhase] = useState('wakeup'); // 'wakeup' | 'data'

  // PWA 설치 프롬프트 캡처 (Android Chrome)
  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      setInstallPrompt(e);
      setShowInstallBanner(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstallClick = async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    if (outcome === 'accepted') setShowInstallBanner(false);
    setInstallPrompt(null);
  };


  useEffect(() => {
    if (!loading) return;
    const timer = setInterval(() => setLoadingDot(d => (d + 1) % 4), 500);
    return () => clearInterval(timer);
  }, [loading]);

  useEffect(() => { fetchReportsWithRetry(); }, []);

  // ── 서버 웜업 → 데이터 로드 ──────────────────────────────
  const fetchReportsWithRetry = async (attempt = 0) => {
    // 1단계: 웜업 핑 (서버를 먼저 깨움)
    if (attempt === 0) {
      setLoadingMsg('서버 연결 중...');
      setLoadingPhase('wakeup');
      setLoadingProgress(5);
      try {
        await axios.get(`${BACKEND_HOST}/ping`, { timeout: 60000 });
        setLoadingProgress(40);
        setLoadingPhase('data');
        setLoadingMsg('데이터 불러오는 중...');
      } catch (e) {
        // ping 실패해도 계속 진행
        setLoadingProgress(20);
      }
    }

    const msgs = [
      '데이터 불러오는 중...',
      '데이터 처리 중...',
      '거의 다 됐어요!',
      '마지막 단계...',
    ];
    setLoadingMsg(msgs[Math.min(attempt, msgs.length - 1)]);
    setRetryCount(attempt);
    setLoadingProgress(40 + attempt * 12);

    try {
      const res = await axios.get(`${API_BASE}/reports`, { timeout: 20000 });
      setReports(res.data);
      setLoadingProgress(90);
      if (res.data.length > 0) await fetchReportDetails(res.data[0].id);
      setLoadingProgress(100);
      setTimeout(() => setLoading(false), 300);
    } catch (e) {
      if (attempt < 5) {
        const delay = Math.min(3000 * (attempt + 1), 10000);
        setTimeout(() => fetchReportsWithRetry(attempt + 1), delay);
      } else {
        setLoadingMsg('연결 실패. 페이지를 새로고침 해주세요.');
        setLoadingProgress(0);
      }
    }
  };

  const fetchReportDetails = async (id) => {
    try {
      const res = await axios.get(`${API_BASE}/reports/${id}`);
      setSelectedReport(res.data);
    } catch (e) { console.error(e); }
  };

  const fetchCompanyFull = async (id) => {
    setCompanyAiAnalysis(null);
    setSidebarOpen(false);
    try {
      const [compRes, profRes, finRes] = await Promise.all([
        axios.get(`${API_BASE}/companies/${id}`),
        axios.get(`${API_BASE}/companies/${id}/profile`),
        axios.get(`${API_BASE}/companies/${id}/financials?limit=200`),
      ]);
      setSelectedCompany(compRes.data);
      setCompanyProfile(profRes.data.profile);
      setCompanyFinancials(finRes.data.financials);
      axios.get(`${API_BASE}/companies/${id}/ai-analysis`)
        .then(r => setCompanyAiAnalysis(r.data))
        .catch(() => setCompanyAiAnalysis({ error: true }));
    } catch (e) { console.error(e); }
  };

  const handleHomeClick = () => {
    setViewMode('research');
    setSelectedCompany(null);
    setCompanyProfile(null);
    setCompanyFinancials(null);
    setCompanyAiAnalysis(null);
    setSidebarOpen(false);
    if (reports.length > 0) fetchReportDetails(reports[0].id);
  };

  // ── 스플래시 로딩 화면 ─────────────────────────────────
  if (loading) return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0e1a 0%, #0d1526 50%, #0a1020 100%)',
      fontFamily: 'Inter, sans-serif',
    }}>
      {/* 로고 */}
      <div style={{ marginBottom: '40px', textAlign: 'center' }}>
        <div style={{
          width: '72px', height: '72px', borderRadius: '20px',
          background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px', boxShadow: '0 0 40px rgba(59,130,246,0.4)',
          animation: 'pulse 2s ease-in-out infinite',
        }}>
          <TrendingUp size={36} color="white" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'white', letterSpacing: '-0.5px' }}>
          Alpha Research
        </div>
        <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
          Industry Intelligence Platform
        </div>
      </div>

      {/* 스피너 */}
      <div style={{ position: 'relative', width: '60px', height: '60px', marginBottom: '32px' }}>
        <div style={{
          position: 'absolute', inset: 0,
          border: '3px solid rgba(59,130,246,0.15)',
          borderTopColor: '#3b82f6', borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }} />
        <div style={{
          position: 'absolute', inset: '8px',
          border: '3px solid rgba(139,92,246,0.15)',
          borderBottomColor: '#8b5cf6', borderRadius: '50%',
          animation: 'spin 1.5s linear infinite reverse',
        }} />
      </div>

      {/* 진행률 바 */}
      <div style={{ width: '280px', marginBottom: '24px' }}>
        <div style={{
          height: '4px', background: 'rgba(255,255,255,0.08)',
          borderRadius: '4px', overflow: 'hidden'
        }}>
          <div style={{
            height: '100%', borderRadius: '4px',
            background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
            width: `${loadingProgress}%`,
            transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
            boxShadow: '0 0 12px rgba(59,130,246,0.6)',
          }} />
        </div>
        <div style={{ display:'flex', justifyContent:'space-between', marginTop:'6px' }}>
          <span style={{ fontSize:'0.7rem', color:'rgba(255,255,255,0.3)' }}>
            {loadingPhase === 'wakeup' ? '🔌 서버 웜업 중' : '📊 데이터 로드 중'}
          </span>
          <span style={{ fontSize:'0.7rem', color:'rgba(255,255,255,0.3)' }}>{loadingProgress}%</span>
        </div>
      </div>

      {/* 메시지 */}
      <div style={{ textAlign: 'center', maxWidth: '320px' }}>
        <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.95rem', marginBottom: '8px', minHeight: '24px' }}>
          {loadingMsg}{'.' .repeat(loadingDot)}
        </div>
        {retryCount >= 1 && (
          <div style={{
            color: 'rgba(255,255,255,0.35)', fontSize: '0.78rem',
            background: 'rgba(255,255,255,0.05)', borderRadius: '8px',
            padding: '8px 16px', marginTop: '12px', lineHeight: '1.6'
          }}>
            🔄 Render 무료 서버는 비활성 시 절전 모드로 전환됩니다.<br />
            최초 접속 시 30~60초 소요될 수 있습니다.
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { transform: scale(1); box-shadow: 0 0 40px rgba(59,130,246,0.4); }
          50% { transform: scale(1.05); box-shadow: 0 0 60px rgba(59,130,246,0.6); } }
      `}</style>
    </div>
  );

  return (
    <div className="layout">

      {/* ── PWA 설치 배너 (Android Chrome) ── */}
      {showInstallBanner && (
        <div style={{
          position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)',
          zIndex: 9999, display: 'flex', alignItems: 'center', gap: '12px',
          background: 'linear-gradient(135deg, #1e293b, #0f172a)',
          border: '1px solid rgba(59,130,246,0.4)',
          borderRadius: '16px', padding: '14px 18px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.1)',
          maxWidth: '340px', width: 'calc(100% - 32px)',
        }}>
          <img src="/icon-192x192.png" alt="icon" style={{ width: '44px', height: '44px', borderRadius: '10px' }} />
          <div style={{ flex: 1 }}>
            <div style={{ color: 'white', fontWeight: 700, fontSize: '0.9rem' }}>앱으로 설치하기</div>
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>홈 화면에 추가하면 앱처럼 사용할 수 있어요</div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <button onClick={handleInstallClick} style={{
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              border: 'none', borderRadius: '8px', color: 'white',
              padding: '6px 14px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
            }}>설치</button>
            <button onClick={() => setShowInstallBanner(false)} style={{
              background: 'transparent', border: 'none',
              color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', cursor: 'pointer',
            }}>닫기</button>
          </div>
        </div>
      )}

      {/* 모바일 상단 헤더 바 */}

      <div className="mobile-topbar">
        <button className="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="메뉴 열기">
          <div style={{display:'flex',flexDirection:'column',gap:'5px'}}>
            <span style={{display:'block',width:'22px',height:'2px',background:'var(--text-primary)',borderRadius:'2px',transition:'all 0.3s',transform: sidebarOpen ? 'rotate(45deg) translate(5px, 5px)' : 'none'}}></span>
            <span style={{display:'block',width:'22px',height:'2px',background:'var(--text-primary)',borderRadius:'2px',transition:'all 0.3s',opacity: sidebarOpen ? 0 : 1}}></span>
            <span style={{display:'block',width:'22px',height:'2px',background:'var(--text-primary)',borderRadius:'2px',transition:'all 0.3s',transform: sidebarOpen ? 'rotate(-45deg) translate(5px, -5px)' : 'none'}}></span>
          </div>
        </button>
        <div style={{display:'flex',alignItems:'center',gap:'8px',cursor:'pointer'}} onClick={handleHomeClick}>
          <TrendingUp size={20} color="var(--accent-blue)" />
          <span style={{fontWeight:700,fontSize:'1rem'}}>Alpha Research</span>
        </div>
        <div style={{width:'40px'}}></div>
      </div>

      {/* 모바일 오버레이 */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* Sidebar */}
      <div className={`sidebar glass-panel ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <h1 onClick={handleHomeClick}><TrendingUp size={24} color="var(--accent-blue)" /> Alpha Research</h1>
        
        <div style={{ display:'flex', flexDirection:'column', gap:'6px', margin:'20px 0', borderBottom:'1px solid var(--border-color)', paddingBottom:'16px' }}>
          <div style={{ display:'flex', gap:'6px' }}>
            <button className={`tab-btn ${viewMode==='research'?'active':''}`}
              style={{ flex:1, padding:'8px', fontSize:'0.8rem', cursor:'pointer' }}
              onClick={() => { setViewMode('research'); setSidebarOpen(false); }}>
              <BookOpen size={13} style={{marginRight:'5px',verticalAlign:'middle'}} /> 리서치 포털
            </button>
            <button className={`tab-btn ${viewMode==='agent-workspace'?'active':''}`}
              style={{ flex:1, padding:'8px', fontSize:'0.8rem', cursor:'pointer' }}
              onClick={() => { setViewMode('agent-workspace'); setSelectedCompany(null); setSidebarOpen(false); }}>
              <Activity size={13} style={{marginRight:'5px',verticalAlign:'middle'}} /> AI 분석팀
            </button>
          </div>
          <button className={`tab-btn ${viewMode==='pdf-library'?'active':''}`}
            style={{ width:'100%', padding:'8px', fontSize:'0.8rem', cursor:'pointer' }}
            onClick={() => { setViewMode('pdf-library'); setSelectedCompany(null); setSidebarOpen(false); }}>
            <FolderOpen size={13} style={{marginRight:'5px',verticalAlign:'middle'}} /> 산업자료 PDF
          </button>
        </div>

        <div style={{ marginTop:'10px' }}>
          {Object.entries(reports.reduce((acc, r) => {
            const tag = r.tag || '일반';
            if (!acc[tag]) acc[tag] = [];
            acc[tag].push(r);
            return acc;
          }, {})).map(([tag, tagReports]) => (
            <div key={tag} style={{ marginBottom:'24px' }}>
              <div style={{ color:'var(--text-secondary)', fontSize:'0.8rem', marginBottom:'10px', fontWeight:'600', textTransform:'uppercase' }}>
                # {tag}
              </div>
              {tagReports.map(r => (
                <div key={r.id}
                  className={`nav-item ${selectedReport?.id===r.id?'active':''}`}
                  onClick={() => { fetchReportDetails(r.id); setSelectedCompany(null); setCompanyProfile(null); setSidebarOpen(false); }}>
                  <FileText size={18} /> {r.title}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Main */}
      <div className="main-content">
        {viewMode === 'agent-workspace' ? (
          <AgentWorkspace />
        ) : viewMode === 'pdf-library' ? (
          <PdfLibraryView />
        ) : selectedCompany ? (
          <CompanyView
            company={selectedCompany}
            profile={companyProfile}
            financials={companyFinancials}
            aiAnalysis={companyAiAnalysis}
            onBack={() => { setSelectedCompany(null); setCompanyProfile(null); setCompanyFinancials(null); setCompanyAiAnalysis(null); }}
            onSync={() => fetchCompanyFull(selectedCompany.id)}
          />
        ) : selectedReport ? (
          <IndustryView report={selectedReport} onSelectCompany={fetchCompanyFull} />
        ) : (
          <div className="page-header">
            <h2>Alpha Research</h2>
            <p>사이드바에서 산업 리포트를 선택해 주세요.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── PdfLibraryView ──────────────────────────────
function PdfLibraryView() {
  const [categories, setCategories] = useState([]);
  const [activePdf, setActivePdf] = useState(null); // { name, url }
  const [expanded, setExpanded] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_BASE}/pdfs`)
      .then(res => {
        setCategories(res.data);
        // 첫 번째 카테고리 펼치기
        if (res.data.length > 0) {
          setExpanded({ [res.data[0].category]: true });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleCategory = (cat) => setExpanded(prev => ({ ...prev, [cat]: !prev[cat] }));

  if (loading) return <div className="page-header"><p>PDF 목록 불러오는 중...</p></div>;

  return (
    <div style={{ display:'flex', height:'100%', gap:'0' }}>
      {/* 좌측 파일 트리 */}
      <div style={{
        width: activePdf ? '260px' : '100%',
        minWidth: '220px',
        borderRight: activePdf ? '1px solid var(--border-color)' : 'none',
        overflowY: 'auto',
        padding: '28px 20px',
        transition: 'width 0.3s',
        flexShrink: 0,
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:'10px', marginBottom:'24px' }}>
          <FolderOpen size={22} color="var(--accent-blue)" />
          <h2 style={{ fontSize:'1.3rem', margin:0 }}>산업자료 PDF</h2>
        </div>
        {categories.length === 0 && (
          <p style={{ color:'var(--text-secondary)' }}>PDF 파일이 없습니다.</p>
        )}
        {categories.map(cat => (
          <div key={cat.category} style={{ marginBottom:'12px' }}>
            <div
              onClick={() => toggleCategory(cat.category)}
              style={{
                display:'flex', alignItems:'center', gap:'8px',
                cursor:'pointer', padding:'8px 10px', borderRadius:'8px',
                background:'rgba(99,102,241,0.08)',
                color:'var(--accent-blue)', fontWeight:600, fontSize:'0.9rem',
                userSelect:'none',
              }}
            >
              {expanded[cat.category]
                ? <ChevronDown size={15} />
                : <ChevronRight size={15} />
              }
              <FolderOpen size={15} />
              {cat.category}
            </div>
            {expanded[cat.category] && (
              <div style={{ marginTop:'4px', paddingLeft:'12px' }}>
                {cat.files.map(file => (
                  <div
                    key={file.filename}
                    onClick={() => setActivePdf({ name: file.name, url: `${BACKEND_HOST}${file.url}` })}
                    style={{
                      display:'flex', alignItems:'center', gap:'8px',
                      padding:'9px 12px', borderRadius:'8px', cursor:'pointer',
                      marginBottom:'4px', fontSize:'0.88rem',
                      background: activePdf?.url === `${BACKEND_HOST}${file.url}`
                        ? 'rgba(99,102,241,0.18)' : 'transparent',
                      color: activePdf?.url === `${BACKEND_HOST}${file.url}`
                        ? 'var(--accent-blue)' : 'var(--text-primary)',
                      borderLeft: activePdf?.url === `${BACKEND_HOST}${file.url}`
                        ? '3px solid var(--accent-blue)' : '3px solid transparent',
                      transition: 'all 0.15s',
                    }}
                  >
                    <FileText size={14} style={{ flexShrink:0, color:'#ef4444' }} />
                    {file.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 우측 PDF 뷰어 */}
      {activePdf && (
        <div style={{ flex:1, display:'flex', flexDirection:'column', minWidth:0 }}>
          {/* 툴바 */}
          <div style={{
            display:'flex', alignItems:'center', justifyContent:'space-between',
            padding:'12px 20px', borderBottom:'1px solid var(--border-color)',
            background:'rgba(239,68,68,0.05)', flexShrink:0,
          }}>
            <div style={{ display:'flex', alignItems:'center', gap:'8px', color:'#ef4444', fontWeight:600, fontSize:'0.9rem' }}>
              <FileText size={16} /> {activePdf.name}
            </div>
            <div style={{ display:'flex', gap:'8px' }}>
              <a
                href={activePdf.url}
                target="_blank"
                rel="noreferrer"
                style={{ display:'flex', alignItems:'center', gap:'6px', padding:'6px 14px', borderRadius:'6px', background:'rgba(99,102,241,0.12)', border:'1px solid rgba(99,102,241,0.3)', color:'var(--accent-blue)', textDecoration:'none', fontSize:'0.85rem', fontWeight:600 }}
              >
                <ExternalLink size={13} /> 새 탭에서 열기
              </a>
              <button
                onClick={() => setActivePdf(null)}
                style={{ padding:'6px 14px', borderRadius:'6px', background:'transparent', border:'1px solid var(--border-color)', color:'var(--text-secondary)', cursor:'pointer', fontSize:'0.85rem' }}
              >
                ✕ 닫기
              </button>
            </div>
          </div>
          {/* iframe */}
          <iframe
            key={activePdf.url}
            src={activePdf.url}
            style={{ flex:1, border:'none', width:'100%' }}
            title={activePdf.name}
          />
        </div>
      )}
    </div>
  );
}

// ── IndustryView ────────────────────────────────
function IndustryView({ report, onSelectCompany }) {

  return (
    <div className="industry-view">
      <div className="page-header" style={{ borderBottom:'1px solid var(--border-color)', paddingBottom:'24px', marginBottom:'32px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'12px', marginBottom:'16px' }}>
          <span style={{ background:'var(--accent-blue)', color:'white', padding:'4px 12px', borderRadius:'16px', fontSize:'0.85rem', fontWeight:'bold' }}>
            #{report.tag}
          </span>
          <span style={{ color:'var(--text-secondary)' }}>Executive Summary Report</span>
        </div>
        <h2 style={{ fontSize:'2.5rem' }}>{report.title}</h2>
      </div>

      <div className="report-content glass-panel" style={{ padding:'40px', marginBottom:'40px', fontSize:'1.1rem', lineHeight:'1.8' }}>
        <h3 style={{ display:'flex', alignItems:'center', gap:'10px', color:'var(--accent-blue)', marginBottom:'24px', fontSize:'1.4rem' }}>
          <BookOpen size={24} /> Industry Overview
        </h3>
        <div className="markdown-body" style={{ color:'var(--text-primary)' }}>
          <ReactMarkdown>{report.summary}</ReactMarkdown>
        </div>
      </div>

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px' }}>
        <h3 style={{ color:'var(--accent-blue)', fontSize:'1.4rem', borderBottom:'none', margin:0 }}>
          🏆 Key Tracked Companies
        </h3>
        <div style={{ fontSize:'0.75rem', color:'var(--text-secondary)', background:'rgba(255,255,255,0.05)', padding:'4px 12px', borderRadius:'20px' }}>
          투자 매력도 순 정렬 · 매월 업데이트
        </div>
      </div>
      <div className="company-list">
        {[...report.companies]
          .sort((a, b) => (a.display_order ?? 999) - (b.display_order ?? 999))
          .map((comp, idx) => {
            const rank = comp.display_order ?? (idx + 1);
            const rankColor = rank === 1 ? '#FFD700' : rank === 2 ? '#C0C0C0' : rank === 3 ? '#CD7F32' : rank <= 5 ? '#3b82f6' : 'rgba(255,255,255,0.25)';
            const rankBg   = rank === 1 ? 'rgba(255,215,0,0.12)' : rank === 2 ? 'rgba(192,192,192,0.10)' : rank === 3 ? 'rgba(205,127,50,0.12)' : rank <= 5 ? 'rgba(59,130,246,0.08)' : 'transparent';
            const rankEmoji = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
            return (
              <div key={comp.id}
                className="company-pill glass-panel"
                onClick={() => onSelectCompany(comp.id)}
                style={{ position:'relative', border: rank <= 3 ? `1px solid ${rankColor}30` : undefined }}
              >
                {/* 순위 배지 */}
                <div style={{
                  position:'absolute', top:'10px', right:'10px',
                  background: rankBg,
                  border: `1px solid ${rankColor}60`,
                  borderRadius:'12px', padding:'2px 8px',
                  fontSize:'0.68rem', fontWeight:700, color: rankColor,
                  display:'flex', alignItems:'center', gap:'3px',
                }}>
                  {rankEmoji} {rank}위
                </div>
                <div className="company-header" style={{ paddingRight:'48px' }}>
                  <span className="company-name">{comp.name}</span>
                  <span className="company-ticker">{comp.ticker}</span>
                </div>
                <div style={{ fontSize:'0.9rem', color:'var(--text-secondary)', display:'-webkit-box', WebkitLineClamp:3, WebkitBoxOrient:'vertical', overflow:'hidden' }}>
                  {comp.role_description}
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}

// ── KPI 카드 ─────────────────────────────────────────────
function KpiCard({ label, value, sub, valueColor, icon: Icon }) {
  return (
    <div className="kpi-card glass-panel">
      {Icon && <Icon size={16} style={{ color:'var(--text-secondary)', marginBottom:'6px' }} />}
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color: valueColor || 'var(--text-primary)' }}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

// ── SectionHeader ─────────────────────────────────────────
function SectionHeader({ icon: Icon, title, color: clr }) {
  return (
    <h3 style={{ display:'flex', alignItems:'center', gap:'10px', color: clr || 'var(--accent-blue)', marginBottom:'20px', fontSize:'1.2rem', borderBottom:'1px solid var(--border-color)', paddingBottom:'10px' }}>
      {Icon && <Icon size={20} />} {title}
    </h3>
  );
}

// ── AiAnalysisSection ─────────────────────────────────────
function AiAnalysisCard({ icon: Icon, title, color, children, span2 }) {
  return (
    <div className="glass-panel" style={{
      padding: '22px 24px',
      gridColumn: span2 ? 'span 2' : 'span 1',
      borderLeft: `3px solid ${color}`,
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'14px' }}>
        <Icon size={17} color={color} />
        <span style={{ fontWeight:700, fontSize:'0.95rem', color }}>{title}</span>
      </div>
      <div style={{ fontSize:'0.92rem', lineHeight:'1.75', color:'var(--text-primary)' }}>
        {children}
      </div>
    </div>
  );
}

function AiAnalysisSection({ data }) {
  const d = data;
  if (!data) return (
    <div className="glass-panel" style={{ padding:'28px', marginBottom:'32px' }}>
      <div style={{ display:'flex', alignItems:'center', gap:'10px', marginBottom:'20px' }}>
        <Activity size={18} color="var(--accent-purple)" />
        <span style={{ fontWeight:700, fontSize:'1rem', color:'var(--accent-purple)' }}>AI 심층 비즈니스 분석 — 로딩 중...</span>
      </div>
      {[1,2,3,4].map(i => (
        <div key={i} style={{ height:'80px', background:'rgba(255,255,255,0.04)', borderRadius:'8px', marginBottom:'12px', animation:'pulse 1.5s infinite' }} />
      ))}
    </div>
  );
  if (data.error && !data.what_they_sell) return (
    <div className="glass-panel" style={{ padding:'20px', color:'#ff6b6b' }}>AI 분석 결과를 불러올 수 없습니다.</div>
  );

  const badge = d.generated_by === 'gemini'
    ? { label: 'Gemini AI', color: '#818cf8' }
    : d.generated_by === 'deepseek'
    ? { label: 'DeepSeek AI', color: '#10b981' }
    : d.generated_by === 'antigravity'
    ? { label: 'Antigravity AI', color: '#00f2fe' }
    : { label: 'Data', color: 'var(--text-secondary)' };

  return (
    <div style={{ marginBottom:'36px' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'18px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
          <Activity size={20} color="var(--accent-purple)" />
          <h3 style={{ fontSize:'1.2rem', fontWeight:700, color:'var(--accent-purple)', margin:0 }}>AI 심층 비즈니스 분석 리포트</h3>
        </div>
        <span style={{ fontSize:'0.75rem', padding:'3px 10px', borderRadius:'12px', background:'rgba(129,140,248,0.15)', color: badge.color, border:`1px solid ${badge.color}40` }}>
          {badge.label}
        </span>
      </div>

      {/* 카드 그리드 */}
      <div className="ai-grid">

        {/* 1. 핵심 제품/서비스 */}
        {d.what_they_sell && (
          <AiAnalysisCard icon={Package} title="핵심 제품 & 서비스" color="var(--accent-blue)" span2={false}>
            {d.what_they_sell}
          </AiAnalysisCard>
        )}

        {/* 2. 수익 모델 */}
        {d.revenue_model && (
          <AiAnalysisCard icon={DollarSign} title="수익 모델 — 어떻게 돈을 버는가" color="var(--accent-green)" span2={false}>
            {d.revenue_model}
          </AiAnalysisCard>
        )}

        {/* 3. 비용 구조 */}
        {d.cost_structure && (
          <AiAnalysisCard icon={BarChart3} title="비용 구조 — 어디에 돈을 쓰는가" color="#f59e0b" span2={false}>
            {d.cost_structure}
          </AiAnalysisCard>
        )}

        {/* 4. 이익 구조 */}
        {d.how_they_profit && (
          <AiAnalysisCard icon={TrendingUp} title="이익 구조 — 어떻게 돈을 남기는가" color="#06b6d4" span2={false}>
            {d.how_they_profit}
          </AiAnalysisCard>
        )}

        {/* 5. 경제적 해자 */}
        {d.competitive_moat && (
          <AiAnalysisCard icon={Shield} title="경제적 해자 (Competitive Moat)" color="var(--accent-purple)" span2={true}>
            {d.competitive_moat}
          </AiAnalysisCard>
        )}

        {/* 6. 사업 세그먼트 */}
        {d.key_segments && d.key_segments.length > 0 && (
          <AiAnalysisCard icon={Layers} title="핵심 사업 세그먼트" color="#84cc16" span2={true}>
            <div style={{ display:'flex', flexWrap:'wrap', gap:'12px' }}>
              {d.key_segments.map((seg, i) => (
                <div key={i} style={{ flex:'1 1 280px', background:'rgba(255,255,255,0.05)', borderRadius:'8px', padding:'12px 16px', borderLeft:'3px solid #84cc16' }}>
                  <div style={{ fontWeight:700, marginBottom:'4px', color:'#84cc16', fontSize:'0.85rem' }}>{seg.name}</div>
                  <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)' }}>{seg.description}</div>
                </div>
              ))}
            </div>
          </AiAnalysisCard>
        )}

        {/* 7. 리스크 */}
        {d.risk_factors && (
          <AiAnalysisCard icon={AlertTriangle} title="핵심 리스크 포인트" color="#ef4444" span2={false}>
            {d.risk_factors}
          </AiAnalysisCard>
        )}

        {/* 8. 투자 포인트 */}
        {d.investment_thesis && (
          <AiAnalysisCard icon={Star} title="투자 포인트 (Investment Thesis)" color="#f97316" span2={false}>
            {d.investment_thesis}
          </AiAnalysisCard>
        )}

        {/* 9. 산업 투자 포인트 */}
        {d.industry_connection && (
          <AiAnalysisCard icon={Globe} title="산업 내 투자 포인트 — 왜 이 산업에서 이 기업인가" color="var(--accent-blue)" span2={true}>
            {d.industry_connection}
          </AiAnalysisCard>
        )}
      </div>
    </div>
  );
}


// ── CompanyView (기관급 풀 대시보드) ──────────────────
function CompanyView({ company, profile, financials, aiAnalysis, onBack, onSync }) {
  const [tab, setTab] = useState('annual');
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      // 빠른 주가 최신화 먼저 (yfinance로 즉시)
      await axios.get(`${API_BASE}/companies/${company.id}/price`);
      await onSync();
    } catch (e) { console.error(e); }
    setSyncing(false);
  };

  // 연간 vs 분기 필터
  // 날짜 내림차순 정렬 후 연도별 중복 제거 (최신 레코드 우선)
  const annualRaw = (financials || [])
    .filter(f => f.period_type === 'annual')
    .sort((a,b) => new Date(b.date)-new Date(a.date)); // 최신순
  const annualMap = new Map();
  annualRaw.forEach(d => {
    const yr = d.date.substring(0,4);
    if (!annualMap.has(yr)) annualMap.set(yr, d); // 최신 레코드만 유지
  });
  // 차트용은 오름차순 (옛날→최신)
  const annualData = Array.from(annualMap.values()).sort((a,b) => new Date(a.date)-new Date(b.date));
  // 비즈니스 모델용 latest는 가장 최신 연간 레코드
  const latestRaw = annualRaw[0] || {};

  const quarterlyData = (financials || [])
    .filter(f => f.period_type === 'quarterly')
    .sort((a,b) => new Date(b.date)-new Date(a.date));

  const tableData = tab === 'annual' ? [...annualData].reverse() : quarterlyData;

  // 차트 데이터 (최근 6년)
  const incomeChartData = annualData.slice(-6).map(d => ({
    year: d.date.substring(0,4),
    Revenue: +(d.revenue/1e9).toFixed(2),
    'Op Income': +(( d.operating_income||0)/1e9).toFixed(2),
    'Net Income': +((d.net_income||0)/1e9).toFixed(2),
    'OPM%': +(d.op_margin||0).toFixed(1),
    'GPM%': +(d.gross_margin||0).toFixed(1),
  }));

  const cashFlowData = annualData.slice(-6).map(d => ({
    year: d.date.substring(0,4),
    OCF: +((d.operating_cash_flow||0)/1e9).toFixed(2),
    CAPEX: +((d.capital_expenditure||0)/1e9).toFixed(2),
    FCF: +((d.free_cash_flow||0)/1e9).toFixed(2),
  }));

  const balanceData = annualData.slice(-6).map(d => ({
    year: d.date.substring(0,4),
    Assets: +((d.total_assets||0)/1e9).toFixed(2),
    Debt: +((d.total_debt||0)/1e9).toFixed(2),
    Equity: +((d.shareholders_equity||0)/1e9).toFixed(2),
    Cash: +((d.cash_and_equivalents||0)/1e9).toFixed(2),
  }));

  const p = profile || {};
  // 최신 연간 레코드 사용 (COGS 등 최신값 보장)
  const latest = (() => {
    const r = latestRaw;
    // cost_of_revenue가 없으면 revenue - gross_profit으로 계산 후 반환
    if (r && r.revenue && r.gross_profit && !r.cost_of_revenue) {
      return { ...r, cost_of_revenue: r.revenue - r.gross_profit };
    }
    return r || {};
  })();

  return (
    <div className="company-details">
      {/* ── 헤더 ─────────────────────────────────────── */}
      <button className="back-btn" onClick={onBack}>
        <ArrowLeft size={20} /> 리포트로 돌아가기
      </button>

      <div className="company-header-row">
        <div>
          <h2 className="company-title">
            {company.name}
            <span style={{ fontSize:'1rem', color:'var(--accent-blue)', marginLeft:'10px', fontWeight:600 }}>{company.ticker}</span>
          </h2>
          {p.sector && (
            <div style={{ color:'var(--text-secondary)', fontSize:'0.85rem', marginBottom:'6px' }}>
              {p.sector} › {p.industry}
            </div>
          )}
          {p.current_price && (
            <div className="price-display">
              <span className="price-value" style={{ color:'var(--accent-green)' }}>${p.current_price?.toFixed(2)}</span>
              {p.beta != null && <span className="price-sub">Beta: {p.beta?.toFixed(2)}</span>}
            </div>
          )}
        </div>
        <div className="company-action-btns">
          {p.website && (
            <a href={p.website} target="_blank" rel="noopener noreferrer" className="action-link">
              <Globe size={14} /> <span className="btn-label">Website</span>
            </a>
          )}
          <button onClick={handleSync} disabled={syncing} className="sync-btn">
            <RefreshCw size={14} className={syncing?'spin':''} />
            <span>{syncing ? '수집 중...' : '주가 최신화'}</span>
          </button>
        </div>
      </div>

      {/* ── Section 0: AI 기업 심층 분석 ──────────────── */}
      <AiAnalysisSection data={aiAnalysis} company={company} />

      {/* ── Section 0b: 비즈니스 모델 수익구조 ──────── */}
      <BusinessModelSection latest={latest} profile={p} company={company} />

      {/* ── Section 1: 밸류에이션 KPI 카드 ─────────────── */}
      <section style={{ marginBottom:'36px' }}>
        <SectionHeader icon={BarChart2} title="밸류에이션 (TTM 기준)" />
        <div className="kpi-grid">
          <KpiCard label="P/E Ratio (PER)" value={fN(p.pe_ratio)} sub="주가수익비율" icon={TrendingUp}
            valueColor={p.pe_ratio < 20 ? 'var(--accent-green)' : p.pe_ratio > 50 ? '#ff6b6b' : 'var(--text-primary)'} />
          <KpiCard label="P/B Ratio (PBR)" value={fN(p.pb_ratio)} sub="주가순자산비율" />
          <KpiCard label="EV/EBITDA" value={fX(p.ev_ebitda)} sub="기업가치 배수"
            valueColor={p.ev_ebitda < 15 ? 'var(--accent-green)' : p.ev_ebitda > 40 ? '#ff6b6b' : 'var(--text-primary)'} />
          <KpiCard label="EV/Sales" value={fX(p.ev_sales)} sub="매출 배수" />
          <KpiCard label="시가총액" value={p.market_cap ? `$${(p.market_cap/1e9).toFixed(1)}B` : '-'} sub="Market Cap" icon={DollarSign} />
          <KpiCard label="애널리스트 목표가" value={fDollar(p.analyst_target)} sub="Consensus Target"
            valueColor={p.analyst_target > p.current_price ? 'var(--accent-green)' : '#ff6b6b'} />
        </div>
      </section>

      {/* ── Section 2: 수익성 지표 ───────────────────────── */}
      <section style={{ marginBottom:'36px' }}>
        <SectionHeader icon={Zap} title="수익성 지표 (Profitability TTM)" color="var(--accent-purple)" />
        <div className="kpi-grid">
          <KpiCard label="GPM (매출총이익률)" value={fP(p.gross_margin_ttm)} sub="Gross Profit Margin"
            valueColor={color(p.gross_margin_ttm*100, 50, 20)} />
          <KpiCard label="OPM (영업이익률)" value={fP(p.op_margin_ttm)} sub="Operating Margin"
            valueColor={color(p.op_margin_ttm*100, 20, 5)} />
          <KpiCard label="EBITDA Margin" value={fP(p.ebitda_margin_ttm)} sub="EBITDA / Revenue"
            valueColor={color(p.ebitda_margin_ttm*100, 25, 10)} />
          <KpiCard label="순이익률" value={fP(p.net_margin_ttm)} sub="Net Profit Margin"
            valueColor={color(p.net_margin_ttm*100, 15, 0)} />
          <KpiCard label="ROE" value={fP(p.roe)} sub="자기자본이익률"
            valueColor={color(p.roe*100, 15, 5)} />
          <KpiCard label="ROA" value={fP(p.roa)} sub="총자산이익률"
            valueColor={color(p.roa*100, 8, 2)} />
        </div>
      </section>

      {/* ── Section 3: 성장성 + 재무건전성 ──────────────── */}
      <section style={{ marginBottom:'36px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'24px' }}>
          <div>
            <SectionHeader icon={TrendingUp} title="성장성 (Growth)" color="var(--accent-green)" />
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px' }}>
              <KpiCard label="매출 성장률 (YoY)" value={p.revenue_growth != null ? fP(p.revenue_growth) : '-'} sub="Revenue Growth"
                valueColor={p.revenue_growth > 0.1 ? 'var(--accent-green)' : p.revenue_growth < 0 ? '#ff6b6b' : 'var(--text-primary)'} />
              <KpiCard label="EPS (TTM)" value={p.eps_growth != null ? fDollar(p.eps_growth) : '-'} sub="Earnings Per Share" />
            </div>
          </div>
          <div>
            <SectionHeader icon={Shield} title="재무건전성 (Financial Health)" color="#f1c40f" />
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px' }}>
              <KpiCard label="유동비율" value={fN(p.current_ratio)} sub="Current Ratio"
                valueColor={color(p.current_ratio, 2, 1)} />
              <KpiCard label="부채비율" value={fN(p.debt_to_equity)} sub="D/E Ratio"
                valueColor={p.debt_to_equity < 50 ? 'var(--accent-green)' : p.debt_to_equity > 200 ? '#ff6b6b' : 'var(--text-primary)'} />
              <KpiCard label="배당수익률" value={p.dividend_yield != null ? fP(p.dividend_yield) : '-'} sub="Dividend Yield"
                valueColor='var(--accent-green)' />
              <KpiCard label="배당성향" value={p.payout_ratio != null ? fP(p.payout_ratio) : '-'} sub="Payout Ratio" />
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 4: 손익 차트 ─────────────────────────── */}
      <section style={{ marginBottom:'36px' }}>
        <SectionHeader icon={BarChart2} title="손익 추이 (Income Statement History — $B)" />
        <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr', gap:'24px' }}>
          <div className="glass-panel" style={{ padding:'24px', height:'300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={incomeChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                <XAxis dataKey="year" stroke="var(--text-secondary)" fontSize={12} />
                <YAxis yAxisId="left" stroke="var(--text-secondary)" fontSize={12} />
                <YAxis yAxisId="right" orientation="right" stroke="#00f2fe" fontSize={12} unit="%" />
                <RechartsTooltip contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', color:'var(--text-primary)', fontSize:'0.85rem' }} />
                <Legend />
                <Bar yAxisId="left" dataKey="Revenue" fill="var(--accent-blue)" radius={[4,4,0,0]} />
                <Bar yAxisId="left" dataKey="Op Income" fill="var(--accent-purple)" radius={[4,4,0,0]} />
                <Bar yAxisId="left" dataKey="Net Income" fill="var(--accent-green)" radius={[4,4,0,0]} />
                <Line yAxisId="right" type="monotone" dataKey="OPM%" stroke="#00f2fe" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="glass-panel" style={{ padding:'24px', height:'300px' }}>
            <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'12px' }}>영업이익률 / 매출총이익률 추이</div>
            <ResponsiveContainer width="100%" height="85%">
              <LineChart data={incomeChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                <XAxis dataKey="year" stroke="var(--text-secondary)" fontSize={11} />
                <YAxis stroke="var(--text-secondary)" fontSize={11} unit="%" />
                <RechartsTooltip contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', color:'var(--text-primary)', fontSize:'0.8rem' }} />
                <Legend />
                <Line type="monotone" dataKey="GPM%" stroke="var(--accent-green)" strokeWidth={2.5} dot={{ r:4 }} />
                <Line type="monotone" dataKey="OPM%" stroke="var(--accent-blue)" strokeWidth={2.5} dot={{ r:4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* ── Section 5: 현금흐름 + 재무상태표 차트 ───────── */}
      <section style={{ marginBottom:'36px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'24px' }}>
          <div>
            <SectionHeader icon={DollarSign} title="현금흐름 (Cash Flow — $B)" color="var(--accent-green)" />
            <div className="glass-panel" style={{ padding:'24px', height:'260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cashFlowData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                  <XAxis dataKey="year" stroke="var(--text-secondary)" fontSize={11} />
                  <YAxis stroke="var(--text-secondary)" fontSize={11} />
                  <RechartsTooltip contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', color:'var(--text-primary)', fontSize:'0.8rem' }} />
                  <Legend />
                  <Bar dataKey="OCF" fill="var(--accent-blue)" radius={[3,3,0,0]} />
                  <Bar dataKey="FCF" fill="var(--accent-green)" radius={[3,3,0,0]} />
                  <Bar dataKey="CAPEX" fill="#ff6b6b" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <SectionHeader icon={Database} title="재무상태표 (Balance Sheet — $B)" color="#f1c40f" />
            <div className="glass-panel" style={{ padding:'24px', height:'260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={balanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                  <XAxis dataKey="year" stroke="var(--text-secondary)" fontSize={11} />
                  <YAxis stroke="var(--text-secondary)" fontSize={11} />
                  <RechartsTooltip contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', color:'var(--text-primary)', fontSize:'0.8rem' }} />
                  <Legend />
                  <Bar dataKey="Assets" fill="rgba(0,191,255,0.6)" radius={[3,3,0,0]} />
                  <Bar dataKey="Equity" fill="rgba(0,255,100,0.6)" radius={[3,3,0,0]} />
                  <Bar dataKey="Debt" fill="rgba(255,107,107,0.6)" radius={[3,3,0,0]} />
                  <Line type="monotone" dataKey="Cash" stroke="#ffd700" strokeWidth={2.5} dot={{ r:4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 6: 풀 재무제표 테이블 ───────────────── */}
      <section style={{ marginBottom:'40px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px' }}>
          <SectionHeader icon={FileText} title="재무제표 데이터 (Full Financials)" />
          <div className="tabs">
            <button className={`tab-btn ${tab==='annual'?'active':''}`} onClick={() => setTab('annual')}>연간</button>
            <button className={`tab-btn ${tab==='quarterly'?'active':''}`} onClick={() => setTab('quarterly')}>분기</button>
          </div>
        </div>

        <div className="data-table-container" style={{ overflowX:'auto' }}>
          <table className="data-table" style={{ minWidth:'1100px' }}>
            <thead>
              <tr>
                <th>기간</th>
                <th>매출</th>
                <th>매출원가</th>
                <th>매출총이익</th>
                <th>영업이익</th>
                <th>EBITDA</th>
                <th>순이익</th>
                <th>EPS</th>
                <th>GPM</th>
                <th>OPM</th>
                <th>OCF</th>
                <th>FCF</th>
                <th>총자산</th>
                <th>순부채</th>
                <th>ROE</th>
              </tr>
            </thead>
            <tbody>
              {tableData.map((d, i) => (
                <tr key={i}>
                  <td style={{ fontWeight:600 }}>{d.date}</td>
                  <td>{fB(d.revenue)}</td>
                  <td style={{ color:'#ff6b6b' }}>{fB(d.cost_of_revenue != null ? d.cost_of_revenue : (d.revenue && d.gross_profit ? d.revenue - d.gross_profit : null))}</td>
                  <td>{fB(d.gross_profit)}</td>
                  <td>{fB(d.operating_income)}</td>
                  <td>{fB(d.ebitda)}</td>
                  <td style={{ color: d.net_income >= 0 ? 'var(--accent-green)' : '#ff6b6b' }}>{fB(d.net_income)}</td>
                  <td>{d.eps != null ? fDollar(d.eps) : '-'}</td>
                  <td style={{ color:'var(--accent-green)' }}>{fP2(d.gross_margin)}</td>
                  <td style={{ color:'var(--accent-blue)' }}>{fP2(d.op_margin)}</td>
                  <td>{fB(d.operating_cash_flow)}</td>
                  <td style={{ color: d.free_cash_flow >= 0 ? 'var(--accent-green)' : '#ff6b6b' }}>{fB(d.free_cash_flow)}</td>
                  <td>{fB(d.total_assets)}</td>
                  <td style={{ color: d.net_debt > 0 ? '#ff6b6b' : 'var(--accent-green)' }}>{fB(d.net_debt)}</td>
                  <td>{d.roe != null ? fP2(d.roe) : '-'}</td>
                </tr>
              ))}
              {tableData.length === 0 && (
                <tr><td colSpan="15" style={{ textAlign:'center', padding:'40px', color:'var(--text-secondary)' }}>No data available</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Section 7: 회사 개요 ─────────────────────────── */}
      {(p.description || company.role_description) && (
        <section style={{ marginBottom:'40px' }}>
          <SectionHeader icon={BookOpen} title="회사 개요 (Business Overview)" />
          <div className="glass-panel" style={{ padding:'28px' }}>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:'16px', marginBottom:'20px' }}>
              {p.employees && (
                <div style={{ display:'flex', alignItems:'center', gap:'8px', color:'var(--text-secondary)', fontSize:'0.9rem' }}>
                  <Users size={16} /> 임직원: {fK(p.employees)}명
                </div>
              )}
              {p.ceo && (
                <div style={{ display:'flex', alignItems:'center', gap:'8px', color:'var(--text-secondary)', fontSize:'0.9rem' }}>
                  <Target size={16} /> CEO: {p.ceo}
                </div>
              )}
              {p.last_updated && (
                <div style={{ display:'flex', alignItems:'center', gap:'8px', color:'var(--text-secondary)', fontSize:'0.9rem' }}>
                  <RefreshCw size={14} /> 갱신: {p.last_updated}
                </div>
              )}
            </div>
            <div className="growth-section" style={{ background:'transparent', padding:0 }}>
              <p style={{ lineHeight:'1.8', color:'var(--text-secondary)', fontSize:'0.95rem' }}>
                {p.description_ko || p.description || company.role_description}
              </p>
            </div>
            {company.future_growth && (
              <div style={{ marginTop:'16px', padding:'16px', borderRadius:'8px', background:'rgba(0,191,255,0.06)', border:'1px solid rgba(0,191,255,0.2)' }}>
                <div style={{ color:'var(--accent-blue)', fontWeight:600, marginBottom:'8px', fontSize:'0.9rem' }}>
                  📈 투자 포인트 / Future Growth
                </div>
                <p style={{ color:'var(--text-primary)', lineHeight:'1.7', fontSize:'0.95rem' }}>{company.future_growth}</p>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

// ── BusinessModelSection ─────────────────────────────
function BusinessModelSection({ latest, profile, company }) {
  const rev = latest.revenue || 0;
  const gp = latest.gross_profit || 0;
  // 매출원가 = DB값 우선, 없으면 매출 - 매출총이익으로 계산
  const cogs = latest.cost_of_revenue || (rev > 0 && gp > 0 ? rev - gp : 0);
  const opInc = latest.operating_income || 0;
  const netInc = latest.net_income || 0;
  const opEx = Math.max(gp - opInc, 0);
  const taxOther = Math.max(opInc - netInc, 0);
  const p = profile || {};

  // Waterfall 데이터 (마이너스 바를 보이지 않는 스택으로 오프셋 처리)
  const wfData = [
    { name: '매출액', value: rev/1e9, start: 0, fill: '#3b82f6', label: fB(rev) },
    { name: '매출원가', value: -cogs/1e9, start: (rev-cogs)/1e9, fill: '#ff6b6b', label: fB(cogs) },
    { name: '매출총이익', value: gp/1e9, start: 0, fill: '#10b981', label: fB(gp), isSum: true },
    { name: '판관·R&D', value: -opEx/1e9, start: opInc/1e9, fill: '#f97316', label: fB(opEx) },
    { name: '영업이익', value: opInc/1e9, start: 0, fill: '#8b5cf6', label: fB(opInc), isSum: true },
    { name: '세금·기타', value: -taxOther/1e9, start: netInc/1e9, fill: '#ef4444', label: fB(taxOther) },
    { name: '순이익', value: netInc/1e9, start: 0, fill: '#00f2fe', label: fB(netInc), isSum: true },
  ];

  // 비용 구조 파이 차트
  const costPieData = [
    { name: '매출원가 (COGS)', value: cogs, color: '#ff6b6b' },
    { name: '판관·R&D 비용', value: opEx, color: '#f97316' },
    { name: '세금·이자·기타', value: taxOther, color: '#ef4444' },
    { name: '순이익', value: Math.max(netInc, 0), color: '#00f2fe' },
  ].filter(d => d.value > 0);

  const gpm = gp / (rev || 1) * 100;
  const opm = opInc / (rev || 1) * 100;
  const npm = netInc / (rev || 1) * 100;

  const CustomWaterfallTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const d = wfData.find(w => w.name === payload[0]?.payload?.name);
      return (
        <div style={{ background:'var(--bg-card)', border:'1px solid var(--border-color)', padding:'10px 14px', borderRadius:'8px', fontSize:'0.85rem' }}>
          <div style={{ fontWeight:600, marginBottom:'4px' }}>{payload[0]?.payload?.name}</div>
          <div style={{ color: d?.fill }}>{d?.label}</div>
        </div>
      );
    }
    return null;
  };

  const CustomPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize="11" fontWeight="600">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  if (!rev) return null;

  return (
    <section style={{ marginBottom:'40px' }}>
      <h3 style={{ display:'flex', alignItems:'center', gap:'10px', color:'#00f2fe', marginBottom:'20px', fontSize:'1.2rem', borderBottom:'1px solid var(--border-color)', paddingBottom:'10px' }}>
        <DollarSign size={20} /> 비즈니스 모델 & 수익 구조 (최근 연간 기준)
      </h3>

      {/* ── 수익 흐름 SVG 플로우 다이어그램 ── */}
      <div className="glass-panel" style={{ padding:'28px', marginBottom:'24px' }}>
        <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'20px', fontWeight:600 }}>
          💰 돈의 흐름 — {company.name}은 어떻게 수익을 만드는가
        </div>

        {/* Flow Diagram */}
        <div style={{ display:'flex', alignItems:'stretch', gap:'0', overflowX:'auto', padding:'4px 0' }}>
          {/* Revenue */}
          <FlowBox
            label="매출액"
            value={fB(rev)}
            pct="100%"
            color="#3b82f6"
            desc={p.industry || '핵심 사업'}
            isFirst
          />
          <FlowArrow />

          {/* COGS Split */}
          <div style={{ display:'flex', flexDirection:'column', gap:'8px', minWidth:'160px' }}>
            <FlowBox label="매출원가 (COGS)" value={fB(cogs)} pct={`${(cogs/rev*100).toFixed(1)}%`} color="#ff6b6b" desc="제품·서비스 원가" small />
            <FlowBox label="매출총이익" value={fB(gp)} pct={`${gpm.toFixed(1)}%`} color="#10b981" desc="Gross Profit" small highlight />
          </div>
          <FlowArrow />

          {/* OpEx Split */}
          <div style={{ display:'flex', flexDirection:'column', gap:'8px', minWidth:'160px' }}>
            <FlowBox label="판관비·R&D" value={fB(opEx)} pct={`${(opEx/rev*100).toFixed(1)}%`} color="#f97316" desc="운영비 공제" small />
            <FlowBox label="영업이익" value={fB(opInc)} pct={`${opm.toFixed(1)}%`} color="#8b5cf6" desc="Operating Income" small highlight />
          </div>
          <FlowArrow />

          {/* Net Income */}
          <div style={{ display:'flex', flexDirection:'column', gap:'8px', minWidth:'160px' }}>
            <FlowBox label="세금·이자·기타" value={fB(taxOther)} pct={`${(taxOther/rev*100).toFixed(1)}%`} color="#ef4444" desc="비영업 비용" small />
            <FlowBox label="🏆 순이익" value={fB(netInc)} pct={`${npm.toFixed(1)}%`} color="#00f2fe" desc="Net Income" small highlight glow />
          </div>
        </div>

        {/* 마진율 요약 바 */}
        <div style={{ marginTop:'24px', padding:'16px', borderRadius:'8px', background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize:'0.8rem', color:'var(--text-secondary)', marginBottom:'12px', fontWeight:600 }}>매출 $1에서 남는 이익</div>
          <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
            {[
              { label:'매출총이익률 (GPM)', pct: gpm, color:'#10b981' },
              { label:'영업이익률 (OPM)', pct: opm, color:'#8b5cf6' },
              { label:'순이익률 (NPM)',   pct: npm, color:'#00f2fe' },
            ].map(row => (
              <div key={row.label} style={{ display:'flex', alignItems:'center', gap:'12px' }}>
                <div style={{ width:'140px', fontSize:'0.8rem', color:'var(--text-secondary)', flexShrink:0 }}>{row.label}</div>
                <div style={{ flex:1, height:'10px', background:'rgba(255,255,255,0.06)', borderRadius:'99px', overflow:'hidden' }}>
                  <div style={{ width:`${Math.max(0,Math.min(100,row.pct))}%`, height:'100%', background:row.color, borderRadius:'99px', transition:'width 0.8s ease' }} />
                </div>
                <div style={{ width:'50px', textAlign:'right', fontSize:'0.85rem', fontWeight:700, color:row.color }}>{row.pct.toFixed(1)}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── 수익 폭포 차트 + 비용 구조 파이 ── */}
      <div style={{ display:'grid', gridTemplateColumns:'3fr 2fr', gap:'20px' }}>
        {/* Waterfall Chart */}
        <div className="glass-panel" style={{ padding:'24px' }}>
          <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'16px', fontWeight:600 }}>
            📊 수익 폭포 차트 (Profit Waterfall) — $B
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={wfData.map(d => ({
              name: d.name,
              invisible: d.isSum ? 0 : d.start,
              visible: Math.abs(d.value),
              fill: d.fill,
              isNeg: d.value < 0,
            }))} margin={{ top:10, right:10, left:10, bottom:40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" stroke="var(--text-secondary)" fontSize={11}
                tick={{ fill:'var(--text-secondary)', fontSize:11 }}
                angle={-20} textAnchor="end" height={55} />
              <YAxis stroke="var(--text-secondary)" fontSize={11} unit="B" />
              <RechartsTooltip content={<CustomWaterfallTooltip />} />
              <Bar dataKey="invisible" stackId="a" fill="transparent" />
              <Bar dataKey="visible" stackId="a" radius={[4,4,0,0]}>
                {wfData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} fillOpacity={entry.isSum ? 1 : 0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Cost Breakdown Pie */}
        <div className="glass-panel" style={{ padding:'24px' }}>
          <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'16px', fontWeight:600 }}>
            🥧 매출 배분 구조
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={costPieData} cx="50%" cy="50%" innerRadius={50} outerRadius={90}
                dataKey="value" labelLine={false} label={CustomPieLabel}>
                {costPieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => fB(v)}
                contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', fontSize:'0.82rem' }}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div style={{ display:'flex', flexDirection:'column', gap:'6px', marginTop:'8px' }}>
            {costPieData.map((d,i) => (
              <div key={i} style={{ display:'flex', alignItems:'center', gap:'8px', fontSize:'0.8rem' }}>
                <div style={{ width:'10px', height:'10px', borderRadius:'2px', background:d.color, flexShrink:0 }} />
                <span style={{ color:'var(--text-secondary)', flex:1 }}>{d.name}</span>
                <span style={{ color:'var(--text-primary)', fontWeight:600 }}>{(d.value/rev*100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ── FlowBox (수익 흐름 시각화 박스) ─────────────────────
function FlowBox({ label, value, pct, color, desc, isFirst, small, highlight, glow }) {
  return (
    <div style={{
      minWidth: small ? '150px' : '180px',
      padding: small ? '12px 14px' : '18px 20px',
      borderRadius:'10px',
      background: highlight
        ? `linear-gradient(135deg, ${color}18, ${color}08)`
        : 'rgba(255,255,255,0.03)',
      border: `1px solid ${highlight ? color + '50' : 'rgba(255,255,255,0.08)'}`,
      boxShadow: glow ? `0 0 20px ${color}40` : 'none',
      display:'flex', flexDirection:'column', gap:'4px',
      flex: small ? '0 0 auto' : '0 0 auto',
    }}>
      <div style={{ fontSize:'0.72rem', color:'var(--text-secondary)', fontWeight:500, textTransform:'uppercase', letterSpacing:'0.04em' }}>{label}</div>
      <div style={{ fontSize: small ? '1rem' : '1.3rem', fontWeight:700, color: color, fontVariantNumeric:'tabular-nums' }}>{value}</div>
      <div style={{ fontSize:'0.75rem', color: highlight ? color : 'var(--text-secondary)' }}>매출 대비 {pct}</div>
      <div style={{ fontSize:'0.72rem', color:'var(--text-secondary)', marginTop:'2px' }}>{desc}</div>
    </div>
  );
}

// ── FlowArrow ────────────────────────────────────────────
function FlowArrow() {
  return (
    <div style={{ display:'flex', alignItems:'center', padding:'0 8px', color:'rgba(255,255,255,0.3)', fontSize:'1.4rem', flexShrink:0, alignSelf:'center' }}>
      →
    </div>
  );
}

// ── AI 포트폴리오 매니저 ─────────────────────────────────
function AgentWorkspace() {
  const [portfolio, setPortfolio] = useState(null);
  const [running, setRunning] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const pollRef = React.useRef(null);

  const LOADING_STEPS = [
    { icon: '🔍', text: '전 산업 밸류체인 분석 중...' },
    { icon: '📊', text: `60+ 기업 성장성 스크리닝 중...` },
    { icon: '💰', text: '현재 주가 대비 업사이드 갭 계산 중...' },
    { icon: '🧮', text: '5~10년 기대수익률 모델링 중...' },
    { icon: '⚖️', text: '최적 비중 배분 알고리즘 실행 중...' },
    { icon: '✍️', text: 'AI가 투자 근거를 작성 중...' },
  ];

  // 로딩 스텝 순환
  useEffect(() => {
    let t;
    if (running) t = setInterval(() => setLoadingStep(s => (s + 1) % LOADING_STEPS.length), 2500);
    return () => clearInterval(t);
  }, [running]);

  // 기존 포트폴리오 로드
  useEffect(() => {
    axios.get(`${API_BASE}/orchestration/report`)
      .then(r => {
        if (r.data?.content) {
          try {
            const d = JSON.parse(r.data.content);
            if (d.type === 'portfolio') setPortfolio(d);
          } catch (_) {}
        }
      }).catch(() => {});
  }, []);

  const startPortfolio = async () => {
    setRunning(true);
    setPortfolio(null);
    setLoadingStep(0);
    try {
      await axios.post(`${API_BASE}/agents/run`);
      // 폴링
      pollRef.current = setInterval(async () => {
        try {
          const r = await axios.get(`${API_BASE}/orchestration/report`);
          if (r.data?.content) {
            try {
              const d = JSON.parse(r.data.content);
              if (d.type === 'portfolio' && d.portfolio?.length > 0) {
                setPortfolio(d);
                setRunning(false);
                clearInterval(pollRef.current);
              }
            } catch (_) {}
          }
        } catch (_) {}
      }, 2000);
      // 3분 타임아웃
      setTimeout(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        setRunning(false);
      }, 180000);
    } catch (e) {
      setRunning(false);
    }
  };

  const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'];
  const RANK_COLORS = ['#FFD700', '#C0C0C0', '#CD7F32', '#3b82f6', '#6b7280'];
  const RANK_LABELS = ['🥇 1위', '🥈 2위', '🥉 3위', '4위', '5위'];

  const pieData = portfolio?.portfolio?.map((s, i) => ({
    name: s.ticker, value: s.weight, fill: PIE_COLORS[i]
  })) || [];

  return (
    <div className="agent-workspace">
      {/* ── 헤더 ── */}
      <div className="page-header" style={{
        display:'flex', justifyContent:'space-between', alignItems:'flex-start',
        borderBottom:'1px solid var(--border-color)', paddingBottom:'24px', marginBottom:'32px'
      }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:'10px', marginBottom:'10px' }}>
            <span className={`live-badge ${running ? 'active' : ''}`}>
              {running ? '● 분석 진행 중' : portfolio ? '● 포트폴리오 구성 완료' : '● 대기 중'}
            </span>
            <span style={{ color:'var(--text-secondary)', fontSize:'0.85rem' }}>
              Multi-Agent Portfolio Manager
            </span>
          </div>
          <h2 style={{ fontSize:'2.2rem', margin:0 }}>AI 포트폴리오 매니저</h2>
          <p style={{ color:'var(--text-secondary)', margin:'8px 0 0', fontSize:'0.9rem' }}>
            전 산업 · 전 기업 스크리닝 → 5종목 집중 포트폴리오 · 5~10년 중장기 최적 비중 배분
          </p>
        </div>
        <button
          className="run-btn"
          disabled={running}
          onClick={startPortfolio}
          style={{ whiteSpace:'nowrap', flexShrink:0 }}
        >
          {running ? '⏳ 포트폴리오 구성 중...' : '🚀 포트폴리오 구성 실행'}
        </button>
      </div>

      {/* ── 로딩 상태 ── */}
      {running && (
        <div className="glass-panel" style={{
          padding:'60px 40px', textAlign:'center',
          background:'linear-gradient(135deg, rgba(59,130,246,0.06), rgba(139,92,246,0.06))',
          border:'1px solid rgba(59,130,246,0.2)', borderRadius:'16px', marginBottom:'32px',
        }}>
          {/* 스피너 */}
          <div style={{ position:'relative', width:'80px', height:'80px', margin:'0 auto 32px' }}>
            <div style={{
              position:'absolute', inset:0,
              border:'3px solid rgba(59,130,246,0.15)', borderTopColor:'#3b82f6',
              borderRadius:'50%', animation:'spin 1s linear infinite',
            }} />
            <div style={{
              position:'absolute', inset:'10px',
              border:'3px solid rgba(139,92,246,0.15)', borderBottomColor:'#8b5cf6',
              borderRadius:'50%', animation:'spin 1.5s linear infinite reverse',
            }} />
            <div style={{
              position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center',
              fontSize:'1.8rem',
            }}>
              {LOADING_STEPS[loadingStep].icon}
            </div>
          </div>
          <div style={{ fontSize:'1.1rem', fontWeight:600, color:'white', marginBottom:'8px' }}>
            {LOADING_STEPS[loadingStep].text}
          </div>
          <div style={{ color:'rgba(255,255,255,0.4)', fontSize:'0.85rem' }}>
            3단계 스크리닝: Quant(30%) + Growth(40%) + Upside Gap(30%)
          </div>
          {/* 단계 도트 */}
          <div style={{ display:'flex', justifyContent:'center', gap:'8px', marginTop:'24px' }}>
            {LOADING_STEPS.map((_, i) => (
              <div key={i} style={{
                width:'8px', height:'8px', borderRadius:'50%',
                background: i === loadingStep ? '#3b82f6' : 'rgba(255,255,255,0.15)',
                transition:'background 0.3s',
              }} />
            ))}
          </div>
        </div>
      )}

      {/* ── 빈 상태 ── */}
      {!running && !portfolio && (
        <div className="glass-panel" style={{
          padding:'80px 40px', textAlign:'center',
          border:'1px dashed rgba(255,255,255,0.1)', borderRadius:'16px',
        }}>
          <div style={{ fontSize:'4rem', marginBottom:'20px' }}>📊</div>
          <div style={{ fontSize:'1.2rem', fontWeight:700, color:'white', marginBottom:'12px' }}>
            AI 포트폴리오 매니저
          </div>
          <div style={{ color:'var(--text-secondary)', maxWidth:'480px', margin:'0 auto', lineHeight:'1.7', fontSize:'0.95rem' }}>
            버튼을 클릭하면 AI가 <strong>5개 산업 · 60개+ 기업</strong>을 전수 분석하여<br />
            현재 주가 대비 <strong>5~10년 기대수익률이 가장 높은 5종목</strong>을<br />
            확신도 비례 차등 비중으로 구성합니다.
          </div>
          <div style={{
            display:'flex', justifyContent:'center', gap:'24px', marginTop:'32px',
            fontSize:'0.82rem', color:'rgba(255,255,255,0.3)',
          }}>
            <span>📐 Quant 30%</span>
            <span>🌱 Growth 40%</span>
            <span>🎯 Upside Gap 30%</span>
          </div>
        </div>
      )}

      {/* ── 포트폴리오 결과 ── */}
      {!running && portfolio && (
        <div>
          {/* 요약 헤더 */}
          <div className="glass-panel" style={{
            padding:'24px 32px', marginBottom:'24px',
            background:'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(139,92,246,0.06))',
            border:'1px solid rgba(59,130,246,0.25)',
          }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:'16px' }}>
              <div>
                <div style={{ fontSize:'1.4rem', fontWeight:800, color:'white', marginBottom:'4px' }}>
                  🏆 AI 최적 포트폴리오 — 중장기 집중 투자 (5~10년)
                </div>
                <div style={{ color:'rgba(255,255,255,0.45)', fontSize:'0.82rem' }}>
                  구성일: {portfolio.created_at} · {portfolio.total_industries_analyzed}개 산업 · {portfolio.total_companies_screened}개 기업 스크리닝
                </div>
              </div>
              <div style={{ display:'flex', gap:'24px' }}>
                {[
                  { label:'Base CAGR', val:`~${portfolio.scenario?.base?.cagr || '-'}%/yr`, color:'#3b82f6' },
                  { label:'5년 기대수익', val:`+${portfolio.scenario?.base?.return_pct || '-'}%`, color:'#10b981' },
                  { label:'Bull Case', val:`+${portfolio.scenario?.bull?.return_pct || '-'}%`, color:'#f59e0b' },
                ].map(({ label, val, color }) => (
                  <div key={label} style={{ textAlign:'center' }}>
                    <div style={{ fontSize:'0.72rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>{label}</div>
                    <div style={{ fontSize:'1.3rem', fontWeight:800, color }}>{val}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 메인: 도넛 차트 + 종목 카드 */}
          <div style={{ display:'grid', gridTemplateColumns:'300px 1fr', gap:'24px', marginBottom:'24px' }}>

            {/* 도넛 차트 */}
            <div className="glass-panel" style={{ padding:'24px', display:'flex', flexDirection:'column', alignItems:'center' }}>
              <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'16px', fontWeight:600 }}>
                포트폴리오 비중 배분
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%" cy="50%"
                    innerRadius={68} outerRadius={100}
                    dataKey="value"
                    paddingAngle={3}
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v, name) => [`${v}%`, name]}
                    contentStyle={{
                      backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)',
                      fontSize:'0.82rem', borderRadius:'8px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* 범례 */}
              <div style={{ width:'100%', display:'flex', flexDirection:'column', gap:'8px', marginTop:'8px' }}>
                {portfolio.portfolio.map((s, i) => (
                  <div key={i} style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                    <div style={{ width:'12px', height:'12px', borderRadius:'3px', background:PIE_COLORS[i], flexShrink:0 }} />
                    <div style={{ flex:1, fontSize:'0.82rem', color:'var(--text-primary)', fontWeight:600 }}>{s.ticker}</div>
                    <div style={{ fontSize:'0.82rem', color:PIE_COLORS[i], fontWeight:700 }}>{s.weight}%</div>
                    {/* 비중 바 */}
                    <div style={{ width:'60px', height:'4px', background:'rgba(255,255,255,0.08)', borderRadius:'4px', overflow:'hidden' }}>
                      <div style={{ width:`${s.weight}%`, height:'100%', background:PIE_COLORS[i], borderRadius:'4px' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 5개 종목 카드 */}
            <div style={{ display:'flex', flexDirection:'column', gap:'12px' }}>
              {portfolio.portfolio.map((stock, i) => {
                const col = PIE_COLORS[i];
                const rankCol = RANK_COLORS[i];
                return (
                  <div key={i} className="glass-panel" style={{
                    padding:'18px 22px',
                    borderLeft:`4px solid ${col}`,
                    background:`linear-gradient(135deg, ${col}08, transparent)`,
                    transition:'box-shadow 0.2s',
                  }}>
                    {/* 상단: 종목명 + 비중 */}
                    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'10px' }}>
                      <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                        <span style={{
                          background:`${rankCol}22`, border:`1px solid ${rankCol}66`,
                          color:rankCol, borderRadius:'10px', padding:'2px 10px',
                          fontSize:'0.72rem', fontWeight:700,
                        }}>
                          {RANK_LABELS[i]}
                        </span>
                        <span style={{ fontSize:'1.05rem', fontWeight:700, color:'white' }}>{stock.name}</span>
                        <span style={{
                          background:'rgba(255,255,255,0.08)', borderRadius:'6px',
                          padding:'2px 8px', fontSize:'0.75rem', color:'rgba(255,255,255,0.5)',
                          fontFamily:'monospace',
                        }}>{stock.ticker}</span>
                        <span style={{
                          background:`${col}18`, border:`1px solid ${col}44`,
                          color:col, borderRadius:'8px', padding:'2px 8px', fontSize:'0.72rem',
                        }}>{stock.industry}</span>
                      </div>
                      <div style={{ textAlign:'right' }}>
                        <div style={{ fontSize:'1.8rem', fontWeight:900, color:col, lineHeight:1 }}>{stock.weight}%</div>
                        <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.3)' }}>포트폴리오 비중</div>
                      </div>
                    </div>

                    {/* 중단: 주가 & CAGR */}
                    <div style={{
                      display:'flex', gap:'20px', marginBottom:'10px',
                      padding:'10px 14px', background:'rgba(0,0,0,0.2)', borderRadius:'8px',
                      flexWrap:'wrap',
                    }}>
                      {stock.current_price && (
                        <div>
                          <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.35)' }}>현재가</div>
                          <div style={{ fontWeight:700, color:'white', fontFamily:'monospace' }}>${stock.current_price}</div>
                        </div>
                      )}
                      {stock.target_price_5y && (
                        <>
                          <div style={{ color:'rgba(255,255,255,0.2)', alignSelf:'center' }}>→</div>
                          <div>
                            <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.35)' }}>5년 목표</div>
                            <div style={{ fontWeight:700, color:'#10b981', fontFamily:'monospace' }}>${stock.target_price_5y}</div>
                          </div>
                          <div>
                            <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.35)' }}>총 수익</div>
                            <div style={{ fontWeight:700, color:'#10b981' }}>+{stock.total_return_5y}%</div>
                          </div>
                          <div>
                            <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.35)' }}>CAGR</div>
                            <div style={{ fontWeight:700, color:col }}>{stock.cagr_5y}%/yr</div>
                          </div>
                        </>
                      )}
                      <div style={{ marginLeft:'auto', display:'flex', gap:'12px' }}>
                        {[
                          { label:'Quant', val:stock.quant_score },
                          { label:'Growth', val:stock.growth_score },
                          { label:'Upside', val:stock.upside_score },
                        ].map(({ label, val }) => (
                          <div key={label} style={{ textAlign:'center' }}>
                            <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.3)' }}>{label}</div>
                            <div style={{
                              fontSize:'0.82rem', fontWeight:700,
                              color: val >= 70 ? '#10b981' : val >= 50 ? '#f59e0b' : '#ef4444',
                            }}>{val}</div>
                          </div>
                        ))}
                        <div style={{ textAlign:'center' }}>
                          <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.3)' }}>종합</div>
                          <div style={{ fontSize:'0.9rem', fontWeight:800, color:col }}>{stock.portfolio_score}</div>
                        </div>
                      </div>
                    </div>

                    {/* 하단: 투자 논거 & 리스크 */}
                    <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                      {/* 핵심 재무 메트릭 한 줄 */}
                      {stock.metrics && (
                        <div style={{
                          display:'flex', gap:'12px', flexWrap:'wrap',
                          padding:'8px 12px',
                          background:'rgba(255,255,255,0.04)',
                          borderRadius:'8px',
                          fontSize:'0.72rem',
                        }}>
                          {[
                            { label:'매출성장', val: stock.metrics.revenue_growth },
                            { label:'순이익률', val: stock.metrics.net_margin },
                            { label:'ROE', val: stock.metrics.roe },
                            { label:'PER', val: stock.metrics.pe_ratio },
                            { label:'EV/EBITDA', val: stock.metrics.ev_ebitda },
                            { label:'부채비율', val: stock.metrics.debt_to_equity },
                            { label:'FCF', val: stock.metrics.fcf },
                          ].filter(m => m.val && m.val !== 'N/A').map(({ label, val }) => (
                            <div key={label} style={{ display:'flex', gap:'4px', alignItems:'center' }}>
                              <span style={{ color:'rgba(255,255,255,0.35)' }}>{label}</span>
                              <span style={{ color:'rgba(255,255,255,0.75)', fontWeight:600, fontFamily:'monospace' }}>{val}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* 투자 논거 (번호 목록) */}
                      <div>
                        <div style={{ fontSize:'0.75rem', color:col, fontWeight:700, marginBottom:'6px' }}>
                          📌 투자 논거
                        </div>
                        <div style={{ display:'flex', flexDirection:'column', gap:'5px' }}>
                          {(stock.thesis || [stock.selection_reason]).map((point, pi) => (
                            <div key={pi} style={{
                              display:'flex', gap:'8px', fontSize:'0.84rem',
                              color:'rgba(255,255,255,0.78)', lineHeight:'1.6',
                              paddingLeft:'4px',
                            }}>
                              <span style={{
                                flexShrink:0, width:'18px', height:'18px',
                                borderRadius:'50%', background:`${col}30`,
                                border:`1px solid ${col}60`, color:col,
                                fontSize:'0.65rem', fontWeight:700,
                                display:'flex', alignItems:'center', justifyContent:'center',
                                marginTop:'2px',
                              }}>{pi + 1}</span>
                              <span>{point}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 리스크 요인 */}
                      <div style={{
                        padding:'10px 12px',
                        background:'rgba(239,68,68,0.06)',
                        border:'1px solid rgba(239,68,68,0.2)',
                        borderRadius:'8px',
                      }}>
                        <div style={{ fontSize:'0.73rem', color:'#ef4444', fontWeight:700, marginBottom:'5px' }}>
                          ⚠️ 리스크 요인
                        </div>
                        <div style={{ display:'flex', flexDirection:'column', gap:'4px' }}>
                          {(stock.risks || [stock.key_risk]).map((risk, ri) => (
                            <div key={ri} style={{
                              display:'flex', gap:'6px',
                              fontSize:'0.82rem', color:'rgba(239,120,100,0.85)', lineHeight:'1.55',
                            }}>
                              <span style={{ flexShrink:0, color:'rgba(239,68,68,0.6)', marginTop:'2px' }}>▸</span>
                              <span>{risk}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 시나리오 테이블 */}
          {portfolio.scenario && (
            <div className="glass-panel" style={{ padding:'24px 28px', marginBottom:'24px' }}>
              <div style={{ fontSize:'1rem', fontWeight:700, marginBottom:'16px', color:'var(--accent-blue)' }}>
                📈 5년 시나리오 분석
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'12px' }}>
                {[
                  { key:'bull', label:'Bull Case', emoji:'🚀', color:'#10b981' },
                  { key:'base', label:'Base Case', emoji:'📊', color:'#3b82f6' },
                  { key:'bear', label:'Bear Case', emoji:'🐻', color:'#ef4444' },
                ].map(({ key, label, emoji, color }) => {
                  const sc = portfolio.scenario[key];
                  if (!sc) return null;
                  return (
                    <div key={key} style={{
                      padding:'16px', borderRadius:'12px',
                      background:`${color}0a`, border:`1px solid ${color}30`,
                    }}>
                      <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'10px' }}>
                        <span style={{ fontSize:'1.2rem' }}>{emoji}</span>
                        <span style={{ fontWeight:700, color }}>{label}</span>
                        <span style={{
                          marginLeft:'auto', background:`${color}20`, border:`1px solid ${color}40`,
                          color, borderRadius:'8px', padding:'2px 8px', fontSize:'0.72rem', fontWeight:700,
                        }}>P: {sc.probability}%</span>
                      </div>
                      <div style={{ fontSize:'1.8rem', fontWeight:900, color, marginBottom:'4px' }}>
                        {sc.return_pct >= 0 ? '+' : ''}{sc.return_pct}%
                      </div>
                      <div style={{ fontSize:'0.8rem', color:`${color}99`, marginBottom:'8px' }}>
                        CAGR {sc.cagr}%/yr
                      </div>
                      <div style={{ fontSize:'0.78rem', color:'rgba(255,255,255,0.45)', lineHeight:'1.5' }}>
                        {sc.trigger}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 스코어링 방법론 */}
          <div className="glass-panel" style={{
            padding:'16px 24px', background:'rgba(255,255,255,0.02)',
            border:'1px solid rgba(255,255,255,0.06)',
          }}>
            <div style={{ display:'flex', gap:'24px', flexWrap:'wrap', fontSize:'0.78rem', color:'rgba(255,255,255,0.35)' }}>
              <span style={{ fontWeight:700, color:'rgba(255,255,255,0.5)' }}>스코어링 방법론</span>
              {portfolio.scoring_weights && Object.values(portfolio.scoring_weights).map((v, i) => (
                <span key={i}>· {v}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

export default App;
