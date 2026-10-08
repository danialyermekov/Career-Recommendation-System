// Build-time rendering of the same public components for every visitor, without database/Auth calls.
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const babel = require('@babel/core')
const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')
const { JSDOM } = require('jsdom')
const getLocalIdent = require('react-dev-utils/getCSSModuleLocalIdent')
const frontend = path.resolve(__dirname, '..')
const source = path.join(frontend, 'src')
const build = path.join(frontend, 'build')
const seo = require('../src/data/seo.json')
const e = React.createElement
// Public rendering does not initialize a configured Auth client or contact external services.
process.env.REACT_APP_SUPABASE_URL = ''
process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY = ''

// Reuse CRA's installed compiler and CSS-module names; no extra framework or duplicated page copy.
const originalJS = require.extensions['.js']
function compile(module, filename) {
  if (!filename.startsWith(source + path.sep)) return originalJS(module, filename)
  const { code } = babel.transformFileSync(filename, {
    babelrc: false, configFile: false,
    presets: [[require.resolve('@babel/preset-env'), { targets: { node: 'current' } }], [require.resolve('@babel/preset-react'), { runtime: 'automatic' }]],
  })
  module._compile(code, filename)
}
require.extensions['.js'] = compile
require.extensions['.jsx'] = compile
require.extensions['.css'] = (module, filename) => {
  // Match CRA's platform-specific hash inputs exactly, on both Windows and Docker/Linux.
  const context = { rootContext: frontend, resourcePath: filename }
  // css-loader replaces filename-reserved slashes in the base64 hash with a dash.
  module.exports = new Proxy({}, { get: (_, name) => name === '__esModule' ? false : getLocalIdent(context, null, name, {}).replaceAll('/', '-') })
}
const { AppProvider } = require('../src/context/AppContext.jsx')
const Navbar = require('../src/components/Navbar.jsx').default
const Footer = require('../src/components/Footer.jsx').default
const components = {
  '/': require('../src/pages/Hero.jsx').default,
  '/about': require('../src/pages/About.jsx').default,
  '/feedback': require('../src/pages/FeedbackPage.jsx').default,
  '/changelog': require('../src/pages/Changelog.jsx').default,
  '/roadmap': require('../src/pages/ProductRoadmap.jsx').default,
}
const PublicPage = require('../src/pages/PublicPage.jsx').default
const templateDOM = new JSDOM(fs.readFileSync(path.join(build, 'index.html'), 'utf8'))
templateDOM.window.document.getElementById('root').replaceChildren()
templateDOM.window.document.querySelectorAll('#careerflow-schema, meta[name="robots"]').forEach(node => node.remove())
const template = templateDOM.serialize()
const escape = text => text.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
function head(html, metadata, route) {
  html = html.replace(/<title>.*?<\/title>/, `<title>${escape(metadata.title)}</title>`)
  const attributes = { description: metadata.description, 'og:title': metadata.title, 'og:description': metadata.description,
    'og:url': seo.origin + route, 'twitter:title': metadata.title, 'twitter:description': metadata.description }
  for (const [name, content] of Object.entries(attributes)) {
    const attribute = name.startsWith('og:') ? 'property' : 'name'
    html = html.replace(new RegExp(`<meta ${attribute}="${name}"[^>]*>`), `<meta ${attribute}="${name}" content="${escape(content)}"/>`)
  }
  return html.replace(/<link rel="canonical"[^>]*>/, `<link rel="canonical" href="${seo.origin + route}"/>`)
}
const { structuredData: schema } = require('../src/data/structuredData.js')
const shell = head(template, { title: 'CareerFlow | Private application', description: 'Sign in or continue as a guest to use CareerFlow.' }, '/')
  .replace(/<link rel="canonical"[^>]*>/, '').replace(/<meta property="og:url"[^>]*>/, '')
  .replace('</head>', '<meta name="robots" content="noindex, follow"/></head>')
fs.writeFileSync(path.join(build, 'app-shell.html'), shell)
for (const [route, metadata] of Object.entries(seo.pages)) {
  const Component = components[route] || PublicPage
  const content = e(Component, { page: route.slice(1) })
  const tree = e(AppProvider, { initialLanguage: 'en' }, e('div', { className: 'appShell' },
    e('div', { className: 'dataGrid', 'aria-hidden': true }), e(Navbar), route === '/' ? e('main', null, content) : content, e(Footer)))
  const markup = renderToStaticMarkup(tree)
  let html = head(template, metadata, route).replace('<div id="root"></div>', `<div id="root">${markup}</div>`)
    .replace('<html lang="en">', '<html lang="en" data-theme="dark">')
    .replace('</head>', '<meta name="robots" content="index, follow"/></head>')
  if (route === '/') html = html.replace('</head>', `<script id="careerflow-schema" type="application/ld+json">${JSON.stringify(schema).replaceAll('<', '\\u003c')}</script></head>`)
  assert(html.includes('<h1'), `Missing initial content: ${route}`)
  assert(html.includes(`href="${seo.origin + route}"`), `Missing canonical: ${route}`)
  const directory = path.join(build, route.slice(1))
  fs.mkdirSync(directory, { recursive: true })
  fs.writeFileSync(path.join(directory, 'index.html'), html)
}
fs.writeFileSync(path.join(build, 'sitemap.xml'), '<?xml version="1.0" encoding="UTF-8"?>\n' +
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
  Object.keys(seo.pages).map(route => `  <url><loc>${seo.origin + route}</loc></url>`).join('\n') + '\n</urlset>\n')
console.log(`Prerendered ${Object.keys(seo.pages).length} public pages and sitemap; no private data or live reviews included.`)
