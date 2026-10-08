# Google Search Console and technical SEO

This is release-candidate configuration, not proof of deployment or Google indexing. No Search Console property was created or ownership verified by this task. No Search Console API credentials are needed.

## Owner steps after deploying the verified candidate

1. Open [Google Search Console](https://search.google.com/search-console/welcome), add a **Domain** property and enter `careerflow.live` without a scheme or path. This covers its protocols and subdomains.
2. Copy the exact `google-site-verification=...` TXT value provided by Google. Add a TXT record for the root domain (`@` or the DNS provider's root-name format) at the domain's authoritative DNS provider. Keep existing TXT records. Wait for DNS propagation, click **Verify** in Search Console and retain the verification record. The value is generated for the owner's property; this repository intentionally has no invented token. See [Google's DNS ownership instructions](https://support.google.com/webmasters/answer/9008080).
3. First confirm the deployed `https://careerflow.live/sitemap.xml` returns XML and lists the intended canonical pages. In **Sitemaps**, submit that full URL and review its fetch/processing status. A successful sitemap submission does not establish that every page is indexed. See [Google's Sitemaps report](https://support.google.com/webmasters/answer/7451001).
4. In **URL inspection**, enter `https://careerflow.live/`. Run **Test live URL**; inspect returned HTML, crawl permission, declared canonical and rendered page. Repeat for `/about` and another public route. After Google has processed the pages, compare its selected canonical with the declared canonical.
5. If the deployed page is accessible and indexable, use **Request indexing** in URL inspection. Submit important URLs selectively; indexing is Google's decision and is not immediate or guaranteed. See [URL inspection help](https://support.google.com/webmasters/answer/9012289).
6. Review **Page indexing** for unintended `noindex`, blocked resources, server/redirect errors, missing pages, duplicate canonicals and crawled/discovered-but-not-indexed pages. Private APIs and nonexistent paths are intentionally excluded. Correct the underlying issue, test the live URL and then request validation where offered.
7. In **Performance / Search results**, monitor actual impressions, clicks, CTR, average position, queries and pages over time. Start with the brand query `CareerFlow`, then relevant IT career-guidance queries. Report only observed data; an empty report is not a traffic estimate.

## Implementation

`npm run build` compiles React, renders nine public pages with ReactDOMServer, then checks the resulting artifacts. The same Hero/About/Feedback/Changelog/Roadmap/policy components and translations generate the initial HTML and the interactive application. All visitors receive the same initial English content; there is no bot detection. React starts normally and replaces the static root with the interactive app. This is build-time prerendering, not request-time SSR or hydration.

Indexable routes: `/`, `/about`, `/feedback`, `/changelog`, `/roadmap`, `/privacy`, `/terms`, `/contact`, `/disclaimer`. The last two are existing substantive public pages. Every route has a unique English title/description, self-referencing canonical, Open Graph/Twitter metadata, headings, text and crawlable internal links before JavaScript executes. Metadata definitions are in `frontend/src/data/seo.json`. Existing EN/RU/KZ switching remains interactive; translated content does not have separate URLs, so no hreflang or translated sitemap entries are emitted.

Feedback rows and community roadmap suggestions are loaded through their existing moderated APIs after React starts. No live reviews, ratings, votes, account state, credentials or private recommendation content are fetched during the build or baked into HTML. The static feedback page includes its purpose and form; JavaScript is required to submit, vote or load current community content. Informational content changes require a new build.

FastAPI serves only known public routes, approved root assets and built static/branding resources. Unknown routes and missing assets return 404. Trailing slashes redirect to the canonical path. `robots.txt` allows public crawling and static resources, and names the absolute sitemap URL. The generated sitemap contains only the nine canonical public routes and has no guessed `lastmod` dates.

Private hash views set `noindex`, remove public canonical/JSON-LD and continue to use authorization for data access. Hash fragments never reach the server; direct `/#profile` requests therefore receive the public root document before React selects the private view. Root OAuth callback queries and `/auth/callback` receive an empty private app shell with `noindex` and `no-store` headers. APIs/errors also receive `noindex` and `no-store`. Robots directives are never an access-control boundary.

The homepage JSON-LD describes `WebSite` and `WebApplication`: actual name/URL/description, educational category, browser environment, social image and logo image URL. It deliberately omits pricing assertions, ratings, reviews, organization credentials and usage figures. The 1200×630 PNG social image and optimized horizontal PNG/WebP logos are reused. Source: [Schema.org WebApplication](https://schema.org/WebApplication).

## Canonical domain and ingress

Preferred origin: `https://careerflow.live`. Application requests for HTTP on the production host or for `www.careerflow.live` redirect with 308 to the HTTPS preferred host; tracking parameters do not enter canonicals or sitemap URLs. The local development origin is not redirected to production.

At the existing ingress, configure HTTPS and the same direct HTTP/www redirect. The owner must ensure `www` DNS points to that ingress and its TLS certificate covers `www.careerflow.live`; application code cannot fix DNS or perform TLS before a request reaches it. Uvicorn must trust forwarded headers only from the actual proxy addresses (`FORWARDED_ALLOW_IPS` or `--forwarded-allow-ips` with those addresses). Do not trust arbitrary public forwarding headers. Incorrect proxy scheme handling can create an HTTPS redirect loop; check through the real ingress before promoting the candidate. Keep OAuth callback query values out of ingress logs.

Read-only live inspection on 2026-10-09: HTTP root returned 301 to HTTPS. Windows Invoke-WebRequest retrieved the HTTPS root with 200, but it still contained the existing empty React shell, without prerendered headings. The curl HTTPS attempt timed out, and the local resolver could not resolve `www.careerflow.live`. These are point-in-time observations, not proof of global availability; recheck DNS/TLS/redirects during release.

## Validation and performance

- Schema.org Validator, code mode: both `WebSite` and `WebApplication` detected; **0 errors, 0 warnings**.
- [Google Rich Results Test, code-mode result](https://search.google.com/test/rich-results/result?id=kI7W7o2qwPCkmFyMFB9GMQ): **1 valid Software Application item**, with two noncritical missing optional fields, `offers` and `aggregateRating`. These fields were not invented to remove warnings. This validates the submitted public markup, not the deployed URL, ownership or indexing status.
- Frontend production gzip sizes after deferring the private Results component: initial JS **206.63 kB**, initial CSS **9.18 kB**. Before this SEO phase, the corresponding sizes were **232.38 kB / 17.91 kB**. The Results JS/CSS are separate chunks loaded when needed. These are build-size measurements, not Lighthouse scores or field Core Web Vitals.
- HTML revalidates (`no-cache`); fingerprinted CRA static assets cache for a year with `immutable`; mutable root branding/SEO assets cache for one hour. Logo dimensions reserve layout space. No dependency was added.

See seo-verification.md for exact test results and HTTP/browser evidence. Existing production and owner-controlled DNS/Search Console were not changed. The previous model-expectation failures and external OAuth/account-deletion release checks remain documented in verification-v1.1.md.
