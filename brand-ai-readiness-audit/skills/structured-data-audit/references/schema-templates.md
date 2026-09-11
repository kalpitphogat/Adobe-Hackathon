# When to recommend structured data, and which type

**Read this table before the templates.** The audit recommends a schema type only when
the page's role makes that type genuinely applicable. A role that is not in this table
receives **no** schema recommendation at all, because suggesting Product markup for a
documentation page, or FAQPage for a site with no questions, is worse than silence.

| Page role | Type recommended | Accepted as already satisfying it |
|-----------|------------------|-----------------------------------|
| homepage | Organization and WebSite | Organization, WebSite, LocalBusiness, Corporation, Person, NGO, EducationalOrganization, GovernmentOrganization |
| article | Article / NewsArticle / BlogPosting | Article, NewsArticle, BlogPosting, Report, LiveBlogPosting |
| product | Product with Offer, or Service | Product, Offer, AggregateOffer, Service, SoftwareApplication, Course |
| contact | ContactPage with contact points | ContactPage, Organization, LocalBusiness |
| documentation | TechArticle or HowTo | TechArticle, HowTo, APIReference, FAQPage, Article |
| utility, authentication, legal, directory, generic, unknown | **nothing** | n/a |

Two further gates apply before any recommendation is made:

- The page's role must have been classified with **confidence** (high or medium). An
  `unknown` role produces no recommendation, and the abstention is recorded in
  `skipped_checks`.
- The finding is an **improvement**, capped at low severity. Missing structured data is
  never automatically a high-severity defect: it leaves fact extraction to inference from
  prose, it does not make the facts unreadable.

The one structured-data **defect** is a JSON-LD block that fails to parse. That is
unambiguous: consumers discard it, so the site is publishing markup that delivers nothing
while appearing done.

FAQPage is recommended only where real question-and-answer content already exists on the
page. The action is to mark up the questions that are there, never to invent questions to
justify the markup.

---

# Paste-ready JSON-LD templates

Concrete fixes for structured-data findings. Drop the relevant block into a
`<script type="application/ld+json">` in the page `<head>`. Replace placeholder values.

## Organization + WebSite (homepage)
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Acme Widgets",
  "url": "https://acme.example",
  "logo": "https://acme.example/logo.png",
  "description": "Acme makes durable industrial widgets for manufacturers.",
  "sameAs": [
    "https://www.linkedin.com/company/acme-widgets",
    "https://en.wikipedia.org/wiki/Acme_Widgets",
    "https://www.crunchbase.com/organization/acme-widgets"
  ]
}
```
The `sameAs` array states which external profiles refer to the same entity, which helps
resolve name collisions. Include only URLs that genuinely describe this brand; this audit
can observe whether the array is present, not whether any given profile exists.

## Product / Offer (product pages)
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Widget Pro 3000",
  "image": "https://acme.example/widget-pro.jpg",
  "description": "Heavy-duty widget rated for 10,000 cycles.",
  "brand": { "@type": "Brand", "name": "Acme" },
  "offers": {
    "@type": "Offer",
    "price": "129.00",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock",
    "url": "https://acme.example/widget-pro"
  }
}
```

## FAQPage (any page with real Q&A)
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is the widget's cycle rating?",
      "acceptedAnswer": { "@type": "Answer", "text": "The Widget Pro 3000 is rated for 10,000 cycles." }
    }
  ]
}
```
Each question-and-answer pair is self-contained, which is why it is easy to quote. Use
this only for questions the page already answers.

## Article (blog/news)
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "How widgets improved throughput 30%",
  "datePublished": "2026-08-01",
  "dateModified": "2026-08-14",
  "author": { "@type": "Person", "name": "Jane Doe" },
  "publisher": { "@type": "Organization", "name": "Acme Widgets" }
}
```
`datePublished`/`dateModified` let assistants judge recency — pair with a visible `<time>`.

## BreadcrumbList (deep pages)
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://acme.example/" },
    { "@type": "ListItem", "position": 2, "name": "Products", "item": "https://acme.example/products" }
  ]
}
```

## Validation
Always validate: JSON must parse, `@context`/`@type` must be present, and required
properties per type must be filled. An invalid block is silently ignored by consumers,
so it delivers zero benefit — worse than none because it looks done.
