// Build: 20260808-184331
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

// ?? ?щ㎎ ?좏떥 ??????????????????????????????????????????
const isKrw = (ticker) => ticker && (ticker.endsWith('.KS') || ticker.endsWith('.KQ'));

const fB = (n, t) => {
  if (n == null) return '-';
  if (isKrw(t)) return `??{(n/1e8).toLocaleString(undefined, {maximumFractionDigits:0})}??;
  return `$${(n/1e9).toFixed(2)}B`;
};

const fM = (n, t) => {
  if (n == null) return '-';
  if (isKrw(t)) return `??{(n/1e8).toLocaleString(undefined, {maximumFractionDigits:1})}??;
  return `$${(n/1e6).toFixed(0)}M`;
};

const fP  = (n) => n == null ? '-' : `${(n*100).toFixed(1)}%`;
const fP2 = (n) => n == null ? '-' : `${n.toFixed(1)}%`;
const fX  = (n) => n == null ? '-' : `${n.toFixed(2)}x`;
const fN  = (n) => n == null ? '-' : n.toFixed(2);
const fK  = (n) => n == null ? '-' : n.toLocaleString();

const fDollar = (n, t) => {
  if (n == null) return '-';
  if (isKrw(t)) return `??{n.toLocaleString(undefined, {maximumFractionDigits:0})}`;
  return `$${n.toFixed(2)}`;
};

const color = (v, good, bad) => {
  if (v == null) return 'var(--text-secondary)';
  return v >= good ? 'var(--accent-green)' : v <= bad ? '#ff6b6b' : 'var(--text-primary)';
};

// ?? 硫붿씤 ???????????????????????????????????????????????
function App() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [companyProfile, setCompanyProfile] = useState(null);
  const [companyFinancials, setCompanyFinancials] = useState(null);
  const [companyAiAnalysis, setCompanyAiAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMsg, setLoadingMsg] = useState('?쒕쾭???곌껐 以?..');
  const [loadingDot, setLoadingDot] = useState(0);
  const [retryCount, setRetryCount] = useState(0);
  const [viewMode, setViewMode] = useState('research');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [installPrompt, setInstallPrompt] = useState(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingPhase, setLoadingPhase] = useState('wakeup');
  const [showUpdateBanner, setShowUpdateBanner] = useState(false);


  // ?ㅻ줈媛湲?Back) 踰꾪듉 ?몃뱾??
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
  const isHomeRef = React.useRef(isHome);
  useEffect(() => {
    if (isHomeRef.current && !isHome) {
      window.history.pushState({ detail: true }, '');
    }
    isHomeRef.current = isHome;
  }, [isHome]);

  // PWA ?ㅼ튂 ?꾨＼?꾪듃 罹≪쿂 (Android Chrome)
  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      setInstallPrompt(e);
      setShowInstallBanner(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  // SW ?낅뜲?댄듃 媛먯? ???낅뜲?댄듃 諛곕꼫 ?쒖떆
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;
    const handleMsg = (e) => {
      if (e.data?.type === 'SW_UPDATED') {
        setShowUpdateBanner(true);
      }
    };
    navigator.serviceWorker.addEventListener('message', handleMsg);
    return () => navigator.serviceWorker.removeEventListener('message', handleMsg);
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

  // ?? ?쒕쾭 ?쒖뾽 ???곗씠??濡쒕뱶 ??????????????????????????????
  const fetchReportsWithRetry = async (attempt = 0) => {
    // 1?④퀎: ?쒖뾽 ??(?쒕쾭瑜?癒쇱? 源⑥?)
    if (attempt === 0) {
      setLoadingMsg('?쒕쾭 ?곌껐 以?..');
      setLoadingPhase('wakeup');
      setLoadingProgress(5);
      try {
        await axios.get(`${BACKEND_HOST}/ping`, { timeout: 60000 });
        setLoadingProgress(40);
        setLoadingPhase('data');
        setLoadingMsg('?곗씠??遺덈윭?ㅻ뒗 以?..');
      } catch (e) {
        // ping ?ㅽ뙣?대룄 怨꾩냽 吏꾪뻾
        setLoadingProgress(20);
      }
    }

    const msgs = [
      '?곗씠??遺덈윭?ㅻ뒗 以?..',
      '?곗씠??泥섎━ 以?..',
      '嫄곗쓽 ???먯뼱??',
      '留덉?留??④퀎...',
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
        setLoadingMsg('?곌껐 ?ㅽ뙣. ?섏씠吏瑜??덈줈怨좎묠 ?댁＜?몄슂.');
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
    setSelectedReport(null);
    setSidebarOpen(false);
  };

  // ?? ?ㅽ뵆?섏떆 濡쒕뵫 ?붾㈃ ?????????????????????????????????
  if (loading) return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0e1a 0%, #0d1526 50%, #0a1020 100%)',
      fontFamily: 'Inter, sans-serif',
    }}>
      {/* 濡쒓퀬 */}
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

      {/* ?ㅽ뵾??*/}
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

      {/* 吏꾪뻾瑜?諛?*/}
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
            {loadingPhase === 'wakeup' ? '?뵆 ?쒕쾭 ?쒖뾽 以? : '?뱤 ?곗씠??濡쒕뱶 以?}
          </span>
          <span style={{ fontSize:'0.7rem', color:'rgba(255,255,255,0.3)' }}>{loadingProgress}%</span>
        </div>
      </div>

      {/* 硫붿떆吏 */}
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
            ?봽 Render 臾대즺 ?쒕쾭??鍮꾪솢?????덉쟾 紐⑤뱶濡??꾪솚?⑸땲??<br />
            理쒖큹 ?묒냽 ??30~60珥??뚯슂?????덉뒿?덈떎.
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { transform: scale(1); box-shadow: 0 0 40px rgba(59,130,246,0.4); }
          50% { transform: scale(1.05); box-shadow: 0 0 60px rgba(59,130,246,0.6); } }
        @keyframes slideDown {
          from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
          to   { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>
  );

  return (
    <div className="layout">

      {/* ?? ???낅뜲?댄듃 諛곕꼫 ?? */}
      {showUpdateBanner && (
        <div style={{
          position: 'fixed', top: '16px', left: '50%', transform: 'translateX(-50%)',
          zIndex: 10000, display: 'flex', alignItems: 'center', gap: '12px',
          background: 'linear-gradient(135deg, #0f2027, #1a2a3a)',
          border: '1px solid rgba(16,185,129,0.5)',
          borderRadius: '14px', padding: '12px 18px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(16,185,129,0.15)',
          maxWidth: '340px', width: 'calc(100% - 32px)',
          animation: 'slideDown 0.3s ease-out',
        }}>
          <span style={{ fontSize: '1.3rem' }}>??</span>
          <div style={{ flex: 1 }}>
            <div style={{ color: 'white', fontWeight: 700, fontSize: '0.88rem' }}>??踰꾩쟾???덉뒿?덈떎</div>
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.74rem' }}>二쇰룄二??ㅼ퐫?대쭅 UI ?낅뜲?댄듃</div>
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: 'linear-gradient(135deg, #10b981, #059669)',
              border: 'none', borderRadius: '8px', color: 'white',
              padding: '7px 14px', fontSize: '0.82rem', fontWeight: 700,
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >吏湲??낅뜲?댄듃</button>
          <button
            onClick={() => setShowUpdateBanner(false)}
            style={{ background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.35)', fontSize: '1.1rem', cursor: 'pointer', padding: '0 4px' }}
          >??/button>
        </div>
      )}

      {/* ?? PWA ?ㅼ튂 諛곕꼫 (Android Chrome) ?? */}
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
            <div style={{ color: 'white', fontWeight: 700, fontSize: '0.9rem' }}>?깆쑝濡??ㅼ튂?섍린</div>
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>???붾㈃??異붽??섎㈃ ?깆쿂???ъ슜?????덉뼱??/div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <button onClick={handleInstallClick} style={{
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              border: 'none', borderRadius: '8px', color: 'white',
              padding: '6px 14px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
            }}>?ㅼ튂</button>
            <button onClick={() => setShowInstallBanner(false)} style={{
              background: 'transparent', border: 'none',
              color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', cursor: 'pointer',
            }}>?リ린</button>
          </div>
        </div>
      )}

      {/* 紐⑤컮???곷떒 ?ㅻ뜑 諛?*/}

      <div className="mobile-topbar">
        <button className="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="硫붾돱 ?닿린">
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

      {/* 紐⑤컮???ㅻ쾭?덉씠 */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* Sidebar */}
      <div className={`sidebar glass-panel ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <h1 onClick={handleHomeClick}><TrendingUp size={24} color="var(--accent-blue)" /> Alpha Research</h1>
        
        <div style={{ display:'flex', flexDirection:'column', gap:'6px', margin:'20px 0', borderBottom:'1px solid var(--border-color)', paddingBottom:'16px' }}>
          <div style={{ display:'flex', gap:'6px' }}>
            <button className={`tab-btn ${viewMode==='research'?'active':''}`}
              style={{ flex:1, padding:'8px', fontSize:'0.8rem', cursor:'pointer' }}
              onClick={() => { setViewMode('research'); setSidebarOpen(false); }}>
              <BookOpen size={13} style={{marginRight:'5px',verticalAlign:'middle'}} /> 由ъ꽌移??ы꽭
            </button>
            <button className={`tab-btn ${viewMode==='agent-workspace'?'active':''}`}
              style={{ flex:1, padding:'8px', fontSize:'0.8rem', cursor:'pointer' }}
              onClick={() => { setViewMode('agent-workspace'); setSelectedCompany(null); setSidebarOpen(false); }}>
              <Activity size={13} style={{marginRight:'5px',verticalAlign:'middle'}} /> AI 遺꾩꽍?
            </button>
          </div>
          <button className={`tab-btn ${viewMode==='pdf-library'?'active':''}`}
            style={{ width:'100%', padding:'8px', fontSize:'0.8rem', cursor:'pointer' }}
            onClick={() => { setViewMode('pdf-library'); setSelectedCompany(null); setSidebarOpen(false); }}>
            <FolderOpen size={13} style={{marginRight:'5px',verticalAlign:'middle'}} /> ?곗뾽?먮즺 PDF
          </button>
        </div>

        <div style={{ marginTop:'10px' }}>
          {reports.map((r, idx) => (
            <div key={r.id}
              className={`nav-item ${selectedReport?.id===r.id?'active':''}`}
              onClick={() => { fetchReportDetails(r.id); setSelectedCompany(null); setCompanyProfile(null); setSidebarOpen(false); }}>
              <span style={{ width:'20px', height:'20px', borderRadius:'50%', background:'rgba(59,130,246,0.15)', color:'var(--accent-blue)', fontSize:'0.65rem', fontWeight:700, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>{idx+1}</span>
              {r.tag || r.title}
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
          <HomeDashboard reports={reports} onSelect={(id) => { fetchReportDetails(id); setSelectedCompany(null); }} />
        )}
      </div>
    </div>
  );
}

// ?? PdfLibraryView ??????????????????????????????
function PdfLibraryView() {
  const [categories, setCategories] = useState([]);
  const [activePdf, setActivePdf] = useState(null); // { name, url }
  const [expanded, setExpanded] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_BASE}/pdfs`)
      .then(res => {
        setCategories(res.data);
        // 泥?踰덉㎏ 移댄뀒怨좊━ ?쇱튂湲?
        if (res.data.length > 0) {
          setExpanded({ [res.data[0].category]: true });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleCategory = (cat) => setExpanded(prev => ({ ...prev, [cat]: !prev[cat] }));

  if (loading) return <div className="page-header"><p>PDF 紐⑸줉 遺덈윭?ㅻ뒗 以?..</p></div>;

  return (
    <div style={{ display:'flex', height:'100%', gap:'0' }}>
      {/* 醫뚯륫 ?뚯씪 ?몃━ */}
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
          <h2 style={{ fontSize:'1.3rem', margin:0 }}>?곗뾽?먮즺 PDF</h2>
        </div>
        {categories.length === 0 && (
          <p style={{ color:'var(--text-secondary)' }}>PDF ?뚯씪???놁뒿?덈떎.</p>
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

      {/* ?곗륫 PDF 酉곗뼱 */}
      {activePdf && (
        <div style={{ flex:1, display:'flex', flexDirection:'column', minWidth:0 }}>
          {/* ?대컮 */}
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
                <ExternalLink size={13} /> ????뿉???닿린
              </a>
              <button
                onClick={() => setActivePdf(null)}
                style={{ padding:'6px 14px', borderRadius:'6px', background:'transparent', border:'1px solid var(--border-color)', color:'var(--text-secondary)', cursor:'pointer', fontSize:'0.85rem' }}
              >
                ???リ린
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

// ?? 二쇰룄二??깃툒 ?됱긽 ?쒖뒪????????????????????????????????
const GRADE_CONFIG = {
  S: { color: '#FFD700', bg: 'rgba(255,215,0,0.15)',  border: 'rgba(255,215,0,0.5)',  label: 'S?깃툒', emoji: '?몣', desc: '?곸썡???깆옣쨌?댁옄쨌?щТ 紐⑤몢 理쒖긽?? },
  A: { color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.4)', label: 'A?깃툒', emoji: '?룇', desc: '?깆옣?깃낵 ?댁옄媛 紐⑤몢 ?곗닔???듭떖 蹂댁쑀二? },
  B: { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.4)', label: 'B?깃툒', emoji: '狩?, desc: '?됯퇏 ?댁긽???꾨━?? 愿??醫낅ぉ ?곹빀' },
  C: { color: '#9ca3af', bg: 'rgba(156,163,175,0.10)',border: 'rgba(156,163,175,0.3)', label: 'C?깃툒', emoji: '?뵷', desc: '?됯퇏 ?섏?, ?뱁꽣 ??쒖＜濡?蹂댁쑀 媛?? },
  D: { color: '#ef4444', bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.3)',  label: 'D?깃툒', emoji: '?좑툘', desc: '?꾩쭅 ?섏씡?굿룹꽦?μ꽦 誘명씉, 二쇱쓽 ?꾩슂' },
};

// ?? 二쇰룄二??먯닔 湲곗? ?ㅻ챸 ?댄똻 ?????????????????????????????????
const SCORE_TOOLTIP = `二쇰룄二??ъ옄踰??먯닔 (100??留뚯젏)
?????????????????????????????
???깆옣 (40??: 留ㅼ텧쨌?댁씡 ?깆옣瑜? ?덉쭏 議곗젙
???댁옄 (30??: GPM쨌OPM 留덉쭊 ?곗쐞
???덉쟾 (20??: 遺梨꾨퉬?㉱룹쑀?숇퉬??
??由щ뜑 (10??: ?쒓?珥앹븸 洹쒕え 由щ뜑??
?????????????????????????????
S??5 / A??0 / B??5 / C??0 / D<40`;

// ?? 二쇰룄二??먯닔 諛?而댄룷?뚰듃 ????????????????????????????????
function LeadingScoreBar({ breakdown, score, grade }) {
  if (!breakdown || !score) return null;
  const cfg = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];
  const items = [
    { key: 'A_?깆옣(?덉쭏議곗젙)', label: '?깆옣', max: 40, color: '#10b981' },
    { key: 'B_留덉쭊?댁옄',       label: '?댁옄', max: 30, color: '#3b82f6' },
    { key: 'C_?щТ?덉쟾??,     label: '?덉쟾', max: 20, color: '#8b5cf6' },
    { key: 'D_洹쒕え由щ뜑??,     label: '由щ뜑', max: 10, color: '#f59e0b' },
  ];
  return (
    <div style={{ marginTop: '10px' }}>
      {/* 珥앹젏 + ?깃툒 */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'8px' }}>
        <span style={{ fontSize:'0.72rem', color:'var(--text-secondary)', cursor:'help' }} title={SCORE_TOOLTIP}>二쇰룄二??먯닔 ??/span>
        <div style={{ display:'flex', alignItems:'center', gap:'6px' }}>
          <div style={{
            fontSize:'0.7rem', fontWeight:800, padding:'2px 8px', borderRadius:'8px',
            background: cfg.bg, border:`1px solid ${cfg.border}`, color: cfg.color,
            letterSpacing:'0.5px', cursor:'help',
          }} title={cfg.desc}>{cfg.emoji} {grade}</div>
          <span style={{ fontSize:'0.85rem', fontWeight:700, color: cfg.color }}>{score}??/span>
        </div>
      </div>
      {/* ?멸렇癒쇳듃 諛?*/}
      <div style={{ display:'flex', gap:'2px', height:'6px', borderRadius:'4px', overflow:'hidden', background:'rgba(255,255,255,0.06)' }}>
        {items.map(item => {
          const val = Math.max(0, breakdown[item.key] || 0);
          const pct = (val / item.max) * (item.max / 100) * 100;
          return (
            <div key={item.key} title={`${item.label}: ${val.toFixed(1)}/${item.max}??}
              style={{ flex: item.max, background: pct > 0 ? item.color : 'transparent',
                       opacity: pct > 0 ? 0.85 : 0.2, transition:'all 0.3s' }} />
          );
        })}
      </div>
      {/* ?쇰꺼 */}
      <div style={{ display:'flex', gap:'2px', marginTop:'4px' }}>
        {items.map(item => (
          <div key={item.key} style={{ flex: item.max, textAlign:'center',
            fontSize:'0.6rem', color:'rgba(255,255,255,0.3)' }}>{item.label}</div>
        ))}
      </div>
    </div>
  );
}

// ?? IndustryView ????????????????????????????????
function IndustryView({ report, onSelectCompany }) {
  const [gradeFilter, setGradeFilter] = useState('?꾩껜');
  const [sortMode, setSortMode]       = useState('upside');

  // 蹂듯빀 ?먯닔: 湲곗뾽媛移??곸듅 湲곕?(upside_score) 60% + 二쇰룄二쇱젏??40%
  const compositeScore = (c) =>
    (c.upside_score ?? 0) * 0.6 + (c.leading_score ?? 0) * 0.4;

  const companies = [...report.companies].sort((a, b) => {
    if (sortMode === 'upside') return compositeScore(b) - compositeScore(a);
    if (sortMode === 'grade') {
      const ord = { S:0, A:1, B:2, C:3, D:4 };
      return (ord[a.leading_grade] ?? 5) - (ord[b.leading_grade] ?? 5);
    }
    return (a.display_order ?? 999) - (b.display_order ?? 999);
  });

  const filtered = gradeFilter === '?꾩껜'
    ? companies
    : companies.filter(c => c.leading_grade === gradeFilter);

  const gradeCounts = companies.reduce((acc, c) => {
    const g = c.leading_grade || 'D';
    acc[g] = (acc[g] || 0) + 1;
    return acc;
  }, {});

  const SORT_OPTS = [
    { key:'upside',  icon:'?뱢', label:'湲곗뾽媛移??곸듅', tip:'留ㅼ텧?깆옣+?곸뾽?댁씡瑜?ROE+?PER+FCF?깆옣 蹂듯빀?먯닔 ?? },
    { key:'grade',   icon:'?룇', label:'二쇰룄二??깃툒',   tip:'S?묨?묪?묬?묭 ?쒖꽌' },
    { key:'default', icon:'?뱥', label:'湲곕낯',           tip:'?낆쥌蹂?湲곕낯 ?쒖꽌' },
  ];

  return (
    <div className="industry-view">
      {/* ?섏씠吏 ?ㅻ뜑 */}
      <div className="page-header" style={{ borderBottom:'1px solid var(--border-color)', paddingBottom:'20px', marginBottom:'28px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'12px', marginBottom:'12px' }}>
          <span style={{ background:'linear-gradient(135deg,var(--accent-blue),var(--accent-purple))', color:'white', padding:'4px 14px', borderRadius:'20px', fontSize:'0.82rem', fontWeight:700, letterSpacing:'0.03em' }}>
            #{report.tag}
          </span>
          <span style={{ color:'var(--text-secondary)', fontSize:'0.85rem' }}>Industry Research</span>
        </div>
        <h2 style={{ fontSize:'2rem', lineHeight:1.2 }}>{report.tag} ?곗뾽</h2>
        <p style={{ color:'var(--text-secondary)', fontSize:'0.9rem', marginTop:'6px' }}>{report.title}</p>
      </div>

      {/* 由ы룷???붿빟 */}
      <div className="report-content glass-panel" style={{ padding:'32px 40px', marginBottom:'36px' }}>
        <h3 style={{ display:'flex', alignItems:'center', gap:'10px', color:'var(--accent-blue)', marginBottom:'20px', fontSize:'1.3rem' }}>
          <BookOpen size={22} /> Industry Overview
        </h3>
        <div className="markdown-body" style={{ color:'var(--text-primary)' }}>
          <ReactMarkdown>{report.summary}</ReactMarkdown>
        </div>
      </div>

      {/* 湲곗뾽 紐⑸줉 而⑦듃濡?*/}
      <div style={{ marginBottom:'16px' }}>
        {/* ??댄? + ?뺣젹 踰꾪듉 */}
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'10px', marginBottom:'12px' }}>
          <div>
            <h3 style={{ color:'var(--accent-blue)', fontSize:'1.2rem', margin:'0 0 4px' }}>
              ?룇 ?듭떖 異붿쟻 湲곗뾽
            </h3>
            <div style={{ fontSize:'0.73rem', color:'var(--text-secondary)' }}>
              {SORT_OPTS.find(o => o.key === sortMode)?.icon}{' '}
              {SORT_OPTS.find(o => o.key === sortMode)?.label} ???뺣젹
            </div>
          </div>
          <div style={{ display:'flex', gap:'5px', flexWrap:'wrap' }}>
            {SORT_OPTS.map(o => (
              <button key={o.key} onClick={() => setSortMode(o.key)} title={o.tip}
                style={{
                  padding:'6px 12px', borderRadius:'20px', cursor:'pointer', border:'none',
                  fontSize:'0.73rem', fontWeight:700, transition:'all 0.2s',
                  background: sortMode === o.key
                    ? 'linear-gradient(135deg,var(--accent-blue),var(--accent-purple))'
                    : 'rgba(255,255,255,0.06)',
                  color: sortMode === o.key ? '#fff' : 'var(--text-secondary)',
                  boxShadow: sortMode === o.key ? '0 2px 10px rgba(59,130,246,0.35)' : 'none',
                }}
              >{o.icon} {o.label}</button>
            ))}
          </div>
        </div>

        {/* ?깃툒 ?꾪꽣 ??*/}
        <div style={{ display:'flex', gap:'6px', flexWrap:'wrap' }}>
          {['?꾩껜', 'S', 'A', 'B', 'C', 'D'].map(g => {
            const cfg    = g === '?꾩껜' ? null : GRADE_CONFIG[g];
            const cnt    = g === '?꾩껜' ? companies.length : (gradeCounts[g] || 0);
            const active = gradeFilter === g;
            return (
              <button key={g} onClick={() => setGradeFilter(g)}
                style={{
                  padding:'5px 12px', borderRadius:'20px', cursor:'pointer',
                  fontSize:'0.77rem', fontWeight:600, transition:'all 0.2s',
                  background: active ? (cfg ? cfg.bg : 'rgba(59,130,246,0.18)') : 'rgba(255,255,255,0.04)',
                  color:      active ? (cfg ? cfg.color : 'var(--accent-blue)') : 'var(--text-secondary)',
                  border:     active ? `1px solid ${cfg ? cfg.border : 'rgba(59,130,246,0.5)'}` : '1px solid transparent',
                  boxShadow:  active && cfg ? `0 0 8px ${cfg.color}25` : 'none',
                }}
              >
                {cfg ? `${cfg.emoji} ${g}` : '?꾩껜'}{' '}
                <span style={{ opacity:0.5, fontSize:'0.68rem' }}>({cnt})</span>
              </button>
            );
          })}
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign:'center', padding:'32px', color:'var(--text-secondary)' }}>
            {gradeFilter}?깃툒 湲곗뾽???놁뒿?덈떎.
          </div>
        )}
      </div>

      {/* 湲곗뾽 移대뱶 紐⑸줉 */}
      <div className="company-list">
        {filtered.map((comp, idx) => {
          const rank   = idx + 1;
          const grade  = comp.leading_grade;
          const cfg    = grade ? (GRADE_CONFIG[grade] || GRADE_CONFIG['C']) : null;
          const upside = comp.upside_score;

          const cardBorder = cfg ? `1px solid ${cfg.border}` : '1px solid rgba(255,255,255,0.06)';
          const cardGlow   = grade === 'S' ? `0 0 20px ${cfg.color}1a`
                           : grade === 'A' ? `0 0 12px ${cfg.color}12` : 'none';
          const rankEmoji  = rank === 1 ? '?쪍' : rank === 2 ? '?쪎' : rank === 3 ? '?쪏' : '';
          const upsideColor = !upside      ? '#6b7280'
                            : upside >= 70 ? '#10b981'
                            : upside >= 50 ? '#3b82f6'
                            : upside >= 30 ? '#f59e0b'
                            :                '#9ca3af';

          return (
            <div key={comp.id}
              className="company-pill glass-panel"
              onClick={() => onSelectCompany(comp.id)}
              style={{ position:'relative', border: cardBorder, boxShadow: cardGlow, transition:'all 0.25s' }}
            >
              {/* 諛곗? */}
              <div style={{ position:'absolute', top:'10px', right:'10px', display:'flex', alignItems:'center', gap:'5px' }}>
                {cfg && (
                  <div title={cfg.desc} style={{
                    background: cfg.bg, border:`1px solid ${cfg.border}`,
                    borderRadius:'10px', padding:'2px 8px',
                    fontSize:'0.68rem', fontWeight:800, color: cfg.color,
                    boxShadow: grade === 'S' ? `0 0 8px ${cfg.color}50` : 'none',
                  }}>{cfg.emoji} {grade}</div>
                )}
                <div style={{
                  background:'rgba(255,255,255,0.05)', border:'1px solid rgba(255,255,255,0.1)',
                  borderRadius:'10px', padding:'2px 7px',
                  fontSize:'0.66rem', fontWeight:600, color:'var(--text-secondary)',
                }}>{rankEmoji} {rank}??/div>
              </div>

              {/* 湲곗뾽紐?*/}
              <div className="company-header" style={{ paddingRight:'100px' }}>
                <span className="company-name">{comp.name}</span>
                <span className="company-ticker">{comp.ticker}</span>
              </div>

              {/* ?ㅻ챸 */}
              <div style={{
                fontSize:'0.86rem', color:'var(--text-secondary)', lineHeight:1.55,
                display:'-webkit-box', WebkitLineClamp:2,
                WebkitBoxOrient:'vertical', overflow:'hidden', marginBottom:'10px',
              }}>{comp.role_description}</div>

              {/* 湲곗뾽媛移??곸듅 湲곕? 諛?*/}
              {upside != null && (
                <div style={{ marginBottom:'8px' }}>
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'4px' }}>
                    <span style={{ fontSize:'0.66rem', color:'var(--text-secondary)', cursor:'help' }}
                      title="留ㅼ텧?깆옣(40)+?곸뾽?댁씡瑜?20)+ROE(15)+?PER?щ?(15)+FCF?깆옣(10) ?⑹궛 100??>
                      ?뱢 湲곗뾽媛移??곸듅 湲곕? ??
                    </span>
                    <span style={{ fontSize:'0.8rem', fontWeight:700, color: upsideColor }}>{upside}??/span>
                  </div>
                  <div style={{ height:'4px', borderRadius:'4px', background:'rgba(255,255,255,0.06)', overflow:'hidden' }}>
                    <div style={{
                      width:`${upside}%`, height:'100%', borderRadius:'4px',
                      background:`linear-gradient(90deg,${upsideColor},${upsideColor}bb)`,
                      transition:'width 0.8s ease',
                    }} />
                  </div>
                </div>
              )}

              {/* 二쇰룄二??먯닔 諛?*/}
              <LeadingScoreBar
                breakdown={comp.leading_breakdown}
                score={comp.leading_score}
                grade={comp.leading_grade}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}


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

// ?? SectionHeader ?????????????????????????????????????????
function SectionHeader({ icon: Icon, title, color: clr }) {
  return (
    <h3 style={{ display:'flex', alignItems:'center', gap:'10px', color: clr || 'var(--accent-blue)', marginBottom:'20px', fontSize:'1.2rem', borderBottom:'1px solid var(--border-color)', paddingBottom:'10px' }}>
      {Icon && <Icon size={20} />} {title}
    </h3>
  );
}

// ?? AiAnalysisSection ?????????????????????????????????????
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
        <span style={{ fontWeight:700, fontSize:'1rem', color:'var(--accent-purple)' }}>AI ?ъ링 鍮꾩쫰?덉뒪 遺꾩꽍 ??濡쒕뵫 以?..</span>
      </div>
      {[1,2,3,4].map(i => (
        <div key={i} style={{ height:'80px', background:'rgba(255,255,255,0.04)', borderRadius:'8px', marginBottom:'12px', animation:'pulse 1.5s infinite' }} />
      ))}
    </div>
  );
  if (data.error && !data.what_they_sell) return (
    <div className="glass-panel" style={{ padding:'20px', color:'#ff6b6b' }}>AI 遺꾩꽍 寃곌낵瑜?遺덈윭?????놁뒿?덈떎.</div>
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
      {/* ?ㅻ뜑 */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'18px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
          <Activity size={20} color="var(--accent-purple)" />
          <h3 style={{ fontSize:'1.2rem', fontWeight:700, color:'var(--accent-purple)', margin:0 }}>AI ?ъ링 鍮꾩쫰?덉뒪 遺꾩꽍 由ы룷??/h3>
        </div>
        <span style={{ fontSize:'0.75rem', padding:'3px 10px', borderRadius:'12px', background:'rgba(129,140,248,0.15)', color: badge.color, border:`1px solid ${badge.color}40` }}>
          {badge.label}
        </span>
      </div>

      {/* 移대뱶 洹몃━??*/}
      <div className="ai-grid">

        {/* 1. ?듭떖 ?쒗뭹/?쒕퉬??*/}
        {d.what_they_sell && (
          <AiAnalysisCard icon={Package} title="?듭떖 ?쒗뭹 & ?쒕퉬?? color="var(--accent-blue)" span2={false}>
            {d.what_they_sell}
          </AiAnalysisCard>
        )}

        {/* 2. ?섏씡 紐⑤뜽 */}
        {d.revenue_model && (
          <AiAnalysisCard icon={DollarSign} title="?섏씡 紐⑤뜽 ???대뼸寃??덉쓣 踰꾨뒗媛" color="var(--accent-green)" span2={false}>
            {d.revenue_model}
          </AiAnalysisCard>
        )}

        {/* 3. 鍮꾩슜 援ъ“ */}
        {d.cost_structure && (
          <AiAnalysisCard icon={BarChart3} title="鍮꾩슜 援ъ“ ???대뵒???덉쓣 ?곕뒗媛" color="#f59e0b" span2={false}>
            {d.cost_structure}
          </AiAnalysisCard>
        )}

        {/* 4. ?댁씡 援ъ“ */}
        {d.how_they_profit && (
          <AiAnalysisCard icon={TrendingUp} title="?댁씡 援ъ“ ???대뼸寃??덉쓣 ?④린?붽?" color="#06b6d4" span2={false}>
            {d.how_they_profit}
          </AiAnalysisCard>
        )}

        {/* 5. 寃쎌젣???댁옄 */}
        {d.competitive_moat && (
          <AiAnalysisCard icon={Shield} title="寃쎌젣???댁옄 (Competitive Moat)" color="var(--accent-purple)" span2={true}>
            {d.competitive_moat}
          </AiAnalysisCard>
        )}

        {/* 6. ?ъ뾽 ?멸렇癒쇳듃 */}
        {d.key_segments && d.key_segments.length > 0 && (
          <AiAnalysisCard icon={Layers} title="?듭떖 ?ъ뾽 ?멸렇癒쇳듃" color="#84cc16" span2={true}>
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

        {/* 7. 由ъ뒪??*/}
        {d.risk_factors && (
          <AiAnalysisCard icon={AlertTriangle} title="?듭떖 由ъ뒪???ъ씤?? color="#ef4444" span2={false}>
            {d.risk_factors}
          </AiAnalysisCard>
        )}

        {/* 8. ?ъ옄 ?ъ씤??*/}
        {d.investment_thesis && (
          <AiAnalysisCard icon={Star} title="?ъ옄 ?ъ씤??(Investment Thesis)" color="#f97316" span2={false}>
            {d.investment_thesis}
          </AiAnalysisCard>
        )}

        {/* 9. ?곗뾽 ?ъ옄 ?ъ씤??*/}
        {d.industry_connection && (
          <AiAnalysisCard icon={Globe} title="?곗뾽 ???ъ옄 ?ъ씤?????????곗뾽?먯꽌 ??湲곗뾽?멸?" color="var(--accent-blue)" span2={true}>
            {d.industry_connection}
          </AiAnalysisCard>
        )}
      </div>
    </div>
  );
}


// ?? CompanyView (湲곌?湲?? ??쒕낫?? ??????????????????
function CompanyView({ company, profile, financials, aiAnalysis, onBack, onSync }) {
  const [tab, setTab] = useState('annual');
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      // 鍮좊Ⅸ 二쇨? 理쒖떊??癒쇱? (yfinance濡?利됱떆)
      await axios.get(`${API_BASE}/companies/${company.id}/price`);
      await onSync();
    } catch (e) { console.error(e); }
    setSyncing(false);
  };

  // ?곌컙 vs 遺꾧린 ?꾪꽣
  // ?좎쭨 ?대┝李⑥닚 ?뺣젹 ???곕룄蹂?以묐났 ?쒓굅 (理쒖떊 ?덉퐫???곗꽑)
  const annualRaw = (financials || [])
    .filter(f => f.period_type === 'annual')
    .sort((a,b) => new Date(b.date)-new Date(a.date)); // 理쒖떊??
  const annualMap = new Map();
  annualRaw.forEach(d => {
    const yr = d.date.substring(0,4);
    if (!annualMap.has(yr)) annualMap.set(yr, d); // 理쒖떊 ?덉퐫?쒕쭔 ?좎?
  });
  // 李⑦듃?⑹? ?ㅻ쫫李⑥닚 (?쏅궇?믪턀??
  const annualData = Array.from(annualMap.values()).sort((a,b) => new Date(a.date)-new Date(b.date));
  // 鍮꾩쫰?덉뒪 紐⑤뜽??latest??媛??理쒖떊 ?곌컙 ?덉퐫??
  const latestRaw = annualRaw[0] || {};

  const quarterlyData = (financials || [])
    .filter(f => f.period_type === 'quarterly')
    .sort((a,b) => new Date(b.date)-new Date(a.date));

  const tableData = tab === 'annual' ? [...annualData].reverse() : quarterlyData;

  // KRW ?щ? 諛?李⑦듃 ?⑥쐞
  const isKrwTicker = isKrw(company?.ticker);
  const chartUnit = isKrwTicker ? '?듭썝' : 'B USD';

  // 李⑦듃 ?곗씠??(理쒓렐 6??
  const incomeChartData = annualData.slice(-6).map(d => {
    const scale = isKrwTicker ? 1e8 : 1e9;
    return {
      year: d.date.substring(0,4),
      留ㅼ텧: +(d.revenue / scale).toFixed(2),
      ?곸뾽?댁씡: +((d.operating_income||0) / scale).toFixed(2),
      ?쒖씠?? +((d.net_income||0) / scale).toFixed(2),
      'OPM%': +(d.op_margin||0).toFixed(1),
      'GPM%': +(d.gross_margin||0).toFixed(1),
    };
  });

  const cashFlowData = annualData.slice(-6).map(d => {
    const scale = isKrwTicker ? 1e8 : 1e9;
    return {
      year: d.date.substring(0,4),
      OCF: +((d.operating_cash_flow||0) / scale).toFixed(2),
      CAPEX: +((d.capital_expenditure||0) / scale).toFixed(2),
      FCF: +((d.free_cash_flow||0) / scale).toFixed(2),
    };
  });

  const balanceData = annualData.slice(-6).map(d => {
    const scale = isKrwTicker ? 1e8 : 1e9;
    return {
      year: d.date.substring(0,4),
      ?먯궛: +((d.total_assets||0) / scale).toFixed(2),
      遺梨? +((d.total_debt||0) / scale).toFixed(2),
      ?먮낯: +((d.shareholders_equity||0) / scale).toFixed(2),
      ?꾧툑: +((d.cash_and_equivalents||0) / scale).toFixed(2),
    };
  });

  const p = profile || {};
  // 理쒖떊 ?곌컙 ?덉퐫???ъ슜 (COGS ??理쒖떊媛?蹂댁옣)
  const latest = (() => {
    const r = latestRaw;
    // cost_of_revenue媛 ?놁쑝硫?revenue - gross_profit?쇰줈 怨꾩궛 ??諛섑솚
    if (r && r.revenue && r.gross_profit && !r.cost_of_revenue) {
      return { ...r, cost_of_revenue: r.revenue - r.gross_profit };
    }
    return r || {};
  })();

  return (
    <div className="company-details">
      {/* ?? ?ㅻ뜑 ??????????????????????????????????????? */}
      <button className="back-btn" onClick={onBack}>
        <ArrowLeft size={16} /> ?뚯븘媛湲?
      </button>

      <div className="company-header-row">
        <div>
          <h2 className="company-title">
            {company.name}
            <span style={{ fontSize:'1rem', color:'var(--accent-blue)', marginLeft:'10px', fontWeight:600 }}>{company.ticker}</span>
          </h2>
          {p.sector && (
            <div style={{ color:'var(--text-secondary)', fontSize:'0.85rem', marginBottom:'6px' }}>
              {p.sector} ??{p.industry}
            </div>
          )}
          {p.current_price && (
            <div className="price-display">
              <span className="price-value" style={{ color:'var(--accent-green)' }}>{fDollar(p.current_price, company?.ticker)}</span>
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
            <span>{syncing ? '?섏쭛 以?..' : '二쇨? 理쒖떊??}</span>
          </button>
        </div>
      </div>

      {/* ?? Section 0: AI 湲곗뾽 ?ъ링 遺꾩꽍 ???????????????? */}
      <AiAnalysisSection data={aiAnalysis} company={company} />

      {/* ?? Section 0b: 鍮꾩쫰?덉뒪 紐⑤뜽 ?섏씡援ъ“ ???????? */}
      <BusinessModelSection latest={latest} profile={p} company={company} />

      {/* ?? Section 1: 諛몃쪟?먯씠??KPI 移대뱶 ??????????????? */}
      <section style={{ marginBottom:'36px' }}>
        <SectionHeader icon={BarChart2} title="諛몃쪟?먯씠??(TTM 湲곗?)" />
        <div className="kpi-grid">
          <KpiCard label="P/E Ratio (PER)" value={fN(p.pe_ratio)} sub="二쇨??섏씡鍮꾩쑉" icon={TrendingUp}
            valueColor={p.pe_ratio < 20 ? 'var(--accent-green)' : p.pe_ratio > 50 ? '#ff6b6b' : 'var(--text-primary)'} />
          <KpiCard label="P/B Ratio (PBR)" value={fN(p.pb_ratio)} sub="二쇨??쒖옄?곕퉬?? />
          <KpiCard label="EV/EBITDA" value={fX(p.ev_ebitda)} sub="湲곗뾽媛移?諛곗닔"
            valueColor={p.ev_ebitda < 15 ? 'var(--accent-green)' : p.ev_ebitda > 40 ? '#ff6b6b' : 'var(--text-primary)'} />
          <KpiCard label="EV/Sales" value={fX(p.ev_sales)} sub="留ㅼ텧 諛곗닔" />
          <KpiCard label="?쒓?珥앹븸" value={fB(p.market_cap, company?.ticker)} sub="Market Cap" icon={DollarSign} />
          <KpiCard label="?좊꼸由ъ뒪??紐⑺몴媛" value={fDollar(p.analyst_target, company?.ticker)} sub="Consensus Target"
            valueColor={p.analyst_target > p.current_price ? 'var(--accent-green)' : '#ff6b6b'} />
        </div>
      </section>

      {/* ?? Section 2: ?섏씡??吏??????????????????????????? */}
      <section style={{ marginBottom:'36px' }}>
        <SectionHeader icon={Zap} title="?섏씡??吏??(Profitability TTM)" color="var(--accent-purple)" />
        <div className="kpi-grid">
          <KpiCard label="GPM (留ㅼ텧珥앹씠?듬쪧)" value={fP(p.gross_margin_ttm)} sub="Gross Profit Margin"
            valueColor={color(p.gross_margin_ttm*100, 50, 20)} />
          <KpiCard label="OPM (?곸뾽?댁씡瑜?" value={fP(p.op_margin_ttm)} sub="Operating Margin"
            valueColor={color(p.op_margin_ttm*100, 20, 5)} />
          <KpiCard label="EBITDA Margin" value={fP(p.ebitda_margin_ttm)} sub="EBITDA / Revenue"
            valueColor={color(p.ebitda_margin_ttm*100, 25, 10)} />
          <KpiCard label="?쒖씠?듬쪧" value={fP(p.net_margin_ttm)} sub="Net Profit Margin"
            valueColor={color(p.net_margin_ttm*100, 15, 0)} />
          <KpiCard label="ROE" value={fP(p.roe)} sub="?먭린?먮낯?댁씡瑜?
            valueColor={color(p.roe*100, 15, 5)} />
          <KpiCard label="ROA" value={fP(p.roa)} sub="珥앹옄?곗씠?듬쪧"
            valueColor={color(p.roa*100, 8, 2)} />
        </div>
      </section>

      {/* ?? Section 3: ?깆옣??+ ?щТ嫄댁쟾?????????????????? */}
      <section style={{ marginBottom:'36px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'24px' }}>
          <div>
            <SectionHeader icon={TrendingUp} title="?깆옣??(Growth)" color="var(--accent-green)" />
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px' }}>
              <KpiCard label="留ㅼ텧 ?깆옣瑜?(YoY)" value={p.revenue_growth != null ? fP(p.revenue_growth) : '-'} sub="Revenue Growth"
                valueColor={p.revenue_growth > 0.1 ? 'var(--accent-green)' : p.revenue_growth < 0 ? '#ff6b6b' : 'var(--text-primary)'} />
              <KpiCard label="EPS (TTM)" value={p.eps_growth != null ? fDollar(p.eps_growth, company?.ticker) : '-'} sub="Earnings Per Share" />
            </div>
          </div>
          <div>
            <SectionHeader icon={Shield} title="?щТ嫄댁쟾??(Financial Health)" color="#f1c40f" />
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px' }}>
              <KpiCard label="?좊룞鍮꾩쑉" value={fN(p.current_ratio)} sub="Current Ratio"
                valueColor={color(p.current_ratio, 2, 1)} />
              <KpiCard label="遺梨꾨퉬?? value={fN(p.debt_to_equity)} sub="D/E Ratio"
                valueColor={p.debt_to_equity < 50 ? 'var(--accent-green)' : p.debt_to_equity > 200 ? '#ff6b6b' : 'var(--text-primary)'} />
              <KpiCard label="諛곕떦?섏씡瑜? value={p.dividend_yield != null ? fP(p.dividend_yield) : '-'} sub="Dividend Yield"
                valueColor='var(--accent-green)' />
              <KpiCard label="諛곕떦?깊뼢" value={p.payout_ratio != null ? fP(p.payout_ratio) : '-'} sub="Payout Ratio" />
            </div>
          </div>
        </div>
      </section>

      {/* ?? Section 4: ?먯씡 李⑦듃 ??????????????????????????? */}
      <section style={{ marginBottom:'36px' }}>
        <SectionHeader icon={BarChart2} title={`?먯씡 異붿씠 (?⑥쐞: ${chartUnit})`} />
        <div className="chart-grid-2">
          <div className="glass-panel" style={{ padding:'24px', height:'300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={incomeChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                <XAxis dataKey="year" stroke="var(--text-secondary)" fontSize={12} />
                <YAxis yAxisId="left" stroke="var(--text-secondary)" fontSize={12} tickFormatter={v => isKrwTicker ? v.toLocaleString() : v} />
                <YAxis yAxisId="right" orientation="right" stroke="#00f2fe" fontSize={12} unit="%" />
                <RechartsTooltip contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', color:'var(--text-primary)', fontSize:'0.85rem' }} formatter={(v, name) => [isKrwTicker ? `??{v.toLocaleString()}?? : `$${v}B`, name]} />
                <Legend />
                <Bar yAxisId="left" dataKey="留ㅼ텧" fill="var(--accent-blue)" radius={[4,4,0,0]} />
                <Bar yAxisId="left" dataKey="?곸뾽?댁씡" fill="var(--accent-purple)" radius={[4,4,0,0]} />
                <Bar yAxisId="left" dataKey="?쒖씠?? fill="var(--accent-green)" radius={[4,4,0,0]} />
                <Line yAxisId="right" type="monotone" dataKey="OPM%" stroke="#00f2fe" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="glass-panel" style={{ padding:'24px', height:'300px' }}>
            <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'12px' }}>?곸뾽?댁씡瑜?/ 留ㅼ텧珥앹씠?듬쪧 異붿씠</div>
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

      {/* ?? Section 5: ?꾧툑?먮쫫 + ?щТ?곹깭??李⑦듃 ????????? */}
      <section style={{ marginBottom:'36px' }}>
        <div className="chart-grid-equal">
          <div>
            <SectionHeader icon={DollarSign} title={`?꾧툑?먮쫫 (${chartUnit})`} color="var(--accent-green)" />
            <div className="glass-panel" style={{ padding:'24px', height:'260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cashFlowData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                  <XAxis dataKey="year" stroke="var(--text-secondary)" fontSize={11} />
                  <YAxis stroke="var(--text-secondary)" fontSize={11} tickFormatter={v => isKrwTicker ? v.toLocaleString() : v} />
                  <RechartsTooltip contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', color:'var(--text-primary)', fontSize:'0.8rem' }} formatter={(v) => [isKrwTicker ? `??{v.toLocaleString()}?? : `$${v}B`]} />
                  <Legend />
                  <Bar dataKey="OCF" fill="var(--accent-blue)" radius={[3,3,0,0]} />
                  <Bar dataKey="FCF" fill="var(--accent-green)" radius={[3,3,0,0]} />
                  <Bar dataKey="CAPEX" fill="#ff6b6b" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <SectionHeader icon={Database} title={`?щТ?곹깭??(${chartUnit})`} color="#f1c40f" />
            <div className="glass-panel" style={{ padding:'24px', height:'260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={balanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                  <XAxis dataKey="year" stroke="var(--text-secondary)" fontSize={11} />
                  <YAxis stroke="var(--text-secondary)" fontSize={11} tickFormatter={v => isKrwTicker ? v.toLocaleString() : v} />
                  <RechartsTooltip contentStyle={{ backgroundColor:'var(--bg-card)', borderColor:'var(--border-color)', color:'var(--text-primary)', fontSize:'0.8rem' }} formatter={(v) => [isKrwTicker ? `??{v.toLocaleString()}?? : `$${v}B`]} />
                  <Legend />
                  <Bar dataKey="?먯궛" fill="rgba(0,191,255,0.6)" radius={[3,3,0,0]} />
                  <Bar dataKey="?먮낯" fill="rgba(0,255,100,0.6)" radius={[3,3,0,0]} />
                  <Bar dataKey="遺梨? fill="rgba(255,107,107,0.6)" radius={[3,3,0,0]} />
                  <Line type="monotone" dataKey="?꾧툑" stroke="#ffd700" strokeWidth={2.5} dot={{ r:4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* ?? Section 6: ? ?щТ?쒗몴 ?뚯씠釉?????????????????? */}
      <section style={{ marginBottom:'40px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px' }}>
          <SectionHeader icon={FileText} title="?щТ?쒗몴 ?곗씠??(Full Financials)" />
          <div className="tabs">
            <button className={`tab-btn ${tab==='annual'?'active':''}`} onClick={() => setTab('annual')}>?곌컙</button>
            <button className={`tab-btn ${tab==='quarterly'?'active':''}`} onClick={() => setTab('quarterly')}>遺꾧린</button>
          </div>
        </div>

        <div className="data-table-container" style={{ overflowX:'auto' }}>
          <table className="data-table" style={{ minWidth:'1100px' }}>
            <thead>
              <tr>
                <th>湲곌컙</th>
                <th>留ㅼ텧</th>
                <th>留ㅼ텧?먭?</th>
                <th>留ㅼ텧珥앹씠??/th>
                <th>?곸뾽?댁씡</th>
                <th>EBITDA</th>
                <th>?쒖씠??/th>
                <th>EPS</th>
                <th>GPM</th>
                <th>OPM</th>
                <th>OCF</th>
                <th>FCF</th>
                <th>珥앹옄??/th>
                <th>?쒕?梨?/th>
                <th>ROE</th>
              </tr>
            </thead>
            <tbody>
              {tableData.map((d, i) => (
                <tr key={i}>
                  <td style={{ fontWeight:600 }}>{d.date}</td>
                  <td>{fB(d.revenue, company?.ticker)}</td>
                  <td style={{ color:'#ff6b6b' }}>{fB(d.cost_of_revenue != null ? d.cost_of_revenue : (d.revenue && d.gross_profit ? d.revenue - d.gross_profit : null), company?.ticker)}</td>
                  <td>{fB(d.gross_profit, company?.ticker)}</td>
                  <td>{fB(d.operating_income, company?.ticker)}</td>
                  <td>{fB(d.ebitda, company?.ticker)}</td>
                  <td style={{ color: d.net_income >= 0 ? 'var(--accent-green)' : '#ff6b6b' }}>{fB(d.net_income, company?.ticker)}</td>
                  <td>{d.eps != null ? fDollar(d.eps, company?.ticker) : '-'}</td>
                  <td style={{ color:'var(--accent-green)' }}>{fP2(d.gross_margin)}</td>
                  <td style={{ color:'var(--accent-blue)' }}>{fP2(d.op_margin)}</td>
                  <td>{fB(d.operating_cash_flow, company?.ticker)}</td>
                  <td style={{ color: d.free_cash_flow >= 0 ? 'var(--accent-green)' : '#ff6b6b' }}>{fB(d.free_cash_flow, company?.ticker)}</td>
                  <td>{fB(d.total_assets, company?.ticker)}</td>
                  <td style={{ color: d.net_debt > 0 ? '#ff6b6b' : 'var(--accent-green)' }}>{fB(d.net_debt, company?.ticker)}</td>
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

      {/* ?? Section 7: ?뚯궗 媛쒖슂 ??????????????????????????? */}
      {(p.description || company.role_description) && (
        <section style={{ marginBottom:'40px' }}>
          <SectionHeader icon={BookOpen} title="?뚯궗 媛쒖슂 (Business Overview)" />
          <div className="glass-panel" style={{ padding:'28px' }}>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:'16px', marginBottom:'20px' }}>
              {p.employees && (
                <div style={{ display:'flex', alignItems:'center', gap:'8px', color:'var(--text-secondary)', fontSize:'0.9rem' }}>
                  <Users size={16} /> ?꾩쭅?? {fK(p.employees)}紐?
                </div>
              )}
              {p.ceo && (
                <div style={{ display:'flex', alignItems:'center', gap:'8px', color:'var(--text-secondary)', fontSize:'0.9rem' }}>
                  <Target size={16} /> CEO: {p.ceo}
                </div>
              )}
              {p.last_updated && (
                <div style={{ display:'flex', alignItems:'center', gap:'8px', color:'var(--text-secondary)', fontSize:'0.9rem' }}>
                  <RefreshCw size={14} /> 媛깆떊: {p.last_updated}
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
                  ?뱢 ?ъ옄 ?ъ씤??/ Future Growth
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

// ?? BusinessModelSection ?????????????????????????????
function BusinessModelSection({ latest, profile, company }) {
  const rev = latest.revenue || 0;
  const gp = latest.gross_profit || 0;
  // 留ㅼ텧?먭? = DB媛??곗꽑, ?놁쑝硫?留ㅼ텧 - 留ㅼ텧珥앹씠?듭쑝濡?怨꾩궛
  const cogs = latest.cost_of_revenue || (rev > 0 && gp > 0 ? rev - gp : 0);
  const opInc = latest.operating_income || 0;
  const netInc = latest.net_income || 0;
  const opEx = Math.max(gp - opInc, 0);
  const taxOther = Math.max(opInc - netInc, 0);
  const p = profile || {};

  // Waterfall ?곗씠????KRW???듭썝 ?⑥쐞, USD????뼲?щ윭 ?⑥쐞
  const wfDiv = (company?.ticker?.endsWith('.KS') || company?.ticker?.endsWith('.KQ')) ? 1e8 : 1e9;
  const wfData = [
    { name: '留ㅼ텧??, value: rev/wfDiv, start: 0, fill: '#3b82f6', label: fB(rev, company?.ticker) },
    { name: '留ㅼ텧?먭?', value: -cogs/wfDiv, start: (rev-cogs)/wfDiv, fill: '#ff6b6b', label: fB(cogs, company?.ticker) },
    { name: '留ㅼ텧珥앹씠??, value: gp/wfDiv, start: 0, fill: '#10b981', label: fB(gp, company?.ticker), isSum: true },
    { name: '?먭?쨌R&D', value: -opEx/wfDiv, start: opInc/wfDiv, fill: '#f97316', label: fB(opEx, company?.ticker) },
    { name: '?곸뾽?댁씡', value: opInc/wfDiv, start: 0, fill: '#8b5cf6', label: fB(opInc, company?.ticker), isSum: true },
    { name: '?멸툑쨌湲고?', value: -taxOther/wfDiv, start: netInc/wfDiv, fill: '#ef4444', label: fB(taxOther, company?.ticker) },
    { name: '?쒖씠??, value: netInc/wfDiv, start: 0, fill: '#00f2fe', label: fB(netInc, company?.ticker), isSum: true },
  ];

  // 鍮꾩슜 援ъ“ ?뚯씠 李⑦듃
  const costPieData = [
    { name: '留ㅼ텧?먭? (COGS)', value: cogs, color: '#ff6b6b' },
    { name: '?먭?쨌R&D 鍮꾩슜', value: opEx, color: '#f97316' },
    { name: '?멸툑쨌?댁옄쨌湲고?', value: taxOther, color: '#ef4444' },
    { name: '?쒖씠??, value: Math.max(netInc, 0), color: '#00f2fe' },
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
        <DollarSign size={20} /> 鍮꾩쫰?덉뒪 紐⑤뜽 & ?섏씡 援ъ“ (理쒓렐 ?곌컙 湲곗?)
      </h3>

      {/* ?? ?섏씡 ?먮쫫 SVG ?뚮줈???ㅼ씠?닿렇???? */}
      <div className="glass-panel" style={{ padding:'28px', marginBottom:'24px' }}>
        <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'20px', fontWeight:600 }}>
          ?뮥 ?덉쓽 ?먮쫫 ??{company.name}? ?대뼸寃??섏씡??留뚮뱶?붽?
        </div>

        {/* Flow Diagram */}
        <div style={{ display:'flex', alignItems:'stretch', gap:'0', overflowX:'auto', padding:'4px 0' }}>
          {/* Revenue */}
          <FlowBox
            label="留ㅼ텧??
            value={fB(rev, company?.ticker)}
            pct="100%"
            color="#3b82f6"
            desc={p.industry || '?듭떖 ?ъ뾽'}
            isFirst
          />
          <FlowArrow />

          {/* COGS Split */}
          <div style={{ display:'flex', flexDirection:'column', gap:'8px', minWidth:'160px' }}>
            <FlowBox label="留ㅼ텧?먭? (COGS)" value={fB(cogs, company?.ticker)} pct={`${(cogs/rev*100).toFixed(1)}%`} color="#ff6b6b" desc="?쒗뭹쨌?쒕퉬???먭?" small />
            <FlowBox label="留ㅼ텧珥앹씠?? value={fB(gp, company?.ticker)} pct={`${gpm.toFixed(1)}%`} color="#10b981" desc="Gross Profit" small highlight />
          </div>
          <FlowArrow />

          {/* OpEx Split */}
          <div style={{ display:'flex', flexDirection:'column', gap:'8px', minWidth:'160px' }}>
            <FlowBox label="?먭?鍮꽷톀&D" value={fB(opEx, company?.ticker)} pct={`${(opEx/rev*100).toFixed(1)}%`} color="#f97316" desc="?댁쁺鍮?怨듭젣" small />
            <FlowBox label="?곸뾽?댁씡" value={fB(opInc, company?.ticker)} pct={`${opm.toFixed(1)}%`} color="#8b5cf6" desc="Operating Income" small highlight />
          </div>
          <FlowArrow />

          {/* Net Income */}
          <div style={{ display:'flex', flexDirection:'column', gap:'8px', minWidth:'160px' }}>
            <FlowBox label="?멸툑쨌?댁옄쨌湲고?" value={fB(taxOther, company?.ticker)} pct={`${(taxOther/rev*100).toFixed(1)}%`} color="#ef4444" desc="鍮꾩쁺??鍮꾩슜" small />
            <FlowBox label="?룇 ?쒖씠?? value={fB(netInc, company?.ticker)} pct={`${npm.toFixed(1)}%`} color="#00f2fe" desc="Net Income" small highlight glow />
          </div>
        </div>
        {/* 留덉쭊???붿빟 諛?*/}
        <div style={{ marginTop:'24px', padding:'16px', borderRadius:'8px', background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize:'0.8rem', color:'var(--text-secondary)', marginBottom:'12px', fontWeight:600 }}>留ㅼ텧 1?⑥쐞?먯꽌 ?⑤뒗 ?댁씡</div>
          <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
            {[
              { label:'留ㅼ텧珥앹씠?듬쪧 (GPM)', pct: gpm, color:'#10b981' },
              { label:'?곸뾽?댁씡瑜?(OPM)', pct: opm, color:'#8b5cf6' },
              { label:'?쒖씠?듬쪧 (NPM)',   pct: npm, color:'#00f2fe' },
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

      {/* ?? ?섏씡 ??룷 李⑦듃 + 鍮꾩슜 援ъ“ ?뚯씠 ?? */}
      <div style={{ display:'grid', gridTemplateColumns:'3fr 2fr', gap:'20px' }}>
        {/* Waterfall Chart */}
        <div className="glass-panel" style={{ padding:'24px' }}>
          <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginBottom:'16px', fontWeight:600 }}>
            ?뱤 ?섏씡 ??룷 李⑦듃 (Profit Waterfall)
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
            ?ⅶ 留ㅼ텧 諛곕텇 援ъ“
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
                formatter={(v) => fB(v, company?.ticker)}
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

// ?? 4?④퀎 ?ъ옄?먯튃 湲곕컲 ?좊땲踰꾩뒪 ?붾줈??& ?ы듃?대━??留ㅻ땲? ?????????????????
function AgentWorkspace() {
  const [universeData, setUniverseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [scanData, setScanData] = useState(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [mainTab, setMainTab] = useState('universe'); // 'universe' | 'autoscan' | 'eps'
  // EPS 遺꾩꽍 state
  const [epsValuation, setEpsValuation] = useState(null);
  const [epsSpread, setEpsSpread] = useState(null);
  const [epsTracker, setEpsTracker] = useState(null);
  const [epsLoading, setEpsLoading] = useState(false);
  const [epsSubTab, setEpsSubTab] = useState('valuation'); // 'valuation'|'spread'|'tracker'
  const [spreadPeriod, setSpreadPeriod] = useState(252);
  // ?ㅽ겕由щ떇 state
  const [screenData, setScreenData] = useState(null);
  const [screenLoading, setScreenLoading] = useState(false);

  useEffect(() => {
    fetchUniverse();
  }, []);

  const fetchUniverse = async (retryCount = 0, forceRefresh = false) => {
    setLoading(true);
    try {
      const endpoint = forceRefresh ? `${API_BASE}/portfolio/refresh_prices` : `${API_BASE}/portfolio/universe`;
      const method = forceRefresh ? axios.post : axios.get;
      const r = await method(endpoint);
      if (r.data && r.data.universe && r.data.universe.length > 0) {
        setUniverseData(r.data);
        setLoading(false);
      } else if (retryCount < 3) {
        setTimeout(() => fetchUniverse(retryCount + 1, forceRefresh), 2000);
      } else {
        setLoading(false);
      }
    } catch (e) {
      console.error("Failed to load universe", e);
      if (retryCount < 3) {
        setTimeout(() => fetchUniverse(retryCount + 1, forceRefresh), 2500);
      } else {
        setLoading(false);
      }
    }
  };

  const fetchAutoScan = async () => {
    setScanLoading(true);
    try {
      const r = await axios.get(`${API_BASE}/portfolio/auto_scan`);
      setScanData(r.data);
    } catch (e) {
      console.error("Auto scan failed", e);
    } finally {
      setScanLoading(false);
    }
  };

  const fetchScreening = async () => {
    setScreenLoading(true);
    try {
      const r = await axios.post(`${API_BASE}/portfolio/screen_to_watchlist?auto_promote=true`);
      setScreenData(r.data);
      if (r.data?.promoted_count > 0) { setUniverseData(null); fetchUniverse(0, false); }
    } catch(e) { console.error('Screening failed', e); }
    finally { setScreenLoading(false); }
  };

  const fetchEpsValuation = async () => {

    setEpsLoading(true);
    try { const r = await axios.get(`${API_BASE}/eps/market_valuation`); setEpsValuation(r.data); }
    catch(e) { console.error('EPS valuation failed', e); }
    finally { setEpsLoading(false); }
  };
  const fetchEpsSpread = async (days) => {
    const d = days || spreadPeriod;
    setEpsLoading(true);
    try { const r = await axios.get(`${API_BASE}/eps/spread_screen?period_days=${d}&top_n=20`); setEpsSpread(r.data); }
    catch(e) { console.error('EPS spread failed', e); }
    finally { setEpsLoading(false); }
  };
  const fetchEpsTracker = async () => {
    setEpsLoading(true);
    try { const r = await axios.get(`${API_BASE}/eps/universe_tracker`); setEpsTracker(r.data); }
    catch(e) { console.error('EPS tracker failed', e); }
    finally { setEpsLoading(false); }
  };
  const handleEpsTabClick = (subTab) => {
    setEpsSubTab(subTab);
    if (subTab === 'valuation' && !epsValuation) fetchEpsValuation();
    if (subTab === 'spread' && !epsSpread) fetchEpsSpread();
    if (subTab === 'tracker' && !epsTracker) fetchEpsTracker();
  };

  const universeList = universeData?.universe || [];


  const filteredList = universeList.filter(item => {
    if (selectedTier === 'Core' && item.portfolio_tier !== 'Core') return false;
    if (selectedTier === 'Satellite' && item.portfolio_tier !== 'Satellite') return false;
    if (selectedTier === 'Watchlist' && item.portfolio_tier !== 'Watchlist') return false;
    if (selectedTier === 'BUY_READY' && !item.buy_signal?.includes('BUY_READY') && !item.buy_signal?.includes('DEEP_DISCOUNT')) return false;

    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      return item.name?.toLowerCase().includes(q) || item.ticker?.toLowerCase().includes(q) || item.industry_title?.toLowerCase().includes(q);
    }
    return true;
  });

  const coreCount = universeList.filter(i => i.portfolio_tier === 'Core').length;
  const satCount = universeList.filter(i => i.portfolio_tier === 'Satellite').length;
  const watchCount = universeList.filter(i => i.portfolio_tier === 'Watchlist').length;
  const buyReadyCount = universeList.filter(i => i.buy_signal?.includes('BUY_READY') || i.buy_signal?.includes('DEEP_DISCOUNT')).length;

  return (
    <div className="agent-workspace">
      <div className="page-header orchestrator-header" style={{ borderBottom:'1px solid var(--border-color)', paddingBottom:'24px', marginBottom:'24px' }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:'10px', marginBottom:'10px' }}>
            <span className="live-badge active" style={{ background:'rgba(16,185,129,0.15)', color:'#10b981', border:'1px solid rgba(16,185,129,0.3)' }}>??4?④퀎 ?ъ옄?먯튃 ?붿쭊 媛??以?/span>
            <span style={{ color:'var(--text-secondary)', fontSize:'0.85rem' }}>Real-time Portfolio Universe Monitor</span>
          </div>
          <h2 style={{ fontSize:'2.2rem', margin:0, background:'linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent' }}>?썳截?4?④퀎 ?ъ옄?먯튃 湲곕컲 ?좊땲踰꾩뒪 紐⑤땲?곕쭅</h2>
        </div>
        <div style={{ display:'flex', gap:'8px', alignItems:'center', flexWrap:'wrap' }}>
          {/* 硫붿씤 ???꾪솚 */}
          <button onClick={() => setMainTab('universe')} style={{
            padding:'8px 18px', borderRadius:'10px', cursor:'pointer', fontWeight:700, fontSize:'0.85rem',
            border: mainTab==='universe' ? '1.5px solid #a5b4fc' : '1px solid rgba(255,255,255,0.1)',
            background: mainTab==='universe' ? 'rgba(165,180,252,0.15)' : 'rgba(255,255,255,0.03)',
            color: mainTab==='universe' ? '#a5b4fc' : 'rgba(255,255,255,0.5)'
          }}>?썳截??붾줈???좊땲踰꾩뒪</button>
          <button onClick={() => { setMainTab('autoscan'); if (!scanData && !scanLoading) fetchAutoScan(); }} style={{
            padding:'8px 18px', borderRadius:'10px', cursor:'pointer', fontWeight:700, fontSize:'0.85rem',
            border: mainTab==='autoscan' ? '1.5px solid #fbbf24' : '1px solid rgba(255,255,255,0.1)',
            background: mainTab==='autoscan' ? 'rgba(251,191,36,0.12)' : 'rgba(255,255,255,0.03)',
            color: mainTab==='autoscan' ? '#fbbf24' : 'rgba(255,255,255,0.5)'
          }}>?뵇 ?먮룞 醫낅ぉ 異붿쿇</button>
          <button onClick={() => { setMainTab('eps'); if (!epsValuation) fetchEpsValuation(); setEpsSubTab('valuation'); }} style={{
            padding:'8px 18px', borderRadius:'10px', cursor:'pointer', fontWeight:700, fontSize:'0.85rem',
            border: mainTab==='eps' ? '1.5px solid #34d399' : '1px solid rgba(255,255,255,0.1)',
            background: mainTab==='eps' ? 'rgba(52,211,153,0.12)' : 'rgba(255,255,255,0.03)',
            color: mainTab==='eps' ? '#34d399' : 'rgba(255,255,255,0.5)'
          }}>?뱤 EPS 遺꾩꽍</button>
          {mainTab === 'universe' && (
            <button className="run-btn" disabled={loading} onClick={() => fetchUniverse(0, true)}>
              {loading ? '??媛깆떊 以?..' : '?봽 ?ㅼ떆媛?二쇨?/MDD ?ъ“??(Yahoo Live)'}
            </button>
          )}
          {mainTab === 'autoscan' && (
            <button className="run-btn" disabled={scanLoading} onClick={fetchAutoScan}>
              {scanLoading ? '???ㅼ틪 以?(??1遺?...' : '?뵇 ?ъ옄?먯튃 湲곕컲 ?좉퇋 醫낅ぉ ?ъ뒪罹?}
            </button>
          )}
          {mainTab === 'eps' && (
            <button className="run-btn" disabled={epsLoading} onClick={() => {
              if (epsSubTab==='valuation') fetchEpsValuation();
              if (epsSubTab==='spread') fetchEpsSpread();
              if (epsSubTab==='tracker') fetchEpsTracker();
            }}>
              {epsLoading ? '??議고쉶 以?..' : '?봽 EPS ?곗씠???덈줈怨좎묠'}
            </button>
          )}
        </div>
      </div>

      {/* ?? EPS 遺꾩꽍 ???? */}
      {mainTab === 'eps' && (
        <div>
          {/* EPS ?쒕툕??*/}
          <div style={{ display:'flex', gap:'8px', marginBottom:'24px', flexWrap:'wrap' }}>
            {[
              { id:'valuation', label:'?뱢 ?쒖옣 諛몃쪟?먯씠???⑤룄怨?, color:'#a78bfa' },
              { id:'spread',    label:'?뵮 二쇨?-EPS 愿대━ ?ㅽ겕由щ꼫', color:'#34d399' },
              { id:'tracker',   label:'?렞 ?붾줈??醫낅ぉ EPS ?몃옒而?, color:'#60a5fa' },
            ].map(t => (
              <button key={t.id} onClick={() => handleEpsTabClick(t.id)} style={{
                padding:'8px 18px', borderRadius:'10px', cursor:'pointer', fontWeight:700, fontSize:'0.85rem',
                border: epsSubTab===t.id ? `1.5px solid ${t.color}` : '1px solid rgba(255,255,255,0.1)',
                background: epsSubTab===t.id ? `${t.color}22` : 'rgba(255,255,255,0.03)',
                color: epsSubTab===t.id ? '#fff' : 'rgba(255,255,255,0.5)'
              }}>{t.label}</button>
            ))}
          </div>

          {epsLoading ? (
            <div className="glass-panel" style={{ padding:'60px', textAlign:'center' }}>
              <div style={{ fontSize:'1.2rem', color:'#34d399', marginBottom:'12px' }}>??EPS ?곗씠??遺꾩꽍 以?..</div>
              <div style={{ fontSize:'0.85rem', color:'rgba(255,255,255,0.4)' }}>KOSPI200+KOSDAQ150 350媛?醫낅ぉ 泥섎━ 以?/div>
            </div>
          ) : (
            <>
              {/* ?? ?쒕툕??1: ?쒖옣 諛몃쪟?먯씠???⑤룄怨??? */}
              {epsSubTab === 'valuation' && (
                !epsValuation ? (
                  <div className="glass-panel" style={{ padding:'50px', textAlign:'center' }}>
                    <button className="run-btn" onClick={fetchEpsValuation} style={{ margin:'0 auto' }}>?뱢 ?쒖옣 PER ?곗씠??遺덈윭?ㅺ린</button>
                  </div>
                ) : epsValuation.error ? (
                  <div className="glass-panel" style={{ padding:'40px', textAlign:'center', color:'#f87171' }}>{epsValuation.error}</div>
                ) : (
                  <div>
                    {/* ?꾩옱 ?⑤룄 寃뚯씠吏 */}
                    <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(200px,1fr))', gap:'12px', marginBottom:'24px' }}>
                      {[
                        { label:'KOSPI200 ?꾩옱 FWD PER', value:`${epsValuation.current?.kospi200}x`, sub:'?쒖옣 ?됯퇏', color:'#a78bfa' },
                        { label:'KOSDAQ150 ?꾩옱 FWD PER', value:`${epsValuation.current?.kosdaq150}x`, sub:'?쒖옣 ?됯퇏', color:'#60a5fa' },
                        { label:'?꾩옱 ??궗??遺꾩쐞??, value:`${epsValuation.current_percentile}%ile`, sub:epsValuation.level, color: epsValuation.current_percentile <= 35 ? '#34d399' : epsValuation.current_percentile <= 55 ? '#fbbf24' : '#f87171' },
                        { label:'10???됯퇏 PER', value:`${epsValuation.history?.avg}x`, sub:`踰붿쐞: ${epsValuation.history?.min}x ~ ${epsValuation.history?.max}x`, color:'#94a3b8' },
                      ].map(s => (
                        <div key={s.label} className="glass-panel" style={{ padding:'18px', borderRadius:'12px', textAlign:'center', border:`1px solid ${s.color}33` }}>
                          <div style={{ fontSize:'0.72rem', color:'rgba(255,255,255,0.45)', marginBottom:'6px' }}>{s.label}</div>
                          <div style={{ fontSize:'1.6rem', fontWeight:900, color:s.color, marginBottom:'4px' }}>{s.value}</div>
                          <div style={{ fontSize:'0.72rem', color:'rgba(255,255,255,0.6)' }}>{s.sub}</div>
                        </div>
                      ))}
                    </div>

                    {/* ?⑤룄怨?諛?*/}
                    <div className="glass-panel" style={{ padding:'20px', marginBottom:'20px', borderRadius:'14px' }}>
                      <div style={{ fontSize:'0.85rem', color:'#a78bfa', fontWeight:700, marginBottom:'14px' }}>
                        ?뙜截?KOSPI200 FWD PER ??궗???꾩튂 ({epsValuation.current_percentile}%ile)
                      </div>
                      {(() => {
                        const pct = epsValuation.current_percentile || 0;
                        const clr = pct<=35?'#34d399':pct<=55?'#fbbf24':'#f87171';
                        return (
                          <div>
                            <div style={{ position:'relative', height:'32px', background:'rgba(255,255,255,0.06)', borderRadius:'16px', overflow:'hidden', marginBottom:'8px' }}>
                              {/* 援ш컙 ?됱긽 */}
                              <div style={{ position:'absolute', left:'0%', width:'20%', height:'100%', background:'rgba(52,211,153,0.25)' }}/>
                              <div style={{ position:'absolute', left:'20%', width:'15%', height:'100%', background:'rgba(52,211,153,0.15)' }}/>
                              <div style={{ position:'absolute', left:'35%', width:'20%', height:'100%', background:'rgba(251,191,36,0.15)' }}/>
                              <div style={{ position:'absolute', left:'55%', width:'20%', height:'100%', background:'rgba(251,191,36,0.25)' }}/>
                              <div style={{ position:'absolute', left:'75%', width:'25%', height:'100%', background:'rgba(239,68,68,0.2)' }}/>
                              {/* ?꾩옱 ?꾩튂 ?ъ씤??*/}
                              <div style={{ position:'absolute', left:`${Math.min(pct,98)}%`, top:'2px', width:'28px', height:'28px', background:clr, borderRadius:'50%', transform:'translateX(-50%)', boxShadow:`0 0 12px ${clr}80`, display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.7rem', fontWeight:900, color:'#000' }}>
                                {pct}
                              </div>
                            </div>
                            <div style={{ display:'flex', justifyContent:'space-between', fontSize:'0.68rem', color:'rgba(255,255,255,0.4)' }}>
                              <span>留ㅼ슦 ??됯?</span><span>??됯?</span><span>?곸젙</span><span>怨좏룊媛</span><span>怨쇱뿴</span>
                            </div>
                            <div style={{ marginTop:'8px', padding:'8px 12px', borderRadius:'8px', background:`${clr}15`, border:`1px solid ${clr}30`, fontSize:'0.82rem', color:clr, fontWeight:700 }}>
                              ??{epsValuation.level}
                            </div>
                          </div>
                        );
                      })()}
                    </div>

                    {/* PER 遺꾩쐞???덉뒪?좊━ */}
                    <div className="glass-panel" style={{ padding:'20px', marginBottom:'20px', borderRadius:'14px' }}>
                      <div style={{ fontSize:'0.85rem', color:'rgba(255,255,255,0.7)', fontWeight:700, marginBottom:'14px' }}>
                        ?뱤 10??PER 遺꾩쐞??諛대뱶
                      </div>
                      <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:'8px' }}>
                        {[
                          { label:'P10 (洹뱀?)', value:epsValuation.history?.p10, color:'#34d399' },
                          { label:'P25 (??됯?)', value:epsValuation.history?.p25, color:'#a7f3d0' },
                          { label:'P50 (以묒븰)', value:epsValuation.history?.p50, color:'#fbbf24' },
                          { label:'P75 (怨좏룊媛)', value:epsValuation.history?.p75, color:'#fb923c' },
                          { label:'P90 (怨쇱뿴)', value:epsValuation.history?.p90, color:'#f87171' },
                        ].map(p => (
                          <div key={p.label} style={{ textAlign:'center', padding:'12px', borderRadius:'10px', background:'rgba(255,255,255,0.04)', border:`1px solid ${p.color}33` }}>
                            <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.45)', marginBottom:'4px' }}>{p.label}</div>
                            <div style={{ fontSize:'1.15rem', fontWeight:800, color:p.color }}>{p.value}x</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 1??PER 異붿씠 李⑦듃 */}
                    {epsValuation.chart_kospi200?.length > 0 && (
                      <div className="glass-panel" style={{ padding:'20px', borderRadius:'14px' }}>
                        <div style={{ fontSize:'0.85rem', color:'rgba(255,255,255,0.7)', fontWeight:700, marginBottom:'14px' }}>
                          ?뱢 KOSPI200 FWD PER 1??異붿씠
                        </div>
                        <ResponsiveContainer width="100%" height={260}>
                          <ComposedChart data={epsValuation.chart_kospi200}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis dataKey="date" tick={{ fontSize:11, fill:'rgba(255,255,255,0.4)' }}
                              tickFormatter={v => v?.slice(5)} interval={30} />
                            <YAxis domain={['auto','auto']} tick={{ fontSize:11, fill:'rgba(255,255,255,0.4)' }} tickFormatter={v=>`${v}x`} />
                            <RechartsTooltip
                              contentStyle={{ background:'rgba(15,23,42,0.95)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'8px', fontSize:'12px' }}
                              formatter={(v,n) => [`${v}x`, n==='per'?'FWD PER':n]}
                              labelFormatter={l=>`?뱟 ${l}`}
                            />
                            {/* 怨쇨굅 ?됯퇏??*/}
                            <Line type="monotone" dataKey={() => epsValuation.history?.avg} stroke="rgba(148,163,184,0.4)" strokeDasharray="5 5" dot={false} name="10?꾪룊洹? />
                            <Area type="monotone" dataKey="per" fill="rgba(167,139,250,0.1)" stroke="#a78bfa" strokeWidth={2} dot={false} name="FWD PER" />
                          </ComposedChart>
                        </ResponsiveContainer>
                        {epsValuation.chart_kosdaq150?.length > 0 && (
                          <>
                            <div style={{ fontSize:'0.85rem', color:'rgba(255,255,255,0.7)', fontWeight:700, margin:'20px 0 14px' }}>
                              ?뱢 KOSDAQ150 FWD PER 1??異붿씠
                            </div>
                            <ResponsiveContainer width="100%" height={200}>
                              <ComposedChart data={epsValuation.chart_kosdaq150}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                <XAxis dataKey="date" tick={{ fontSize:11, fill:'rgba(255,255,255,0.4)' }} tickFormatter={v=>v?.slice(5)} interval={30}/>
                                <YAxis domain={['auto','auto']} tick={{ fontSize:11, fill:'rgba(255,255,255,0.4)' }} tickFormatter={v=>`${v}x`}/>
                                <RechartsTooltip contentStyle={{ background:'rgba(15,23,42,0.95)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'8px', fontSize:'12px' }} formatter={(v)=>[`${v}x`,'FWD PER']} labelFormatter={l=>`?뱟 ${l}`}/>
                                <Area type="monotone" dataKey="per" fill="rgba(96,165,250,0.1)" stroke="#60a5fa" strokeWidth={2} dot={false} name="FWD PER"/>
                              </ComposedChart>
                            </ResponsiveContainer>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )
              )}

              {/* ?? ?쒕툕??2: 二쇨?-EPS 愿대━ ?ㅽ겕由щ꼫 ?? */}
              {epsSubTab === 'spread' && (
                !epsSpread ? (
                  <div className="glass-panel" style={{ padding:'50px', textAlign:'center' }}>
                    <div style={{ color:'rgba(255,255,255,0.6)', marginBottom:'20px' }}>
                      EPS ?깆옣 ?鍮?二쇨? ?깆옣 愿대━瑜?遺꾩꽍?⑸땲??br/>
                      <span style={{ fontSize:'0.8rem', color:'rgba(255,255,255,0.4)' }}>?뚯닔 愿대━ = EPS媛 二쇨?蹂대떎 ???щ옄??= ??됯? 湲고쉶</span>
                    </div>
                    <button className="run-btn" onClick={() => fetchEpsSpread()} style={{ margin:'0 auto' }}>?뵮 ?ㅽ겕由щ떇 ?쒖옉</button>
                  </div>
                ) : epsSpread.error ? (
                  <div className="glass-panel" style={{ padding:'40px', textAlign:'center', color:'#f87171' }}>{epsSpread.error}</div>
                ) : (
                  <div>
                    {/* 湲곌컙 ?좏깮 */}
                    <div style={{ display:'flex', gap:'8px', marginBottom:'20px', alignItems:'center', flexWrap:'wrap' }}>
                      <span style={{ fontSize:'0.82rem', color:'rgba(255,255,255,0.5)' }}>鍮꾧탳 湲곌컙:</span>
                      {[[63,'3媛쒖썡'],[126,'6媛쒖썡'],[252,'1??],[504,'2??]].map(([d,l]) => (
                        <button key={d} onClick={() => { setSpreadPeriod(d); fetchEpsSpread(d); }} style={{
                          padding:'5px 12px', borderRadius:'8px', cursor:'pointer', fontSize:'0.8rem', fontWeight:600,
                          border: spreadPeriod===d ? '1.5px solid #34d399' : '1px solid rgba(255,255,255,0.1)',
                          background: spreadPeriod===d ? 'rgba(52,211,153,0.15)' : 'rgba(255,255,255,0.03)',
                          color: spreadPeriod===d ? '#34d399' : 'rgba(255,255,255,0.5)'
                        }}>{l}</button>
                      ))}
                      <span style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.35)', marginLeft:'auto' }}>
                        湲곗??? {epsSpread.past_date} ??{epsSpread.latest_date} | 珥?{epsSpread.total_screened}醫낅ぉ 遺꾩꽍
                      </span>
                    </div>

                    {/* ??됯? ?뱀뀡 */}
                    <div style={{ marginBottom:'24px' }}>
                      <div style={{ fontSize:'1rem', fontWeight:700, color:'#34d399', marginBottom:'12px', display:'flex', alignItems:'center', gap:'8px' }}>
                        ?윟 ??됯? TOP {epsSpread.undervalued?.length}
                        <span style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.4)', fontWeight:400 }}>EPS ?깆옣 &gt;&gt; 二쇨? ?곸듅 ???쒖옣???꾩쭅 諛섏쁺 紐삵븳 湲고쉶</span>
                      </div>
                      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(320px,1fr))', gap:'12px' }}>
                        {epsSpread.undervalued?.map((item, idx) => (
                          <div key={idx} className="glass-panel" style={{ padding:'16px', borderRadius:'12px', border:'1.5px solid rgba(52,211,153,0.3)', background:'rgba(52,211,153,0.04)' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'8px' }}>
                              <div style={{ display:'flex', gap:'8px', alignItems:'center' }}>
                                <span style={{ fontSize:'0.9rem', fontWeight:900, color:'#34d399' }}>#{idx+1}</span>
                                <span style={{ fontSize:'1rem', fontWeight:700, color:'white' }}>{item.name}</span>
                                <span style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.4)' }}>{item.index_type}</span>
                              </div>
                              <span style={{ fontSize:'0.75rem', padding:'2px 8px', borderRadius:'6px', background:'rgba(52,211,153,0.15)', color:'#34d399', fontWeight:700 }}>
                                FWD {item.fwd_per}x
                              </span>
                            </div>
                            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'6px', background:'rgba(0,0,0,0.2)', padding:'10px', borderRadius:'8px' }}>
                              <div style={{ textAlign:'center' }}>
                                <div style={{ fontSize:'0.62rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>EPS ?깆옣</div>
                                <div style={{ fontSize:'0.92rem', fontWeight:800, color:'#34d399' }}>+{item.eps_growth_pct?.toFixed(0)}%</div>
                              </div>
                              <div style={{ textAlign:'center' }}>
                                <div style={{ fontSize:'0.62rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>二쇨? ?깆옣</div>
                                <div style={{ fontSize:'0.92rem', fontWeight:800, color: item.price_growth_pct >= 0 ? '#60a5fa' : '#f87171' }}>
                                  {item.price_growth_pct >= 0 ? '+' : ''}{item.price_growth_pct?.toFixed(0)}%
                                </div>
                              </div>
                              <div style={{ textAlign:'center' }}>
                                <div style={{ fontSize:'0.62rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>愿대━</div>
                                <div style={{ fontSize:'0.92rem', fontWeight:800, color:'#34d399' }}>{item.spread_pct?.toFixed(0)}%p</div>
                              </div>
                            </div>
                            <div style={{ marginTop:'8px', fontSize:'0.72rem', color:'rgba(255,255,255,0.45)', display:'flex', gap:'12px' }}>
                              <span>?꾩옱媛 {item.price?.toLocaleString()}??/span>
                              <span>EPS {item.eps_fwd?.toLocaleString()}??/span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 怨쇱뿴 ?뱀뀡 */}
                    <div>
                      <div style={{ fontSize:'1rem', fontWeight:700, color:'#f87171', marginBottom:'12px', display:'flex', alignItems:'center', gap:'8px' }}>
                        ?뵶 二쇱쓽 怨쇱뿴 TOP {epsSpread.overheated?.length}
                        <span style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.4)', fontWeight:400 }}>二쇨? ?곸듅 &gt;&gt; EPS ?깆옣 ??二쇱쓽 ?꾩슂</span>
                      </div>
                      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(320px,1fr))', gap:'12px' }}>
                        {epsSpread.overheated?.map((item, idx) => (
                          <div key={idx} className="glass-panel" style={{ padding:'16px', borderRadius:'12px', border:'1px solid rgba(239,68,68,0.25)', background:'rgba(239,68,68,0.04)' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'8px' }}>
                              <div style={{ display:'flex', gap:'8px', alignItems:'center' }}>
                                <span style={{ fontSize:'0.9rem', fontWeight:900, color:'#f87171' }}>?좑툘</span>
                                <span style={{ fontSize:'1rem', fontWeight:700, color:'white' }}>{item.name}</span>
                                <span style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.4)' }}>{item.index_type}</span>
                              </div>
                              <span style={{ fontSize:'0.75rem', padding:'2px 8px', borderRadius:'6px', background:'rgba(239,68,68,0.15)', color:'#f87171', fontWeight:700 }}>
                                FWD {item.fwd_per}x
                              </span>
                            </div>
                            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'6px', background:'rgba(0,0,0,0.2)', padding:'10px', borderRadius:'8px' }}>
                              <div style={{ textAlign:'center' }}>
                                <div style={{ fontSize:'0.62rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>EPS ?깆옣</div>
                                <div style={{ fontSize:'0.92rem', fontWeight:800, color:'#94a3b8' }}>{item.eps_growth_pct?.toFixed(0)}%</div>
                              </div>
                              <div style={{ textAlign:'center' }}>
                                <div style={{ fontSize:'0.62rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>二쇨? ?깆옣</div>
                                <div style={{ fontSize:'0.92rem', fontWeight:800, color:'#f87171' }}>+{item.price_growth_pct?.toFixed(0)}%</div>
                              </div>
                              <div style={{ textAlign:'center' }}>
                                <div style={{ fontSize:'0.62rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>愿대━</div>
                                <div style={{ fontSize:'0.92rem', fontWeight:800, color:'#f87171' }}>+{item.spread_pct?.toFixed(0)}%p</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              )}

              {/* ?? ?쒕툕??3: ?붾줈??醫낅ぉ EPS ?몃옒而??? */}
              {epsSubTab === 'tracker' && (
                !epsTracker ? (
                  <div className="glass-panel" style={{ padding:'50px', textAlign:'center' }}>
                    <div style={{ color:'rgba(255,255,255,0.6)', marginBottom:'20px' }}>?좊땲踰꾩뒪 ?쒓뎅 醫낅ぉ??FWD EPS + 二쇨? 異붿씠瑜?異붿쟻?⑸땲??/div>
                    <button className="run-btn" onClick={fetchEpsTracker} style={{ margin:'0 auto' }}>?렞 EPS ?몃옒而?遺덈윭?ㅺ린</button>
                  </div>
                ) : epsTracker.tracker?.length === 0 ? (
                  <div className="glass-panel" style={{ padding:'40px', textAlign:'center', color:'rgba(255,255,255,0.5)' }}>
                    KOSPI200/KOSDAQ150 留ㅼ묶 醫낅ぉ???놁뒿?덈떎. ?좊땲踰꾩뒪???쒓뎅 醫낅ぉ??異붽??댁＜?몄슂.
                  </div>
                ) : (
                  <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(380px,1fr))', gap:'16px' }}>
                    {epsTracker.tracker?.map((item, idx) => {
                      const isCore = item.portfolio_tier === 'Core';
                      const isSat  = item.portfolio_tier === 'Satellite';
                      const tierC  = isCore ? '#60a5fa' : isSat ? '#c084fc' : '#fbbf24';
                      const isBuy  = item.buy_signal?.includes('BUY_READY') || item.buy_signal?.includes('DEEP_DISCOUNT');
                      const spreadColor = item.spread_1y < -10 ? '#34d399' : item.spread_1y > 10 ? '#f87171' : '#94a3b8';
                      return (
                        <div key={idx} className="glass-panel" style={{
                          padding:'20px', borderRadius:'14px',
                          border: isBuy ? '1.5px solid rgba(52,211,153,0.4)' : `1px solid ${tierC}22`,
                          background: isBuy ? 'rgba(52,211,153,0.04)' : 'rgba(30,41,59,0.5)'
                        }}>
                          {/* ?ㅻ뜑 */}
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'12px' }}>
                            <div>
                              <span style={{ fontSize:'0.72rem', padding:'2px 7px', borderRadius:'6px', background:`${tierC}22`, color:tierC, fontWeight:700, marginRight:'8px' }}>
                                {isCore ? '?룇 Core' : isSat ? '?? Satellite' : '??Watchlist'}
                              </span>
                              <span style={{ fontSize:'1.05rem', fontWeight:700, color:'white' }}>{item.name}</span>
                            </div>
                            {isBuy && <span style={{ fontSize:'0.7rem', padding:'2px 8px', borderRadius:'10px', background:'rgba(52,211,153,0.15)', color:'#34d399', border:'1px solid rgba(52,211,153,0.3)', fontWeight:700 }}>BUY READY</span>}
                          </div>

                          {/* FWD PER + MDD 寃뚯씠吏 */}
                          <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'8px', background:'rgba(0,0,0,0.2)', padding:'10px', borderRadius:'8px', marginBottom:'12px' }}>
                            <div style={{ textAlign:'center' }}>
                              <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.35)', marginBottom:'2px' }}>?꾩옱媛</div>
                              <div style={{ fontSize:'0.82rem', fontWeight:700, color:'white' }}>{item.price_latest?.toLocaleString()}??/div>
                            </div>
                            <div style={{ textAlign:'center' }}>
                              <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.35)', marginBottom:'2px' }}>FWD PER</div>
                              <div style={{ fontSize:'0.82rem', fontWeight:700, color:'#a78bfa' }}>{item.fwd_per_latest}x</div>
                            </div>
                            <div style={{ textAlign:'center' }}>
                              <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.35)', marginBottom:'2px' }}>MDD</div>
                              <div style={{ fontSize:'0.82rem', fontWeight:800, color: item.mdd_pct <= -20 ? '#34d399' : '#f87171' }}>
                                {item.mdd_pct?.toFixed(1)}%
                              </div>
                            </div>
                            <div style={{ textAlign:'center' }}>
                              <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.35)', marginBottom:'2px' }}>FWD EPS</div>
                              <div style={{ fontSize:'0.82rem', fontWeight:700, color:'#fbbf24' }}>{item.eps_latest?.toLocaleString()}??/div>
                            </div>
                          </div>

                          {/* EPS vs 二쇨? ?깆옣 鍮꾧탳 */}
                          <div style={{ marginBottom:'12px', padding:'10px', borderRadius:'8px', background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.06)' }}>
                            <div style={{ fontSize:'0.7rem', color:'rgba(255,255,255,0.4)', marginBottom:'8px' }}>1??EPS ?깆옣 vs 二쇨? ?섏씡瑜?/div>
                            <div style={{ display:'flex', gap:'12px', alignItems:'center', flexWrap:'wrap' }}>
                              <div style={{ display:'flex', alignItems:'center', gap:'6px' }}>
                                <span style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.5)' }}>EPS</span>
                                <span style={{ fontSize:'1rem', fontWeight:800, color: item.eps_change_1y >= 0 ? '#34d399' : '#f87171' }}>
                                  {item.eps_change_1y >= 0 ? '+' : ''}{item.eps_change_1y?.toFixed(1)}%
                                </span>
                              </div>
                              <span style={{ color:'rgba(255,255,255,0.2)' }}>vs</span>
                              <div style={{ display:'flex', alignItems:'center', gap:'6px' }}>
                                <span style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.5)' }}>二쇨?</span>
                                <span style={{ fontSize:'1rem', fontWeight:800, color: item.price_change_1y >= 0 ? '#60a5fa' : '#f87171' }}>
                                  {item.price_change_1y >= 0 ? '+' : ''}{item.price_change_1y?.toFixed(1)}%
                                </span>
                              </div>
                              <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:'4px' }}>
                                <span style={{ fontSize:'0.7rem', color:'rgba(255,255,255,0.4)' }}>愿대━</span>
                                <span style={{ fontSize:'0.95rem', fontWeight:800, color:spreadColor }}>
                                  {item.spread_1y > 0 ? '+' : ''}{item.spread_1y?.toFixed(1)}%p
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* 誘몃땲 李⑦듃 (EPS + 二쇨? ?뺢퇋?? */}
                          {item.chart?.length > 2 && (() => {
                            const base_eps   = item.chart[0].eps   || 1;
                            const base_price = item.chart[0].price || 1;
                            const chartData  = item.chart.map(d => ({
                              date: d.date?.slice(5),
                              eps_idx:   d.eps   ? Math.round(d.eps   / base_eps   * 100) : null,
                              price_idx: d.price ? Math.round(d.price / base_price * 100) : null,
                            }));
                            return (
                              <div>
                                <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.35)', marginBottom:'4px' }}>
                                  ?뱢 EPS(二쇳솴) vs 二쇨?(?뚮옉) ?뺢퇋??(湲곗?=100)
                                </div>
                                <ResponsiveContainer width="100%" height={100}>
                                  <LineChart data={chartData}>
                                    <XAxis dataKey="date" hide />
                                    <YAxis hide domain={['auto','auto']}/>
                                    <RechartsTooltip
                                      contentStyle={{ background:'rgba(15,23,42,0.95)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'6px', fontSize:'11px' }}
                                      formatter={(v,n) => [`${v}`, n==='eps_idx'?'FWD EPS':'二쇨?']}
                                    />
                                    <Line type="monotone" dataKey="eps_idx"   stroke="#fbbf24" strokeWidth={1.5} dot={false} name="eps_idx"/>
                                    <Line type="monotone" dataKey="price_idx" stroke="#60a5fa" strokeWidth={1.5} dot={false} name="price_idx"/>
                                  </LineChart>
                                </ResponsiveContainer>
                              </div>
                            );
                          })()}
                        </div>
                      );
                    })}
                  </div>
                )
              )}
            </>
          )}
        </div>
      )}

      {/* ?? ?붾줈???좊땲踰꾩뒪 ???? */}
      {mainTab === 'universe' && (<>

        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:'16px', marginBottom:'24px' }}>
          <div style={{ display:'flex', gap:'8px', flexWrap:'wrap' }}>
            {[
              { id: 'ALL', label: `?꾩껜 ?좊땲踰꾩뒪 (${universeList.length})`, color: '#64748b' },
              { id: 'BUY_READY', label: `?윟 留ㅼ닔 媛??(${buyReadyCount})`, color: '#10b981' },
              { id: 'Core', label: `?룇 Core ?낆젏 (${coreCount})`, color: '#3b82f6' },
              { id: 'Satellite', label: `?? Satellite ?깆옣 (${satCount})`, color: '#8b5cf6' },
              { id: 'Watchlist', label: `??愿?ъ쥌紐?(${watchCount})`, color: '#f59e0b' },
            ].map(tab => (
              <button key={tab.id} onClick={() => setSelectedTier(tab.id)} style={{
                padding: '8px 16px', borderRadius: '10px',
                border: selectedTier === tab.id ? `1.5px solid ${tab.color}` : '1px solid rgba(255,255,255,0.1)',
                background: selectedTier === tab.id ? `${tab.color}22` : 'rgba(255,255,255,0.03)',
                color: selectedTier === tab.id ? '#ffffff' : 'rgba(255,255,255,0.6)',
                fontWeight: selectedTier === tab.id ? 700 : 500, fontSize: '0.85rem', cursor: 'pointer'
              }}>{tab.label}</button>
            ))}
          </div>

          <div style={{ position:'relative', minWidth:'240px' }}>
            <input type="text" placeholder="醫낅ぉ紐? ?곗빱, ?곗뾽 寃??.." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} style={{
              width:'100%', padding:'8px 14px', borderRadius:'10px', border:'1px solid rgba(255,255,255,0.15)', background:'rgba(15,23,42,0.6)', color:'white', fontSize:'0.85rem', outline:'none'
            }} />
          </div>
        </div>

        {loading ? (
          <div className="glass-panel" style={{ padding:'60px', textAlign:'center', color:'rgba(255,255,255,0.5)' }}>
            <div style={{ fontSize:'1.2rem', marginBottom:'12px' }}>???ㅼ떆媛??좊땲踰꾩뒪 ?곗씠???섏쭛 以?..</div>
          </div>
        ) : universeList.length === 0 ? (
          <div className="glass-panel" style={{ padding:'50px 24px', textAlign:'center' }}>
            <div style={{ fontSize:'1.2rem', color:'#f59e0b', fontWeight:700, marginBottom:'10px' }}>
              ?좑툘 ?좊땲踰꾩뒪 ?곗씠?곕? 遺덈윭?ㅻ뒗 以묒엯?덈떎 (?쒕쾭 ?곌껐 ?湲?
            </div>
            <div style={{ fontSize:'0.88rem', color:'rgba(255,255,255,0.6)', marginBottom:'20px' }}>
              Render 諛깆뿏???쒕쾭媛 耳쒖???以묒엯?덈떎. ?꾨옒 踰꾪듉???뚮윭 諛붾줈 ?곌껐???ъ떆?꾪븯?몄슂.
            </div>
            <button className="run-btn" onClick={() => fetchUniverse(0, false)} style={{ margin:'0 auto' }}>
              ?봽 ?ㅼ떆媛??곗씠???ㅼ떆 遺덈윭?ㅺ린
            </button>
          </div>
        ) : filteredList.length === 0 ? (
          <div className="glass-panel" style={{ padding:'60px', textAlign:'center', color:'rgba(255,255,255,0.5)' }}>?대떦 ?꾪꽣 議곌굔??遺?⑺븯??醫낅ぉ???놁뒿?덈떎.</div>
        ) : (
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(340px, 1fr))', gap:'16px' }}>
            {filteredList.map((item) => {
              const isCore = item.portfolio_tier === 'Core';
              const isSat = item.portfolio_tier === 'Satellite';
              const isWatch = item.portfolio_tier === 'Watchlist';
              const isBuyReady = item.buy_signal?.includes('BUY_READY') || item.buy_signal?.includes('DEEP_DISCOUNT');
              const isDeepDiscount = item.buy_signal?.includes('DEEP_DISCOUNT');

              let [badgeBg, badgeBorder, badgeText] = isBuyReady ? ['rgba(16, 185, 129, 0.15)', 'rgba(16, 185, 129, 0.4)', '#34d399'] : ['rgba(239, 68, 68, 0.15)', 'rgba(239, 68, 68, 0.4)', '#f87171'];
              if (isDeepDiscount) [badgeBg, badgeBorder, badgeText] = ['rgba(59, 130, 246, 0.2)', 'rgba(59, 130, 246, 0.5)', '#60a5fa'];
              
              let [tierTagBg, tierTagText] = ['rgba(255,255,255,0.06)', '#94a3b8'];
              if (isCore) [tierTagBg, tierTagText] = ['rgba(59,130,246,0.15)', '#60a5fa'];
              if (isSat) [tierTagBg, tierTagText] = ['rgba(139,92,246,0.15)', '#c084fc'];
              if (isWatch) [tierTagBg, tierTagText] = ['rgba(245,158,11,0.15)', '#fbbf24'];

              return (
                <div key={item.id} className="glass-panel" style={{
                  padding: '20px', borderRadius: '14px',
                  border: isBuyReady ? '1.5px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                  background: isBuyReady ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.05), rgba(15, 23, 42, 0.7))' : 'linear-gradient(135deg, rgba(30, 41, 59, 0.4), rgba(15, 23, 42, 0.6))',
                  display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'10px' }}>
                      <span style={{
                        padding:'3px 8px', borderRadius:'6px', background:tierTagBg, color:tierTagText,
                        fontSize:'0.75rem', fontWeight:700
                      }}>
                        {isCore ? '?룇 Core (?낆젏)' : isSat ? '?? Satellite (?깆옣)' : isWatch ? '??Watchlist' : '?룫 Standard'}
                      </span>
                      <span style={{
                        padding:'3px 10px', borderRadius:'12px', background:badgeBg, border:`1px solid ${badgeBorder}`,
                        color:badgeText, fontSize:'0.75rem', fontWeight:700
                      }}>
                        {item.buy_signal || 'WAIT'}
                      </span>
                    </div>

                    {/* 湲곗뾽紐?諛??곗빱 */}
                    <div style={{ display:'flex', alignItems:'baseline', gap:'8px', marginBottom:'4px' }}>
                      <h3 style={{ margin:0, fontSize:'1.15rem', color:'white', fontWeight:700 }}>{item.name}</h3>
                      <span style={{ fontSize:'0.82rem', color:'rgba(255,255,255,0.4)', fontWeight:600 }}>{item.ticker}</span>
                    </div>

                    <div style={{ fontSize:'0.78rem', color:'#a5b4fc', marginBottom:'12px' }}>
                      ?뱛 {item.industry_title}
                    </div>

                    {/* 媛寃?諛?MDD 硫뷀듃由?諛?*/}
                    <div style={{
                      display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'8px',
                      background:'rgba(0,0,0,0.25)', padding:'10px 12px', borderRadius:'8px', marginBottom:'12px',
                      border:'1px solid rgba(255,255,255,0.06)'
                    }}>
                      <div>
                        <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>?꾩옱媛</div>
                        <div style={{ fontSize:'0.88rem', color:'white', fontWeight:700 }}>
                          {item.current_price != null && item.current_price > 0
                            ? (item.ticker?.includes('.KS') || item.ticker?.includes('.KQ')
                                ? `${Math.round(item.current_price).toLocaleString()}??
                                : `$${item.current_price.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}`)
                            : '-'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>52二?理쒓퀬媛</div>
                        <div style={{ fontSize:'0.85rem', color:'rgba(255,255,255,0.7)', fontWeight:600 }}>
                          {item.high_52w != null && item.high_52w > 0
                            ? (item.ticker?.includes('.KS') || item.ticker?.includes('.KQ')
                                ? `${Math.round(item.high_52w).toLocaleString()}??
                                : `$${item.high_52w.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}`)
                            : '-'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize:'0.68rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>?꾩옱 MDD</div>
                        <div style={{
                          fontSize:'0.9rem', fontWeight:800,
                          color: (item.mdd_pct != null && item.mdd_pct <= -20) ? '#34d399' : '#f87171'
                        }}>
                          {item.mdd_pct != null ? `${item.mdd_pct.toFixed(1)}%` : '-'}
                        </div>
                      </div>
                    </div>

                    {/* ?먯튃 遺???ъ쑀 */}
                    {item.principle_reason && (
                      <div style={{
                        fontSize:'0.8rem', color:'rgba(255,255,255,0.85)', background:'rgba(99, 102, 241, 0.08)',
                        padding:'8px 10px', borderRadius:'6px', borderLeft:'3px solid #6366f1', marginBottom:'10px',
                        lineHeight:'1.4'
                      }}>
                        ?뮕 <strong>?먯튃 洹쇨굅:</strong> {item.principle_reason}
                      </div>
                    )}

                    {/* ??븷 ?ㅻ챸 */}
                    <div style={{ fontSize:'0.78rem', color:'rgba(255,255,255,0.6)', lineHeight:'1.4', marginBottom:'8px' }}>
                      {item.role_description}
                    </div>
                  </div>

                  {/* ?섎떒 誘몃옒 ?깆옣??*/}
                  {item.future_growth && (
                    <div style={{
                      fontSize:'0.75rem', color:'rgba(16, 185, 129, 0.8)', borderTop:'1px dashed rgba(255,255,255,0.08)',
                      paddingTop:'8px', marginTop:'6px'
                    }}>
                      ?뙮 {item.future_growth}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </>)}

      {/* ?? ?먮룞 醫낅ぉ 異붿쿇 ???? */}
      {mainTab === 'autoscan' && (
        <div>
          {/* ?? ?ъ옄?먯튃 ?ㅽ겕由щ떇 諛곕꼫 ?? */}
          <div className="glass-panel" style={{ padding:'20px 24px', marginBottom:'20px', borderRadius:'14px', border:'1px solid rgba(52,211,153,0.25)', background:'rgba(52,211,153,0.04)' }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:'12px' }}>
              <div>
                <div style={{ fontSize:'0.95rem', fontWeight:800, color:'#34d399', marginBottom:'6px' }}>
                  ?렞 BUY_CANDIDATE ??Watchlist ?먮룞 ?ㅽ겕由щ떇
                </div>
                <div style={{ fontSize:'0.8rem', color:'rgba(255,255,255,0.55)', lineHeight:'1.6' }}>
                  ?꾩옱 ?좊땲踰꾩뒪??BUY_CANDIDATE 醫낅ぉ?ㅼ쓣 ?ъ옄?먯튃(?낆젏?Β룹닔?듭꽦쨌?쒖킑)?쇰줈 ?ш?利?br/>
                  湲곗? ?듦낵 ???먮룞?쇰줈 <strong style={{ color:'#fbbf24' }}>愿?ъ쥌紐?Watchlist)</strong> ?щ’???깆옱?⑸땲??
                </div>
              </div>
              <button
                className="run-btn"
                disabled={screenLoading}
                onClick={fetchScreening}
                style={{ background:'linear-gradient(135deg, rgba(52,211,153,0.2), rgba(16,185,129,0.15))', borderColor:'rgba(52,211,153,0.4)', color:'#34d399', minWidth:'160px' }}
              >
                {screenLoading ? '???ㅽ겕由щ떇 以?(??30珥?...' : '?뵮 ?ъ옄?먯튃 ?ㅽ겕由щ떇 ?ㅽ뻾'}
              </button>
            </div>

            {/* ?ㅽ겕由щ떇 寃곌낵 */}
            {screenData && !screenLoading && (
              <div style={{ marginTop:'16px', borderTop:'1px solid rgba(255,255,255,0.08)', paddingTop:'16px' }}>
                {/* ?붿빟 諛곗? */}
                <div style={{ display:'flex', gap:'10px', flexWrap:'wrap', marginBottom:'14px' }}>
                  <span style={{ padding:'4px 12px', borderRadius:'8px', background:'rgba(52,211,153,0.15)', color:'#34d399', fontSize:'0.8rem', fontWeight:700 }}>
                    ??Watchlist ?밴꺽 {screenData.promoted_count}媛?
                  </span>
                  <span style={{ padding:'4px 12px', borderRadius:'8px', background:'rgba(255,255,255,0.06)', color:'rgba(255,255,255,0.5)', fontSize:'0.8rem' }}>
                    珥?遺꾩꽍 {screenData.total_screened}媛?
                  </span>
                  {screenData.promoted_count > 0 && (
                    <span style={{ padding:'4px 12px', borderRadius:'8px', background:'rgba(251,191,36,0.12)', color:'#fbbf24', fontSize:'0.8rem', fontWeight:600 }}>
                      ?럦 ?좊땲踰꾩뒪???먮룞 ?깆옱??
                    </span>
                  )}
                </div>

                {/* ?밴꺽 醫낅ぉ 移대뱶 */}
                {screenData.promoted?.length > 0 && (
                  <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))', gap:'10px' }}>
                    {screenData.promoted.map((item, idx) => (
                      <div key={idx} style={{ padding:'14px', borderRadius:'10px', background:'rgba(52,211,153,0.06)', border:'1px solid rgba(52,211,153,0.25)' }}>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'8px' }}>
                          <div>
                            <span style={{ fontSize:'0.95rem', fontWeight:700, color:'white' }}>{item.name}</span>
                            <span style={{ fontSize:'0.72rem', color:'rgba(255,255,255,0.4)', marginLeft:'6px' }}>{item.ticker}</span>
                          </div>
                          <span style={{ fontSize:'0.72rem', padding:'2px 8px', borderRadius:'6px', background:'rgba(52,211,153,0.2)', color:'#34d399', fontWeight:800 }}>
                            ?먯닔 {item.score}
                          </span>
                        </div>
                        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'6px', background:'rgba(0,0,0,0.2)', padding:'8px', borderRadius:'6px', marginBottom:'8px' }}>
                          <div style={{ textAlign:'center' }}>
                            <div style={{ fontSize:'0.58rem', color:'rgba(255,255,255,0.35)' }}>MDD</div>
                            <div style={{ fontSize:'0.82rem', fontWeight:700, color:'#34d399' }}>{item.mdd_pct?.toFixed(1)}%</div>
                          </div>
                          <div style={{ textAlign:'center' }}>
                            <div style={{ fontSize:'0.58rem', color:'rgba(255,255,255,0.35)' }}>ROE</div>
                            <div style={{ fontSize:'0.82rem', fontWeight:700, color:'#a78bfa' }}>{item.roe != null ? `${item.roe}%` : '-'}</div>
                          </div>
                          <div style={{ textAlign:'center' }}>
                            <div style={{ fontSize:'0.58rem', color:'rgba(255,255,255,0.35)' }}>OPM</div>
                            <div style={{ fontSize:'0.82rem', fontWeight:700, color:'#60a5fa' }}>{item.opm != null ? `${item.opm}%` : '-'}</div>
                          </div>
                        </div>
                        <div style={{ display:'flex', flexWrap:'wrap', gap:'4px' }}>
                          {item.tags?.map((tag, ti) => (
                            <span key={ti} style={{ fontSize:'0.62rem', padding:'2px 6px', borderRadius:'4px', background:'rgba(255,255,255,0.06)', color:'rgba(255,255,255,0.6)' }}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {screenData.promoted_count === 0 && (
                  <div style={{ textAlign:'center', padding:'20px', color:'rgba(255,255,255,0.4)', fontSize:'0.85rem' }}>
                    ?꾩옱 BUY_CANDIDATE 以??ъ옄?먯튃 湲곗????듦낵???좉퇋 醫낅ぉ???놁뒿?덈떎.<br/>
                    <span style={{ fontSize:'0.78rem', color:'rgba(255,255,255,0.3)' }}>湲곗〈 Watchlist 醫낅ぉ? ?대? ?깆옱?섏뼱 ?덉뒿?덈떎.</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 湲곗〈 ?먮룞 ?ㅼ틪 UI */}
          {scanLoading ? (

            <div className="glass-panel" style={{ padding:'60px', textAlign:'center' }}>
              <div style={{ fontSize:'1.3rem', color:'#fbbf24', marginBottom:'12px' }}>?뵇 ?ъ옄?먯튃 湲곕컲 ?먮룞 ?ㅼ틪 以?..</div>
              <div style={{ fontSize:'0.88rem', color:'rgba(255,255,255,0.5)' }}>
                80?ш컻 湲濡쒕쾶 ?곕웾二??꾨낫援곗쓣 yfinance濡??ㅼ틪 以묒엯?덈떎.<br/>??30~60珥??뚯슂?⑸땲??
              </div>
            </div>
          ) : !scanData ? (
            <div className="glass-panel" style={{ padding:'60px', textAlign:'center' }}>
              <div style={{ fontSize:'1.2rem', color:'rgba(255,255,255,0.6)', marginBottom:'16px' }}>
                ?뵇 4?④퀎 ?ъ옄?먯튃 湲곕컲?쇰줈 ?좉퇋 ?ъ옄 ?꾨낫 醫낅ぉ???먮룞?쇰줈 ?ㅼ틪?⑸땲??
              </div>
              <div style={{ fontSize:'0.85rem', color:'rgba(255,255,255,0.4)', marginBottom:'24px', lineHeight:'1.7' }}>
                ???대? ?붾줈???좊땲踰꾩뒪???녿뒗 醫낅ぉ留????br/>
                ??S&P500 + 肄붿뒪???곕웾二??꾨낫援?80醫낅ぉ ?ㅼ틪<br/>
                ??MDD -15% ?댁긽 議곗젙 + ?섏씡???낆젏??湲곗? ?꾪꽣留?br/>
                ???ъ옄?먯튃 ?먯닔 湲곕컲 ??궧 ?뺣젹
              </div>
              <button className="run-btn" onClick={fetchAutoScan} style={{ margin:'0 auto' }}>
                ?뵇 吏湲?諛붾줈 ?ㅼ틪 ?쒖옉
              </button>
            </div>
          ) : (
            <div>
              {/* ?ㅼ틪 ?붿빟 */}
              <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(200px, 1fr))', gap:'12px', marginBottom:'24px' }}>
                {[
                  { label:'?ㅼ틪 ???, value:`${scanData.scanned_tickers}媛?醫낅ぉ`, color:'#a5b4fc' },
                  { label:'?ъ옄 ?곹빀', value:`${scanData.scan_count}媛?諛쒓껄`, color:'#34d399' },
                  { label:'?꾪꽣 湲곗?', value:'MDD -15%+ / ?쒖킑 7??+', color:'#fbbf24' },
                ].map(s => (
                  <div key={s.label} className="glass-panel" style={{ padding:'16px', borderRadius:'12px', textAlign:'center' }}>
                    <div style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.4)', marginBottom:'6px' }}>{s.label}</div>
                    <div style={{ fontSize:'1.1rem', fontWeight:800, color:s.color }}>{s.value}</div>
                  </div>
                ))}
              </div>

              {scanData.scan_count === 0 ? (
                <div className="glass-panel" style={{ padding:'40px', textAlign:'center', color:'rgba(255,255,255,0.5)' }}>
                  ?꾩옱 ?ъ옄?먯튃 湲곗???異⑹”?섎뒗 ?좉퇋 醫낅ぉ???놁뒿?덈떎 (?쒖옣 怨좎젏 遺洹?
                </div>
              ) : (
                <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(360px, 1fr))', gap:'16px' }}>
                  {scanData.recommendations.map((item, idx) => {
                    const isBuy = item.signal?.includes('BUY_異붿쿇') || item.signal?.includes('DEEP_DISCOUNT');
                    const isDeep = item.signal?.includes('DEEP_DISCOUNT');
                    const borderC = isDeep ? 'rgba(59,130,246,0.5)' : isBuy ? 'rgba(16,185,129,0.4)' : 'rgba(251,191,36,0.3)';
                    const bgC = isDeep ? 'rgba(59,130,246,0.06)' : isBuy ? 'rgba(16,185,129,0.05)' : 'rgba(251,191,36,0.04)';
                    const signalColor = isDeep ? '#60a5fa' : isBuy ? '#34d399' : '#fbbf24';
                    return (
                      <div key={idx} className="glass-panel" style={{
                        padding:'20px', borderRadius:'14px',
                        border:`1.5px solid ${borderC}`,
                        background:`linear-gradient(135deg, ${bgC}, rgba(15,23,42,0.7))`
                      }}>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'10px' }}>
                          <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
                            <span style={{ fontSize:'1.2rem', fontWeight:900, color:'#fbbf24' }}>#{idx+1}</span>
                            <span style={{ fontSize:'0.72rem', padding:'2px 8px', borderRadius:'6px', background:'rgba(251,191,36,0.12)', color:'#fbbf24', fontWeight:700 }}>
                              ?먯닔 {item.score}pt
                            </span>
                          </div>
                          <span style={{ fontSize:'0.72rem', padding:'3px 10px', borderRadius:'12px', background:`${signalColor}22`, border:`1px solid ${signalColor}44`, color:signalColor, fontWeight:700 }}>
                            {item.signal}
                          </span>
                        </div>

                        <div style={{ display:'flex', alignItems:'baseline', gap:'8px', marginBottom:'4px' }}>
                          <h3 style={{ margin:0, fontSize:'1.1rem', color:'white', fontWeight:700 }}>{item.name}</h3>
                          <span style={{ fontSize:'0.82rem', color:'rgba(255,255,255,0.4)', fontWeight:600 }}>{item.ticker}</span>
                        </div>
                        <div style={{ fontSize:'0.75rem', color:'#a5b4fc', marginBottom:'12px' }}>
                          {item.sector} {item.industry ? `쨌 ${item.industry}` : ''}
                        </div>

                        {/* 媛寃?硫뷀듃由?*/}
                        <div style={{
                          display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'8px',
                          background:'rgba(0,0,0,0.25)', padding:'10px 12px', borderRadius:'8px', marginBottom:'12px',
                          border:'1px solid rgba(255,255,255,0.06)'
                        }}>
                          <div>
                            <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>?꾩옱媛</div>
                            <div style={{ fontSize:'0.85rem', color:'white', fontWeight:700 }}>
                              {item.ticker?.includes('.KS') || item.ticker?.includes('.KQ')
                                ? `${Math.round(item.current_price).toLocaleString()}??
                                : `$${item.current_price?.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>52二?怨좉?</div>
                            <div style={{ fontSize:'0.82rem', color:'rgba(255,255,255,0.7)', fontWeight:600 }}>
                              {item.ticker?.includes('.KS') || item.ticker?.includes('.KQ')
                                ? `${Math.round(item.high_52w).toLocaleString()}??
                                : `$${item.high_52w?.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.4)', marginBottom:'2px' }}>MDD</div>
                            <div style={{ fontSize:'0.92rem', fontWeight:800, color:signalColor }}>
                              {item.mdd_pct?.toFixed(1)}%
                            </div>
                          </div>
                        </div>

                        {/* ?섏씡??吏??*/}
                        <div style={{ display:'flex', gap:'6px', flexWrap:'wrap', marginBottom:'10px' }}>
                          {item.tags?.map((tag, ti) => (
                            <span key={ti} style={{ fontSize:'0.7rem', padding:'2px 7px', borderRadius:'5px', background:'rgba(99,102,241,0.12)', color:'#a5b4fc', fontWeight:600 }}>
                              {tag}
                            </span>
                          ))}
                        </div>

                        {/* ?щТ ?붿빟 */}
                        <div style={{ display:'flex', gap:'12px', fontSize:'0.73rem', color:'rgba(255,255,255,0.5)', flexWrap:'wrap' }}>
                          {item.roe != null && <span>ROE {item.roe}%</span>}
                          {item.op_margin != null && <span>OPM {item.op_margin}%</span>}
                          {item.profit_margin != null && <span>?쒖씠?듬쪧 {item.profit_margin}%</span>}
                          {item.pe_ratio != null && <span>PER {item.pe_ratio}x</span>}
                          {item.market_cap_b != null && <span>?쒖킑 ${item.market_cap_b}B</span>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ?? HomeDashboard ?????????????????????????????????????????????
const INDUSTRY_ICONS = {
  '?먯쑉二쇳뻾': '?슅', '濡쒕큸': '?쨼', '?먮꼫吏': '??, '?곗＜': '??',
  'AI': 'AI', '?꾨젰?명봽??: '?뵆', '?댁감?꾩?': '?뵅', '?⑤뵒諛붿씠?짞I': '?벑',
  '諛섎룄泥?: '?뭿', '寃뚯엫': '?렜', '?뷀꽣?뚯씤癒쇳듃': '?렗', '議곗꽑': '?슓',
};

function HomeDashboard({ reports, onSelect }) {
  return (
    <div style={{ animation:'fadeIn 0.4s ease' }}>
      {/* Hero */}
      <div style={{
        textAlign:'center', padding:'48px 24px 40px',
        background:'linear-gradient(180deg, rgba(59,130,246,0.06) 0%, transparent 100%)',
        borderBottom:'1px solid var(--border-color)', marginBottom:'36px',
      }}>
        <div style={{ display:'inline-flex', alignItems:'center', gap:'8px', background:'rgba(59,130,246,0.1)', border:'1px solid rgba(59,130,246,0.25)', borderRadius:'20px', padding:'6px 16px', marginBottom:'20px' }}>
          <span style={{ fontSize:'0.75rem', color:'var(--accent-blue)', fontWeight:600, letterSpacing:'0.05em' }}>ALPHA RESEARCH PLATFORM</span>
        </div>
        <h1 style={{ fontSize:'2.8rem', fontWeight:900, lineHeight:1.1, marginBottom:'16px', background:'linear-gradient(135deg,#f8fafc,#94a3b8)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent' }}>
          Industry Intelligence
        </h1>
        <p style={{ color:'var(--text-secondary)', fontSize:'1rem', maxWidth:'480px', margin:'0 auto', lineHeight:1.7 }}>
          {reports.length}媛??곗뾽??諛몃쪟泥댁씤, 湲곗뾽 ?щТ, AI 遺꾩꽍??br/>??怨녹뿉???뺤씤?섏꽭??
        </p>
      </div>

      {/* Stats Bar */}
      <div style={{ display:'flex', gap:'16px', justifyContent:'center', marginBottom:'40px', flexWrap:'wrap' }}>
        {[
          { label:'而ㅻ쾭由ъ? ?곗뾽', value:`${reports.length}媛?, color:'var(--accent-blue)' },
          { label:'異붿쟻 湲곗뾽', value:'100媛?', color:'var(--accent-purple)' },
          { label:'?щТ ?곗씠??, value:'?곌컙+遺꾧린', color:'var(--accent-green)' },
          { label:'AI 遺꾩꽍', value:'湲곗뾽蹂?留욎땄', color:'#f59e0b' },
        ].map(s => (
          <div key={s.label} style={{ textAlign:'center', padding:'16px 24px', borderRadius:'12px', background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.07)' }}>
            <div style={{ fontSize:'1.4rem', fontWeight:800, color:s.color }}>{s.value}</div>
            <div style={{ fontSize:'0.75rem', color:'var(--text-secondary)', marginTop:'2px' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Industry Cards Grid */}
      <div style={{ marginBottom:'12px', fontSize:'0.8rem', color:'var(--text-secondary)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.05em' }}>?곗뾽 由ы룷???좏깮</div>
      <div className="home-industry-grid">
        {reports.map((r, idx) => {
          const icon = INDUSTRY_ICONS[r.tag] || '?뱤';
          return (
            <div key={r.id}
              className="home-industry-card"
              onClick={() => onSelect(r.id)}
            >
              <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:'14px' }}>
                <div style={{ fontSize:'2rem', lineHeight:1 }}>{icon}</div>
                <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.25)', fontWeight:600, background:'rgba(255,255,255,0.04)', padding:'2px 8px', borderRadius:'8px' }}>#{idx+1}</div>
              </div>
              <div style={{ fontWeight:700, fontSize:'1.05rem', color:'var(--text-primary)', marginBottom:'6px' }}>{r.tag}</div>
              <div style={{ fontSize:'0.78rem', color:'var(--text-secondary)', lineHeight:1.5 }}>{r.title.replace(/ (?곗뾽|諛몃쪟泥댁씤|?꾨꼍|?ъ링|遺꾩꽍|媛?대뱶|由ы룷??Report|?꾩꽦).*/g,'').slice(0,40)}</div>
              <div style={{ marginTop:'14px', display:'flex', alignItems:'center', gap:'6px', color:'var(--accent-blue)', fontSize:'0.78rem', fontWeight:600 }}>
                <span>由ы룷??蹂닿린</span>
                <span style={{ fontSize:'0.9rem' }}>??/span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Tips */}
      <div style={{ marginTop:'40px', padding:'20px 24px', borderRadius:'12px', background:'rgba(59,130,246,0.04)', border:'1px solid rgba(59,130,246,0.12)' }}>
        <div style={{ fontSize:'0.8rem', color:'var(--accent-blue)', fontWeight:700, marginBottom:'12px' }}>?뮕 ?ъ슜 媛?대뱶</div>
        <div style={{ display:'flex', gap:'20px', flexWrap:'wrap' }}>
          {[
            { icon:'1截뤴깵', text:'?곗뾽 移대뱶 ?대┃ ??諛몃쪟泥댁씤 & 湲곗뾽 紐⑸줉 ?뺤씤' },
            { icon:'2截뤴깵', text:'湲곗뾽 移대뱶 ?대┃ ???щТ?쒗몴쨌李⑦듃쨌AI 遺꾩꽍 ?뺤씤' },
            { icon:'3截뤴깵', text:'AI 遺꾩꽍? ????AI媛 理쒖쟻 ?ы듃?대━??5醫낅ぉ 異붿쿇' },
          ].map(tip => (
            <div key={tip.text} style={{ display:'flex', gap:'8px', alignItems:'flex-start', fontSize:'0.82rem', color:'var(--text-secondary)', flex:'1 1 200px' }}>
              <span>{tip.icon}</span><span>{tip.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
