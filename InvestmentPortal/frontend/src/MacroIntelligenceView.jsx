import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  TrendingUp, TrendingDown, Activity, Globe, RefreshCw,
  ExternalLink, Layers, Shield, Zap, AlertTriangle,
  CheckCircle2, ArrowUpRight, ArrowDownRight, Clock,
  Filter, FileText, ChevronRight, BarChart2, BarChart3,
  DollarSign, Percent
} from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Line, Area,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  Legend, ReferenceLine
} from 'recharts';

import staticMacroData from '../public/macro_intelligence_data.json';

const BACKEND_HOST = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://industry-t5gt.onrender.com';
const API_BASE = `${BACKEND_HOST}/api`;

export default function MacroIntelligenceView({ onSelectCompany }) {
  const [data, setData] = useState(staticMacroData);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedSource, setSelectedSource] = useState('ALL');
  const [selectedSentiment, setSelectedSentiment] = useState('ALL');
  const [activePerspectives, setActivePerspectives] = useState({}); // { [reportId]: 'discount' | 'factor' | 'sector' | 'fx' }

  // Load from backend API with fallback
  useEffect(() => {
    let isMounted = true;
    const fetchMacro = async () => {
      try {
        setLoading(true);
        const res = await axios.get(`${API_BASE}/v1/macro/summary`, { timeout: 4000 });
        if (isMounted && res.data && res.data.status === 'success') {
          setData(res.data);
        }
      } catch (err) {
        // Fallback to static data
        if (isMounted) {
          setData(staticMacroData);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchMacro();
    return () => { isMounted = false; };
  }, []);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const res = await axios.post(`${API_BASE}/v1/macro/refresh`, {}, { timeout: 8000 });
      if (res.data && res.data.status === 'success') {
        setData(res.data);
      }
    } catch (err) {
      console.warn("Macro refresh API failed, using static data fallback", err);
    } finally {
      setRefreshing(false);
    }
  };

  const regime = data?.regime || staticMacroData.regime;
  const indicators = data?.indicators || staticMacroData.indicators;
  const reports = data?.reports || staticMacroData.reports || [];

  const filteredReports = useMemo(() => {
    return reports.filter(r => {
      if (selectedSource !== 'ALL' && r.source !== selectedSource) return false;
      if (selectedSentiment !== 'ALL' && r.sentiment !== selectedSentiment) return false;
      return true;
    });
  }, [reports, selectedSource, selectedSentiment]);

  const togglePerspective = (reportId, key) => {
    setActivePerspectives(prev => ({
      ...prev,
      [reportId]: key
    }));
  };

  const getSourceBadgeColor = (source) => {
    switch (source) {
      case 'FOMC': return { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.4)', text: '#60a5fa' };
      case 'NY Fed': return { bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.4)', text: '#34d399' };
      case 'St. Louis Fed': return { bg: 'rgba(139, 92, 246, 0.15)', border: 'rgba(139, 92, 246, 0.4)', text: '#c084fc' };
      default: return { bg: 'rgba(255, 255, 255, 0.1)', border: 'rgba(255, 255, 255, 0.2)', text: '#e5e7eb' };
    }
  };

  const getSentimentBadge = (sentiment) => {
    switch (sentiment) {
      case 'DOVISH':
        return { label: '비둘기파 (완화적)', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' };
      case 'HAWKISH':
        return { label: '매파 (긴축적)', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' };
      default:
        return { label: '중립 (Neutral)', color: '#9ca3af', bg: 'rgba(156, 163, 175, 0.15)' };
    }
  };

  const getSectorRatingBadge = (rating) => {
    switch (rating) {
      case 'OVERWEIGHT':
        return { label: '비중확대 (Overweight)', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.35)' };
      case 'UNDERWEIGHT':
        return { label: '비중축소 (Underweight)', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.12)', border: 'rgba(239, 68, 68, 0.35)' };
      default:
        return { label: '중립 (Neutral)', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.12)', border: 'rgba(251, 191, 36, 0.35)' };
    }
  };

  return (
    <div className="macro-view" style={{ padding: '24px 28px', maxWidth: '1440px', margin: '0 auto', color: 'var(--text-primary)' }}>
      {/* ── Page Header ── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        borderBottom: '1px solid var(--border-color)', paddingBottom: '20px', marginBottom: '28px', flexWrap: 'wrap', gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{
              background: 'linear-gradient(135deg, #0ea5e9, #3b82f6)',
              color: 'white', padding: '4px 14px', borderRadius: '20px', fontSize: '0.82rem', fontWeight: 700, letterSpacing: '0.03em'
            }}>
              FED & MACRO INTELLIGENCE
            </span>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              연준 공식 의사록 & 연은 싱크탱크 정량 분석
            </span>
          </div>
          <h2 style={{ fontSize: '1.9rem', fontWeight: 800, margin: '4px 0 6px 0', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Globe size={28} color="#38bdf8" />
            거시경제 & 연준 리서치 인텔리전스
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', margin: 0 }}>
            FOMC 성명서·의사록, 뉴욕·세인트루이스 연은 연구보고서와 10Y/2Y 국채 수익률 곡선 및 거시 유동성(Net Liquidity) 실시간 종합 진단
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '9px 18px', borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(59, 130, 246, 0.2))',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              color: '#38bdf8', fontWeight: 600, fontSize: '0.88rem',
              cursor: refreshing ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              opacity: refreshing ? 0.7 : 1
            }}
          >
            <RefreshCw size={15} className={refreshing ? 'spin' : ''} />
            {refreshing ? '지표 갱신 중...' : '지표 새로고침'}
          </button>
        </div>
      </div>

      {/* ── Section 1: Rate & Liquidity Dashboard (4 KPI Cards) ── */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Activity size={20} color="#38bdf8" />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>거시 유동성 및 금리 상태 게이지 (Rate & Liquidity Dashboard)</h3>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '6px' }}>
            기준일: {indicators?.indicator_date || '2026-10-09'}
          </span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
          marginBottom: '20px'
        }}>
          {/* Card 1: 10Y/2Y Yield & Spread */}
          <div className="glass-panel" style={{ padding: '20px 22px', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '14px', background: 'rgba(15, 23, 42, 0.65)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', fontWeight: 600 }}>10Y / 2Y 국채금리 & 스프레드</span>
              <span style={{
                fontSize: '0.75rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px',
                background: indicators?.yield_spread_10y_2y >= 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: indicators?.yield_spread_10y_2y >= 0 ? '#10b981' : '#ef4444',
                border: `1px solid ${indicators?.yield_spread_10y_2y >= 0 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
              }}>
                {indicators?.curve_shift_type || 'BULL_STEEPENER'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '10px' }}>
              <span style={{ fontSize: '2rem', fontWeight: 800, color: indicators?.yield_spread_10y_2y >= 0 ? '#10b981' : '#ef4444' }}>
                {indicators?.yield_spread_10y_2y > 0 ? `+${indicators.yield_spread_10y_2y}%p` : `${indicators?.yield_spread_10y_2y}%p`}
              </span>
              <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                ({Math.round((indicators?.yield_spread_10y_2y || 0) * 100)} bp)
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', color: 'var(--text-secondary)' }}>
              <div>10년물 금리: <strong style={{ color: 'var(--text-primary)' }}>{indicators?.us_10y_yield}%</strong></div>
              <div>2년물 금리: <strong style={{ color: 'var(--text-primary)' }}>{indicators?.us_2y_yield}%</strong></div>
            </div>
          </div>

          {/* Card 2: Fed Policy Stance & Neutral Rate */}
          <div className="glass-panel" style={{ padding: '20px 22px', border: '1px solid rgba(139, 92, 246, 0.2)', borderRadius: '14px', background: 'rgba(15, 23, 42, 0.65)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', fontWeight: 600 }}>연준 기준금리 & 통화 긴축 격차</span>
              <span style={{
                fontSize: '0.75rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px',
                background: 'rgba(139, 92, 246, 0.15)', color: '#c084fc', border: '1px solid rgba(139, 92, 246, 0.3)'
              }}>
                {indicators?.policy_stance || 'RESTRICTIVE'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '10px' }}>
              <span style={{ fontSize: '2rem', fontWeight: 800, color: '#c084fc' }}>
                {indicators?.fed_funds_rate}%
              </span>
              <span style={{ fontSize: '0.85rem', color: '#a78bfa' }}>
                긴축 격차: +{indicators?.policy_restrictiveness_gap}%p
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', color: 'var(--text-secondary)' }}>
              <div>실질 중립금리(r*): <strong style={{ color: 'var(--text-primary)' }}>{indicators?.real_neutral_rate_r_star}%</strong></div>
              <div>근원 PCE 물가: <strong style={{ color: 'var(--text-primary)' }}>{indicators?.core_pce_inflation}%</strong></div>
            </div>
          </div>

          {/* Card 3: Net Liquidity & Reserve Buffer */}
          <div className="glass-panel" style={{ padding: '20px 22px', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '14px', background: 'rgba(15, 23, 42, 0.65)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', fontWeight: 600 }}>연준 순유동성 (Net Liquidity)</span>
              <span style={{
                fontSize: '0.75rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px',
                background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)'
              }}>
                {indicators?.on_rrp_buffer_status || 'ADEQUATE_BUFFER'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '10px' }}>
              <span style={{ fontSize: '2rem', fontWeight: 800, color: '#34d399' }}>
                ${indicators?.net_liquidity_billion ? Number(indicators.net_liquidity_billion).toLocaleString() : '6,113.6'}B
              </span>
              <span style={{ fontSize: '0.82rem', color: (indicators?.net_liquidity_change_30d || 0) >= 0 ? '#10b981' : '#f87171' }}>
                30d: {indicators?.net_liquidity_change_30d > 0 ? `+${indicators.net_liquidity_change_30d}B` : `${indicators?.net_liquidity_change_30d}B`}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', color: 'var(--text-secondary)' }}>
              <div>TGA 잔고: <strong style={{ color: 'var(--text-primary)' }}>${indicators?.tga_balance_billion}B</strong></div>
              <div>ON RRP 역레포: <strong style={{ color: 'var(--text-primary)' }}>${indicators?.on_rrp_balance_billion}B</strong></div>
            </div>
          </div>

          {/* Card 4: FX & Market Sentiment */}
          <div className="glass-panel" style={{ padding: '20px 22px', border: '1px solid rgba(245, 158, 11, 0.2)', borderRadius: '14px', background: 'rgba(15, 23, 42, 0.65)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', fontWeight: 600 }}>환율 및 변동성 지수 (FX & VIX)</span>
              <span style={{
                fontSize: '0.75rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px',
                background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)'
              }}>
                안정 국면
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '10px' }}>
              <span style={{ fontSize: '2rem', fontWeight: 800, color: '#fbbf24' }}>
                ₩{indicators?.usdkrw_exchange_rate?.toLocaleString() || '1,342.0'}
              </span>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                USD/KRW
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', color: 'var(--text-secondary)' }}>
              <div>달러 인덱스 (DXY): <strong style={{ color: 'var(--text-primary)' }}>{indicators?.dxy_index} pt</strong></div>
              <div>변동성 VIX: <strong style={{ color: 'var(--text-primary)' }}>{indicators?.vix_index} pt</strong></div>
            </div>
          </div>
        </div>

        {/* ── 30-Day Yield Curve & Net Liquidity Interactive Chart ── */}
        {indicators?.history && indicators.history.length > 0 && (
          <div className="glass-panel" style={{ padding: '22px 24px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(15, 23, 42, 0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  30일 시계열 추이: 10Y-2Y 수익률 곡선 스프레드 및 순유동성
                </h4>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  수익률 역전 해소(Un-inversion) 및 연준 순유동성(Fed Assets - TGA - RRP) 변동 궤적
                </p>
              </div>
              <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '12px', height: '3px', background: '#38bdf8', borderRadius: '2px' }} />
                  스프레드 (%p)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '12px', height: '3px', background: '#10b981', borderRadius: '2px' }} />
                  순유동성 ($B)
                </span>
              </div>
            </div>

            <div style={{ height: '240px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={indicators.history} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis
                    dataKey="indicator_date"
                    stroke="rgba(255,255,255,0.3)"
                    fontSize={11}
                    tickFormatter={(val) => val.slice(5)}
                  />
                  <YAxis
                    yAxisId="left"
                    stroke="#38bdf8"
                    fontSize={11}
                    domain={[-0.2, 0.4]}
                    tickFormatter={(val) => `${val}%p`}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke="#10b981"
                    fontSize={11}
                    domain={['dataMin - 20', 'dataMax + 20']}
                    tickFormatter={(val) => `$${Math.round(val)}B`}
                  />
                  <RechartsTooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', fontSize: '0.82rem' }}
                    labelFormatter={(label) => `일자: ${label}`}
                  />
                  <ReferenceLine yAxisId="left" y={0} stroke="#ef4444" strokeDasharray="3 3" label={{ value: '역전 기준 (0%p)', fill: '#ef4444', fontSize: 10 }} />
                  <Line yAxisId="left" type="monotone" dataKey="yield_spread_10y_2y" name="10Y-2Y 스프레드" stroke="#38bdf8" strokeWidth={2.5} dot={false} />
                  <Area yAxisId="right" type="monotone" dataKey="net_liquidity_billion" name="순유동성($B)" stroke="#10b981" fill="rgba(16, 185, 129, 0.12)" strokeWidth={1.5} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* ── Section 2: Macro Regime & Factor / Sector Allocation Matrix ── */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Layers size={20} color="#a855f7" />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>거시 국면(Macro Regime) & 팩터·섹터 배분 매트릭스</h3>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '6px' }}>
            켄 피셔 100년 백테스트 & 연은 RIMP 모델 기반
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px', marginBottom: '20px' }}>
          {/* Regime Summary Card */}
          <div className="glass-panel" style={{ padding: '22px 24px', borderRadius: '14px', border: '1px solid rgba(168, 85, 247, 0.25)', background: 'rgba(15, 23, 42, 0.65)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <span style={{ fontSize: '0.76rem', color: '#c084fc', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  현재 거시경제 국면 (Current Regime)
                </span>
                <h4 style={{ margin: '4px 0 0 0', fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {regime?.current_regime}
                </h4>
              </div>
              <span style={{
                fontSize: '0.75rem', fontWeight: 700, padding: '4px 10px', borderRadius: '6px',
                background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)'
              }}>
                {regime?.ken_fisher_signal}
              </span>
            </div>

            <p style={{ fontSize: '0.88rem', color: 'rgba(255,255,255,0.8)', lineHeight: 1.55, marginBottom: '16px' }}>
              {regime?.regime_description}
            </p>

            <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '10px', padding: '12px 16px', marginBottom: '14px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Zap size={13} color="#eab308" />
                <span>기업 이질성 RIMP 모델 (Restricted Intermediate Model) 분석:</span>
              </div>
              <div style={{ fontSize: '0.84rem', color: '#e2e8f0', lineHeight: 1.5 }}>
                {regime?.rimp_model_analysis}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.84rem', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
              <div>
                증시 P/E 멀티플 전망: <strong style={{ color: (regime?.pe_expansion_compression_pct || 0) >= 0 ? '#10b981' : '#f87171' }}>
                  {regime?.pe_expansion_compression_pct > 0 ? `+${regime.pe_expansion_compression_pct}%` : `${regime?.pe_expansion_compression_pct}%`}
                  ({regime?.per_multiple_outlook})
                </strong>
              </div>
              <div>
                우량주 기대 알파 스프레드: <strong style={{ color: '#38bdf8' }}>+{regime?.factor_allocations?.quality_alpha_spread_pct}%p</strong>
              </div>
            </div>
          </div>

          {/* Factor Allocation Card */}
          <div className="glass-panel" style={{ padding: '22px 24px', borderRadius: '14px', border: '1px solid rgba(59, 130, 246, 0.25)', background: 'rgba(15, 23, 42, 0.65)' }}>
            <span style={{ fontSize: '0.76rem', color: '#60a5fa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              권고 포트폴리오 팩터 배분 (Factor Allocation)
            </span>
            <h4 style={{ margin: '4px 0 16px 0', fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              Core 60% : Satellite 15% : Cash 25%
            </h4>

            {/* Visual Bar */}
            <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', marginBottom: '18px', background: 'rgba(255,255,255,0.1)' }}>
              <div style={{ width: `${regime?.factor_allocations?.core_pct || 60}%`, background: 'linear-gradient(90deg, #3b82f6, #60a5fa)', title: 'Core 우량주 60%' }} />
              <div style={{ width: `${regime?.factor_allocations?.satellite_pct || 15}%`, background: 'linear-gradient(90deg, #8b5cf6, #c084fc)', title: 'Satellite 성장주 15%' }} />
              <div style={{ width: `${regime?.factor_allocations?.cash_pct || 25}%`, background: 'linear-gradient(90deg, #10b981, #34d399)', title: '방어 현금 25%' }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#3b82f6' }} />
                Core 우량 대형주: {regime?.factor_allocations?.core_pct}%
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#8b5cf6' }} />
                Satellite 알파: {regime?.factor_allocations?.satellite_pct}%
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
                방어적 현금: {regime?.factor_allocations?.cash_pct}%
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.84rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(16, 185, 129, 0.08)', padding: '8px 12px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                <strong style={{ color: '#34d399', whiteSpace: 'nowrap' }}>선호 팩터:</strong>
                <span style={{ color: '#e2e8f0' }}>{regime?.factor_allocations?.favored}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(239, 68, 68, 0.08)', padding: '8px 12px', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                <strong style={{ color: '#f87171', whiteSpace: 'nowrap' }}>비선호 팩터:</strong>
                <span style={{ color: '#e2e8f0' }}>{regime?.factor_allocations?.unfavored}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Sector Sensitivity Matrix */}
        <div className="glass-panel" style={{ padding: '22px 24px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(15, 23, 42, 0.5)' }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart3 size={18} color="#38bdf8" />
            거시 환경 국면별 6대 섹터 민감도 및 투자 의견 매트릭스
          </h4>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {regime?.sector_matrix?.map((sec, idx) => {
              const badge = getSectorRatingBadge(sec.rating);
              return (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${badge.border}`,
                    borderRadius: '10px',
                    padding: '14px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.94rem', color: '#f8fafc' }}>
                      {sec.sector}
                    </div>
                    <span style={{
                      fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '4px',
                      background: badge.bg, color: badge.color, border: `1px solid ${badge.border}`
                    }}>
                      {sec.rating}
                    </span>
                  </div>

                  <p style={{ margin: '0 0 10px 0', fontSize: '0.82rem', color: 'rgba(255, 255, 255, 0.7)', lineHeight: 1.45 }}>
                    {sec.rationale}
                  </p>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', color: 'var(--text-secondary)', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                    <span>민감도: <strong style={{ color: '#e2e8f0' }}>{sec.sensitivity}</strong></span>
                    <span>포지션 스코어: <strong style={{ color: sec.score > 0 ? '#10b981' : sec.score < 0 ? '#ef4444' : '#fbbf24' }}>{sec.score > 0 ? `+${sec.score}` : sec.score}</strong></span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Section 3: Fed & Regional Fed Research Feed ── */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={20} color="#10b981" />
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>연은 리서치 & FOMC 시계열 타임라인</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              (총 {filteredReports.length}건 리포트)
            </span>
          </div>

          {/* Filters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {/* Source Filter */}
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '3px', border: '1px solid rgba(255,255,255,0.08)' }}>
              {['ALL', 'FOMC', 'NY Fed', 'St. Louis Fed'].map((src) => (
                <button
                  key={src}
                  onClick={() => setSelectedSource(src)}
                  style={{
                    padding: '5px 12px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 600,
                    background: selectedSource === src ? '#3b82f6' : 'transparent',
                    color: selectedSource === src ? '#fff' : 'var(--text-secondary)',
                    border: 'none', cursor: 'pointer', transition: 'all 0.15s'
                  }}
                >
                  {src === 'ALL' ? '출처: 전체' : src}
                </button>
              ))}
            </div>

            {/* Sentiment Filter */}
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '3px', border: '1px solid rgba(255,255,255,0.08)' }}>
              {[
                { id: 'ALL', label: '성향: 전체' },
                { id: 'DOVISH', label: '비둘기파' },
                { id: 'NEUTRAL', label: '중립' },
                { id: 'HAWKISH', label: '매파' }
              ].map((st) => (
                <button
                  key={st.id}
                  onClick={() => setSelectedSentiment(st.id)}
                  style={{
                    padding: '5px 12px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 600,
                    background: selectedSentiment === st.id ? '#10b981' : 'transparent',
                    color: selectedSentiment === st.id ? '#fff' : 'var(--text-secondary)',
                    border: 'none', cursor: 'pointer', transition: 'all 0.15s'
                  }}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Report Cards Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {filteredReports.map((report) => {
            const srcColor = getSourceBadgeColor(report.source);
            const sentimentBadge = getSentimentBadge(report.sentiment);
            const currentTab = activePerspectives[report.id] || 'discount';

            return (
              <div
                key={report.id || report.report_id}
                className="glass-panel"
                style={{
                  padding: '24px 26px',
                  borderRadius: '16px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  background: 'rgba(15, 23, 42, 0.7)',
                  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)'
                }}
              >
                {/* Header row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{
                      padding: '4px 10px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 700,
                      background: srcColor.bg, color: srcColor.text, border: `1px solid ${srcColor.border}`
                    }}>
                      {report.source}
                    </span>
                    <span style={{
                      padding: '4px 10px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 600,
                      background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)'
                    }}>
                      {report.category}
                    </span>
                    <span style={{
                      padding: '4px 10px', borderRadius: '6px', fontSize: '0.76rem', fontWeight: 700,
                      background: sentimentBadge.bg, color: sentimentBadge.color
                    }}>
                      {sentimentBadge.label}
                    </span>
                    {report.pe_impact_pct_estimate !== null && report.pe_impact_pct_estimate !== undefined && (
                      <span style={{
                        padding: '4px 10px', borderRadius: '6px', fontSize: '0.76rem', fontWeight: 700,
                        background: report.pe_impact_pct_estimate >= 0 ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                        color: report.pe_impact_pct_estimate >= 0 ? '#10b981' : '#ef4444'
                      }}>
                        P/E 영향: {report.pe_impact_pct_estimate > 0 ? `+${report.pe_impact_pct_estimate}%` : `${report.pe_impact_pct_estimate}%`}
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    <Clock size={13} />
                    <span>{report.publish_date}</span>
                    {report.url && (
                      <a
                        href={report.url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: 'flex', alignItems: 'center', gap: '4px',
                          color: '#38bdf8', textDecoration: 'none', marginLeft: '6px',
                          background: 'rgba(56, 189, 248, 0.1)', padding: '3px 8px', borderRadius: '4px'
                        }}
                      >
                        원문 <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>

                {/* Title */}
                <h4 style={{ margin: '0 0 10px 0', fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', lineHeight: 1.35 }}>
                  {report.title}
                </h4>

                {/* Summary */}
                <p style={{ margin: '0 0 16px 0', fontSize: '0.92rem', color: 'rgba(255, 255, 255, 0.85)', lineHeight: 1.6 }}>
                  {report.summary}
                </p>

                {/* Key Takeaways */}
                {report.key_takeaways && report.key_takeaways.length > 0 && (
                  <div style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: '10px',
                    padding: '12px 18px',
                    marginBottom: '18px'
                  }}>
                    <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#38bdf8', marginBottom: '8px' }}>
                      핵심 결론 및 테이크어웨이 (Key Takeaways):
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {report.key_takeaways.map((point, pIdx) => (
                        <li key={pIdx} style={{ fontSize: '0.84rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 4 Core Perspectives Interactive Tabs */}
                <div style={{
                  background: 'rgba(10, 15, 26, 0.6)',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  overflow: 'hidden',
                  marginBottom: '16px'
                }}>
                  {/* Perspective Tab Buttons */}
                  <div style={{
                    display: 'flex',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    overflowX: 'auto'
                  }}>
                    {[
                      { key: 'discount', label: '① 매크로 할인율 & 밸류에이션' },
                      { key: 'factor', label: '② 스타일·팩터 영향' },
                      { key: 'sector', label: '③ 섹터 및 산업 영향' },
                      { key: 'fx', label: '④ 외환 및 외국인 수급' }
                    ].map(tab => {
                      const isActive = currentTab === tab.key;
                      return (
                        <button
                          key={tab.key}
                          onClick={() => togglePerspective(report.id, tab.key)}
                          style={{
                            padding: '10px 16px',
                            background: isActive ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                            color: isActive ? '#38bdf8' : 'var(--text-secondary)',
                            fontWeight: isActive ? 700 : 500,
                            fontSize: '0.82rem',
                            border: 'none',
                            borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                            cursor: 'pointer',
                            whiteSpace: 'nowrap',
                            transition: 'all 0.15s'
                          }}
                        >
                          {tab.label}
                        </button>
                      );
                    })}
                  </div>

                  {/* Perspective Content */}
                  <div style={{ padding: '16px 20px', fontSize: '0.88rem', color: '#e2e8f0', lineHeight: 1.65 }}>
                    {currentTab === 'discount' && (
                      <div>
                        {report.perspectives?.discount_rate_impact || report.discount_rate_impact}
                      </div>
                    )}
                    {currentTab === 'factor' && (
                      <div>
                        {report.perspectives?.factor_style_impact || report.factor_style_impact}
                      </div>
                    )}
                    {currentTab === 'sector' && (
                      <div>
                        {report.perspectives?.sector_industry_impact || report.sector_industry_impact}
                      </div>
                    )}
                    {currentTab === 'fx' && (
                      <div>
                        {report.perspectives?.fx_liquidity_flow_impact || report.fx_liquidity_flow_impact}
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer Tags */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    {report.favored_factor && (
                      <span>선호: <strong style={{ color: '#34d399' }}>{report.favored_factor}</strong></span>
                    )}
                    {report.unfavored_factor && (
                      <span>비선호: <strong style={{ color: '#f87171' }}>{report.unfavored_factor}</strong></span>
                    )}
                  </div>

                  {report.overweight_sectors && report.overweight_sectors.length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>비중확대 섹터:</span>
                      {report.overweight_sectors.map((sec, sIdx) => (
                        <span key={sIdx} style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#34d399', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                          {sec}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
