import { getScoreBreakdown, formatMatchScore } from './scoring'

test('the displayed contributions reproduce backend sum/max normalization without final rescaling', () => {
  const results = {
    classification_scores: { A: 0.2, B: 0.6 }, skill_scores: { A: 0.15, B: 0.3 },
    demand_scores: { A: { trend_score: 0.4, market_share: 0.2 }, B: { trend_score: 0.8, market_share: 0.6 } },
    scoring_weights: { classifier: 0.38, skill_matcher: 0.35, demand_trend: 0.2, demand_market_share: 0.07 },
  }
  const breakdown = getScoreBreakdown(results, 'A')
  breakdown.forEach((item, index) => expect(item.value).toBeCloseTo([0.25, 0.5, 0.5, 1 / 3][index], 12))
  expect(breakdown.reduce((sum, item) => sum + item.contribution, 0)).toBeCloseTo(39.333333)
  expect(getScoreBreakdown(results, 'B').reduce((sum, item) => sum + item.contribution, 0)).toBeCloseTo(90.5)
  expect(formatMatchScore(0.3933)).toBe('39.3 / 100')
  expect(formatMatchScore(0.9435)).toBe('94.4 / 100')
  expect(getScoreBreakdown({ ...results, skill_scores: { A: 0, B: 0 } }, 'A')[1].value).toBe(0)
  expect(getScoreBreakdown({}, 'A').every(item => item.value === 0 && item.contribution === null)).toBe(true)
})
