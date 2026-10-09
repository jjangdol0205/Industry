import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  BookOpen, Zap, ExternalLink, Search, X, Filter, Sparkles,
  RefreshCw, TrendingUp, TrendingDown, Layers, Shield,
  Activity, Globe, ChevronRight, CheckCircle2, Cpu, Award, Play
} from 'lucide-react';

import staticInsightsData from '../public/insights_data.json';

const BACKEND_HOST = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://industry-t5gt.onrender.com';
const API_BASE = `${BACKEND_HOST}/api`;

export const TICKER_NAME_MAP = {
  '402340.KS': 'SK스퀘어',
  '000660.KS': 'SK하이닉스',
  'TSLA': '테슬라',
  'UBER': '우버',
  'CELH': '셀시우스',
  'ENPH': '엔페이즈 에너지',
  'FLNC': '플루언스 에너지',
  'MBLY': '모빌아이',
  'UPST': '업스타트',
  'NVDA': '엔비디아',
  'MSFT': '마이크로소프트',
  'AAPL': '애플',
  'GOOGL': '알파벳',
  'META': '메타',
  'AMZN': '아마존',
};

// ── 1. Glossary Modal Component ──────────────────────────────────────────
export function GlossaryModal({ isOpen, onClose, initialTermId = null, onSelectCompany = null }) {
  const [activeCategory, setActiveCategory] = useState('ALL'); // 'ALL' | 'financial' | 'technology'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTermId, setSelectedTermId] = useState(initialTermId);

  useEffect(() => {
    if (initialTermId) {
      setSelectedTermId(initialTermId);
    }
  }, [initialTermId]);

  if (!isOpen) return null;

  const financialList = staticInsightsData?.glossaries?.financial || [];
  const techList = staticInsightsData?.glossaries?.technology || [];
  const allGlossaries = [...financialList, ...techList];

  const filteredGlossaries = allGlossaries.filter(item => {
    if (activeCategory === 'financial' && item.category !== 'financial') return false;
    if (activeCategory === 'technology' && item.category !== 'technology') return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (item.term && item.term.toLowerCase().includes(q)) ||
      (item.term_en && item.term_en.toLowerCase().includes(q)) ||
      (item.summary && item.summary.toLowerCase().includes(q)) ||
      (item.detailed_guide && item.detailed_guide.toLowerCase().includes(q)) ||
      (item.formula && item.formula.toLowerCase().includes(q))
    );
  });

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(10, 12, 16, 0.82)', backdropFilter: 'blur(8px)',
      zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '20px'
    }}>
      <div className="glass-panel" style={{
        width: '1000px', maxWidth: '95vw', maxHeight: '88vh',
        background: '#161922', border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '16px', display: 'flex', flexDirection: 'column',
        boxShadow: '0 24px 48px rgba(0, 0, 0, 0.6)', overflow: 'hidden'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '20px 24px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'linear-gradient(90deg, rgba(139, 92, 246, 0.12), rgba(59, 130, 246, 0.08))'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '10px',
              background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <BookOpen size={18} color="#fff" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#f3f4f6' }}>
                심층 금융·회계 및 핵심 기술 용어사전 (16선)
              </h3>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.8rem', color: '#9ca3af' }}>
                글로벌 투자 거장의 회계 철학과 실리콘밸리 테크 리더의 아키텍처 핵심 개념 해설
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.06)', border: 'none', borderRadius: '8px',
              width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: '#9ca3af', transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#fff'; e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#9ca3af'; e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'; }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Search & Category Filter Toolbar */}
        <div style={{
          padding: '16px 24px', borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap',
          background: 'rgba(20, 23, 31, 0.6)'
        }}>
          {/* Category Tabs */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => setActiveCategory('ALL')}
              style={{
                padding: '6px 14px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 600,
                cursor: 'pointer', border: '1px solid',
                background: activeCategory === 'ALL' ? 'rgba(139, 92, 246, 0.25)' : 'rgba(255, 255, 255, 0.04)',
                borderColor: activeCategory === 'ALL' ? '#8b5cf6' : 'rgba(255, 255, 255, 0.08)',
                color: activeCategory === 'ALL' ? '#c084fc' : '#9ca3af'
              }}
            >
              전체 ({allGlossaries.length})
            </button>
            <button
              onClick={() => setActiveCategory('financial')}
              style={{
                padding: '6px 14px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 600,
                cursor: 'pointer', border: '1px solid',
                background: activeCategory === 'financial' ? 'rgba(59, 130, 246, 0.25)' : 'rgba(255, 255, 255, 0.04)',
                borderColor: activeCategory === 'financial' ? '#3b82f6' : 'rgba(255, 255, 255, 0.08)',
                color: activeCategory === 'financial' ? '#60a5fa' : '#9ca3af'
              }}
            >
              📊 금융·회계 ({financialList.length})
            </button>
            <button
              onClick={() => setActiveCategory('technology')}
              style={{
                padding: '6px 14px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 600,
                cursor: 'pointer', border: '1px solid',
                background: activeCategory === 'technology' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.04)',
                borderColor: activeCategory === 'technology' ? '#10b981' : 'rgba(255, 255, 255, 0.08)',
                color: activeCategory === 'technology' ? '#34d399' : '#9ca3af'
              }}
            >
              ⚡ 첨단 기술 ({techList.length})
            </button>
          </div>

          {/* Search Input */}
          <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#6b7280' }} />
            <input
              type="text"
              placeholder="용어, 공식, 키워드 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '7px 12px 7px 34px',
                borderRadius: '8px', background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)', color: '#fff', fontSize: '0.82rem',
                outline: 'none'
              }}
            />
            {searchQuery && (
              <X
                size={14}
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af', cursor: 'pointer' }}
              />
            )}
          </div>
        </div>

        {/* Modal Body: Scrollable Glossaries List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredGlossaries.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#9ca3af' }}>
              검색된 용어가 없습니다.
            </div>
          ) : (
            filteredGlossaries.map(term => {
              const isFin = term.category === 'financial';
              return (
                <div
                  key={term.id}
                  id={`glossary-item-${term.id}`}
                  style={{
                    padding: '20px', borderRadius: '12px',
                    background: isFin ? 'rgba(30, 41, 59, 0.5)' : 'rgba(19, 42, 38, 0.4)',
                    border: `1px solid ${isFin ? 'rgba(59, 130, 246, 0.22)' : 'rgba(16, 185, 129, 0.22)'}`,
                    transition: 'all 0.2s'
                  }}
                >
                  {/* Title & Category Badge */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', fontWeight: 700,
                        background: isFin ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: isFin ? '#60a5fa' : '#34d399',
                        border: `1px solid ${isFin ? 'rgba(59, 130, 246, 0.4)' : 'rgba(16, 185, 129, 0.4)'}`
                      }}>
                        {isFin ? '📊 금융·회계' : '⚡ 첨단 기술'}
                      </span>
                      <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#f9fafb' }}>
                        {term.term}
                      </h4>
                    </div>
                    {term.term_en && (
                      <span style={{ fontSize: '0.8rem', color: '#9ca3af', fontStyle: 'italic' }}>
                        {term.term_en}
                      </span>
                    )}
                  </div>

                  {/* Formula Block if exists */}
                  {term.formula && term.formula !== 'N/A' && (
                    <div style={{
                      margin: '10px 0', padding: '8px 14px', borderRadius: '8px',
                      background: 'rgba(0, 0, 0, 0.35)', border: '1px dashed rgba(255, 255, 255, 0.15)',
                      fontFamily: 'monospace', fontSize: '0.82rem', color: isFin ? '#93c5fd' : '#6ee7b7',
                      display: 'flex', alignItems: 'center', gap: '8px'
                    }}>
                      <span style={{ color: '#9ca3af', fontSize: '0.75rem', fontWeight: 700 }}>수식/공식:</span>
                      <code>{term.formula}</code>
                    </div>
                  )}

                  {/* Core Summary */}
                  <p style={{ margin: '8px 0', fontSize: '0.88rem', color: '#e5e7eb', lineHeight: 1.55 }}>
                    {term.summary}
                  </p>

                  {/* Detailed Institutional Guide */}
                  {term.detailed_guide && (
                    <div style={{
                      marginTop: '10px', padding: '12px 14px', borderRadius: '8px',
                      background: 'rgba(255, 255, 255, 0.03)', borderLeft: `3px solid ${isFin ? '#3b82f6' : '#10b981'}`,
                      fontSize: '0.84rem', color: '#d1d5db', lineHeight: 1.6
                    }}>
                      <div style={{ fontWeight: 600, marginBottom: '4px', color: isFin ? '#60a5fa' : '#34d399', fontSize: '0.78rem' }}>
                        💡 기관 리서치 심층 해설
                      </div>
                      {term.detailed_guide}
                    </div>
                  )}

                  {/* Related Leaders & Tickers */}
                  <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                    {term.related_leaders && term.related_leaders.length > 0 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>주요 인물:</span>
                        {term.related_leaders.map((lead, idx) => (
                          <span key={idx} style={{
                            padding: '2px 8px', borderRadius: '4px', fontSize: '0.74rem',
                            background: 'rgba(255, 255, 255, 0.08)', color: '#e2e8f0'
                          }}>
                            {lead}
                          </span>
                        ))}
                      </div>
                    )}

                    {term.related_tickers && term.related_tickers.length > 0 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>연계 종목:</span>
                        {term.related_tickers.map((tk, idx) => {
                          const koName = TICKER_NAME_MAP[tk] || tk;
                          return (
                            <button
                              key={idx}
                              onClick={() => {
                                if (onSelectCompany) {
                                  onClose();
                                  onSelectCompany(tk, { id: tk, ticker: tk, name: koName });
                                }
                              }}
                              style={{
                                padding: '2px 8px', borderRadius: '4px', fontSize: '0.74rem', fontWeight: 600,
                                background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24',
                                border: '1px solid rgba(245, 158, 11, 0.3)', cursor: 'pointer',
                                transition: 'all 0.15s'
                              }}
                              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(245, 158, 11, 0.28)'; }}
                              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(245, 158, 11, 0.15)'; }}
                            >
                              #{koName} ({tk})
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// ── 2. Guru Letter Card Component ─────────────────────────────────────────
function GuruLetterCard({ letter, onOpenGlossary, onSelectCompany }) {
  const sentimentColor = letter.sentiment === 'BULLISH' ? '#10b981' : letter.sentiment === 'BEARISH' ? '#ef4444' : '#f59e0b';

  return (
    <div className="glass-panel" style={{
      background: 'rgba(28, 32, 42, 0.65)', border: '1px solid rgba(255, 255, 255, 0.08)',
      borderRadius: '14px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)', position: 'relative', overflow: 'hidden'
    }}>
      {/* Top Banner: Author, Firm & Date */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '44px', height: '44px', borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.35), rgba(59, 130, 246, 0.35))',
            border: '1px solid rgba(139, 92, 246, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1rem', fontWeight: 800, color: '#c084fc'
          }}>
            {letter.guru_name ? letter.guru_name.substring(0, 1) : 'G'}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#f3f4f6' }}>
                {letter.guru_name}
              </h4>
              <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
                ({letter.guru_name_en})
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#a78bfa', fontWeight: 600 }}>
              {letter.firm}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            padding: '3px 10px', borderRadius: '6px', fontSize: '0.74rem', fontWeight: 600,
            background: 'rgba(255, 255, 255, 0.05)', color: '#9ca3af', border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            📅 {letter.publish_date}
          </span>
          <span style={{
            padding: '3px 10px', borderRadius: '6px', fontSize: '0.74rem', fontWeight: 700,
            background: `${sentimentColor}15`, color: sentimentColor, border: `1px solid ${sentimentColor}40`
          }}>
            {letter.sentiment || 'BULLISH'}
          </span>
        </div>
      </div>

      {/* Official Letter Title */}
      <div>
        <h5 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', lineHeight: 1.45 }}>
          {letter.title}
        </h5>
        {letter.thesis_pillar && (
          <div style={{ marginTop: '6px', display: 'flex', gap: '6px' }}>
            <span style={{
              padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600,
              background: 'rgba(139, 92, 246, 0.15)', color: '#c084fc', border: '1px solid rgba(139, 92, 246, 0.3)'
            }}>
              🎯 {letter.thesis_pillar}
            </span>
            {letter.core_thesis && (
              <span style={{ fontSize: '0.78rem', color: '#9ca3af', alignSelf: 'center' }}>
                · {letter.core_thesis}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Verbatim English Quote in Stylized Blockquote */}
      <div style={{
        padding: '16px 20px', borderRadius: '10px',
        background: 'linear-gradient(135deg, rgba(20, 24, 34, 0.9), rgba(26, 30, 42, 0.9))',
        borderLeft: '4px solid #8b5cf6', border: '1px solid rgba(139, 92, 246, 0.25)',
        borderLeftWidth: '4px', position: 'relative'
      }}>
        <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.5px' }}>
          VERBATIM ENGLISH QUOTE
        </div>
        <p style={{
          margin: 0, fontStyle: 'italic', fontSize: '0.92rem', color: '#f3f4f6', lineHeight: 1.6,
          fontFamily: 'Georgia, serif'
        }}>
          "{letter.original_quote}"
        </p>
      </div>

      {/* Korean Quote Translation */}
      {letter.original_quote_ko && (
        <div style={{
          padding: '12px 16px', borderRadius: '8px',
          background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.6
        }}>
          <span style={{ fontWeight: 700, color: '#818cf8', marginRight: '6px' }}>원문 한글 번역:</span>
          {letter.original_quote_ko}
        </div>
      )}

      {/* Korean Summary & Synthesis */}
      <div style={{ fontSize: '0.88rem', color: '#d1d5db', lineHeight: 1.65 }}>
        <p style={{ margin: 0 }}>
          {letter.summary}
        </p>
      </div>

      {/* Deep Concept Guide Action */}
      {letter.deep_concept_guide && (
        <div style={{
          padding: '12px 14px', borderRadius: '8px',
          background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '240px' }}>
            <BookOpen size={16} color="#60a5fa" />
            <span style={{ fontSize: '0.82rem', color: '#bfdbfe' }}>
              <strong>심층 금융·회계 개념:</strong> {letter.deep_concept_guide}
            </span>
          </div>
          <button
            onClick={() => onOpenGlossary && onOpenGlossary()}
            style={{
              padding: '4px 10px', borderRadius: '6px', fontSize: '0.74rem', fontWeight: 600,
              background: '#3b82f6', color: '#fff', border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', transition: 'all 0.15s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#2563eb'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '#3b82f6'; }}
          >
            용어사전 해설 보기 <ChevronRight size={13} />
          </button>
        </div>
      )}

      {/* Ticker Implication Badges */}
      {letter.related_tickers && letter.related_tickers.length > 0 && (
        <div style={{
          paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex', flexDirection: 'column', gap: '8px'
        }}>
          <div style={{ fontSize: '0.76rem', color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase' }}>
            PORTFOLIO TICKER IMPLICATIONS (포털 보유·관심 종목 연계)
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {letter.related_tickers.map(tk => {
              const impObj = letter.ticker_implications ? letter.ticker_implications[tk] : null;
              const impSentiment = impObj?.sentiment || 'BULLISH';
              const sColor = impSentiment === 'BULLISH' ? '#10b981' : impSentiment === 'BEARISH' ? '#ef4444' : '#f59e0b';
              const koName = TICKER_NAME_MAP[tk] || tk;

              return (
                <div
                  key={tk}
                  onClick={() => {
                    if (onSelectCompany) {
                      onSelectCompany(tk, { id: tk, ticker: tk, name: koName });
                    }
                  }}
                  style={{
                    padding: '6px 12px', borderRadius: '8px', cursor: 'pointer',
                    background: 'rgba(255, 255, 255, 0.04)', border: `1px solid ${sColor}45`,
                    display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.15s'
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = `${sColor}18`; e.currentTarget.style.borderColor = sColor; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)'; e.currentTarget.style.borderColor = `${sColor}45`; }}
                  title={impObj?.implication || `${koName} 연계 시사점`}
                >
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#f3f4f6' }}>
                    #{koName} ({tk})
                  </span>
                  <span style={{
                    fontSize: '0.68rem', fontWeight: 800, padding: '1px 5px', borderRadius: '4px',
                    background: `${sColor}25`, color: sColor
                  }}>
                    {impSentiment}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* External Action Button */}
      {letter.url && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px' }}>
          <a
            href={letter.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: '7px 14px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 600,
              background: 'rgba(255, 255, 255, 0.05)', color: '#a78bfa', border: '1px solid rgba(139, 92, 246, 0.3)',
              textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(139, 92, 246, 0.18)'; e.currentTarget.style.color = '#c084fc'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'; e.currentTarget.style.color = '#a78bfa'; }}
          >
            <ExternalLink size={14} /> 📑 공식 서한/메모 원문 바로가기
          </a>
        </div>
      )}
    </div>
  );
}

// ── 3. Tech Leader Interview Card Component ───────────────────────────────
function TechInterviewCard({ interview, onOpenGlossary, onSelectCompany }) {
  const isYoutube = interview.url && interview.url.includes('youtube.com');

  return (
    <div className="glass-panel" style={{
      background: 'rgba(24, 32, 38, 0.65)', border: '1px solid rgba(255, 255, 255, 0.08)',
      borderRadius: '14px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)', position: 'relative', overflow: 'hidden'
    }}>
      {/* Top Banner: Leader, Company & Media Source */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '44px', height: '44px', borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.35), rgba(6, 182, 212, 0.35))',
            border: '1px solid rgba(16, 185, 129, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1rem', fontWeight: 800, color: '#34d399'
          }}>
            {interview.leader_name ? interview.leader_name.substring(0, 1) : 'T'}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#f3f4f6' }}>
                {interview.leader_name}
              </h4>
              <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
                ({interview.leader_name_en})
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 600 }}>
              {interview.company} · {interview.role}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            padding: '3px 10px', borderRadius: '6px', fontSize: '0.74rem', fontWeight: 600,
            background: 'rgba(255, 255, 255, 0.05)', color: '#9ca3af', border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            📅 {interview.publish_date}
          </span>
          <span style={{
            padding: '3px 10px', borderRadius: '6px', fontSize: '0.74rem', fontWeight: 700,
            background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.35)',
            display: 'flex', alignItems: 'center', gap: '4px'
          }}>
            <Play size={10} fill="#f87171" /> {interview.media_source || 'YouTube'}
          </span>
        </div>
      </div>

      {/* Interview Title & Thesis */}
      <div>
        <h5 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', lineHeight: 1.45 }}>
          {interview.title}
        </h5>
        {interview.thesis_pillar && (
          <div style={{ marginTop: '6px', display: 'flex', gap: '6px' }}>
            <span style={{
              padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600,
              background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)'
            }}>
              ⚡ {interview.thesis_pillar}
            </span>
            {interview.core_thesis && (
              <span style={{ fontSize: '0.78rem', color: '#9ca3af', alignSelf: 'center' }}>
                · {interview.core_thesis}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Supply Chain Impact Tag */}
      {interview.supply_chain_impact && (
        <div style={{
          padding: '10px 14px', borderRadius: '8px',
          background: 'linear-gradient(90deg, rgba(6, 182, 212, 0.12), rgba(16, 185, 129, 0.08))',
          border: '1px solid rgba(6, 182, 212, 0.35)', display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <Zap size={16} color="#22d3ee" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: '0.82rem', color: '#e0f2fe', lineHeight: 1.5 }}>
            <strong style={{ color: '#38bdf8' }}>공급망 영향도 (Supply Chain):</strong> {interview.supply_chain_impact}
          </span>
        </div>
      )}

      {/* Verbatim English Quote */}
      <div style={{
        padding: '16px 20px', borderRadius: '10px',
        background: 'linear-gradient(135deg, rgba(16, 26, 32, 0.9), rgba(20, 34, 40, 0.9))',
        borderLeft: '4px solid #10b981', border: '1px solid rgba(16, 185, 129, 0.25)',
        borderLeftWidth: '4px', position: 'relative'
      }}>
        <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#34d399', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.5px' }}>
          VERBATIM KEY QUOTATION
        </div>
        <p style={{
          margin: 0, fontStyle: 'italic', fontSize: '0.92rem', color: '#f3f4f6', lineHeight: 1.6,
          fontFamily: 'Georgia, serif'
        }}>
          "{interview.original_quote}"
        </p>
      </div>

      {/* Korean Quote Translation */}
      {interview.original_quote_ko && (
        <div style={{
          padding: '12px 16px', borderRadius: '8px',
          background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.6
        }}>
          <span style={{ fontWeight: 700, color: '#34d399', marginRight: '6px' }}>핵심 발언 한글 번역:</span>
          {interview.original_quote_ko}
        </div>
      )}

      {/* Korean Summary & Strategic Context */}
      <div style={{ fontSize: '0.88rem', color: '#d1d5db', lineHeight: 1.65 }}>
        <p style={{ margin: 0 }}>
          {interview.summary}
        </p>
      </div>

      {/* Tech Concept Guide */}
      {interview.tech_concept_guide && (
        <div style={{
          padding: '12px 14px', borderRadius: '8px',
          background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '240px' }}>
            <Cpu size={16} color="#34d399" />
            <span style={{ fontSize: '0.82rem', color: '#d1fae5' }}>
              <strong>핵심 기술 개념:</strong> {interview.tech_concept_guide}
            </span>
          </div>
          <button
            onClick={() => onOpenGlossary && onOpenGlossary()}
            style={{
              padding: '4px 10px', borderRadius: '6px', fontSize: '0.74rem', fontWeight: 600,
              background: '#10b981', color: '#fff', border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', transition: 'all 0.15s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#059669'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '#10b981'; }}
          >
            기술사전 해설 보기 <ChevronRight size={13} />
          </button>
        </div>
      )}

      {/* Ticker Implication Badges */}
      {interview.related_tickers && interview.related_tickers.length > 0 && (
        <div style={{
          paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex', flexDirection: 'column', gap: '8px'
        }}>
          <div style={{ fontSize: '0.76rem', color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase' }}>
            SUPPLY CHAIN & PORTFOLIO TICKERS (공급망 수혜 & 포털 관심 종목)
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {interview.related_tickers.map(tk => {
              const impObj = interview.ticker_implications ? interview.ticker_implications[tk] : null;
              const impSentiment = impObj?.sentiment || 'BULLISH';
              const sColor = impSentiment === 'BULLISH' ? '#10b981' : impSentiment === 'BEARISH' ? '#ef4444' : '#f59e0b';
              const koName = TICKER_NAME_MAP[tk] || tk;

              return (
                <div
                  key={tk}
                  onClick={() => {
                    if (onSelectCompany) {
                      onSelectCompany(tk, { id: tk, ticker: tk, name: koName });
                    }
                  }}
                  style={{
                    padding: '6px 12px', borderRadius: '8px', cursor: 'pointer',
                    background: 'rgba(255, 255, 255, 0.04)', border: `1px solid ${sColor}45`,
                    display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.15s'
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = `${sColor}18`; e.currentTarget.style.borderColor = sColor; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)'; e.currentTarget.style.borderColor = `${sColor}45`; }}
                  title={impObj?.implication || `${koName} 연계 시사점`}
                >
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#f3f4f6' }}>
                    #{koName} ({tk})
                  </span>
                  <span style={{
                    fontSize: '0.68rem', fontWeight: 800, padding: '1px 5px', borderRadius: '4px',
                    background: `${sColor}25`, color: sColor
                  }}>
                    {impSentiment}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* External Video Action Button */}
      {interview.url && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px' }}>
          <a
            href={interview.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: '7px 14px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 600,
              background: 'rgba(239, 68, 68, 0.12)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.35)',
              textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)'; e.currentTarget.style.color = '#fff'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.12)'; e.currentTarget.style.color = '#f87171'; }}
          >
            <ExternalLink size={14} /> ▶️ 유튜브 영상 바로가기
          </a>
        </div>
      )}
    </div>
  );
}

// ── 4. Main InsightCenterView Component ────────────────────────────────────
export default function InsightCenterView({ onSelectCompany }) {
  // Sub-Tab: 'gurus' | 'tech-leaders'
  const [subTab, setSubTab] = useState('gurus');

  // Filters
  const [selectedGuru, setSelectedGuru] = useState('ALL');
  const [selectedLeader, setSelectedLeader] = useState('ALL');
  const [selectedThesis, setSelectedThesis] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals & Status
  const [glossaryModalOpen, setGlossaryModalOpen] = useState(false);
  const [activeGlossaryTermId, setActiveGlossaryTermId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  // Feed Data (Multi-tier loaded)
  const [data, setData] = useState(staticInsightsData);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadInsightsData();
  }, []);

  const loadInsightsData = async () => {
    setLoading(true);
    // 1st tier: API
    try {
      const res = await axios.get(`${API_BASE}/v1/insights/feed`, { timeout: 4000 });
      if (res.data && res.data.status === 'success') {
        setData(prev => ({
          ...prev,
          ...res.data,
          guru_letters: res.data.guru_letters || prev.guru_letters,
          tech_interviews: res.data.tech_interviews || prev.tech_interviews,
          gurus: res.data.gurus || prev.gurus,
          tech_leaders: res.data.tech_leaders || prev.tech_leaders,
        }));
        setLoading(false);
        return;
      }
    } catch (e) {
      try {
        const res2 = await axios.get(`${API_BASE}/insights/feed`, { timeout: 4000 });
        if (res2.data && res2.data.status === 'success') {
          setData(prev => ({ ...prev, ...res2.data }));
          setLoading(false);
          return;
        }
      } catch (e2) {}
    }

    // 2nd tier: Static JSON file fetch
    try {
      const staticRes = await axios.get(`./insights_data.json?t=${Date.now()}`);
      if (staticRes.data && staticRes.data.status === 'success') {
        setData(staticRes.data);
        setLoading(false);
        return;
      }
    } catch (err) {
      // 3rd tier: Bundled static import fallback
      if (staticInsightsData) {
        setData(staticInsightsData);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setToastMessage('인사이트 데이터 동기화 파이프라인 가동 중...');
    try {
      const res = await axios.post(`${API_BASE}/v1/insights/refresh`, {}, { timeout: 8000 });
      setToastMessage('최신 서한 및 인터뷰 데이터 갱신 완료!');
      await loadInsightsData();
    } catch (e) {
      setToastMessage('동기화 완료 (로컬 캐시 최신 상태 유지)');
      await loadInsightsData();
    } finally {
      setRefreshing(false);
      setTimeout(() => setToastMessage(''), 3500);
    }
  };

  const openGlossary = (termId = null) => {
    setActiveGlossaryTermId(termId);
    setGlossaryModalOpen(true);
  };

  // Lists
  const guruLetters = data?.guru_letters || [];
  const techInterviews = data?.tech_interviews || [];
  const gurus = data?.gurus || [];
  const techLeaders = data?.tech_leaders || data?.leaders || [];
  const theses = data?.theses || [];

  // Filtered Guru Letters
  const filteredGuruLetters = useMemo(() => {
    return guruLetters.filter(item => {
      // Guru filter
      if (selectedGuru !== 'ALL') {
        const nameKo = item.guru_name || '';
        const nameEn = item.guru_name_en || '';
        if (nameKo !== selectedGuru && nameEn !== selectedGuru) return false;
      }
      // Thesis filter
      if (selectedThesis !== 'ALL') {
        const p = item.thesis_pillar || '';
        if (!p.includes(selectedThesis)) return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const str = `${item.guru_name} ${item.guru_name_en} ${item.title} ${item.summary} ${item.original_quote} ${item.deep_concept_guide} ${(item.related_tickers || []).join(' ')}`.toLowerCase();
        if (!str.includes(q)) return false;
      }
      return true;
    });
  }, [guruLetters, selectedGuru, selectedThesis, searchQuery]);

  // Filtered Tech Interviews
  const filteredTechInterviews = useMemo(() => {
    return techInterviews.filter(item => {
      // Tech Leader filter
      if (selectedLeader !== 'ALL') {
        const nameKo = item.leader_name || '';
        const nameEn = item.leader_name_en || '';
        if (nameKo !== selectedLeader && nameEn !== selectedLeader) return false;
      }
      // Thesis filter
      if (selectedThesis !== 'ALL') {
        const p = item.thesis_pillar || '';
        if (!p.includes(selectedThesis)) return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const str = `${item.leader_name} ${item.leader_name_en} ${item.company} ${item.title} ${item.summary} ${item.original_quote} ${item.supply_chain_impact} ${item.tech_concept_guide} ${(item.related_tickers || []).join(' ')}`.toLowerCase();
        if (!str.includes(q)) return false;
      }
      return true;
    });
  }, [techInterviews, selectedLeader, selectedThesis, searchQuery]);

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px 20px', minHeight: '85vh' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed', top: '24px', right: '24px', zIndex: 10000,
          background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff',
          padding: '12px 20px', borderRadius: '10px', boxShadow: '0 10px 25px rgba(0,0,0,0.4)',
          fontWeight: 600, fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <Sparkles size={16} /> {toastMessage}
        </div>
      )}

      {/* Header & Hero Section */}
      <div style={{
        marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        flexWrap: 'wrap', gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.8rem' }}>💡</span>
            <h1 style={{
              margin: 0, fontSize: '1.75rem', fontWeight: 800,
              background: 'linear-gradient(135deg, #ffffff, #c084fc, #60a5fa)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
            }}>
              인사이트 센터 (Thought Leaders & Gurus Hub)
            </h1>
          </div>
          <p style={{ margin: '6px 0 0 0', color: '#9ca3af', fontSize: '0.92rem' }}>
            세계적 투자 거장 7인의 공식 서한 & 글로벌 AI·테크 리더 7인의 인터뷰 레이더 (3대 테제 및 포털 유니버스 종목 연계)
          </p>
        </div>

        {/* Global Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => openGlossary()}
            style={{
              padding: '9px 16px', borderRadius: '10px', fontSize: '0.84rem', fontWeight: 700,
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.25), rgba(59, 130, 246, 0.25))',
              border: '1px solid #8b5cf6', color: '#c084fc', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '7px', transition: 'all 0.2s',
              boxShadow: '0 4px 12px rgba(139, 92, 246, 0.2)'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'linear-gradient(135deg, rgba(139, 92, 246, 0.4), rgba(59, 130, 246, 0.4))'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'linear-gradient(135deg, rgba(139, 92, 246, 0.25), rgba(59, 130, 246, 0.25))'; }}
          >
            <BookOpen size={16} color="#c084fc" />
            <span>📖 심층 금융·기술 용어사전 (16선)</span>
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              padding: '9px 16px', borderRadius: '10px', fontSize: '0.84rem', fontWeight: 700,
              background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#f3f4f6', cursor: refreshing ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', gap: '7px', transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => { if (!refreshing) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'; }}
            onMouseLeave={(e) => { if (!refreshing) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'; }}
          >
            <RefreshCw size={15} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            <span>{refreshing ? '동기화 중...' : '🔄 인사이트 최신화'}</span>
          </button>
        </div>
      </div>

      {/* 3 Core Theses Overview Banner */}
      <div className="glass-panel" style={{
        marginBottom: '24px', padding: '16px 20px', borderRadius: '14px',
        background: 'linear-gradient(135deg, rgba(20, 24, 34, 0.75), rgba(28, 34, 48, 0.75))',
        border: '1px solid rgba(255, 255, 255, 0.08)'
      }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', marginBottom: '10px' }}>
          3 CORE THESIS PILLARS (인사이트 센터 3대 핵심 테제 축)
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
          {theses.map(t => (
            <div
              key={t.id}
              onClick={() => setSelectedThesis(selectedThesis === t.title ? 'ALL' : t.title)}
              style={{
                padding: '12px 16px', borderRadius: '10px', cursor: 'pointer',
                background: selectedThesis === t.title ? 'rgba(139, 92, 246, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                border: selectedThesis === t.title ? '1px solid #8b5cf6' : '1px solid rgba(255, 255, 255, 0.06)',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.92rem', color: '#f3f4f6' }}>
                  {t.id === 'models_and_safety' ? '🤖 ' : t.id === 'semiconductor_and_energy_infrastructure' ? '⚡ ' : '💼 '}
                  {t.title}
                </span>
                <span style={{ fontSize: '0.72rem', color: '#9ca3af' }}>{t.title_en}</span>
              </div>
              <p style={{ margin: 0, fontSize: '0.78rem', color: '#9ca3af', lineHeight: 1.45, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {t.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Dual Sub-Tabs Header */}
      <div style={{
        display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        paddingBottom: '12px'
      }}>
        <button
          onClick={() => { setSubTab('gurus'); setSelectedLeader('ALL'); }}
          style={{
            padding: '10px 22px', borderRadius: '10px', fontSize: '0.95rem', fontWeight: 700,
            cursor: 'pointer', border: '1px solid',
            background: subTab === 'gurus' ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.3), rgba(59, 130, 246, 0.2))' : 'rgba(255, 255, 255, 0.03)',
            borderColor: subTab === 'gurus' ? '#8b5cf6' : 'rgba(255, 255, 255, 0.08)',
            color: subTab === 'gurus' ? '#c084fc' : '#9ca3af',
            display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s'
          }}
        >
          <BookOpen size={18} color={subTab === 'gurus' ? '#c084fc' : '#9ca3af'} />
          <span>투자 거장의 서한</span>
          <span style={{
            fontSize: '0.72rem', padding: '2px 7px', borderRadius: '10px',
            background: subTab === 'gurus' ? 'rgba(139, 92, 246, 0.4)' : 'rgba(255, 255, 255, 0.1)',
            color: '#fff'
          }}>
            7인 / {guruLetters.length}편
          </span>
        </button>

        <button
          onClick={() => { setSubTab('tech-leaders'); setSelectedGuru('ALL'); }}
          style={{
            padding: '10px 22px', borderRadius: '10px', fontSize: '0.95rem', fontWeight: 700,
            cursor: 'pointer', border: '1px solid',
            background: subTab === 'tech-leaders' ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.3), rgba(6, 182, 212, 0.2))' : 'rgba(255, 255, 255, 0.03)',
            borderColor: subTab === 'tech-leaders' ? '#10b981' : 'rgba(255, 255, 255, 0.08)',
            color: subTab === 'tech-leaders' ? '#34d399' : '#9ca3af',
            display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s'
          }}
        >
          <Zap size={18} color={subTab === 'tech-leaders' ? '#34d399' : '#9ca3af'} />
          <span>AI & 테크 리더 레이더</span>
          <span style={{
            fontSize: '0.72rem', padding: '2px 7px', borderRadius: '10px',
            background: subTab === 'tech-leaders' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.1)',
            color: '#fff'
          }}>
            7인 / {techInterviews.length}건
          </span>
        </button>
      </div>

      {/* Filter Bar: Gurus/Leaders chips, Thesis filter, and Search */}
      <div className="glass-panel" style={{
        padding: '16px 20px', borderRadius: '12px', marginBottom: '24px',
        background: 'rgba(22, 26, 36, 0.7)', border: '1px solid rgba(255, 255, 255, 0.07)',
        display: 'flex', flexDirection: 'column', gap: '14px'
      }}>
        {/* Row 1: Person Chips Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', color: '#9ca3af', fontWeight: 700, minWidth: '60px' }}>
            {subTab === 'gurus' ? '거장 선택:' : '리더 선택:'}
          </span>

          <button
            onClick={() => subTab === 'gurus' ? setSelectedGuru('ALL') : setSelectedLeader('ALL')}
            style={{
              padding: '5px 12px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 600,
              cursor: 'pointer', border: '1px solid',
              background: (subTab === 'gurus' ? selectedGuru === 'ALL' : selectedLeader === 'ALL') ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.04)',
              borderColor: (subTab === 'gurus' ? selectedGuru === 'ALL' : selectedLeader === 'ALL') ? '#fff' : 'rgba(255, 255, 255, 0.08)',
              color: (subTab === 'gurus' ? selectedGuru === 'ALL' : selectedLeader === 'ALL') ? '#fff' : '#9ca3af'
            }}
          >
            전체 ({subTab === 'gurus' ? '7 Gurus' : '7 Leaders'})
          </button>

          {subTab === 'gurus' ? (
            gurus.map(g => (
              <button
                key={g.guru_name || g.name_ko}
                onClick={() => setSelectedGuru(selectedGuru === (g.guru_name || g.name_ko) ? 'ALL' : (g.guru_name || g.name_ko))}
                style={{
                  padding: '5px 12px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 600,
                  cursor: 'pointer', border: '1px solid',
                  background: selectedGuru === (g.guru_name || g.name_ko) ? 'rgba(139, 92, 246, 0.3)' : 'rgba(255, 255, 255, 0.03)',
                  borderColor: selectedGuru === (g.guru_name || g.name_ko) ? '#8b5cf6' : 'rgba(255, 255, 255, 0.08)',
                  color: selectedGuru === (g.guru_name || g.name_ko) ? '#c084fc' : '#d1d5db',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}
              >
                <span>{g.name_ko || g.guru_name}</span>
                <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>({g.firm})</span>
              </button>
            ))
          ) : (
            techLeaders.map(l => (
              <button
                key={l.leader_name || l.name_ko}
                onClick={() => setSelectedLeader(selectedLeader === (l.leader_name || l.name_ko) ? 'ALL' : (l.leader_name || l.name_ko))}
                style={{
                  padding: '5px 12px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 600,
                  cursor: 'pointer', border: '1px solid',
                  background: selectedLeader === (l.leader_name || l.name_ko) ? 'rgba(16, 185, 129, 0.3)' : 'rgba(255, 255, 255, 0.03)',
                  borderColor: selectedLeader === (l.leader_name || l.name_ko) ? '#10b981' : 'rgba(255, 255, 255, 0.08)',
                  color: selectedLeader === (l.leader_name || l.name_ko) ? '#34d399' : '#d1d5db',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}
              >
                <span>{l.name_ko || l.leader_name}</span>
                <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>({l.company})</span>
              </button>
            ))
          )}
        </div>

        {/* Row 2: Thesis & Search Inputs */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Thesis filter buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.78rem', color: '#9ca3af', fontWeight: 700 }}>테제:</span>
            <button
              onClick={() => setSelectedThesis('ALL')}
              style={{
                padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                background: selectedThesis === 'ALL' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.1)', color: selectedThesis === 'ALL' ? '#fff' : '#9ca3af'
              }}
            >
              전체
            </button>
            <button
              onClick={() => setSelectedThesis(selectedThesis === '모델·안전성' ? 'ALL' : '모델·안전성')}
              style={{
                padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                background: selectedThesis === '모델·안전성' ? 'rgba(139, 92, 246, 0.25)' : 'rgba(255, 255, 255, 0.03)',
                border: selectedThesis === '모델·안전성' ? '1px solid #8b5cf6' : '1px solid rgba(255, 255, 255, 0.1)',
                color: selectedThesis === '모델·안전성' ? '#c084fc' : '#9ca3af'
              }}
            >
              🤖 모델·안전성
            </button>
            <button
              onClick={() => setSelectedThesis(selectedThesis === '반도체·에너지 인프라' ? 'ALL' : '반도체·에너지 인프라')}
              style={{
                padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                background: selectedThesis === '반도체·에너지 인프라' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.03)',
                border: selectedThesis === '반도체·에너지 인프라' ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.1)',
                color: selectedThesis === '반도체·에너지 인프라' ? '#34d399' : '#9ca3af'
              }}
            >
              ⚡ 반도체·에너지 인프라
            </button>
            <button
              onClick={() => setSelectedThesis(selectedThesis === '플랫폼 비즈니스' ? 'ALL' : '플랫폼 비즈니스')}
              style={{
                padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                background: selectedThesis === '플랫폼 비즈니스' ? 'rgba(59, 130, 246, 0.25)' : 'rgba(255, 255, 255, 0.03)',
                border: selectedThesis === '플랫폼 비즈니스' ? '1px solid #3b82f6' : '1px solid rgba(255, 255, 255, 0.1)',
                color: selectedThesis === '플랫폼 비즈니스' ? '#60a5fa' : '#9ca3af'
              }}
            >
              💼 플랫폼 비즈니스
            </button>
          </div>

          {/* Search Bar */}
          <div style={{ flex: 1, minWidth: '240px', position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#6b7280' }} />
            <input
              type="text"
              placeholder="인물, 명언, 한글 요약, 종목(#000660.KS) 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '8px 12px 8px 34px',
                borderRadius: '8px', background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)', color: '#fff', fontSize: '0.82rem',
                outline: 'none'
              }}
            />
            {searchQuery && (
              <X
                size={14}
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af', cursor: 'pointer' }}
              />
            )}
          </div>
        </div>
      </div>

      {/* Content Feed Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {subTab === 'gurus' ? (
          filteredGuruLetters.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#9ca3af' }}>
              조건에 맞는 거장 서한이 없습니다.
            </div>
          ) : (
            filteredGuruLetters.map(letter => (
              <GuruLetterCard
                key={letter.letter_id || letter.id}
                letter={letter}
                onOpenGlossary={() => openGlossary()}
                onSelectCompany={onSelectCompany}
              />
            ))
          )
        ) : (
          filteredTechInterviews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#9ca3af' }}>
              조건에 맞는 테크 리더 인터뷰가 없습니다.
            </div>
          ) : (
            filteredTechInterviews.map(interview => (
              <TechInterviewCard
                key={interview.interview_id || interview.id}
                interview={interview}
                onOpenGlossary={() => openGlossary()}
                onSelectCompany={onSelectCompany}
              />
            ))
          )
        )}
      </div>

      {/* Deep Glossary Modal */}
      <GlossaryModal
        isOpen={glossaryModalOpen}
        onClose={() => setGlossaryModalOpen(false)}
        initialTermId={activeGlossaryTermId}
        onSelectCompany={onSelectCompany}
      />
    </div>
  );
}

// ── 5. GuruTechInsightsWidget for CompanyView Integration ──────────────────
export function GuruTechInsightsWidget({ ticker, companyName, onSelectCompany }) {
  const [tickerData, setTickerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (!ticker) {
      setLoading(false);
      return;
    }
    loadTickerInsights(ticker);
  }, [ticker]);

  const loadTickerInsights = async (targetTicker) => {
    setLoading(true);
    const tkUpper = targetTicker.toUpperCase();
    const tkNorm = tkUpper.endsWith('.KS') ? tkUpper : `${tkUpper}.KS`;

    // 1. Try FastAPI endpoint
    try {
      const res = await axios.get(`${API_BASE}/v1/insights/ticker/${targetTicker}`, { timeout: 3500 });
      if (res.data && res.data.status === 'success' && res.data.total > 0) {
        setTickerData(res.data);
        setLoading(false);
        return;
      }
    } catch (e) {
      try {
        const res2 = await axios.get(`${API_BASE}/insights/ticker/${targetTicker}`, { timeout: 3500 });
        if (res2.data && res2.data.status === 'success' && res2.data.total > 0) {
          setTickerData(res2.data);
          setLoading(false);
          return;
        }
      } catch (e2) {}
    }

    // 2. Fallback to client-side static JSON
    try {
      const allLetters = staticInsightsData?.guru_letters || [];
      const allInterviews = staticInsightsData?.tech_interviews || [];

      const matchedLetters = allLetters.filter(l =>
        (l.related_tickers || []).some(t => t.toUpperCase() === tkUpper || t.toUpperCase() === tkNorm)
      );
      const matchedInterviews = allInterviews.filter(i =>
        (i.related_tickers || []).some(t => t.toUpperCase() === tkUpper || t.toUpperCase() === tkNorm)
      );

      const total = matchedLetters.length + matchedInterviews.length;
      if (total > 0) {
        setTickerData({
          status: 'success',
          ticker: targetTicker,
          total: total,
          guru_letters: matchedLetters,
          tech_interviews: matchedInterviews
        });
      } else {
        setTickerData(null);
      }
    } catch (err) {
      setTickerData(null);
    } finally {
      setLoading(false);
    }
  };

  if (!ticker || (!loading && (!tickerData || tickerData.total === 0))) {
    return null;
  }

  const letters = tickerData?.guru_letters || [];
  const interviews = tickerData?.tech_interviews || [];
  const total = tickerData?.total || 0;

  return (
    <section style={{ marginBottom: '32px' }}>
      <div className="glass-panel" style={{
        background: 'linear-gradient(135deg, rgba(20, 24, 34, 0.85), rgba(28, 34, 48, 0.85))',
        border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '14px', padding: '20px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)'
      }}>
        {/* Widget Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: expanded ? '16px' : 0, cursor: 'pointer'
        }}
        onClick={() => setExpanded(!expanded)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <Sparkles size={16} color="#fff" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#f3f4f6' }}>
                💡 투자 거장 & 테크 리더 인사이트 연동 ({total}건)
              </h3>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.78rem', color: '#9ca3af' }}>
                {companyName || ticker} 종목과 직결되는 세계적 투자 거장의 철학과 AI 테크 리더의 코멘트
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontSize: '0.74rem', padding: '3px 8px', borderRadius: '6px',
              background: 'rgba(139, 92, 246, 0.2)', color: '#c084fc', border: '1px solid rgba(139, 92, 246, 0.35)',
              fontWeight: 700
            }}>
              거장 {letters.length}건 · 테크 {interviews.length}건
            </span>
            <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>
              {expanded ? '▲ 접기' : '▼ 펼치기'}
            </span>
          </div>
        </div>

        {/* Expanded Content List */}
        {expanded && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Guru Letters Linkages */}
            {letters.map((letter, idx) => {
              const tkUpper = ticker.toUpperCase();
              const tkNorm = tkUpper.endsWith('.KS') ? tkUpper : `${tkUpper}.KS`;
              const imp = letter.ticker_implications?.[tkUpper] || letter.ticker_implications?.[tkNorm];
              const sColor = imp?.sentiment === 'BULLISH' ? '#10b981' : imp?.sentiment === 'BEARISH' ? '#ef4444' : '#f59e0b';

              return (
                <div key={idx} style={{
                  padding: '14px 16px', borderRadius: '10px',
                  background: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.25)',
                  display: 'flex', flexDirection: 'column', gap: '6px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700,
                        background: 'rgba(139, 92, 246, 0.25)', color: '#c084fc'
                      }}>
                        🏛️ 투자 거장
                      </span>
                      <strong style={{ fontSize: '0.9rem', color: '#f3f4f6' }}>
                        {letter.guru_name} ({letter.firm})
                      </strong>
                    </div>
                    {imp?.sentiment && (
                      <span style={{
                        fontSize: '0.7rem', fontWeight: 800, padding: '2px 6px', borderRadius: '4px',
                        background: `${sColor}20`, color: sColor, border: `1px solid ${sColor}40`
                      }}>
                        {imp.sentiment}
                      </span>
                    )}
                  </div>

                  {imp?.implication && (
                    <div style={{ fontSize: '0.84rem', color: '#e2e8f0', lineHeight: 1.5, fontWeight: 500 }}>
                      👉 <strong>종목 시사점:</strong> {imp.implication}
                    </div>
                  )}

                  {letter.original_quote && (
                    <div style={{
                      fontSize: '0.78rem', color: '#cbd5e1', fontStyle: 'italic',
                      padding: '6px 10px', borderRadius: '6px', background: 'rgba(0, 0, 0, 0.25)',
                      borderLeft: '3px solid #8b5cf6'
                    }}>
                      "{letter.original_quote}"
                    </div>
                  )}
                </div>
              );
            })}

            {/* Tech Interviews Linkages */}
            {interviews.map((interview, idx) => {
              const tkUpper = ticker.toUpperCase();
              const tkNorm = tkUpper.endsWith('.KS') ? tkUpper : `${tkUpper}.KS`;
              const imp = interview.ticker_implications?.[tkUpper] || interview.ticker_implications?.[tkNorm];
              const sColor = imp?.sentiment === 'BULLISH' ? '#10b981' : imp?.sentiment === 'BEARISH' ? '#ef4444' : '#f59e0b';

              return (
                <div key={idx} style={{
                  padding: '14px 16px', borderRadius: '10px',
                  background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)',
                  display: 'flex', flexDirection: 'column', gap: '6px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700,
                        background: 'rgba(16, 185, 129, 0.25)', color: '#34d399'
                      }}>
                        ⚡ 테크 리더
                      </span>
                      <strong style={{ fontSize: '0.9rem', color: '#f3f4f6' }}>
                        {interview.leader_name} ({interview.company})
                      </strong>
                    </div>
                    {imp?.sentiment && (
                      <span style={{
                        fontSize: '0.7rem', fontWeight: 800, padding: '2px 6px', borderRadius: '4px',
                        background: `${sColor}20`, color: sColor, border: `1px solid ${sColor}40`
                      }}>
                        {imp.sentiment}
                      </span>
                    )}
                  </div>

                  {imp?.implication && (
                    <div style={{ fontSize: '0.84rem', color: '#e2e8f0', lineHeight: 1.5, fontWeight: 500 }}>
                      👉 <strong>공급망/기술 시사점:</strong> {imp.implication}
                    </div>
                  )}

                  {interview.supply_chain_impact && (
                    <div style={{ fontSize: '0.78rem', color: '#6ee7b7' }}>
                      🔗 <strong>공급망 파급력:</strong> {interview.supply_chain_impact}
                    </div>
                  )}

                  {interview.url && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                      <a
                        href={interview.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: '0.74rem', color: '#f87171', textDecoration: 'none',
                          display: 'flex', alignItems: 'center', gap: '4px'
                        }}
                      >
                        <Play size={10} fill="#f87171" /> 유튜브 영상 보기 <ExternalLink size={11} />
                      </a>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
