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

  // Cold Start 대응: 최대 5회 재시도, 점진적 대기
  const fetchReportsWithRetry = async (attempt = 0) => {
    const msgs = [
      '서버에 연결 중...',
      '서버를 깨우는 중... (최초 접속 시 약 30초 소요)',
      '데이터를 불러오는 중...',
      '거의 다 됐어요!',
      '마지막 단계...',
    ];
    setLoadingMsg(msgs[Math.min(attempt, msgs.length - 1)]);
    setRetryCount(attempt);
    try {
      const res = await axios.get(`${API_BASE}/reports`, { timeout: 15000 });
      setReports(res.data);
      if (res.data.length > 0) fetchReportDetails(res.data[0].id);
      setLoading(false);
    } catch (e) {
      if (attempt < 6) {
        const delay = Math.min(3000 * (attempt + 1), 12000);
        setTimeout(() => fetchReportsWithRetry(attempt + 1), delay);
      } else {
        setLoadingMsg('연결 실패. 페이지를 새로고침 해주세요.');
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

      {/* 메시지 */}
      <div style={{ textAlign: 'center', maxWidth: '320px' }}>
        <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.95rem', marginBottom: '8px', minHeight: '24px' }}>
          {loadingMsg}{'.'  .repeat(loadingDot)}
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

      <h3 style={{ marginBottom:'24px', color:'var(--accent-blue)', fontSize:'1.4rem', borderBottom:'1px solid var(--border-color)', paddingBottom:'12px' }}>
        Key Tracked Companies
      </h3>
      <div className="company-list">
        {report.companies.map(comp => (
          <div key={comp.id} className="company-pill glass-panel" onClick={() => onSelectCompany(comp.id)}>
            <div className="company-header">
              <span className="company-name">{comp.name}</span>
              <span className="company-ticker">{comp.ticker}</span>
            </div>
            <div style={{ fontSize:'0.9rem', color:'var(--text-secondary)', display:'-webkit-box', WebkitLineClamp:3, WebkitBoxOrient:'vertical', overflow:'hidden' }}>
              {comp.role_description}
            </div>
          </div>
        ))}
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
  const annualRaw = (financials || []).filter(f => f.period_type === 'annual').sort((a,b) => new Date(a.date)-new Date(b.date));
  const annualMap = new Map();
  annualRaw.forEach(d => annualMap.set(d.date.substring(0,4), d));
  const annualData = Array.from(annualMap.values());

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
  const latest = annualData[annualData.length-1] || {};

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
                <tr><td colSpan="14" style={{ textAlign:'center', padding:'40px', color:'var(--text-secondary)' }}>No data available</td></tr>
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
  const cogs = latest.cost_of_revenue || 0;
  const gp = latest.gross_profit || (rev - cogs);
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

// ── AgentWorkspace (기존 코드 유지) ──────────────────────
function AgentWorkspace() {

  const [agents, setAgents] = useState([]);
  const [messages, setMessages] = useState([]);
  const [report, setReport] = useState(null);
  const [running, setRunning] = useState(false);
  const [activeAgentName, setActiveAgentName] = useState(null);
  const terminalEndRef = React.useRef(null);

  useEffect(() => { fetchAgents(); fetchMessages(); fetchReport(); }, []);

  useEffect(() => {
    if (terminalEndRef.current) terminalEndRef.current.scrollIntoView({ behavior:'smooth' });
    if (messages.length > 0) {
      const last = messages[messages.length-1];
      if (last.sender !== 'System') setActiveAgentName(last.sender);
    }
  }, [messages]);

  useEffect(() => {
    let interval;
    if (running) interval = setInterval(() => { fetchMessages(); fetchReport(); }, 1500);
    return () => clearInterval(interval);
  }, [running]);

  const fetchAgents = async () => { try { const r = await axios.get(`${API_BASE}/agents`); setAgents(r.data); } catch(e){} };
  const fetchMessages = async () => {
    try {
      const r = await axios.get(`${API_BASE}/agents/messages`);
      setMessages(r.data);
      if (r.data.some(m => m.content.includes('시뮬레이션을 종료합니다.'))) setRunning(false);
    } catch(e){}
  };
  const fetchReport = async () => {
    try {
      const r = await axios.get(`${API_BASE}/orchestration/report`);
      setReport(r.data?.title !== '보고서 없음' ? r.data : null);
    } catch(e){}
  };
  const startAnalysis = async () => {
    setRunning(true); setMessages([]); setReport(null); setActiveAgentName(null);
    try { await axios.post(`${API_BASE}/agents/run`); } catch(e) { setRunning(false); }
  };

  const getAgentColor = (sender, type, isThought) => {
    if (isThought) return '#888888';
    if (sender === 'System') return '#00f2fe';
    if (type === 'orchestrator') return '#39ff14';
    if (type === 'management') return '#00f2fe';
    if (type === 'industry') return '#00bfff';
    if (type === 'company') return '#bd93f9';
    return 'var(--text-primary)';
  };

  const orchestrator = agents.find(a => a.type === 'orchestrator');
  const managers = agents.filter(a => a.type === 'management');
  const industryAgents = agents.filter(a => a.type === 'industry');
  const companyAgents = agents.filter(a => a.type === 'company');

  return (
    <div className="agent-workspace">
      <div className="page-header" style={{ display:'flex', justifyContent:'space-between', alignItems:'center', borderBottom:'1px solid var(--border-color)', paddingBottom:'24px', marginBottom:'32px' }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'8px' }}>
            <span className={`live-badge ${running?'active':''}`}>{running?'● LIVE ANALYSIS':'● IDLE'}</span>
            <span style={{ color:'var(--text-secondary)' }}>Multi-Agent Strategy Room</span>
          </div>
          <h2 style={{ fontSize:'2.5rem' }}>AI 애널리스트 워크스페이스</h2>
        </div>
        <button className="run-btn" disabled={running} onClick={startAnalysis}>
          {running ? '협동 분석 진행 중...' : 'AI 협동 분석 가동'}
        </button>
      </div>

      <div className="workspace-grid">
        <div className="glass-panel" style={{ padding:'24px', display:'flex', flexDirection:'column', gap:'20px' }}>
          <h3 style={{ color:'var(--accent-blue)', display:'flex', alignItems:'center', gap:'8px' }}>
            <Activity size={20} /> 오케스트레이션 구성망 (Agent Tree)
          </h3>
          <div className="agent-tree">
            <div className="tree-level row-layout wrap-layout" style={{ justifyContent: 'center', gap: '24px' }}>
              {orchestrator && (
                <div className={`agent-node orch-node ${activeAgentName===orchestrator.name?'active-glow':''}`}>
                  <div className="node-role">Orchestrator</div>
                  <div className="node-name">{orchestrator.name}</div>
                  <div className="node-desc" style={{ fontSize:'0.75rem', opacity:0.8 }}>{orchestrator.role}</div>
                </div>
              )}
              {managers.map(m => (
                <div key={m.id} className={`agent-node manager-node ${activeAgentName===m.name?'active-glow':''}`}>
                  <div className="node-role">{m.name === 'App Developer Agent' ? 'App Manager' : 'Site Manager'}</div>
                  <div className="node-name">{m.name}</div>
                  <div className="node-desc" style={{ fontSize:'0.75rem', opacity:0.8 }}>{m.role}</div>
                </div>
              ))}
            </div>
            <div className="tree-divider"></div>
            <div className="tree-level row-layout">
              {industryAgents.map(a => (
                <div key={a.id} className={`agent-node ind-node ${activeAgentName===a.name?'active-glow':''}`}>
                  <div className="node-role">Industry Analyst</div>
                  <div className="node-name">{a.name}</div>
                  <div className="node-desc" style={{ fontSize:'0.75rem', opacity:0.8 }}>{a.role}</div>
                </div>
              ))}
            </div>
            <div className="tree-divider"></div>
            <div className="tree-level row-layout wrap-layout">
              {companyAgents.map(a => (
                <div key={a.id} className={`agent-node comp-node ${activeAgentName===a.name?'active-glow':''}`}>
                  <div className="node-role">Company Monitor</div>
                  <div className="node-name">{a.name}</div>
                  <div className="node-desc" style={{ fontSize:'0.75rem', opacity:0.8 }}>{a.role}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="terminal-panel glass-panel">
          <div className="terminal-header">
            <span>TERMINAL LOGS</span>
            {running && <span className="loader-dots"></span>}
          </div>
          <div className="terminal-body">
            {messages.length === 0 ? (
              <div className="terminal-placeholder">AI 분석 가동 버튼을 누르면 에이전트들이 실시간 대화를 나누며 보고서를 도출합니다.</div>
            ) : (
              messages.map((m) => {
                const isThought = m.msg_type === 'thought';
                return (
                  <div key={m.id} className={`terminal-line ${isThought?'thought-line':''}`}>
                    <span className="timestamp">[{m.timestamp.substring(11)}]</span>{' '}
                    <span className="sender" style={{ color:getAgentColor(m.sender, m.sender_type, isThought) }}>
                      {m.sender}{isThought?'의 생각':''}:
                    </span>{' '}
                    <span className="content">{m.content}</span>
                  </div>
                );
              })
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>
      </div>

      {report && (
        <div className="report-content glass-panel" style={{ padding:'40px', marginTop:'40px' }}>
          <h2 style={{ color:'var(--accent-blue)', fontSize:'1.8rem', borderBottom:'1px solid var(--border-color)', paddingBottom:'16px', marginBottom:'24px' }}>
            {report.title}
          </h2>
          <div className="markdown-body">
            <ReactMarkdown>{report.content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
