import seo from '../data/seo.json'
import { structuredData } from '../data/structuredData'

export function updatePageMetadata(page, t, lang) {
  const path = page === 'hero' ? '/' : `/${page}`
  const metadata = seo.pages[path]
  const publicPage = Boolean(metadata)
  document.title = publicPage && lang === 'en' ? metadata.title : `CareerFlow — ${t.product[page] || t.beta[page] || t.nav.title}`
  const descriptions = { about: t.product.whatText, feedback: t.product.feedbackSubtitle, changelog: t.product.changelogSubtitle, roadmap: t.product.roadmapSubtitle }
  const description = publicPage && lang === 'en' ? metadata.description : descriptions[page] || t.product.whatText
  const meta = (attribute, key, value) => {
    let node = document.head.querySelector(`meta[${attribute}="${key}"]`)
    if (!node) { node = document.createElement('meta'); node.setAttribute(attribute, key); document.head.appendChild(node) }
    node.content = value
  }
  meta('name', 'description', description)
  meta('name', 'robots', publicPage ? 'index, follow' : 'noindex, follow')
  for (const attribute of ['og:title', 'twitter:title']) meta(attribute.startsWith('og:') ? 'property' : 'name', attribute, document.title)
  for (const attribute of ['og:description', 'twitter:description']) meta(attribute.startsWith('og:') ? 'property' : 'name', attribute, description)
  let canonical = document.head.querySelector('link[rel="canonical"]')
  if (publicPage) {
    if (!canonical) { canonical = document.createElement('link'); canonical.rel = 'canonical'; document.head.appendChild(canonical) }
    canonical.href = seo.origin + path
    meta('property', 'og:url', seo.origin + path)
  } else {
    canonical?.remove()
    document.head.querySelector('meta[property="og:url"]')?.remove()
  }
  // Hash-based private views share the root document; never describe their data as public markup.
  if (path !== '/') document.getElementById('careerflow-schema')?.remove()
  else if (!document.getElementById('careerflow-schema')) {
    const node = document.createElement('script')
    node.id = 'careerflow-schema'; node.type = 'application/ld+json'
    node.textContent = JSON.stringify(structuredData)
    document.head.appendChild(node)
  }
}
