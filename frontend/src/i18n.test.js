import { translations } from './i18n'

test('public beta elements and policy content have complete EN/RU/KZ translations', () => {
  for (const lang of ['ru', 'kk']) {
    expect(Object.keys(translations[lang].beta).sort()).toEqual(Object.keys(translations.en.beta).sort())
    for (const key of Object.keys(translations.en.beta)) expect(translations[lang].beta[key]).toBeTruthy()
  }
})

test('public product pages have matching translated keys and roadmap items', () => {
  for (const lang of ['ru', 'kk']) {
    expect(Object.keys(translations[lang].product).sort()).toEqual(Object.keys(translations.en.product).sort())
    expect(Object.keys(translations[lang].product.roadmapItems).sort()).toEqual(Object.keys(translations.en.product.roadmapItems).sort())
    expect(translations[lang].product.howSteps).toHaveLength(5)
    expect(translations[lang].product.mvpChanges).toHaveLength(4)
  }
})

const supportedLanguages = ['en', 'ru', 'kk']

test.each(['en', 'ru', 'kk'])('%s translates the complete walkthrough and preview', lang => {
  expect(Object.keys(translations[lang].experience).sort()).toEqual(Object.keys(translations.en.experience).sort())
  expect(translations[lang].experience.steps).toHaveLength(5)
  expect(translations[lang].experience.suggestions).toHaveLength(3)
  expect(translations[lang].experience.remaining(2, 3)).toContain('2')
})

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
