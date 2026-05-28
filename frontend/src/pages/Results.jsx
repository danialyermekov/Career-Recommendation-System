import { useState, useRef, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import styles from './Results.module.css'
import {
  clearRecommendationHistory,
  getRecommendationHistory,
  getRecommendationState,
  saveCourseFilterPreferences,
  saveRoadmapProgress,
  sendChatStream,
  transcribeVoice,
} from '../utils/api';
/* ─── Constants ─────────────────────────────────────────────── */
const CATEGORY_ICONS = {
  programming: '</>',
  libraries: '☰',
  analyst_tools: '◈',
  cloud: '☁',
  databases: '◫',
  webframeworks: '◻',
  other: '◎',
  os: '⊞',
}
const BAR_COLORS = {
  skill_match:   '#5b8dee',
  profile_match: '#9b6ddf',
  trend_score:   '#4caf82',
  market_share:  '#f0943a',
}
const BAR_TOOLTIPS = {
  ru: {
    skill_match:   'Насколько ваши технические навыки соответствуют требованиям профессии',
    profile_match: 'Насколько ваш профиль подходит для этого карьерного пути',
    trend_score:   'Тренд рыночного спроса на данную профессию',
    market_share:  'Доля рынка вакансий, занимаемая этой профессией',
  },
  en: {
    skill_match:   'How well your technical skills match the profession requirements',
    profile_match: 'How your overall profile fits this career path',
    trend_score:   'Market demand trend for this profession',
    market_share:  'Vacancy market share occupied by this profession',
  },
  kk: {
    skill_match:   'Техникалық дағдыларыңыз мамандық талаптарына қаншалықты сәйкес келеді',
    profile_match: 'Жалпы профиліңіз осы мансап бағытына қаншалықты сәйкес келеді',
    trend_score:   'Бұл мамандық бойынша нарық сұранысының тренді',
    market_share:  'Бұл мамандықтың вакансиялар нарығындағы үлесі',
  },
}

const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : s

const detectCourseLanguage = course => {
  if (course?.language) return course.language
  const text = `${course?.title || ''} ${course?.description || ''}`
  if (/[ӘәҒғҚқҢңӨөҰұҮүҺһІі]/.test(text)) return 'kk'
  return /[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]/.test(text) ? 'ru' : 'en'
}

const COURSE_FILTER_DEFAULTS = {
  certificate: 'all',
  price: 'all',
  language: 'all',
  platform: 'all',
  level: 'all',
}
const COURSE_FILTER_KEYS = Object.keys(COURSE_FILTER_DEFAULTS)
const normalizeFilterValue = value => String(value ?? '').trim().toLowerCase()
const normalizeCourseLevel = value => {
  const text = normalizeFilterValue(value || 'Mixed')
  if (text.includes('beginner') || text.includes('нач')) return 'Beginner'
  if (text.includes('intermediate') || text.includes('сред')) return 'Intermediate'
  if (text.includes('advanced') || text.includes('продвин') || text.includes('проф')) return 'Advanced'
  return 'Mixed'
}
const courseHasCertificate = course => course?.certificate === true || normalizeFilterValue(course?.certificate) === 'true'
const coursePriceType = course => {
  if (course?.price_type) return normalizeFilterValue(course.price_type)
  const numeric = Number(course?.price)
  if (Number.isFinite(numeric)) return numeric <= 0 ? 'free' : 'paid'
  return normalizeFilterValue(course?.price || 'unknown')
}
const formatCoursePrice = (course, t) => {
  const type = coursePriceType(course)
  const labels = t.results.courseFilters || {}
  const numeric = Number(course?.price)
  if (type === 'free') return labels.free || 'Free'
  if (Number.isFinite(numeric) && numeric > 0) return numeric.toFixed(2)
  if (type === 'paid') return labels.paid || 'Paid'
  return ''
}
const normalizeCourse = course => ({
  ...course,
  language: detectCourseLanguage(course),
  level: normalizeCourseLevel(course?.level || course?.difficulty),
  price_type: coursePriceType(course),
  certificate: courseHasCertificate(course),
})
const courseMatchesFilters = (course, filters = COURSE_FILTER_DEFAULTS) => {
  const c = normalizeCourse(course)
  if (filters.certificate === 'with' && !c.certificate) return false
  if (filters.certificate === 'without' && c.certificate) return false
  if (filters.price === 'free' && c.price_type !== 'free') return false
  if (filters.price === 'paid' && c.price_type !== 'paid') return false
  if (filters.language !== 'all' && c.language !== filters.language) return false
  if (filters.platform !== 'all' && normalizeFilterValue(c.platform) !== normalizeFilterValue(filters.platform)) return false
  if (filters.level !== 'all' && c.level !== filters.level) return false
  return true
}
const filterCourses = (courses = [], filters) => courses.map(normalizeCourse).filter(course => courseMatchesFilters(course, filters))
const getCourseFilterOptions = courses => {
  const normalized = courses.map(normalizeCourse)
  return {
    languages: [...new Set(normalized.map(course => course.language).filter(Boolean))],
    platforms: [...new Set(normalized.map(course => course.platform).filter(Boolean))].sort(),
    levels: [...new Set(normalized.map(course => course.level).filter(Boolean))],
  }
}
const activeCourseFilterCount = filters => COURSE_FILTER_KEYS.filter(key => filters[key] && filters[key] !== 'all').length

const normalizeSkillKey = s => String(s || '').toLowerCase().replace(/[^a-z0-9+#]+/g, '_').replace(/^_+|_+$/g, '')
const pct = (value, max = 1) => Math.max(0, Math.min(100, Math.round((parseFloat(value || 0) / max) * 100)))
const sumSkillCount = roadmap => Object.values(roadmap || {}).reduce((total, skills) => total + (Array.isArray(skills) ? skills.length : 0), 0)
const flattenRoadmapSkills = roadmap => Object.entries(roadmap || {}).flatMap(([cat, skills]) =>
  (Array.isArray(skills) ? skills : []).map(skill => ({ cat, skill }))
)
const getProfessionRoadmapSummary = (results, profession) => {
  const all = results?.roadmaps_by_profession?.[profession]
  if (all) return all
  return { full: results?.full_roadmap || {}, gap: {} }
}

const mergeAudioChunks = chunks => {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const samples = new Float32Array(totalLength)
  let offset = 0
  chunks.forEach(chunk => {
    samples.set(chunk, offset)
    offset += chunk.length
  })
  return samples
}

const getAudioRms = samples => {
  if (!samples.length) return 0
  const sumSquares = samples.reduce((sum, sample) => sum + sample * sample, 0)
  return Math.sqrt(sumSquares / samples.length)
}

const encodeWav = (samples, sampleRate) => {
  const bytesPerSample = 2
  const blockAlign = bytesPerSample
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample)
  const view = new DataView(buffer)
  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i += 1) view.setUint8(offset + i, string.charCodeAt(i))
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * bytesPerSample, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * bytesPerSample, true)

  let offset = 44
  samples.forEach(sample => {
    const clamped = Math.max(-1, Math.min(1, sample))
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
    offset += bytesPerSample
  })

  return new Blob([view], { type: 'audio/wav' })
}

const createWavRecorder = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const AudioContext = window.AudioContext || window.webkitAudioContext
  const audioContext = new AudioContext()
  const source = audioContext.createMediaStreamSource(stream)
  const processor = audioContext.createScriptProcessor(4096, 1, 1)
  const mutedOutput = audioContext.createGain()
  const chunks = []

  mutedOutput.gain.value = 0
  processor.onaudioprocess = event => {
    chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
  }

  source.connect(processor)
  processor.connect(mutedOutput)
  mutedOutput.connect(audioContext.destination)

  return {
    stop: async () => {
      processor.disconnect()
      mutedOutput.disconnect()
      source.disconnect()
      stream.getTracks().forEach(track => track.stop())
      await audioContext.close()
      const samples = mergeAudioChunks(chunks)
      return {
        blob: encodeWav(samples, audioContext.sampleRate),
        rms: getAudioRms(samples),
      }
    },
  }
}

const DEPENDENCY_RULES = {
  fastapi: ['python'],
  django: ['python'],
  flask: ['python'],
  pandas: ['python'],
  numpy: ['python'],
  pytorch: ['python'],
  tensorflow: ['python'],
  scikit_learn: ['python'],
  spark: ['python', 'sql'],
  airflow: ['python'],
  dbt: ['sql'],
  tableau: ['sql'],
  power_bi: ['sql'],
  react: ['javascript'],
  next_js: ['javascript', 'react'],
  node_js: ['javascript'],
  kubernetes: ['docker'],
  terraform: ['cloud_computing'],
}

const ChevronIcon = ({ dir = 'left' }) => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    {dir === 'left'  && <path d="M15 18l-6-6 6-6"/>}
    {dir === 'right' && <path d="M9 18l6-6-6-6"/>}
    {dir === 'down'  && <path d="M6 9l6 6 6-6"/>}
    {dir === 'up'    && <path d="M18 15l-6-6-6 6"/>}
  </svg>
)

/* ─── Copy Icon ──────────────────────────────────────────────── */
const CopyIcon = ({ size = 12 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
)
const CheckIcon = ({ size = 12 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
)

/* ─── Progress Ring ──────────────────────────────────────────── */
function ProgressRing({ value, size = 64, stroke = 5, color = '#5b8dee', animKey, tooltipText }) {
  const [progress, setProgress] = useState(0)
  const r    = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const pct  = Math.round(value * 100)

  useEffect(() => {
    setProgress(0)
    const t = setTimeout(() => setProgress(pct), 80)
    return () => clearTimeout(t)
  }, [pct, animKey])

  return (
    <div className={tooltipText ? styles.scoreCircleTooltip : ''} data-tip={tooltipText}
      style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ - circ * progress / 100}
          style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.4,0,0.2,1)' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: size < 60 ? '0.65rem' : '0.78rem',
        fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text)',
      }}>{pct}%</div>
    </div>
  )
}

/* ─── Animated Bar ───────────────────────────────────────────── */
function AnimatedBar({ value, max = 1, color, animKey, tooltipText }) {
  const [width, setWidth] = useState(0)
  const pct = Math.round(value / max * 100)
  useEffect(() => {
    setWidth(0)
    const raf = requestAnimationFrame(() => {
      const t = setTimeout(() => setWidth(pct), 30)
      return () => clearTimeout(t)
    })
    return () => cancelAnimationFrame(raf)
  }, [pct, animKey])

  return (
    <div className={styles.barWrap}>
      <div className={`${styles.bar} ${tooltipText ? styles.barTooltipWrap : ''}`} data-tip={tooltipText}>
        <div className={styles.barFill} style={{ width: `${width}%`, background: color, transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)' }}/>
      </div>
      <span className={styles.barPct}>{pct}%</span>
    </div>
  )
}

/* ─── Radar Chart (4 axes: profession metrics) ─────────────────── */
function RadarChart({ data, animKey, lang }) {
  const RADAR_TOOLTIPS = {
    ru: { skill_match: 'Навыки', profile_match: 'Профиль', trend_score: 'Тренд', market_share: 'Рынок' },
    en: { skill_match: 'Skills', profile_match: 'Profile', trend_score: 'Trend', market_share: 'Market' },
    kk: { skill_match: 'Дағдылар', profile_match: 'Профиль', trend_score: 'Тренд', market_share: 'Нарық' },
  }
  const tips = RADAR_TOOLTIPS[lang] || RADAR_TOOLTIPS.en

  const axes = [
    { key: 'skill_match',   label: tips.skill_match,   color: '#5b8dee' },
    { key: 'profile_match', label: tips.profile_match, color: '#9b6ddf' },
    { key: 'trend_score',   label: tips.trend_score,   color: '#4caf82' },
    { key: 'market_share',  label: tips.market_share,  color: '#f0943a' },
  ]

  const [tooltip, setTooltip] = useState(null)
  const [opacity, setOpacity] = useState(0)

  useEffect(() => {
    setOpacity(0)
    const t = setTimeout(() => setOpacity(1), 60)
    return () => clearTimeout(t)
  }, [animKey])

  const size   = 300
  const cx     = size / 2
  const cy     = size / 2
  const r      = 100
  const n      = axes.length
  const levels = [0.25, 0.5, 0.75, 1.0]
  const angleOf = i => (Math.PI * 2 * i / n) - Math.PI / 2
  const pt = (i, ratio) => ({
    x: cx + r * ratio * Math.cos(angleOf(i)),
    y: cy + r * ratio * Math.sin(angleOf(i)),
  })

  const rings = levels.map(lvl =>
    axes.map((_, i) => pt(i, lvl))
      .map((p, j) => (j === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ') + ' Z'
  )

  const radarData = {
    skill_match:   Math.min(parseFloat(data.skill_match   ?? 0), 1),
    profile_match: Math.min(parseFloat(data.profile_match ?? 0), 1),
    trend_score:   Math.min(parseFloat(data.trend_score   ?? 0), 1),
    market_share:  Math.min(parseFloat(data.market_share  ?? 0) / 100, 1),
  }

  const polyPoints = axes.map((ax, i) => pt(i, radarData[ax.key] || 0))
  const polyPath   = polyPoints
    .map((p, j) => (j === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ') + ' Z'

  const labelPt = i => pt(i, 1.45)

  return (
    <div style={{ position: 'relative', display: 'inline-block', flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`-36 -36 ${size + 72} ${size + 72}`}
        style={{ opacity, transition: 'opacity 0.5s ease', display: 'block' }}>
        {levels.map((lvl, i) => (
          <text key={i} x={cx + 4} y={cy - r * lvl - 4}
            fontSize="8" fill="var(--text-3)" fontFamily="var(--font-mono)" opacity="0.7">
            {Math.round(lvl * 100)}
          </text>
        ))}
        {rings.map((d, i) => (
          <path key={i} d={d} fill="none"
            stroke={i === levels.length - 1 ? 'var(--border-hover)' : 'var(--border)'}
            strokeWidth={i === levels.length - 1 ? 1.5 : 1}/>
        ))}
        {axes.map((_, i) => {
          const end = pt(i, 1)
          return <line key={i} x1={cx} y1={cy} x2={end.x} y2={end.y} stroke="var(--border)" strokeWidth="1"/>
        })}
        <path d={polyPath} fill="var(--accent)" fillOpacity="0.18" stroke="var(--accent)" strokeWidth="2.5"/>
        {polyPoints.map((p, i) => {
          const val = Math.round(radarData[axes[i].key] * 100)
          return (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r="5" fill={axes[i].color} stroke="var(--bg)" strokeWidth="2"/>
              <circle cx={p.x} cy={p.y} r="14" fill="transparent" stroke="none"
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setTooltip({ x: p.x, y: p.y, label: tips[axes[i].key], val, color: axes[i].color })}
                onMouseLeave={() => setTooltip(null)}
              />
            </g>
          )
        })}
        {axes.map((ax, i) => {
          const lp = labelPt(i)
          return (
            <text key={i} x={lp.x} y={lp.y} textAnchor="middle" dominantBaseline="middle"
              fontSize="11" fill="var(--text-2)" fontFamily="var(--font-mono)" fontWeight="600">
              {ax.label}
            </text>
          )
        })}
      </svg>
      {tooltip && (
        <div style={{
          position: 'absolute',
          left: tooltip.x + 44, top: tooltip.y + 20,
          background: 'var(--surface)', border: `1px solid ${tooltip.color}40`,
          borderRadius: '6px', padding: '5px 10px', fontSize: '0.72rem',
          fontFamily: 'var(--font-mono)', color: 'var(--text)',
          pointerEvents: 'none', whiteSpace: 'nowrap', zIndex: 10,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}>
          <span style={{ color: tooltip.color, fontWeight: 700 }}>{tooltip.val}%</span> {tooltip.label}
        </div>
      )}
    </div>
  )
}

function ProfessionBarsChart({ professions, rows, profLabel, t, animKey, onSelect }) {
  const maxScore = Math.max(...professions.map(p => p.final_score || 0), 1)
  const [hovered, setHovered] = useState(null)

  return (
    <div className={styles.compareChart}>
      <div className={styles.compareHeader}>
        <span>{t.results.compareAll}</span>
        <small>{t.results.scoreOverview}</small>
      </div>
      <div className={styles.professionBars}>
        {professions.map((p, index) => {
          const scorePct = pct(p.final_score, maxScore)
          const tooltip = `${profLabel(p.name)}\n${t.results.scoreOverview}: ${pct(p.final_score)}%\n${rows
            .filter(r => p[r.key] != null)
            .map(r => `${r.label}: ${pct(p[r.key], r.max)}%`)
            .join('\n')}`
          return (
            <button
              key={p.name}
              type="button"
              className={`${styles.professionBarRow} ${hovered === p.name ? styles.professionBarRowHover : ''}`}
              data-tip={tooltip}
              onMouseEnter={() => setHovered(p.name)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelect?.(p.name)}
            >
              <span className={styles.professionBarRank}>#{index + 1}</span>
              <span className={styles.professionBarName}>{profLabel(p.name)}</span>
              <span className={styles.professionBarTrack}>
                <span
                  className={styles.professionBarFill}
                  style={{ width: `${scorePct}%`, transitionDelay: `${index * 35}ms` }}
                />
                <span className={styles.professionBarFactors}>
                  {rows.map(r => p[r.key] != null && (
                    <span
                      key={r.key}
                      style={{
                        width: `${Math.max(3, pct(p[r.key], r.max) / rows.length)}%`,
                        background: BAR_COLORS[r.key],
                      }}
                    />
                  ))}
                </span>
              </span>
              <span className={styles.professionBarPct}>{pct(p.final_score)}%</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function MultiProfessionRadar({ professions, profLabel, rows, t, animKey }) {
  const [tooltip, setTooltip] = useState(null)
  const [opacity, setOpacity] = useState(0)

  useEffect(() => {
    setOpacity(0)
    const timer = setTimeout(() => setOpacity(1), 60)
    return () => clearTimeout(timer)
  }, [animKey])

  const axes = professions
  const size = 330
  const cx = size / 2
  const cy = size / 2
  const r = 112
  const levels = [0.25, 0.5, 0.75, 1]
  const angleOf = i => (Math.PI * 2 * i / axes.length) - Math.PI / 2
  const point = (i, ratio) => ({
    x: cx + r * ratio * Math.cos(angleOf(i)),
    y: cy + r * ratio * Math.sin(angleOf(i)),
  })
  const poly = (key, max = 1) => axes
    .map((p, i) => point(i, Math.min(parseFloat(p[key] || 0) / max, 1)))
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') + ' Z'
  const rings = levels.map(level => axes.map((_, i) => point(i, level))
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') + ' Z')

  return (
    <div className={styles.radarCompare}>
      <div className={styles.compareHeader}>
        <span>{t.results.chartModes.radar}</span>
        <small>{t.results.compareAll}</small>
      </div>
      <div className={styles.radarCompareBody}>
        <svg width={size} height={size} viewBox={`-44 -44 ${size + 88} ${size + 88}`}
          style={{ opacity, transition: 'opacity .35s ease' }}>
          {rings.map((d, i) => (
            <path key={i} d={d} fill="none" stroke="var(--border)" strokeWidth={i === rings.length - 1 ? 1.5 : 1}/>
          ))}
          {axes.map((p, i) => {
            const end = point(i, 1)
            const label = profLabel(p.name)
            return (
              <g key={p.name}>
                <line x1={cx} y1={cy} x2={end.x} y2={end.y} stroke="var(--border)" />
                <text
                  x={point(i, 1.27).x}
                  y={point(i, 1.27).y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="10"
                  fill="var(--text-2)"
                  fontFamily="var(--font-mono)"
                >
                  {label.length > 15 ? label.slice(0, 14) + '…' : label}
                </text>
              </g>
            )
          })}
          <path d={poly('final_score')} fill="#5b8dee" fillOpacity=".17" stroke="#5b8dee" strokeWidth="2.5"/>
          <path d={poly('skill_match')} fill="none" stroke="#4caf82" strokeWidth="1.8" strokeDasharray="5 4"/>
          <path d={poly('profile_match')} fill="none" stroke="#9b6ddf" strokeWidth="1.8" strokeDasharray="2 4"/>
          {axes.map((p, i) => {
            const pos = point(i, Math.min(p.final_score || 0, 1))
            const tooltipText = `${profLabel(p.name)}\n${t.results.scoreOverview}: ${pct(p.final_score)}%\n${rows.map(r => `${r.label}: ${pct(p[r.key], r.max)}%`).join('\n')}`
            return (
              <circle
                key={p.name}
                cx={pos.x}
                cy={pos.y}
                r="6"
                fill="#5b8dee"
                stroke="var(--bg)"
                strokeWidth="2"
                onMouseEnter={() => setTooltip({ x: pos.x, y: pos.y, text: tooltipText })}
                onMouseLeave={() => setTooltip(null)}
              />
            )
          })}
        </svg>
        <div className={styles.radarLegend}>
          <span><i style={{ background: '#5b8dee' }}/>{t.results.scoreOverview}</span>
          <span><i style={{ background: '#4caf82' }}/>{t.results.skillMatch}</span>
          <span><i style={{ background: '#9b6ddf' }}/>{t.results.classification}</span>
        </div>
        {tooltip && (
          <div className={styles.chartTooltip} style={{ left: tooltip.x + 42, top: tooltip.y + 24 }}>
            {tooltip.text}
          </div>
        )}
      </div>
    </div>
  )
}

function SkillGapComparison({ professions, results, profLabel, t, onSelect }) {
  return (
    <div className={styles.gapCompare}>
      <div className={styles.compareHeader}>
        <span>{t.results.gapByProfession}</span>
        <small>{t.results.compareAll}</small>
      </div>
      {professions.map(p => {
        const summary = getProfessionRoadmapSummary(results, p.name)
        const total = sumSkillCount(summary.full)
        const gap = sumSkillCount(summary.gap)
        const known = Math.max(total - gap, 0)
        const completion = total ? Math.round((known / total) * 100) : 0
        const tooltip = `${profLabel(p.name)}\n${t.results.youKnow}: ${known}/${total}\n${t.results.toLearn}: ${gap}`
        return (
          <button key={p.name} type="button" className={styles.gapCompareRow} data-tip={tooltip} onClick={() => onSelect?.(p.name)}>
            <span className={styles.gapCompareName}>{profLabel(p.name)}</span>
            <span className={styles.gapCompareTrack}>
              <span className={styles.gapKnown} style={{ width: `${completion}%` }}/>
            </span>
            <span className={styles.gapCompareMeta}>{known}/{total}</span>
          </button>
        )
      })}
    </div>
  )
}

function ScoreCircleGrid({ professions, rows, profLabel, t, onSelect }) {
  return (
    <div className={styles.scoreCircleGrid}>
      {professions.map(p => {
        const tooltip = `${profLabel(p.name)}\n${t.results.scoreOverview}: ${pct(p.final_score)}%\n${rows.map(r => `${r.label}: ${pct(p[r.key], r.max)}%`).join('\n')}`
        return (
          <button key={p.name} className={styles.scoreCircleCard} onClick={() => onSelect?.(p.name)}>
            <ProgressRing value={p.final_score ?? 0} size={58} stroke={4} color="#5b8dee" animKey={p.name} tooltipText={tooltip}/>
            <span>{profLabel(p.name)}</span>
          </button>
        )
      })}
    </div>
  )
}

function SkillImpactChart({ explanation, profName, t }) {
  const items = explanation?.items || []
  if (!items.length) return null
  const maxImpact = Math.max(...items.map(item => item.abs_value || Math.abs(item.value || 0)), 0.001)
  const positive = explanation.positive || items.filter(item => item.value > 0)
  const negative = explanation.negative || items.filter(item => item.value < 0)
  const methodText = explanation.method === 'catboost_shap' ? t.results.shapMethod : t.results.shapFallback
  const magnitude = item => t.results.impactMagnitude?.[item.magnitude] || item.magnitude
  const itemText = item => {
    if (item.direction === 'positive') return t.results.skillPositiveText?.(item.skill, magnitude(item), profName) || item.text
    if (item.direction === 'missing') return t.results.skillMissingText?.(item.skill, magnitude(item), profName) || item.text
    return t.results.skillNegativeText?.(item.skill, magnitude(item), profName) || item.text
  }

  return (
    <div className={styles.skillExplainBlock}>
      <div className={styles.skillExplainHeader}>
        <div>
          <strong>{t.results.skillImpactTitle}</strong>
          <span>{methodText}</span>
        </div>
        <button className={styles.infoPill} type="button" title={t.results.shapTooltip}>SHAP</button>
      </div>
      <p className={styles.explainText}>
        {t.results.skillImpactSummary?.(
          profName,
          positive[0]?.skill || t.results.yourCurrentSkills,
          negative[0]?.skill || t.results.noMajorGaps,
        ) || explanation.summary}
      </p>
      <div className={styles.skillImpactChart}>
        {items.map(item => {
          const width = Math.max(5, Math.round((item.abs_value || Math.abs(item.value || 0)) / maxImpact * 100))
          const positiveImpact = item.value >= 0
          return (
            <div key={item.feature || item.skill} className={styles.skillImpactRow} title={itemText(item)}>
              <span className={styles.skillImpactName}>{item.skill}</span>
              <span className={styles.skillImpactTrack}>
                <i
                  className={positiveImpact ? styles.skillImpactPositive : styles.skillImpactNegative}
                  style={{ width: `${width}%` }}
                />
              </span>
              <span className={styles.skillImpactValue}>{positiveImpact ? '+' : ''}{Math.round((item.value || 0) * 100)}%</span>
            </div>
          )
        })}
      </div>
      <div className={styles.skillImpactLists}>
        <div>
          <strong>{t.results.topPositiveSkills}</strong>
          {positive.length ? positive.slice(0, 4).map(item => (
            <p key={item.feature || item.skill}>{itemText(item)}</p>
          )) : <p>{t.results.noPositiveSkills}</p>}
        </div>
        <div>
          <strong>{t.results.topMissingSkills}</strong>
          {negative.length ? negative.slice(0, 4).map(item => (
            <p key={item.feature || item.skill}>{itemText(item)}</p>
          )) : <p>{t.results.noMissingSkills}</p>}
        </div>
      </div>
    </div>
  )
}

function ExplainabilityPanel({ profession, rows, profLabel, t, skillExplanation }) {
  if (!profession) return null
  const contributions = rows
    .filter(row => profession[row.key] != null)
    .map(row => {
      const weight = row.key === 'trend_score' ? 0.15 : row.key === 'market_share' ? 0.05 : 0.4
      return { ...row, contribution: pct(profession[row.key], row.max) * weight }
    })
    .sort((a, b) => b.contribution - a.contribution)
  const maxContribution = Math.max(...contributions.map(item => item.contribution), 1)

  return (
    <section className={styles.explainCard}>
      <div className={styles.compareHeader}>
        <span>{t.results.explainability}</span>
        <small>{t.results.featureImportance}</small>
      </div>
      <p className={styles.explainText}>
        {t.results.whyTop ? t.results.whyTop(profLabel(profession.name)) : profLabel(profession.name)}
      </p>
      <SkillImpactChart explanation={skillExplanation} profName={profLabel(profession.name)} t={t}/>
      <div className={styles.explainFactors}>
        {contributions.map(item => (
          <div key={item.key} className={styles.explainFactor}>
            <div className={styles.explainFactorTop}>
              <span>{item.label}</span>
              <strong>{pct(profession[item.key], item.max)}%</strong>
            </div>
            <div className={styles.explainFactorTrack}>
              <span style={{ width: `${Math.round(item.contribution / maxContribution * 100)}%`, background: BAR_COLORS[item.key] }}/>
            </div>
            <p>{t.results.factorTexts?.[item.key]}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function SkillDependencyTree({ roadmap, doneSkills, formSkills, t }) {
  const learned = new Set([
    ...(formSkills || []).map(normalizeSkillKey),
    ...Array.from(doneSkills || []).map(key => normalizeSkillKey(key.split('::')[1] || key)),
  ])
  const items = flattenRoadmapSkills(Object.fromEntries(
    Object.entries(roadmap || {}).map(([cat, skills]) => [cat, skills.map(item => item.skill)])
  ))
  const enriched = items.map(item => {
    const key = normalizeSkillKey(item.skill)
    const prerequisites = DEPENDENCY_RULES[key] || []
    const isDone = learned.has(key)
    const ready = prerequisites.every(dep => learned.has(normalizeSkillKey(dep)))
    return { ...item, key, prerequisites, isDone, ready }
  })
  const next = enriched.find(item => !item.isDone && item.ready) || enriched.find(item => !item.isDone)

  if (!enriched.length) return null

  return (
    <section className={styles.dependencyPanel}>
      <div className={styles.compareHeader}>
        <span>{t.results.dependencyTree}</span>
        {next && <small>{t.results.nextStep}: {cap(next.skill)}</small>}
      </div>
      <div className={styles.dependencyTree}>
        {enriched.map(item => (
          <div key={`${item.cat}-${item.skill}`} className={`${styles.dependencyNode} ${item.isDone ? styles.dependencyDone : item.ready ? styles.dependencyReady : styles.dependencyLocked}`}>
            <div className={styles.dependencyNodeTop}>
              <span>{cap(item.skill)}</span>
              <strong>{item.isDone ? t.results.learned : item.ready ? t.results.ready : t.results.locked}</strong>
            </div>
            <div className={styles.dependencyPrereq}>
              <span>{t.results.prerequisites}</span>
              <div>
                {item.prerequisites.length
                  ? item.prerequisites.map(dep => (
                    <i key={dep} className={learned.has(normalizeSkillKey(dep)) ? styles.prereqDone : ''}>{cap(dep.replace(/_/g, ' '))}</i>
                  ))
                  : <i className={styles.prereqDone}>{t.results.ready}</i>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function CourseFilters({ filters, options, onChange, onReset, t }) {
  const labels = t.results.courseFilters
  const languageLabels = t.results.courseLanguages || {}
  const activeCount = activeCourseFilterCount(filters)
  const setFilter = (key, value) => onChange({ ...filters, [key]: value })
  const languageOptions = ['en', 'ru', 'kk', 'other', ...(options.languages || [])]
    .filter((value, index, arr) => arr.indexOf(value) === index)
  const levelOptions = ['Beginner', 'Intermediate', 'Advanced', 'Mixed', ...(options.levels || [])]
    .filter((value, index, arr) => arr.indexOf(value) === index)
  const platformOptions = ['Coursera', 'Udemy', 'edX', ...(options.platforms || [])]
    .filter(Boolean)
    .filter((value, index, arr) => arr.findIndex(item => normalizeFilterValue(item) === normalizeFilterValue(value)) === index)

  return (
    <section className={styles.courseFilterPanel}>
      <div className={styles.compareHeader}>
        <span>{labels.title}</span>
        <small>{labels.active(activeCount)}</small>
      </div>
      <div className={styles.courseFilterGrid}>
        <label>
          <span>{labels.certificate}</span>
          <select value={filters.certificate} onChange={e => setFilter('certificate', e.target.value)}>
            <option value="all">{labels.all}</option>
            <option value="with">{labels.withCertificate}</option>
            <option value="without">{labels.withoutCertificate}</option>
          </select>
        </label>
        <label>
          <span>{labels.price}</span>
          <select value={filters.price} onChange={e => setFilter('price', e.target.value)}>
            <option value="all">{labels.all}</option>
            <option value="free">{labels.free}</option>
            <option value="paid">{labels.paid}</option>
          </select>
        </label>
        <label>
          <span>{labels.language}</span>
          <select value={filters.language} onChange={e => setFilter('language', e.target.value)}>
            <option value="all">{labels.all}</option>
            {languageOptions.map(value => (
              <option key={value} value={value}>{languageLabels[value] || value}</option>
            ))}
          </select>
        </label>
        <label>
          <span>{labels.platform}</span>
          <select value={filters.platform} onChange={e => setFilter('platform', e.target.value)}>
            <option value="all">{labels.all}</option>
            {platformOptions.map(value => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          <span>{labels.level}</span>
          <select value={filters.level} onChange={e => setFilter('level', e.target.value)}>
            <option value="all">{labels.all}</option>
            {levelOptions.map(value => (
              <option key={value} value={value}>{labels.levels?.[value] || value}</option>
            ))}
          </select>
        </label>
      </div>
      {activeCount > 0 && (
        <div className={styles.activeFilters}>
          {COURSE_FILTER_KEYS.filter(key => filters[key] !== 'all').map(key => (
            <button key={key} type="button" onClick={() => setFilter(key, 'all')}>
              {labels[key]}: {labels[filters[key]] || languageLabels[filters[key]] || labels.levels?.[filters[key]] || filters[key]}
            </button>
          ))}
          <button type="button" className={styles.resetFilters} onClick={onReset}>{labels.reset}</button>
        </div>
      )}
    </section>
  )
}

function CourseCard({ course, t, onOpen, onCopy, copied }) {
  return (
    <div className={styles.courseWrap}>
      <div className={styles.course} style={{ cursor: 'pointer' }} onClick={() => onOpen(course)}>
        <span className={styles.coursePlatform}>{course.platform}</span>
        <span className={styles.courseTitle}>{course.title}</span>
        <span className={styles.courseMeta}>
          {course.rating > 0 && <span className={styles.courseRating}>★ {course.rating}</span>}
          {course.reviews != null && (
            <span className={styles.courseReviews}>
              {Number(course.reviews).toLocaleString()} {t.results.reviews}
            </span>
          )}
          <span className={styles.courseReviews}>{t.results.courseLanguages?.[course.language] || course.language}</span>
          <span className={styles.courseReviews}>{t.results.courseFilters?.levels?.[course.level] || course.level}</span>
          {formatCoursePrice(course, t) && <span className={styles.coursePrice}>{formatCoursePrice(course, t)}</span>}
        </span>
      </div>
      <button className={styles.courseCopyBtn} onClick={onCopy}>
        {copied ? <CheckIcon/> : <CopyIcon/>}
      </button>
    </div>
  )
}

function RecommendedCoursePanel({ courses, filters, t, onOpen, onCopy, copiedMsg }) {
  const visible = filterCourses(courses, filters)
  return (
    <section className={styles.recommendedCoursesPanel}>
      <div className={styles.compareHeader}>
        <span>{t.results.courses}</span>
        <small>{visible.length}/{courses.length}</small>
      </div>
      {visible.length === 0 ? (
        <div className={styles.courseEmptyState}>{t.results.courseEmptyState}</div>
      ) : (
        <div className={styles.courseCardGrid}>
          {visible.slice(0, 8).map((course, index) => (
            <div key={`${course.skill}-${course.title}-${index}`} className={styles.courseGridItem}>
              <span className={styles.courseSkillTag}>{cap(course.skill)}</span>
              <CourseCard
                course={course}
                t={t}
                onOpen={onOpen}
                copied={copiedMsg === `recommended-${index}`}
                onCopy={e => onCopy(e, course, `recommended-${index}`)}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
const SKILL_IMPLIES = {

    "react.js":         ["javascript"],
    "next.js":          ["javascript"],
    "vue.js":           ["javascript"],
    "nuxt.js":          ["javascript"],
    "angular":          ["typescript"],   
    "angular.js":       ["javascript"],
    "ember.js":         ["javascript"],
    "svelte":           ["javascript"],
    "gatsby":           ["javascript"],
    "express":          ["javascript"],
    "node.js":          ["javascript"],
    "deno":             ["typescript"],
    "fastify":          ["javascript"],

    "django":           ["python"],
    "flask":            ["python"],
    "fastapi":          ["python"],
    "scikit-learn":     ["python"],
    "tensorflow":       ["python"],
    "pytorch":          ["python"],
    "keras":            ["python"],
    "pandas":           ["python"],
    "numpy":            ["python"],
    "matplotlib":       ["python"],
    "seaborn":          ["python"],
    "plotly":           ["python"],
    "airflow":          ["python"],
    "pyspark":          ["python"],
    "nltk":             ["python"],
    "opencv":           ["python"],
    "hugging face":     ["python"],
    "selenium":         ["python"],
    "jupyter":          ["python"],

    "ruby on rails":    ["ruby"],
    "sinatra":          ["ruby"],

    "laravel":          ["php"],
    "symfony":          ["php"],
    "drupal":           ["php"],

    "spring":           ["java"],
    "play framework":   ["java"],        

    "android":          ["kotlin"],

    "ios":             ["swift"],

    "asp.net":          ["c#"],
    "asp.net core":     ["c#"],
    "blazor":           ["c#"],
    "unity":            ["c#"],

    "akka":             ["scala"],

    "gin":              ["go"],
    "fiber":            ["go"],

    "actix":            ["rust"],
    "tokio":            ["rust"],

    "flutter":          ["dart"],

    "ggplot2":          ["r"],
    "dplyr":            ["r"],
    "tidyr":            ["r"],
    "tidyverse":        ["r"],
    "rshiny":           ["r"],
    "mlr":              ["r"],

    "phoenix":          ["elixir"],

    "luminus":          ["clojure"],

    "simulink":         ["matlab"],

    "dax":              ["sql"],        

    "ionic":            ["typescript"],
    "capacitor":        ["typescript"],
    "cordova":          ["javascript"],
    "xamarin":          ["c#"],
    "react native":     ["javascript"],

    "ansible":          ["yaml"],
    "terraform":        ["hcl"],
    "puppet":           ["ruby"],
    "chef":             ["ruby"],
    "jenkins":          ["groovy"],
}

function SkillGapRadar({ results, formData, profession, animKey, lang }) {
  const [tooltip, setTooltip] = useState(null)
  const [opacity, setOpacity]  = useState(0)
  useEffect(() => {
    setOpacity(0)
    const t = setTimeout(() => setOpacity(1), 60)
    return () => clearTimeout(t)
  }, [animKey])

  const norm = normalizeSkillKey
  const baseSkills = new Set(
    (formData?.skills || []).map(s =>
      norm(typeof s === 'string' ? s : s.label || s.value || s.name || '')
    )
  )
  // Normalized student skill set
  const studentNorm = new Set(baseSkills)
let changed = true
while (changed) {
  changed = false
  for (const [skill, implies] of Object.entries(SKILL_IMPLIES)) {
    if (studentNorm.has(skill)) {
      for (const implied of implies) {
        if (!studentNorm.has(implied)) {
          studentNorm.add(implied)
          changed = true
        }
      }
    }
  }
}

  const studentHas = (skillKey) => {
  if (studentNorm.has(skillKey)) return true

  const bare = s => s.replace(/[_\d]/g, '').trim()
  const bareKey = bare(skillKey)

  for (const sk of studentNorm) {
    const bareSk = bare(sk)
    if (!bareSk || bareSk.length < 3) continue
    if (
      bareKey === bareSk ||
      bareKey.includes(bareSk) ||
      bareSk.includes(bareKey) ||
      skillKey.split('_')[0] === sk.split('_')[0]
    ) return true
  }
  return false
}

  const professionSummary = getProfessionRoadmapSummary(results, profession || results?.top_profession)
  const fullRoadmap = professionSummary.full || {}

  // Collect axes: up to 10 skills from full_roadmap
  const axes = []
  for (const [cat, skills] of Object.entries(fullRoadmap)) {
    for (const skill of skills) {
      const key = norm(skill)
      if (!axes.find(a => a.key === key)) {
        axes.push({ key, label: cap(skill), cat })
      }
      if (axes.length >= 10) break
    }
    if (axes.length >= 10) break
  }

  if (axes.length < 3) return null

  const n      = axes.length
  const size   = 300
  const cx     = size / 2
  const cy     = size / 2
  const r      = 100
  const levels = [0.25, 0.5, 0.75, 1.0]

  const angleOf = i => (Math.PI * 2 * i / n) - Math.PI / 2
  const pt = (i, ratio) => ({
    x: cx + r * ratio * Math.cos(angleOf(i)),
    y: cy + r * ratio * Math.sin(angleOf(i)),
  })

  const rings = levels.map(lvl =>
    axes.map((_, i) => pt(i, lvl))
      .map((p, j) => (j === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ') + ' Z'
  )

  // Benchmark = always 1.0 (entire full_roadmap)
  const idealPoints = axes.map((_, i) => pt(i, 1.0))
  const idealPath = idealPoints.map((p, j) => (j === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ') + ' Z'

  // Student = 1.0 if known, 0 if not
  const studentValues = axes.map(ax => studentHas(ax.key) ? 1.0 : 0.0)
  // Filter zero points - draw only where there is knowledge
  // For polygon we put zeros in center (0.04 so it doesnt collapse)
  const studentPoints = axes.map((_, i) => pt(i, Math.max(studentValues[i], 0.04)))
  const studentPath = studentPoints.map((p, j) => (j === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ') + ' Z'

  const labelPt = i => pt(i, 1.45)

  const knownCount = studentValues.filter(v => v === 1.0).length
  const totalCount = axes.length
  const text = {
    ru: { known: 'навыков уже есть', youKnow: 'Знаете', toLearn: 'Нужно изучить' },
    en: { known: 'skills already known', youKnow: 'You know', toLearn: 'To learn' },
    kk: { known: 'дағды бар', youKnow: 'Білесің', toLearn: 'Үйрену керек' },
  }[lang] || { known: 'skills already known', youKnow: 'You know', toLearn: 'To learn' }

  return (
    <div style={{ position: 'relative', display: 'inline-block', flexShrink: 0 }}>

      {/* Counter */}
      <div style={{
        marginBottom: 8, fontSize: '0.72rem', fontFamily: 'var(--font-mono)',
        color: 'var(--text-2)',
      }}>
        <span style={{ color: '#4caf82', fontWeight: 700 }}>{knownCount}</span>
        {' / '}{totalCount}{' '}
        {text.known}
      </div>

      <svg width={size} height={size} viewBox={`-40 -40 ${size + 80} ${size + 80}`}
        style={{ opacity, transition: 'opacity 0.5s ease', display: 'block' }}>

        {/* Grid */}
        {rings.map((d, i) => (
          <path key={i} d={d} fill="none"
            stroke={i === levels.length - 1 ? 'var(--border-hover)' : 'var(--border)'}
            strokeWidth={i === levels.length - 1 ? 1.5 : 1} />
        ))}
        {axes.map((_, i) => {
          const end = pt(i, 1)
          return <line key={i} x1={cx} y1={cy} x2={end.x} y2={end.y}
            stroke="var(--border)" strokeWidth="1" />
        })}

        {/* Benchmark - full profession profile */}
        <path d={idealPath} fill="#4caf82" fillOpacity="0.08"
          stroke="#4caf82" strokeWidth="1.5" strokeDasharray="4 3" />

        {/* Student - only what is known */}
        <path d={studentPath} fill="#5b8dee" fillOpacity="0.25"
          stroke="#5b8dee" strokeWidth="2.5" />

        {/* Points on each axis */}
        {axes.map((ax, i) => {
          const has = studentValues[i] === 1.0
          const p = pt(i, 1.0)
          return (
            <g key={i}>
              {has && (
                <circle cx={p.x} cy={p.y} r={5}
                  fill="#5b8dee"
                  stroke="var(--bg)" strokeWidth={2} />
              )}
              {/* hover zone stays for all */}
              <circle cx={p.x} cy={p.y} r="14"
                fill="transparent" style={{ cursor: 'pointer' }}
                onMouseEnter={() => setTooltip({ x: p.x, y: p.y, label: ax.label, has })}
                onMouseLeave={() => setTooltip(null)} />
            </g>
          )
        })}

        {/* Axis labels - green if known, gray if not */}
        {axes.map((ax, i) => {
          const lp = labelPt(i)
          const has = studentValues[i] === 1.0
          return (
            <text key={i} x={lp.x} y={lp.y} textAnchor="middle" dominantBaseline="middle"
              fontSize="10" fontFamily="var(--font-mono)" fontWeight="600"
              fill={has ? '#5b8dee' : 'var(--text-3)'}>
              {ax.label.length > 10 ? ax.label.slice(0, 9) + '…' : ax.label}
            </text>
          )
        })}

        {/* Legend */}
        <g transform={`translate(${cx - 85}, ${size + 18})`}>
          <circle cx="5" cy="5" r="4" fill="#5b8dee" />  {/* ← was #4caf82, became blue */}
          <text x="14" y="9" fontSize="10" fill="var(--text-2)" fontFamily="var(--font-mono)">
            {text.youKnow}
          </text>
        </g>
        <g transform={`translate(${cx + 20}, ${size + 18})`}>
          <circle cx="5" cy="5" r="4" fill="#4caf82" />
          <text x="14" y="9" fontSize="10" fill="var(--text-2)" fontFamily="var(--font-mono)">
            {text.toLearn}
          </text>
        </g>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: 'absolute',
          left: tooltip.x + 44, top: tooltip.y + 20,
          background: 'var(--surface)',
          border: `1px solid ${tooltip.has ? '#4caf8240' : '#f0943a40'}`,
          borderRadius: '6px', padding: '5px 10px',
          fontSize: '0.72rem', fontFamily: 'var(--font-mono)',
          color: 'var(--text)', pointerEvents: 'none',
          whiteSpace: 'nowrap', zIndex: 10,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}>
          <span style={{ color: tooltip.has ? '#4caf82' : '#f0943a', fontWeight: 700 }}>
            {tooltip.has ? '✓' : '✗'}
          </span>{' '}{tooltip.label}
        </div>
      )}
    </div>
  )
}


/* ─── Metric Bars ────────────────────────────────────────────── */
function MetricBars({ data, rows, animKey, lang }) {
  const tips = BAR_TOOLTIPS[lang] || BAR_TOOLTIPS.en
  return (
    <div style={{ flex: 1, minWidth: 180, display: 'flex', flexDirection: 'column', gap: 18, justifyContent: 'center' }}>
      {rows.map(({ key, label, max }) => {
        if (data[key] == null) return null
        return (
          <div key={key}>
            <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'baseline', marginBottom: 6 }}>
              <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>{label}</span>
            </div>
            <AnimatedBar value={parseFloat(data[key])} max={max} color={BAR_COLORS[key]}
              animKey={animKey} tooltipText={tips[key]}/>
          </div>
        )
      })}
    </div>
  )
}

/* ─── Score Rows ─────────────────────────────────────────────── */
function ProfScores({ p, rows, animKey, lang }) {
  const tips = BAR_TOOLTIPS[lang] || BAR_TOOLTIPS.en
  return (
    <div className={styles.profScores}>
      {rows.map(({ key, label, max }) =>
        p[key] != null ? (
          <div key={key} className={styles.scoreRow}>
            <span className={styles.scoreLabel}>{label}</span>
            <AnimatedBar
              value={parseFloat(p[key])}
              max={max}
              color={BAR_COLORS[key]}
              animKey={animKey}
              tooltipText={tips[key]}
            />
          </div>
        ) : null
      )}
    </div>
  )
}

/* ─── Vacancy trend ──────────────────────────────────────────── */
function VacancyTrend({ value }) {
  if (!value) return null
  const color = value > 500 ? '#4caf82' : value > 100 ? '#f0943a' : '#9b6ddf'
  const arrow = value > 500 ? '↑' : value > 100 ? '→' : '↓'
  return (
    <span style={{ color, fontFamily: 'var(--font-mono)', fontSize: '0.9rem', marginRight: 4 }}>{arrow}</span>
  )
}

/* ─── Helpers ────────────────────────────────────────────────── */
const copyText = (text) => {
  // Modern API - works only on HTTPS/localhost
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text)
  }

  // Fallback for HTTP / local network
  const el = document.createElement('textarea')
  el.value = text
  el.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0'
  document.body.appendChild(el)
  el.focus()
  el.select()
  try {
    document.execCommand('copy')
  } catch (e) {
    console.warn('Copy failed', e)
  }
  document.body.removeChild(el)
}

function orderedRows(allRows, sortBy) {
  const idx = allRows.findIndex(r => r.sortKey === sortBy)
  if (idx <= 0) return allRows
  return [allRows[idx], ...allRows.slice(0, idx), ...allRows.slice(idx + 1)]
}

const stripMarkdown = text => text
  .replace(/#{1,6}\s/g, '')
  .replace(/\*\*(.+?)\*\*/g, '$1')
  .replace(/\*(.+?)\*/g, '$1')
  .replace(/_{1,3}(.+?)_{1,3}/g, '$1')
  .replace(/- /gm, '\u2022 ')
  .replace(/\[(.+?)\]\(.+?\)/g, '$1')
  .replace(/`(.+?)`/g, '$1')
  .replace(/```[\s\S]*?```/g, '')
  .replace(/> /gm, '')
  .trim()

const isCareerChatAllowed = message => {
  const text = String(message || '').toLowerCase()
  const injection = [
    'ignore previous', 'system prompt', 'developer message', 'reveal instructions',
    'забудь инструкции', 'игнорируй инструкции', 'системный промпт', 'раскрой инструкции',
  ]
  const offTopic = [
    'bubble sort', 'write code', 'generate code', 'solve math', 'math problem', 'essay',
    'пузырьковую сортировку', 'напиши код', 'сгенерируй эссе', 'реши задачу', 'математик',
  ]
  const career = [
    'career', 'profession', 'job', 'roadmap', 'skill', 'course', 'recommendation',
    'карьер', 'професс', 'работ', 'роадмап', 'навык', 'курс', 'рекомендац',
    'мансап', 'маман', 'жұмыс', 'жоспар', 'дағды', 'курс', 'ұсыныс',
  ]
  if (injection.some(pattern => text.includes(pattern))) return false
  if (offTopic.some(pattern => text.includes(pattern)) && !career.some(pattern => text.includes(pattern))) return false
  return true
}

/* ─── Course description modal ───────────────────────────────── */
function CourseModal({ course, onClose, t }) {
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalBox} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div className={styles.modalMeta}>
            <span className={styles.modalPlatform}>{course.platform}</span>
            {course.rating && (
              <span className={styles.modalRating}>★ {course.rating}</span>
            )}
          </div>
          <button className={styles.modalClose} onClick={onClose}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <h3 className={styles.modalTitle}>{course.title}</h3>
        {course.description ? (
          <p className={styles.modalDesc}>{course.description}</p>
        ) : (
          <p className={styles.modalDescEmpty}>{t.results.noDescription}</p>
        )}
        {course.url && (
          <a href={course.url} target="_blank" rel="noopener noreferrer" className={styles.modalLink}>
            {t.results.openCourse} →
          </a>
        )}
      </div>
    </div>
  )
}

/* ─── Deep Mode Button ───────────────────────────────────────── */
function DeepModeBtn({ active, onClick, lang, t }) {
  return (
    <button
      className={`${styles.deepModeBtn} ${active ? styles.deepModeBtnActive : ''}`}
      onClick={onClick}
      title={active ? t.results.disableDeep : t.results.enableDeep}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.3 4.7-3.3 6L15 21H9l-.3-5.9A7 7 0 0 1 5 9a7 7 0 0 1 7-7z"/>
        <line x1="9" y1="21" x2="15" y2="21"/>
      </svg>
      <span>{t.results.thinking}</span>
      {active && (
        <span className={styles.deepModePulse}/>
      )}
    </button>
  )
}

/* ─── Main Component ─────────────────────────────────────────── */
export default function Results({ results: initialResults, formData, onBack, onRetry, onNewAnalysis }) {
  const { t, lang } = useApp()

  const [results,      setResults]      = useState(initialResults)
  const [tab,          setTab]          = useState('best')
  const [doneSkills, setDoneSkills] = useState(new Set())
  const [sortBy,       setSortBy]       = useState('score')
  const [selectedProf, setSelectedProf] = useState(null)
  const [viewMode,     setViewMode]     = useState('bars')
  const [messages,     setMessages]     = useState([])
  const [input,        setInput]        = useState('')
  const [chatLoading,  setChatLoading]  = useState(false)
  const [deepMode,     setDeepMode]     = useState(false)
  const [copied,       setCopied]       = useState(null)
  const [leftOpen,     setLeftOpen]     = useState(true)
  const [rightOpen,    setRightOpen]    = useState(false)
  const [pdfLoading,   setPdfLoading]   = useState(false)
  const [openCats,     setOpenCats]     = useState(new Set())
  const [cardKey,      setCardKey]      = useState(0)
  const [copiedMsg,    setCopiedMsg]    = useState(null)
  const [activeCourse, setActiveCourse] = useState(null)   // ← for course modal
  const [categoryOrder, setCategoryOrder] = useState([])
  const [skillOrders, setSkillOrders] = useState({})
  const [dragItem, setDragItem] = useState(null)
  const [history, setHistory] = useState([])
  const [savedCurrent, setSavedCurrent] = useState(false)
  const [listening, setListening] = useState(false)
  const [voiceNotice, setVoiceNotice] = useState('')
  const [chatSize, setChatSize] = useState({ width: 360, height: null })
  const [courseFilters, setCourseFilters] = useState(COURSE_FILTER_DEFAULTS)

  const messagesEndRef = useRef(null)
  const greetedRef     = useRef(false)
  const textareaRef    = useRef(null)
  const abortRef       = useRef(null)
  const voiceRecorderRef = useRef(null)

  useEffect(() => {
    setResults(initialResults)
    setSelectedProf(null)
    setSavedCurrent(false)
  }, [initialResults])

  const top_profession = results.top_profession
  const rawRoadmap     = results.roadmap_with_courses
  const resultStorageKey = `career-result:${results.session_id || top_profession || 'local'}`
  const profLabel = name => t.professions?.[name] || name
  const catLabel = cat => t.categories?.[cat] || cat.replace(/_/g, ' ')
  const skillWord = n => t.results.skillWord ? t.results.skillWord(n) : `${n} skills`

  const ALL_SCORE_ROWS = [
    { key: 'skill_match',   label: t.results.skillMatch,      sortKey: 'skill',   max: 1   },
    { key: 'profile_match', label: t.results.classification,  sortKey: 'profile', max: 1   },
    { key: 'trend_score',   label: t.results.trend,           sortKey: 'trend',   max: 1   },
    { key: 'market_share',  label: t.results.marketShare,     sortKey: 'market',  max: 100 },
  ]

  const SORT_OPTIONS = [
    { key: 'score',   label: t.results.sortOptions.score   },
    { key: 'skill',   label: t.results.sortOptions.skill   },
    { key: 'profile', label: t.results.sortOptions.profile },
    { key: 'trend',   label: t.results.sortOptions.trend   },
    { key: 'market',  label: t.results.sortOptions.market  },
  ]

  const tabs = [
    { key: 'best',    label: t.results.tabs.best    },
    { key: 'all',     label: t.results.tabs.all     },
    { key: 'roadmap', label: t.results.tabs.roadmap },
  ]

  const allProfessions = Object.entries(results.final_scores)
    .map(([name, final_score]) => ({
      name,
      final_score,
      skill_match:   results.skill_scores?.[name]    ?? 0,
      profile_match: results.classification_scores?.[name] ?? 0,
      trend_score:   results.demand_scores?.[name]?.trend_score   ?? 0,
      market_share:  results.demand_scores?.[name]?.market_share != null
        ? parseFloat(results.demand_scores[name].market_share * 100).toFixed(1)
        : null,
      vacancies_per_week: results.demand_scores?.[name]?.predicted_vacancies ?? null,
    }))

  const sorted = [...allProfessions].sort((a, b) => {
    if (sortBy === 'score')   return (b.final_score ?? 0)  - (a.final_score ?? 0)
    if (sortBy === 'skill')   return (b.skill_match ?? 0)  - (a.skill_match ?? 0)
    if (sortBy === 'profile') return (b.profile_match ?? 0)- (a.profile_match ?? 0)
    if (sortBy === 'trend')   return (b.trend_score ?? 0)  - (a.trend_score ?? 0)
    if (sortBy === 'market')  return parseFloat(b.market_share ?? 0) - parseFloat(a.market_share ?? 0)
    return 0
  })

  const activeProfName = selectedProf || top_profession
  const activeProf     = sorted.find(p => p.name === activeProfName) || sorted[0]

  const roadmapAdapted = Object.fromEntries(
    Object.entries(rawRoadmap || {}).map(([cat, skills]) => [
      cat,
      Object.entries(skills).map(([skill, data]) => ({
        skill,
        courses: (data.courses || []).map(c => ({
          title:       c.title,
          platform:    c.platform,
          rating:      c.rating,
          reviews:     c.num_reviews ?? c.reviews ?? null,
          url:         c.course_url || null,
          description: c.description || c.short_intro || null,
          certificate: c.certificate ?? false,
          language:    c.language,
          level:       c.level || c.difficulty || 'Mixed',
          difficulty:  c.difficulty || c.level || 'Mixed',
          price_type:  c.price_type || 'unknown',
          price:       c.price ?? null,
        })),
      })),
    ])
  )

  const allRoadmapCourses = Object.entries(roadmapAdapted).flatMap(([cat, skills]) =>
    skills.flatMap(item => (item.courses || []).map(course => ({
      ...normalizeCourse(course),
      cat,
      skill: item.skill,
    })))
  )
  const courseFilterOptions = getCourseFilterOptions(allRoadmapCourses)
  const selectedSkillExplanation = results.skill_explanations?.[activeProf?.name] || null

  const orderedCategoryKeys = (categoryOrder.length ? categoryOrder : Object.keys(roadmapAdapted))
    .filter(cat => roadmapAdapted[cat])
  const orderedRoadmapEntries = orderedCategoryKeys.map(cat => {
    const order = skillOrders[cat] || []
    const skills = [...(roadmapAdapted[cat] || [])].sort((a, b) => {
      const ai = order.indexOf(a.skill)
      const bi = order.indexOf(b.skill)
      if (ai === -1 && bi === -1) return 0
      if (ai === -1) return 1
      if (bi === -1) return -1
      return ai - bi
    })
    const active = skills.filter(s => !doneSkills.has(`${cat}::${s.skill}`))
    const completed = skills.filter(s => doneSkills.has(`${cat}::${s.skill}`))
    return [cat, [...active, ...completed]]
  })
  const totalRoadmapSteps = Object.values(roadmapAdapted).reduce((sum, skills) => sum + skills.length, 0)
  const doneRoadmapSteps = Array.from(doneSkills).filter(key => {
    const [cat, skill] = key.split('::')
    return roadmapAdapted[cat]?.some(item => item.skill === skill)
  }).length

  const roadmapPreview = Object.entries(roadmapAdapted).map(([cat, skills]) => ({
    cat,
    skill: skills[0]?.skill ? cap(skills[0].skill) : '',
    count: skills.length,
  }))

  const toggleSkill = (cat, skillName) => {
  const key = `${cat}::${skillName}`
  setDoneSkills(prev => {
    const next = new Set(prev)
    next.has(key) ? next.delete(key) : next.add(key)
    return next
  })
}
  useEffect(() => {
    const keys = Object.keys(roadmapAdapted)
    setOpenCats(new Set(keys))
    setCategoryOrder(keys)
    setSkillOrders(Object.fromEntries(keys.map(cat => [cat, roadmapAdapted[cat].map(item => item.skill)])))
    setDoneSkills(new Set())
    setCourseFilters(COURSE_FILTER_DEFAULTS)
    let cancelled = false
    const applyLocalFallback = () => {
      try {
        const saved = JSON.parse(localStorage.getItem(resultStorageKey) || '{}')
        if (Array.isArray(saved.doneSkills)) setDoneSkills(new Set(saved.doneSkills))
        if (Array.isArray(saved.categoryOrder)) setCategoryOrder(saved.categoryOrder)
        if (saved.skillOrders) setSkillOrders(saved.skillOrders)
        if (saved.courseFilters) setCourseFilters({ ...COURSE_FILTER_DEFAULTS, ...saved.courseFilters })
      } catch {}
    }
    if (results.session_id) {
      getRecommendationState(results.session_id)
        .then(state => {
          if (cancelled) return
          const progress = state.progress || {}
          if (Array.isArray(progress.doneSkills)) setDoneSkills(new Set(progress.doneSkills))
          if (Array.isArray(progress.categoryOrder) && progress.categoryOrder.length) setCategoryOrder(progress.categoryOrder)
          if (progress.skillOrders) setSkillOrders(progress.skillOrders)
          if (progress.selectedProfession) setSelectedProf(progress.selectedProfession)
          if (state.filters && Object.keys(state.filters).length) {
            setCourseFilters({ ...COURSE_FILTER_DEFAULTS, ...state.filters })
          }
        })
        .catch(applyLocalFallback)
    } else {
      applyLocalFallback()
    }
    return () => { cancelled = true }
  }, [resultStorageKey])

  useEffect(() => {
    try {
      localStorage.setItem(resultStorageKey, JSON.stringify({
        doneSkills: Array.from(doneSkills),
        categoryOrder,
        skillOrders,
        courseFilters,
      }))
    } catch {}
  }, [doneSkills, categoryOrder, skillOrders, courseFilters, resultStorageKey])

  useEffect(() => {
    if (!results.session_id) return
    const timer = setTimeout(() => {
      saveRoadmapProgress(results.session_id, {
        doneSkills: Array.from(doneSkills),
        categoryOrder,
        skillOrders,
        selectedProfession: activeProfName,
      }).catch(() => {})
    }, 350)
    return () => clearTimeout(timer)
  }, [doneSkills, categoryOrder, skillOrders, activeProfName, results.session_id])

  useEffect(() => {
    if (!results.session_id) return
    const timer = setTimeout(() => {
      saveCourseFilterPreferences(results.session_id, courseFilters).catch(() => {})
    }, 350)
    return () => clearTimeout(timer)
  }, [courseFilters, results.session_id])

  useEffect(() => {
    getRecommendationHistory()
      .then(data => setHistory(data.items || []))
      .catch(() => {
        try {
          setHistory(JSON.parse(localStorage.getItem('career-recommendation-history') || '[]'))
        } catch {
          setHistory([])
        }
      })
  }, [])

  useEffect(() => {
    const onKey = e => {
      if (e.key === 'Escape') {
        setRightOpen(false)
        setActiveCourse(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const toggleCat = cat => setOpenCats(prev => {
    const next = new Set(prev)
    next.has(cat) ? next.delete(cat) : next.add(cat)
    return next
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (greetedRef.current) return
    greetedRef.current = true
    const staticMsg = t.results.initialChat
      ? t.results.initialChat(profLabel(top_profession))
      : `Your top match is ${profLabel(top_profession)}.`
    setMessages([{ role: 'assistant', content: staticMsg, streaming: false }])
  }, [])

  useEffect(() => { return () => abortRef.current?.abort() }, [])

  /* ─── Send message ─────────────────────────────────────────── */
  const sendMessage = async (overrideMsg) => {
    const msg = (overrideMsg ?? input).trim()
    if (!msg || chatLoading) return

    if (!isCareerChatAllowed(msg)) {
      setMessages(p => [
        ...p,
        { role: 'user', content: msg },
        { role: 'assistant', content: t.results.assistantScope, streaming: false },
      ])
      setInput('')
      return
    }

    const userMsg         = { role: 'user', content: msg }
    const historySnapshot = [...messages, userMsg]

    setMessages(p => [...p, userMsg, { role: 'assistant', content: '', streaming: true }])
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setChatLoading(true)

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller


    
    try {
          const response = await sendChatStream(
              {
                session_id: results.session_id,
                history: historySnapshot,
                message: msg,
                deep: deepMode,
                lang: lang,
              },
              controller.signal
            );

      if (!response.ok) throw new Error('Stream failed')

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let full     = ''
      let thoughts = ''
      let buffer   = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split(/(?=data:)/)
        buffer = (parts[parts.length - 1]?.endsWith('\n') || parts[parts.length - 1]?.includes('[DONE]'))
          ? ''
          : (parts.pop() ?? '')

        for (const part of parts) {
          const text = part.replace(/^data:\s*/, '').trim()
          if (!text || text === '[DONE]') continue

          try {
            const data = JSON.parse(text)
            if (data.type === 'thought') {
              thoughts += data.content
            } else if (data.content) {
              full += data.content
            }
          } catch {
            full += text
          }

          setMessages(p => {
            const updated = [...p]
            updated[updated.length - 1] = {
              role: 'assistant', content: stripMarkdown(full), thoughts, streaming: true,
            }
            return updated
          })
        }
      }

      setMessages(p => {
        const updated = [...p]
        updated[updated.length - 1] = {
          role: 'assistant', content: stripMarkdown(full) || t.errors.api, thoughts, streaming: false,
        }
        return updated
      })

    } catch (err) {
      if (err.name === 'AbortError') return
      setMessages(p => {
        const updated = [...p]
        updated[updated.length - 1] = {
          role: 'assistant', content: t.errors.api, thoughts: '', streaming: false,
        }
        return updated
      })
    } finally {
      setChatLoading(false)
    }
  }

  const handleSelectProf = name => {
    setSelectedProf(name)
    setTab('best')
    setCardKey(k => k + 1)
  }

  const handleCopyRoadmap = () => {
    const lines = []
    Object.entries(roadmapAdapted).forEach(([cat, skills]) => {
      lines.push(catLabel(cat).toUpperCase())
      skills.forEach(s => {
        lines.push(`  - ${cap(s.skill)}`)
        s.courses.forEach(c => lines.push(`    ${c.title} (${c.platform})`))
      })
    })
    copyText(`${t.results.roadmap}: ${profLabel(top_profession)}\n\n` + lines.join('\n'))
    setCopied('roadmap')
    setTimeout(() => setCopied(null), 2000)
  }

  const handleCopyCourse = (event, course, key) => {
    event.preventDefault()
    event.stopPropagation()
    const text = course.url ? `${course.title} (${course.platform}): ${course.url}` : `${course.title} (${course.platform})`
    copyText(text)
    setCopiedMsg(key)
    setTimeout(() => setCopiedMsg(null), 2000)
  }

  const resetCourseFilters = () => setCourseFilters(COURSE_FILTER_DEFAULTS)

  const handleShare = () => {
    const text = `${t.results.selectedCareer}: ${profLabel(top_profession)} ${activeProf?.final_score ? Math.round(activeProf.final_score * 100) + '%' : ''} - CareerPath`
    if (navigator.share) {
      navigator.share({ title: 'CareerPath', text }).catch(() => {})
    } else {
      copyText(text)
      setCopied('share')
      setTimeout(() => setCopied(null), 2000)
    }
  }

  const saveCurrentResult = () => {
    const entry = {
      id: `${Date.now()}-${results.session_id || top_profession}`,
      createdAt: new Date().toISOString(),
      top_profession,
      selectedProfession: activeProfName,
      results,
      progress: {
        done: Array.from(doneSkills),
        categoryOrder,
        skillOrders,
      },
    }
    const next = [entry, ...history.filter(item => item.results?.session_id !== results.session_id && item.id !== entry.id)].slice(0, 12)
    setHistory(next)
    setSavedCurrent(true)
    try { localStorage.setItem('career-recommendation-history', JSON.stringify(next)) } catch {}
    if (results.session_id) {
      saveRoadmapProgress(results.session_id, {
        doneSkills: Array.from(doneSkills),
        categoryOrder,
        skillOrders,
        selectedProfession: activeProfName,
      })
        .then(() => getRecommendationHistory())
        .then(data => setHistory(data.items || next))
        .catch(() => {})
    }
  }

  const openHistoryItem = item => {
    setResults(item.results)
    setSelectedProf(item.selectedProfession || item.top_profession)
    setDoneSkills(new Set(item.progress?.done || []))
    setCategoryOrder(item.progress?.categoryOrder || [])
    setSkillOrders(item.progress?.skillOrders || {})
    setTab('best')
    setSavedCurrent(true)
    if (item.results?.session_id) {
      getRecommendationState(item.results.session_id)
        .then(state => {
          if (state.filters) setCourseFilters({ ...COURSE_FILTER_DEFAULTS, ...state.filters })
        })
        .catch(() => {})
    }
  }

  const clearHistory = () => {
    setHistory([])
    try { localStorage.removeItem('career-recommendation-history') } catch {}
    clearRecommendationHistory().catch(() => {})
  }

  const moveCategory = (fromCat, toCat) => {
    if (!fromCat || !toCat || fromCat === toCat) return
    setCategoryOrder(prev => {
      const base = (prev.length ? prev : Object.keys(roadmapAdapted)).filter(cat => roadmapAdapted[cat])
      const next = [...base]
      const from = next.indexOf(fromCat)
      const to = next.indexOf(toCat)
      if (from < 0 || to < 0) return prev
      const [item] = next.splice(from, 1)
      next.splice(to, 0, item)
      return next
    })
  }

  const moveSkill = (cat, fromSkill, toSkill) => {
    if (!cat || !fromSkill || !toSkill || fromSkill === toSkill) return
    setSkillOrders(prev => {
      const base = prev[cat] || roadmapAdapted[cat]?.map(item => item.skill) || []
      const next = [...base]
      const from = next.indexOf(fromSkill)
      const to = next.indexOf(toSkill)
      if (from < 0 || to < 0) return prev
      const [item] = next.splice(from, 1)
      next.splice(to, 0, item)
      return { ...prev, [cat]: next }
    })
  }

  const resizeChatInput = () => {
    requestAnimationFrame(() => {
      if (!textareaRef.current) return
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px'
    })
  }

  const startVoiceInput = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !(window.AudioContext || window.webkitAudioContext)) {
      setVoiceNotice(t.results.voiceUnsupported)
      return
    }

    const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname)
    if (window.isSecureContext === false && !isLocalhost) {
      setVoiceNotice(t.results.voiceSecureContext)
      return
    }

    try {
      voiceRecorderRef.current = await createWavRecorder()
      setListening(true)
      setVoiceNotice(t.results.voiceListening)
    } catch (err) {
      setListening(false)
      if (err?.name === 'NotAllowedError' || err?.name === 'SecurityError') {
        setVoiceNotice(t.results.voicePermission)
      } else if (err?.name === 'NotFoundError') {
        setVoiceNotice(t.results.voiceNoMic)
      } else {
        setVoiceNotice(t.results.voiceError)
      }
    }
  }

  const stopVoiceInput = async () => {
    const recorder = voiceRecorderRef.current
    voiceRecorderRef.current = null
    setListening(false)
    if (!recorder) return

    try {
      setVoiceNotice(t.results.voiceTranscribing)
      const audio = await recorder.stop()
      if (audio.rms < 0.004) {
        setVoiceNotice(t.results.voiceNoSpeech)
        return
      }
      const data = await transcribeVoice(audio.blob, lang)
      const text = (data.text || '').trim()
      if (!text) {
        setVoiceNotice(t.results.voiceNoSpeech)
        return
      }
      setInput(text)
      setVoiceNotice('')
      resizeChatInput()
    } catch {
      setVoiceNotice(t.results.voiceError)
    }
  }

  const startChatResize = e => {
    e.preventDefault()
    const startX = e.clientX
    const startWidth = chatSize.width
    const onMove = event => {
      const nextWidth = Math.min(Math.max(startWidth + (startX - event.clientX), 300), Math.min(window.innerWidth - 24, 620))
      setChatSize(size => ({ ...size, width: nextWidth }))
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  const speakLastAnswer = () => {
    if (!window.speechSynthesis) return
    const last = [...messages].reverse().find(m => m.role === 'assistant' && m.content)
    if (!last) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(last.content)
    utterance.lang = lang === 'kk' ? 'kk-KZ' : lang === 'ru' ? 'ru-RU' : 'en-US'
    window.speechSynthesis.speak(utterance)
  }

  const handleExportPdf = () => {
  setPdfLoading(true)
  const rows = orderedRows(ALL_SCORE_ROWS, 'score')

  // Remove garbage from strings
  const clean = str => String(str || '')
    .replace(/[★✓□◎*·•]/g, '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  const esc = str => clean(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  const scoreLines = rows
    .filter(r => activeProf?.[r.key] != null)
    .map(r => `<div class="score-row">
      <span class="score-label">${r.label}</span>
      <div class="score-bar-wrap">
        <div class="score-bar">
          <div class="score-fill" style="width:${Math.round(parseFloat(activeProf[r.key]) / r.max * 100)}%;background:${BAR_COLORS[r.key]}"></div>
        </div>
        <span class="score-pct">${Math.round(parseFloat(activeProf[r.key]) / r.max * 100)}%</span>
      </div>
    </div>`).join('')

  const allScoreLines = sorted.map(p => {
    const factors = rows.map(r => `<span style="background:${BAR_COLORS[r.key]};width:${Math.max(4, pct(p[r.key], r.max) / rows.length)}%"></span>`).join('')
    return `<div class="all-score-row">
      <span class="all-score-name">${esc(profLabel(p.name))}</span>
      <div class="all-score-track"><i style="width:${pct(p.final_score)}%"></i><b>${factors}</b></div>
      <span class="all-score-pct">${pct(p.final_score)}%</span>
    </div>`
  }).join('')

  const scoreCircles = sorted.map(p => {
    const score = pct(p.final_score)
    return `<div class="score-circle">
      <div class="circle" style="--score:${score * 3.6}deg"><span>${score}%</span></div>
      <strong>${esc(profLabel(p.name))}</strong>
    </div>`
  }).join('')

  const gapRows = sorted.map(p => {
    const summary = getProfessionRoadmapSummary(results, p.name)
    const total = sumSkillCount(summary.full)
    const gap = sumSkillCount(summary.gap)
    const known = Math.max(total - gap, 0)
    const completion = total ? Math.round(known / total * 100) : 0
    return `<div class="gap-row">
      <span>${esc(profLabel(p.name))}</span>
      <div class="gap-track"><i style="width:${completion}%"></i></div>
      <b>${known}/${total}</b>
    </div>`
  }).join('')

  const explainRows = rows
    .filter(r => activeProf?.[r.key] != null)
    .map(r => `<div class="explain-row">
      <span>${esc(r.label)}</span>
      <div><i style="width:${pct(activeProf[r.key], r.max)}%;background:${BAR_COLORS[r.key]}"></i></div>
      <b>${pct(activeProf[r.key], r.max)}%</b>
    </div>`)
    .join('')

  const roadmapSections = Object.entries(roadmapAdapted).map(([cat, skills]) =>
    `<div class="rm-section">
      <div class="rm-cat">
        <span>${catLabel(cat).toUpperCase()}</span>
        <span class="rm-count">${skillWord(skills.length)}</span>
      </div>
      ${skills.map(s => `<div class="rm-skill">
        <span class="rm-check">□</span>
        <div class="rm-skill-body">
          <span class="rm-skill-name">${esc(cap(s.skill))}</span>
          ${s.courses.slice(0, 2).map(c => {
            const rating = c.rating && !isNaN(parseFloat(c.rating))
              ? `<span class="rm-rating">★ ${parseFloat(c.rating).toFixed(1)}</span>`
              : ''
            const reviews = c.reviews && Number(c.reviews) > 10
              ? `<span class="rm-reviews">${Number(c.reviews).toLocaleString()} ${t.results.reviews}</span>`
              : ''
            return `<div class="rm-course">
              <span class="rm-platform">${esc(c.platform)}</span>
              <span class="rm-title">${esc(c.title)}</span>
              <span class="rm-meta">${rating}${reviews}</span>
            </div>`
          }).join('')}
        </div>
      </div>`).join('')}
    </div>`
  ).join('')


  // Username from formData
  const userName = formData?.name || formData?.fullName || ''
  const headerSub = userName
    ? `${t.results.pdfFor} ${userName} · ${new Date().toLocaleDateString()}`
    : new Date().toLocaleDateString()

  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8">
  <title>${t.results.pdfRoadmap}: ${esc(profLabel(top_profession))}</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,Segoe UI,sans-serif;color:#1e1e1c;font-size:13px;line-height:1.5}
    .header{background:#5b8dee;color:white;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
    .header-title{font-size:15px;font-weight:700}
    .header-sub{font-size:11px;opacity:0.8}
    .body{padding:24px}
    .prof-name{font-size:22px;font-weight:800;letter-spacing:-0.03em;margin-bottom:4px}
    .prof-sub{font-size:12px;color:#888;margin-bottom:18px}
    .section-title{font-size:9px;font-weight:700;letter-spacing:0.1em;color:#999;text-transform:uppercase;font-family:monospace;margin-bottom:10px}
    .scores{margin-bottom:24px;padding-bottom:20px;border-bottom:1px solid #eee}
    .score-circles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
    .score-circle{display:flex;align-items:center;gap:8px;padding:8px;border:1px solid #eee;border-radius:8px;break-inside:avoid}
    .circle{width:38px;height:38px;border-radius:50%;background:conic-gradient(#5b8dee var(--score),#e8edf5 0);display:grid;place-items:center;flex-shrink:0}
    .circle span{width:29px;height:29px;border-radius:50%;background:#fff;display:grid;place-items:center;font-size:9px;font-family:monospace;font-weight:700}
    .score-circle strong{font-size:10px;line-height:1.25}
    .all-scores{display:flex;flex-direction:column;gap:7px;margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid #eee}
    .all-score-row{display:grid;grid-template-columns:150px 1fr 38px;gap:10px;align-items:center}
    .all-score-name{font-size:11px;color:#444}
    .all-score-track{position:relative;height:8px;background:#edf1f7;border-radius:99px;overflow:hidden}
    .all-score-track>i{position:absolute;inset:0 auto 0 0;background:#5b8dee;border-radius:99px}
    .all-score-track>b{position:absolute;inset:0;display:flex;opacity:.55}
    .all-score-track>b span{display:block;height:100%}
    .all-score-pct{font-size:11px;font-family:monospace;text-align:right}
    .score-row{display:flex;align-items:center;gap:10px;margin-bottom:8px}
    .score-label{font-size:11px;color:#666;font-family:monospace;min-width:130px}
    .score-bar-wrap{flex:1;display:flex;align-items:center;gap:8px}
    .score-bar{flex:1;height:5px;background:#eee;border-radius:3px;overflow:hidden}
    .score-fill{height:100%;border-radius:3px}
    .score-pct{font-size:11px;font-family:monospace;color:#444;min-width:34px;text-align:right}
    .explain-copy{font-size:12px;color:#555;margin-bottom:10px}
    .explain{display:flex;flex-direction:column;gap:7px;margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid #eee}
    .explain-row{display:grid;grid-template-columns:130px 1fr 34px;gap:10px;align-items:center}
    .explain-row span{font-size:11px;color:#555}
    .explain-row div{height:6px;background:#eee;border-radius:99px;overflow:hidden}
    .explain-row i{display:block;height:100%;border-radius:99px}
    .explain-row b{font-size:11px;font-family:monospace;text-align:right}
    .gap-summary{display:flex;flex-direction:column;gap:7px;margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid #eee}
    .gap-row{display:grid;grid-template-columns:150px 1fr 42px;gap:10px;align-items:center}
    .gap-row span{font-size:11px}
    .gap-row b{font-size:11px;font-family:monospace;text-align:right}
    .gap-track{height:7px;background:#edf1f7;border-radius:99px;overflow:hidden}
    .gap-track i{display:block;height:100%;background:#4caf82;border-radius:99px}
    .progress-line{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding:10px;border:1px solid #eee;border-radius:8px}
    .progress-line span{font-size:12px;font-weight:600;min-width:170px}
    .progress-line i{flex:1;height:8px;background:#edf1f7;border-radius:99px;overflow:hidden}
    .progress-line b{display:block;height:100%;background:#5b8dee;border-radius:99px}
    .rm-section{margin-bottom:20px;break-inside:avoid}
    .rm-cat{font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;font-family:monospace;color:#5b8dee;background:#f0f4ff;padding:5px 10px;border-radius:4px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
    .rm-count{font-weight:400;opacity:0.7;font-size:9px}
    .rm-skill{display:flex;gap:8px;margin-bottom:10px;padding-left:4px}
    .rm-check{font-size:12px;color:#bbb;margin-top:1px;flex-shrink:0;font-family:monospace}
    .rm-skill-body{flex:1}
    .rm-skill-name{font-size:13px;font-weight:600;display:block;margin-bottom:4px}
    .rm-course{display:flex;gap:8px;align-items:center;margin-top:3px}
    .rm-platform{font-size:10px;font-family:monospace;color:#aaa;min-width:48px;flex-shrink:0}
    .rm-title{font-size:11px;color:#555;flex:1}
    .rm-meta{display:flex;gap:6px;align-items:center;flex-shrink:0}
    .rm-rating{font-size:10px;color:#e8a045;font-family:monospace;white-space:nowrap}
    .rm-reviews{font-size:10px;color:#bbb;font-family:monospace;white-space:nowrap}
    .footer{margin-top:32px;padding-top:12px;border-top:1px solid #eee;font-size:10px;color:#bbb;font-family:monospace}
    @media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}@page{margin:12mm 14mm}}
  </style></head>
  <body>
    <div class="header">
      <span class="header-title">CareerPath - ${t.results.pdfRoadmap}</span>
      <span class="header-sub">${esc(headerSub)}</span>
    </div>
    <div class="body">
      <div class="prof-name">${esc(profLabel(top_profession))}</div>
      <div class="prof-sub">${t.results.pdfSubtitle}</div>
      <div class="section-title">${t.results.pdfAllScores}</div>
      <div class="score-circles">${scoreCircles}</div>
      <div class="all-scores">${allScoreLines}</div>
      <div class="section-title">${t.results.pdfScores}</div>
      <div class="scores">${scoreLines}</div>
      <div class="section-title">${t.results.pdfExplain}</div>
      <div class="explain-copy">${esc(t.results.whyTop ? t.results.whyTop(profLabel(activeProf.name)) : '')}</div>
      <div class="explain">${explainRows}</div>
      <div class="section-title">${t.results.pdfSkillGap}</div>
      <div class="gap-summary">${gapRows}</div>
      <div class="section-title">${t.results.pdfProgress}</div>
      <div class="progress-line"><span>${esc(t.results.roadmapProgress(doneRoadmapSteps, totalRoadmapSteps))}</span><i><b style="width:${totalRoadmapSteps ? Math.round(doneRoadmapSteps / totalRoadmapSteps * 100) : 0}%"></b></i></div>
      <div class="section-title">${t.results.pdfRoadmap}</div>
      ${roadmapSections}
      <div class="footer">${t.results.pdfGenerated}</div>
    </div>
  </body></html>`

  const win = window.open('', '_blank', 'width=800,height=900')
  win.document.write(html)
  win.document.close()
  win.onload = () => { win.focus(); win.print() }
  setPdfLoading(false)
}

  const layoutClass = [
    styles.layout,
    !leftOpen  ? styles.layoutLeftClosed  : '',
    !rightOpen ? styles.layoutRightClosed : '',
  ].filter(Boolean).join(' ')

  const animKey = `${activeProfName}${tab}${cardKey}`

  return (
    <div className={layoutClass} style={{ '--chat-w': `${chatSize.width}px` }}>
      {rightOpen && <button className={styles.chatOverlay} onClick={() => setRightOpen(false)} aria-label={t.results.closeAiPanel} />}
      {!rightOpen && (
        <button className={styles.aiFab} onClick={() => setRightOpen(true)}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          {t.results.openAiPanel}
        </button>
      )}
      {/* ─ LEFT TOGGLE ─ */}
      <button
        className={[styles.sidebarToggle, styles.sidebarToggleLeft, !leftOpen ? styles.sidebarToggleLeftClosed : ''].join(' ')}
        onClick={() => setLeftOpen(v => !v)}
        title={leftOpen ? t.results.collapseLeft : t.results.expandLeft}
      >
        <ChevronIcon dir={leftOpen ? 'left' : 'right'}/>
      </button>

      {/* ─ RIGHT TOGGLE ─ */}
      <button
        className={[styles.sidebarToggle, styles.sidebarToggleRight, !rightOpen ? styles.sidebarToggleRightClosed : ''].join(' ')}
        onClick={() => setRightOpen(v => !v)}
        title={rightOpen ? t.results.collapseRight : t.results.expandRight}
      >
        <ChevronIcon dir={rightOpen ? 'right' : 'left'}/>
      </button>

      {/* ─ LEFT SIDEBAR ─ */}
      <aside className={styles.sidebar}>
        <button className={styles.backBtn} onClick={onBack}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          {t.results.back}
        </button>

        <div className={styles.sidebarSection}>
          <div className={styles.sidebarLabel}>{t.results.sidebarLabels.recommendation}</div>
          <div className={styles.sidebarProfession}>{profLabel(activeProfName)}</div>
          {activeProf?.final_score != null && (
            <div style={{ marginTop: 8 }}>
              <ProgressRing value={activeProf.final_score} size={56} stroke={4} color="var(--accent)" animKey={animKey}/>
            </div>
          )}
        </div>

        {sorted.length > 1 && (
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarLabel}>{t.results.sidebarLabels.scores}</div>
            <div className={styles.sidebarScores}>
              {sorted.map(p => (
                <div key={p.name}
                  className={`${styles.sidebarScoreRow} ${p.name === activeProfName ? styles.sidebarScoreRowActive : ''}`}
                  onClick={() => handleSelectProf(p.name)}
                >
                  <span className={styles.sidebarScoreKey}>{profLabel(p.name)}</span>
                  <span className={styles.sidebarScoreVal}>
                    {typeof p.final_score === 'number' ? Math.round(p.final_score * 100) + '%' : '—'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {roadmapPreview.length > 0 && (
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarLabel}>{t.results.sidebarLabels.roadmapOverview}</div>
            <div className={styles.roadmapPreview}>
              {roadmapPreview.map(({ cat, skill, count }) => (
                <div key={cat} className={styles.roadmapPreviewItem} onClick={() => setTab('roadmap')}>
                  <span className={styles.roadmapPreviewIcon}>{CATEGORY_ICONS[cat] || '◎'}</span>
                  <div className={styles.roadmapPreviewBody}>
                    <span className={styles.roadmapPreviewCat}>{catLabel(cat)}</span>
                    <span className={styles.roadmapPreviewSkill}>{skill}{count > 1 ? ` +${count - 1}` : ''}</span>
                  </div>
                </div>
              ))}
            </div>
            <button className={styles.roadmapPreviewBtn} onClick={() => setTab('roadmap')}>
              {t.results.viewFullRoadmap}
            </button>
          </div>
        )}

        <div className={styles.sidebarSection}>
          <div className={styles.sidebarLabel}>{t.results.historyTitle}</div>
          {history.length === 0 ? (
            <div className={styles.sidebarEmpty}>{t.results.noHistory}</div>
          ) : (
            <div className={styles.historyList}>
              {history.slice(0, 4).map(item => (
                <button key={item.id} className={styles.historyItem} onClick={() => openHistoryItem(item)}>
                  <span>{profLabel(item.selectedProfession || item.top_profession)}</span>
                  <small>{t.results.savedAt}: {new Date(item.createdAt).toLocaleDateString()}</small>
                </button>
              ))}
            </div>
          )}
          {history.length > 0 && (
            <button className={styles.historyClear} onClick={clearHistory}>{t.results.clearHistory}</button>
          )}
        </div>

        <div className={styles.sidebarActions}>
          <button className={styles.actionBtn} onClick={saveCurrentResult}>
            <CheckIcon size={12}/>
            {savedCurrent ? t.results.savedResult : t.results.saveResult}
          </button>
          <button className={styles.actionBtn} onClick={handleCopyRoadmap}>
            {copied === 'roadmap' ? <CheckIcon size={12}/> : <CopyIcon size={12}/>}
            {copied === 'roadmap' ? t.results.copied : t.results.copyRoadmap}
          </button>
          <button className={styles.actionBtn} onClick={handleShare}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
            {copied === 'share' ? t.results.copied : t.results.shareResults}
          </button>
          <button className={styles.actionBtn} onClick={handleExportPdf} disabled={pdfLoading}>
            {pdfLoading
              ? <span className={styles.spinner}/>
              : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
            }
            {pdfLoading ? '...' : t.results.downloadPdf}
          </button>
          <button className={styles.actionBtnNew} onClick={() => { onNewAnalysis?.(); onRetry ? onRetry() : onBack?.() }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12l7-7 7 7"/>
            </svg>
            {t.results.newAnalysis}
          </button>
        </div>
      </aside>

      {/* ─ MAIN ─ */}
      <main className={styles.main}>
        <div className={styles.tabsSticky}>
          <div className={styles.tabs}>
            {tabs.map(({ key, label }) => (
              <button key={key} className={`${styles.tab} ${tab === key ? styles.tabActive : ''}`}
                onClick={() => setTab(key)}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.tabContent} key={`${tab}${activeProfName}${cardKey}`}>

          {/* ─ BEST MATCH ─ */}
          {tab === 'best' && activeProf && (() => {
            const rows = orderedRows(ALL_SCORE_ROWS, 'score')
            const activeRank = Math.max(1, sorted.findIndex(p => p.name === activeProf.name) + 1)
            return (
              <div className={styles.bestStack}>
              <div className={styles.bestCard}>
                <div className={styles.bestHeader}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <ProgressRing value={activeProf.final_score ?? 0} size={72} stroke={5}
                      color="#5b8dee" animKey={animKey}
                      tooltipText={`${profLabel(activeProf.name)}\n${t.results.scoreOverview}: ${pct(activeProf.final_score)}%`}/>
                    <div>
                      <div className={styles.bestRank}>#{activeRank} {activeProf.name === top_profession ? t.results.bestMatch : t.results.selectedProfession}</div>
                      <div className={styles.bestName}>{profLabel(activeProf.name)}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
                    {activeProf.name === top_profession && <span className={styles.topBadge}>{t.results.bestMatch.toUpperCase()}</span>}
                    <div style={{ display: 'flex', gap: 4 }}>
                      {['bars', 'radar', 'gap'].map(m => (
                        <button key={m} onClick={() => setViewMode(m)} style={{
                          padding: '3px 10px', borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border)',
                          background: viewMode === m ? 'var(--accent-light)' : 'transparent',
                          color: viewMode === m ? 'var(--accent)' : 'var(--text-3)',
                          fontSize: '0.7rem', fontFamily: 'var(--font-mono)',
                          cursor: 'pointer', transition: 'all var(--transition)',
                        }}>
                          {t.results.chartModes?.[m] || m}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {viewMode === 'bars' && (
                  <div className={styles.chartStack}>
                    <ProfessionBarsChart professions={sorted} rows={rows} profLabel={profLabel} t={t} animKey={animKey} onSelect={handleSelectProf}/>
                    <div className={styles.activeMetricPanel}>
                      <div className={styles.compareHeader}>
                        <span>{profLabel(activeProf.name)}</span>
                        <small>{t.results.factors}</small>
                      </div>
                      <ProfScores p={activeProf} rows={rows} animKey={animKey} lang={lang}/>
                    </div>
                  </div>
                )}
                {viewMode === 'radar' && (
                  <div style={{ display: 'flex', gap: 24, alignItems: 'center', padding: '16px 0 8px', flexWrap: 'wrap' }}>
                    <MultiProfessionRadar professions={sorted} profLabel={profLabel} rows={rows} t={t} animKey={animKey}/>
                    <MetricBars data={activeProf} rows={rows} animKey={animKey} lang={lang}/>
                  </div>
                )}
                {viewMode === 'gap' && (
                  <div style={{ padding: '16px 0 8px' }}>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>
                      {t.results.gapLegend}
                    </p>
                    <div style={{
                        display: 'flex', gap: 24, alignItems: 'center',
                        padding: '16px 0 8px', flexWrap: 'wrap',
                      }}>
                        <SkillGapComparison professions={sorted} results={results} profLabel={profLabel} t={t} onSelect={handleSelectProf}/>
                        <SkillGapRadar results={results} formData={results._formData} profession={activeProf.name} animKey={animKey} lang={lang} />
                        <MetricBars data={activeProf} rows={rows} animKey={animKey} lang={lang} />
                      </div>
                  </div>
                )}

                {activeProf.vacancies_per_week && (
                  <div className={styles.demandRow}>
                    <div className={styles.demandItem}>
                      <VacancyTrend value={activeProf.vacancies_per_week}/>
                      {activeProf.vacancies_per_week.toLocaleString()} {t.results.vacanciesWeek}
                    </div>
                  </div>
                )}
              </div>
              <ExplainabilityPanel
                profession={activeProf}
                rows={rows}
                profLabel={profLabel}
                t={t}
                skillExplanation={selectedSkillExplanation}
              />
              <RecommendedCoursePanel
                courses={allRoadmapCourses}
                filters={courseFilters}
                t={t}
                onOpen={setActiveCourse}
                onCopy={handleCopyCourse}
                copiedMsg={copiedMsg}
              />
              </div>
            )
          })()}

          {/* ─ ALL PROFESSIONS ─ */}
          {tab === 'all' && (
            <>
              <div className={styles.sortBar}>
                <span className={styles.sortLabel}>{t.results.sortBy}</span>
                {SORT_OPTIONS.map(({ key, label }) => (
                  <button key={key}
                    className={`${styles.sortBtn} ${sortBy === key ? styles.sortBtnActive : ''}`}
                    onClick={() => setSortBy(key)}>{label}
                  </button>
                ))}
              </div>
              <ScoreCircleGrid professions={sorted} rows={ALL_SCORE_ROWS} profLabel={profLabel} t={t} onSelect={handleSelectProf}/>
              <div className={styles.allCharts}>
                <ProfessionBarsChart professions={sorted} rows={orderedRows(ALL_SCORE_ROWS, sortBy)} profLabel={profLabel} t={t} animKey={`${sortBy}${cardKey}`} onSelect={handleSelectProf}/>
                <SkillGapComparison professions={sorted} results={results} profLabel={profLabel} t={t} onSelect={handleSelectProf}/>
              </div>
              <div className={styles.allGrid}>
                {sorted.map((p, i) => {
                  const rows = orderedRows(ALL_SCORE_ROWS, sortBy)
                  const aKey = `${p.name}${sortBy}`
                  return (
                    <div key={p.name} className={`${styles.profCard} ${i === 0 ? styles.profCardTop : ''}`}>
                      <div className={styles.profHeader}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <ProgressRing value={p.final_score ?? 0} size={40} stroke={3}
                            color={BAR_COLORS.skill_match} animKey={aKey}
                            tooltipText={`${profLabel(p.name)}\n${t.results.scoreOverview}: ${pct(p.final_score)}%`}/>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span className={styles.profRank}>#{i+1}</span>
                            <span className={styles.profName}>{profLabel(p.name)}</span>
                            {i === 0 && <span className={styles.topBadge}>{t.results.bestMatch.toUpperCase()}</span>}
                          </div>
                        </div>
                      </div>
                      <ProfScores p={p} rows={rows} animKey={aKey} lang={lang}/>
                      {p.vacancies_per_week && (
                        <div className={styles.demandRow}>
                          <div className={styles.demandItem}>
                            <VacancyTrend value={p.vacancies_per_week}/>
                            {p.vacancies_per_week.toLocaleString()} {t.results.vacanciesWeek}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {/* ─ ROADMAP ─ */}
          {tab === 'roadmap' && (
  <>
    <p className={styles.roadmapHint}>
      {t.results.skillsToLearn} <strong>{profLabel(top_profession)}</strong>
    </p>
    <div className={styles.roadmapProgressPanel}>
      <span>{t.results.roadmapProgress(doneRoadmapSteps, totalRoadmapSteps)}</span>
      <div className={styles.roadmapProgressTrack}>
        <i style={{ width: `${totalRoadmapSteps ? Math.round(doneRoadmapSteps / totalRoadmapSteps * 100) : 0}%` }}/>
      </div>
    </div>
    <p className={styles.dragHint}>{t.results.dragHint}</p>
    <CourseFilters
      filters={courseFilters}
      options={courseFilterOptions}
      onChange={setCourseFilters}
      onReset={resetCourseFilters}
      t={t}
    />
    <SkillDependencyTree roadmap={roadmapAdapted} doneSkills={doneSkills} formSkills={results._formData?.skills} t={t}/>
    <div className={styles.roadmap}>
      {orderedRoadmapEntries.map(([cat, skills]) => {
        const isOpen = openCats.has(cat)

        // Sorting: uncompleted at top, completed at bottom
        const sorted = [...skills].sort((a, b) => {
          const aDone = doneSkills.has(`${cat}::${a.skill}`)
          const bDone = doneSkills.has(`${cat}::${b.skill}`)
          return aDone - bDone
        })

        const doneCount = skills.filter(s => doneSkills.has(`${cat}::${s.skill}`)).length
        const firstCompletedIndex = sorted.findIndex(s => doneSkills.has(`${cat}::${s.skill}`))

        return (
          <div
            key={cat}
            className={styles.roadmapCat}
            draggable
            onDragStart={() => setDragItem({ type: 'category', cat })}
            onDragOver={e => e.preventDefault()}
            onDrop={e => {
              e.preventDefault()
              if (dragItem?.type === 'category') moveCategory(dragItem.cat, cat)
              setDragItem(null)
            }}
          >
            <button className={styles.catHeader} onClick={() => toggleCat(cat)}>
              <span className={styles.catIcon}>{CATEGORY_ICONS[cat] || '◎'}</span>
              <span className={styles.catName}>{catLabel(cat).toUpperCase()}</span>
              <span className={styles.catCount}>{skillWord(skills.length)}</span>
              {/* progress inside category */}
              {doneCount > 0 && (
                <span style={{
                  fontSize: '0.68rem', fontFamily: 'var(--font-mono)',
                  color: '#1f533c', marginLeft: 6,
                }}>
                  {doneCount}/{skills.length} ✓
                </span>
              )}
              <span style={{ marginLeft: 'auto', color: 'var(--text-3)', display: 'flex' }}>
                <ChevronIcon dir={isOpen ? 'up' : 'down'}/>
              </span>
            </button>

            {isOpen && (
              <div className={styles.skillList}>
                {sorted.map((s, i) => {
                  const isDone = doneSkills.has(`${cat}::${s.skill}`)
                  const visibleCourses = filterCourses(s.courses, courseFilters)
                  return (
                    <div
                      key={s.skill}
                      className={styles.skillItemWrap}
                      draggable
                      onDragStart={e => {
                        e.stopPropagation()
                        setDragItem({ type: 'skill', cat, skill: s.skill })
                      }}
                      onDragOver={e => e.preventDefault()}
                      onDrop={e => {
                        e.preventDefault()
                        e.stopPropagation()
                        if (dragItem?.type === 'skill' && dragItem.cat === cat) moveSkill(cat, dragItem.skill, s.skill)
                        setDragItem(null)
                      }}
                    >
                    {firstCompletedIndex === i && (
                      <div className={styles.completedDivider}>{t.results.completedSteps}</div>
                    )}
                    <div className={styles.skillItem}
                      style={{ opacity: isDone ? 0.55 : 1, transition: 'opacity 0.2s ease' }}>
                      <div className={styles.skillTopRow}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                        {/* Clickable checkbox */}
                        <button
                          onClick={() => toggleSkill(cat, s.skill)}
                          style={{
                            width: 18, height: 18, borderRadius: 4,
                            border: `1.5px solid ${isDone ? '#4caf82' : 'var(--border)'}`,
                            background: isDone ? '#4caf82' : 'transparent',
                            flexShrink: 0, cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            transition: 'all 0.15s ease',
                            padding: 0,
                          }}
                        >
                          {isDone && (
                            <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                              <path d="M2 6l3 3 5-5" stroke="white" strokeWidth="1.8"
                                strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                          )}
                        </button>
                        <span className={styles.skillName} style={{
                          margin: 0,
                          textDecoration: isDone ? 'line-through' : 'none',
                          color: isDone ? 'var(--text-3)' : 'var(--text)',
                          transition: 'color 0.2s ease',
                        }}>
                          {cap(s.skill)}
                        </span>
                        </div>
                      </div>

                      {!isDone && s.courses.length > 0 && (
                        <div className={styles.courses}>
                          {visibleCourses.length === 0 && (
                            <div className={styles.courseFallback}>{t.results.courseEmptyState || t.results.noCourses}</div>
                          )}
                          {visibleCourses.map((c, j) => (
                            <CourseCard
                              key={`${c.title}-${j}`}
                              course={c}
                              t={t}
                              onOpen={setActiveCourse}
                              copied={copiedMsg === `course-${j}-${i}`}
                              onCopy={e => handleCopyCourse(e, c, `course-${j}-${i}`)}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  </>
)}
        </div>
      </main>

      {/* ─ RIGHT CHAT ─ */}
      {rightOpen && (
      <aside className={styles.chatSidebar} style={{ width: chatSize.width }}>
        <span className={styles.chatResizeHandle} onMouseDown={startChatResize}/>
        <div className={styles.chatHeader}>
          <div className={styles.chatDot}/>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span className={styles.chatTitle}>{t.results.chatTitle}</span>
          <button className={styles.chatCloseBtn} onClick={() => setRightOpen(false)} title={t.results.closeAiPanel}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div className={styles.chatMessages}>
          {messages.length === 0 && (
            <div className={styles.chatEmpty}>
              <span className={styles.chatEmptyIcon}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              </span>
              <span>{t.results.askAnything}</span>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`${styles.msg} ${m.role === 'user' ? styles.msgUser : styles.msgAi}`}>
              <div className={styles.msgOuter}>
                {m.thoughts && !m.streaming && (
                  <details className={styles.thoughtBlock}>
                    <summary>{t.results.thoughts}</summary>
                    <div className={styles.thoughtContent}>{m.thoughts}</div>
                  </details>
                )}
                <div className={`${styles.msgBubble} ${m.streaming ? styles.msgStreaming : ''}`}>
                  {m.content}
                  {m.streaming && !m.content && (
                    <span className={styles.thinkingStatus}>
                      {t.results.analyzing}
                      <span className={styles.thinkingDots}><i/><i/><i/></span>
                    </span>
                  )}
                </div>
                {!m.streaming && m.content && (
                  <button
                    className={`${styles.msgCopyBtn} ${m.role === 'user' ? styles.msgCopyBtnUser : styles.msgCopyBtnAi}`}
                    title={t.results.copy}
                    onClick={() => {
                      copyText(m.content)
                      setCopiedMsg(`msg-${i}`)
                      setTimeout(() => setCopiedMsg(null), 2000)
                    }}
                  >
                    {copiedMsg === `msg-${i}` ? <CheckIcon size={10}/> : <CopyIcon size={10}/>}
                  </button>
                )}
              </div>
            </div>
          ))}

          {/* Suggestions */}
          {messages.length === 1 && messages[0]?.role === 'assistant' && !messages[0]?.streaming && (
            <div className={styles.chatSuggestions}>
              {t.results.suggestions.map(q => (
                <button key={q} className={styles.suggestion} onClick={() => sendMessage(q)}>{q}</button>
              ))}
            </div>
          )}

          {/* Typing */}
          {chatLoading && messages[messages.length - 1]?.content === '' && !messages[messages.length - 1]?.streaming && (
            <div className={`${styles.msg} ${styles.msgAi}`}>
              <div className={styles.msgBubble}>
                <div className={styles.typing}><span/><span/><span/></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef}/>
        </div>

        <div className={styles.chatBottom}>
          <div className={styles.chatToolbar}>
            <DeepModeBtn active={deepMode} onClick={() => setDeepMode(v => !v)} lang={lang} t={t}/>
            <button
              className={`${styles.voiceBtn} ${listening ? styles.voiceBtnActive : ''}`}
              onClick={listening ? stopVoiceInput : startVoiceInput}
              title={listening ? t.results.voiceStop : t.results.voiceRecord}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
              </svg>
            </button>
            <button className={styles.voiceBtn} onClick={speakLastAnswer} title={t.results.voicePlay}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
              </svg>
            </button>
          </div>
          <div className={styles.chatScope}>{voiceNotice || t.results.assistantScope}</div>
          <div className={styles.chatInput}>
            <textarea
              ref={textareaRef}
              className={styles.chatInputField}
              value={input}
              rows={1}
              onChange={e => {
                setInput(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
              }}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
              }}
              placeholder={t.results.chatPlaceholder}
            />
            <button className={styles.chatSend} onClick={() => sendMessage()} disabled={chatLoading || !input.trim()}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>
      )}

      {/* ─ COURSE MODAL ─ */}
      {activeCourse && (
        <CourseModal course={activeCourse} onClose={() => setActiveCourse(null)} t={t}/>
      )}

      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
    </div>
  )
}
