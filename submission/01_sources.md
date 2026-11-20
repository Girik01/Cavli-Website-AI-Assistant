# Sources used (Assignment 1)

All sources are public pages of cavliwireless.com. Nothing from internal systems, logins or customer data.
26 pages were fetched, parsed and indexed: 7 category pages + 19 module pages. The assistant answers from these only.

**Two modules chosen for the demo focus:** C16QS (LTE Cat 1bis) and CQM220 (5G RedCap). The other 17 modules are indexed as well, which lets the assistant compare and recommend.

## Module pages (19)

| Module | Category | URL | Fetched | Chunks |
|---|---|---|---|---|
| CQM220 | 5G RedCap | https://www.cavliwireless.com/iot-modules/c-series/cqm220 | 2026-11-20 | 16 |
| CQ20 | LTE Cat 4 | https://www.cavliwireless.com/iot-modules/c-series/cq20 | 2026-11-20 | 16 |
| CQS292 | LTE Cat 4 | https://www.cavliwireless.com/iot-modules/c-series/cqs292 | 2026-11-20 | 10 |
| C20QM | LTE Cat 4 | https://www.cavliwireless.com/iot-modules/c-series/c20qm | 2026-11-20 | 20 |
| CQS315 | LTE Cat 4 | https://www.cavliwireless.com/iot-modules/c-series/cqs315 | 2026-11-20 | 21 |
| CQS290 | LTE Cat 4 | https://www.cavliwireless.com/iot-modules/c-series/cqs290 | 2026-11-20 | 17 |
| CQS291 | LTE Cat 4 | https://www.cavliwireless.com/iot-modules/c-series/cqs291 | 2026-11-20 | 10 |
| C10QM | LTE Cat 1 | https://www.cavliwireless.com/iot-modules/c-series/c10qm | 2026-11-20 | 21 |
| CQ10 | LTE Cat 1 | https://www.cavliwireless.com/iot-modules/c-series/cq10 | 2026-11-20 | 16 |
| C11QM | LTE Cat 1 | https://www.cavliwireless.com/iot-modules/c-series/c11qm | 2026-11-20 | 17 |
| CQM211 | 5G NR | https://www.cavliwireless.com/iot-modules/c-series/cqm211 | 2026-11-20 | 16 |
| CQM212 | 5G NR | https://www.cavliwireless.com/iot-modules/c-series/cqm212 | 2026-11-20 | 16 |
| CQM215 | 5G NR | https://www.cavliwireless.com/iot-modules/c-series/cqm215 | 2026-11-20 | 16 |
| C41QS | LPWA | https://www.cavliwireless.com/iot-modules/c-series/c41qs | 2026-11-20 | 17 |
| AQ62 | Automotive, 5G NR | https://www.cavliwireless.com/iot-modules/a-series/aq62 | 2026-11-20 | 23 |
| AQ65 | Automotive, 5G NR | https://www.cavliwireless.com/iot-modules/a-series/aq65 | 2026-11-20 | 14 |
| CQ16 | LTE Cat 1bis | https://www.cavliwireless.com/iot-modules/c-series/cq16 | 2026-11-20 | 21 |
| C16QS | LTE Cat 1bis | https://www.cavliwireless.com/iot-modules/c-series/c16qs | 2026-11-20 | 26 |
| P16QS | LTE Cat 1bis | https://www.cavliwireless.com/iot-modules/c-series/p16qs | 2026-11-20 | 15 |

## Category pages (7)

| Category | URL | Fetched | Chunks |
|---|---|---|---|
| 5G RedCap | https://www.cavliwireless.com/iot-modules/5g-redcap-iot-module | 2026-11-20 | 21 |
| LTE Cat 4 | https://www.cavliwireless.com/iot-modules/lte-Cat4-iot-module | 2026-11-20 | 11 |
| LTE Cat 1 | https://www.cavliwireless.com/iot-modules/lte-Cat1-iot-module | 2026-11-20 | 10 |
| 5G NR | https://www.cavliwireless.com/iot-modules/5g-nr-iot-module | 2026-11-20 | 22 |
| LPWA | https://www.cavliwireless.com/iot-modules/lpwa-iot-module | 2026-11-20 | 12 |
| Automotive | https://www.cavliwireless.com/iot-modules/automotive-grade-iot-module | 2026-11-20 | 14 |
| LTE Cat 1bis | https://www.cavliwireless.com/iot-modules/lte-Cat1-bis-iot-module | 2026-11-20 | 6 |

## Not used, and why

- Hardware manual and AT command manual: behind a login (cep.cavliwireless.com), so not public. Questions about them get the standard "not verified" reply.
- Product brochures (PDF): not indexed in this version. The product pages carry the same specifications.
- Blogs and news: not indexed (marketing text, can disagree with the product pages).
- Excluded on every page: menus, hero banners, promo boxes, videos, download lists, newsletter and footer. Details: `docs/chunking_strategy_26_pages.md`.

## Known disagreements between the sources (kept, not resolved)

- **CQM220 – peak speed**: a speed figure differs from the product page's Technical Data.
- **CQM220 – peak speed**: a speed figure differs from the product page's Technical Data.
- **CQS315 – eSIM**: Key Highlights / category card say 'Integrated eSIM' but every variant SKU listed for ordering is without eSIM.
- **CQS315 – category**: Key Highlights shows a '5G RedCap' badge, but the page category is LTE Cat 4.
- **CQM212 – peak speed**: category comparison table lists a speed figure that is not on the product page (e.g. a different network mode).
- **CQM215 – peak speed**: category comparison table lists a speed figure that is not on the product page (e.g. a different network mode).
- **C41QS – peak speed**: a speed figure differs from the product page's Technical Data.
- **AQ62 – peak speed**: a speed figure differs from the product page's Technical Data.
- **CQ16 – bands EU**: category comparison table and product page list different bands.
- **CQ16 – bands NA**: category comparison table and product page list different bands.
- **CQ16 – eSIM**: Key Highlights / category card say 'Integrated eSIM' but every variant SKU listed for ordering is without eSIM.
- **CQ16 – USIM**: category table says USIM x2 but the product page lists 1.
- **CQ16 – GPIO**: category table says GPIO x4 but the product page lists 3.
- **All – EA**: the region code EA is defined differently on different product pages.
