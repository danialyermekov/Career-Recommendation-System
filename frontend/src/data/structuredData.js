import seo from './seo.json'

export const structuredData = { '@context': 'https://schema.org', '@graph': [
  { '@type': 'WebSite', '@id': seo.origin + '/#website', name: 'CareerFlow', url: seo.origin + '/', description: seo.pages['/'].description, inLanguage: 'en' },
  { '@type': 'WebApplication', '@id': seo.origin + '/#application', name: 'CareerFlow', url: seo.origin + '/',
    description: seo.pages['/'].description, applicationCategory: 'EducationalApplication', operatingSystem: 'Any operating system with a modern web browser',
    browserRequirements: 'JavaScript required for recommendations and interactive features.', image: [seo.image, seo.origin + '/icon-512.png'] },
] }
