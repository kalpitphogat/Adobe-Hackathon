# Required properties, and why this bar is stricter than schema.org

## The bar

schema.org marks almost everything optional, deliberately: it is a vocabulary,
not a validator, and it has to describe an enormous range of things.

That permissiveness is not useful for an audit. A `Product` node carrying a name
and nothing else is technically valid and answers nothing. So "required" here
means something narrower:

> Without this property, the markup cannot answer the question the page exists
> to answer.

A product page exists to answer "what is this and what does it cost". A `Product`
with no `offers.price` does not answer it. So `offers.price` is required here
even though schema.org does not require it, and the finding says which bar it is
applying.

## Per type

| page type | expected @type | required |
|---|---|---|
| product | Product | name, offers.price, offers.priceCurrency |
| pricing | Product, Offer, Service, SoftwareApplication | name |
| article | Article, NewsArticle, BlogPosting | headline, datePublished |
| docs | TechArticle, Article, HowTo, APIReference | headline |
| home | Organization, WebSite, LocalBusiness, Person | name |
| contact | ContactPage, Organization, LocalBusiness | — |
| about | AboutPage, Organization, Person | — |
| category | CollectionPage, ItemList | — |

Contact, about and category pages have **no** required properties. Their markup
is useful when present and its absence is not a defect; inventing a requirement
there would manufacture findings.

## Aliases

Different vocabularies spell the same idea differently, and a property supplied
under a documented alias counts as present. `headline` is satisfied by `name`;
`offers.price` is satisfied by `offers.lowPrice` or by a `priceSpecification`.

Without alias handling this check would fire on correct markup, which is the
exact failure mode the whole project is organised against.

A property supplied through an `@id` reference that resolves inside the page
graph also counts. That is how a well-built graph avoids repeating itself, and
penalising it would punish the better implementation.

## Contradiction is worse than absence

`extract.sd.contradicts_visible_content` is scored **higher** than
`extract.sd.absent_on_eligible_page`.

Absent markup means a consumer falls back to reading the prose, which it can
often do successfully. Markup that disagrees with the page means a consumer that
trusts it will confidently state the wrong price. Wrong is worse than missing.

Values are normalised before comparison — currency symbols, thousands
separators, ISO versus display dates, whitespace — so a formatting difference is
never reported as a contradiction. The check fires only on genuine disagreement,
and quotes both values with their locations so the reader can verify it rather
than trust us.

## Eligibility comes first

Before judging any of this, the skill decides whether the page should carry
markup at all. Utility pages — login, 404, cart, checkout, search results — and
pages under the word floor are excluded.

Reporting a missing `Product` node on a 404 page is the most common
structured-data false positive there is, and it is the fastest way to teach a
reader that a tool is not paying attention.
