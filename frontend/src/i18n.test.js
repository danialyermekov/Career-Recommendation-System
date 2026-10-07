import { translations } from './i18n'

const supportedLanguages = ['en', 'ru', 'kk']

const supportedProfessions = [
  'Data Scientist',
  'Data Analyst',
  'Data Engineer',
  'Business Analyst',
  'Machine Learning Engineer',
  'Software Engineer',
  'Cloud Engineer',
]

const roadmapCategories = [
  'programming',
  'libraries',
  'analyst_tools',
  'cloud',
  'databases',
  'webframeworks',
  'other',
  'os',
]

describe('translations', () => {
  test.each(supportedLanguages)('%s has navigation, hero, form, and results dictionaries', lang => {
    expect(translations[lang].nav.steps).toHaveLength(4)
    expect(translations[lang].hero.title).toBeTruthy()
    expect(translations[lang].form.submit).toBeTruthy()
    expect(translations[lang].results.tabs.best).toBeTruthy()
  })

  test.each(supportedLanguages)('%s translates every supported profession', lang => {
    for (const profession of supportedProfessions) {
      expect(translations[lang].professions[profession]).toBeTruthy()
    }
  })

  test.each(supportedLanguages)('%s translates roadmap categories', lang => {
    for (const category of roadmapCategories) {
      expect(translations[lang].categories[category]).toBeTruthy()
    }
  })

  test.each(supportedLanguages)('%s translates chart modes', lang => {
    expect(translations[lang].results.chartModes.bars).toBeTruthy()
    expect(translations[lang].results.chartModes.radar).toBeTruthy()
    expect(translations[lang].results.chartModes.gap).toBeTruthy()
  })
})
