# 26-page corpus: chunking strategy as built

Corpus: 7 category pages + 19 product pages of cavliwireless.com (URL list in `ingest/cavli26.py`).
Qdrant collection: `cavli_modules` (425 points, cosine, `text-embedding-3-small`). The older `cavli_assistant` collection is untouched.

```
uv run python -m ingest.build26                 # fetch (cached) -> parse -> chunk -> specs + conflicts, no LLM
uv run python -m ingest.build26 --profile       # + product profiles (LLM, cached) + lineup + conflict chunks
uv run python -m ingest.build26 --upsert        # + embed and write the Qdrant collection
uv run python -m eval.retrieval26               # dense vs hybrid on the frozen 351-question set
```

Outputs in `data/cavli26/`: `chunks.json`, `specs.json` (one record per product, every value tagged with its source),
`conflicts.json`, `normalizations.json`, `profile_rejected.json`, `products.json`, `categories.json`, `raw/*.html`.

## What is indexed (425 chunks)

| chunk_type | n | rule |
|---|---|---|
| about / key_highlights / gnss_os / speeds / packaging / interfaces / use_cases | 19 each | one per product page section; highlights and use cases de-duplicated; `*` expanded to "(optional)", `**` to "(requires SDK)"; form factors and 3GPP release live in the packaging chunk; fallback statements are added to the speeds chunk |
| bands | 66 | one per region (all technologies inside); pages with no regions get one per technology (CQM220: 5G, 4G) |
| variants | 14 | SKU list **or** part-number decoder (AQ62/AQ65), plus the page's own regional and variant codes |
| faq | 130 | one per question + answer, topic-tagged, purchase FAQs flagged (`purchase_faq`) |
| intro / explainer / highlights_advantages | 7 / 29 / 7 | category pages, one chunk per section (packed to about 500 tokens, never cut mid-sentence) |
| table | 5 | whole comparison table + the sentence before and after; every cell carries its product name |
| profile | 19 | same fields in the same order for every module (LLM-extracted, see checks below) |
| lineup | 7 | one per category, deterministic one line per module |
| conflict | 8 | one per product whose sources disagree, plus one site-wide |

Every chunk starts with `[Product: X | Category: Y | Section: Z]` (category chunks: `[Category: Y | Page: category overview | Section: Z]`).
Metadata: product, series, category, page_type, section, chunk_type, region, topic, question, purchase_faq, mentions, legacy_mentions, url.

## Never indexed
Nav, hero (name / category / release read as metadata only), promo `cta-block`s, product cards (their facts go to the spec record), downloadable resources
(only the brochure link is kept as metadata), case-study stubs, "Meet our solution consulting team" and everything after it (videos, awards, newsletter, footer).
A scan for 20 chrome strings ("Order Samples", "Featured Videos", "Know More", "Subscribe", ...) finds none; the one "Downloadable Resources" hit is inside a genuine purchase-FAQ answer.

## Conflicts (never resolved silently)
`conflicts.json` keeps both values with their source URL. 14 are flagged: CQS315 eSIM (highlights vs both listed SKUs), CQS315 "5G RedCap" badge on an LTE Cat 4 page,
CQM220 speed (page 220/120 and 150/50 Mbps vs category text 226 and 195/105), CQ16 bands (EU and NA, page vs comparison table) and USIM/GPIO counts, CQ16 eSIM
(highlights vs S00N-only SKUs), AQ62 FAQ 4.4 Gbps vs table 2.5 Gbps, CQM212/215 table NSA figures, C41QS NB1 figures, and "EA" defined as East Asia on 12 pages but Europe-Asia on AQ62/AQ65.
Of your four known cases all four are found; the CQM220 LTE-fallback figure is the 195/105 pair above.

## Normalisations (logged with counts)
12S->I2S, Kyro->Kryo, BDU->BDS, Wi-FI->Wi-Fi, AdrenoTM->Adreno(TM), "Gbps Mbps" -> one unit, footnote digit after "package", "deploymnet", "Technolog y", unit spacing (150Mbps -> 150 Mbps), band lists "1/ 3/ 5" -> "1/3/5".
`BDU->BDS` is an assumption (BeiDou); remove it from `fix()` if you would rather keep the site's text.

## Profile chunk guards (LLM)
Temperature 0, "only the supplied text, null if not stated". Afterwards: every number in a value must appear in the source text; a processor that equals the OS is rejected;
facts that merely repeat Technical Data are dropped. 4 fields were rejected on the last run (`profile_rejected.json`). The eSIM line is deterministic, not LLM.

## Retrieval accuracy (frozen set, `eval/questions26.json`, 351 questions, retrieval only)
Questions: 221 templated (bands, speeds, interfaces, GNSS, OS, dimensions, variants, use cases, about, 30 comparisons, category, 12 filter, 3 conflict) and 130 LLM paraphrases of every FAQ.
A question passes when every required chunk (or an accepted alternative) is in the top k.

| retrieval | k=3 | k=5 | k=8 | k=12 | MRR |
|---|---|---|---|---|---|
| **dense only** | 85.5% | 92.0% | **96.6%** | 97.4% | 0.749 |
| hybrid (dense + BM25, RRF) | 78.1% | 85.5% | 92.9% | 96.9% | 0.678 |
| hybrid, dense weight x2 | 83.2% | 90.9% | 94.6% | 96.9% | 0.703 |
| hybrid, BM25 on body only | 63.5% | 78.1% | 88.6% | 94.0% | 0.591 |
| BM25 only | 53.3% | 61.8% | 69.2% | 80.9% | 0.456 |

Dense only is best, so no BM25 is needed for this corpus. Reason: the context header repeats the product name on every chunk, so keyword scores mostly say
"a chunk of this product" rather than "the chunk with this fact". Hybrid helps only rare-token selection questions ("Wi-Fi 6 and Bluetooth 5.4"), 12 of the 351.

## Limits
- Retrieval only. Answer quality and citation behaviour are not measured here; the app (`app/rag.py`) still points at the old collection.
- The question set is generated from the same chunks (templates + paraphrases), so it is friendlier than real traffic; a hand-written blind set should be added before quoting the numbers externally.
- Remaining dense misses are mostly spec questions where the FAQ chunk with the same question outranks the spec chunk (still a relevant answer, but without exact counts), and "which modules..." selection questions that need several chunks.
- 169 chunks are under 80 tokens (bands, GNSS/OS, speeds, use cases by design) and 4 are over 500 (three whole comparison tables, P16QS about); tables are kept whole by rule.
- Chunk count is 425, not the 300-350 estimated: 130 FAQs plus profile, lineup and conflict chunks.
- Hardware Manual / AT Command Manual are behind a login and not indexed.
