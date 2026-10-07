// Mirrors backend/top_profession.py. API values stay untouched; these are display values.
export function getScoreBreakdown(results, profession) {
  const sources = [
    ['profile_match', 'classifier', results.classification_scores || {}, true],
    ['skill_match', 'skill_matcher', results.skill_scores || {}, false],
    ['trend_score', 'demand_trend', Object.fromEntries(Object.entries(results.demand_scores || {}).map(([name, data]) => [name, data.trend_score])), false],
    ['market_share', 'demand_market_share', Object.fromEntries(Object.entries(results.demand_scores || {}).map(([name, data]) => [name, data.market_share])), false],
  ]
  return sources.map(([key, weightKey, values, bySum]) => {
    const numbers = Object.values(values)
    const divisor = (bySum ? numbers.reduce((sum, value) => sum + value, 0) : Math.max(0, ...numbers)) || 1
    const raw = values[profession] || 0
    const value = raw / divisor
    const weight = results.scoring_weights?.[weightKey]
    return { key, raw, divisor, value, weight, contribution: weight == null ? null : value * weight * 100 }
  })
}

export const formatMatchPoints = value => (Math.round(Number(value || 0) * 1000) / 10).toFixed(1)
export const formatMatchScore = value => `${formatMatchPoints(value)} / 100`
