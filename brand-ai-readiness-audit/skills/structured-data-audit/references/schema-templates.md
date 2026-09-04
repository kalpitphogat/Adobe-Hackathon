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
The `sameAs` array is what resolves name collisions and merges independent signals onto
the right entity — always include it.

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
This is the single most quotable format for AI assistants — each Q→A is a self-contained
fact.

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
