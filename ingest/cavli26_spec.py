"""Spec records, conflict flags, LLM product profiles and category lineups for the 26-page corpus."""
import hashlib, json, re
from collections import defaultdict

from ingest import cavli26 as K
from ingest.cavli26 import (CAT_SLUG, CATEGORIES, PRODUCTS, REGIONS, add, fix, pairs, parse_bands, parse_interfaces,
                            split_commas, tech_sections)

PROFILE_CACHE = K.DATA / "profile_cache.json"


# ------------------------------------------------------------------ spec records
def parse_card(lines):
    sec = tech_sections(lines)
    bands, _ = parse_bands(sec.get("bands", []))
    return dict(
        category=lines[2] if len(lines) > 2 else None,
        release=next((l for l in lines if l.startswith("3GPP Release")), None),
        os=fix(" ".join(sec.get("os", []))), bands=bands,
        speeds=[(fix(l), fix(v)) for l, v in pairs(sec.get("speeds", []))],
        interfaces=parse_interfaces(" ".join(sec.get("interfaces", []))),
        highlights=[fix(x) for x in split_commas(" ".join(sec.get("highlights", [])))],
    )


def build_specs(products, categories):
    """One record per product. Every value lists where it came from: product_page | category_card | category_table | faq."""
    specs = {}
    for p, r in products.items():
        card = {}
        table = {}
        for c in categories.values():
            if p in c["cards"] and not card:
                card = parse_card(c["cards"][p])
                card["source_url"] = c["url"]
            for t in c["tables"]:
                if p in t.get("facts", {}):
                    table.setdefault(p, {}).update({k: dict(value=v, source="category_table", url=c["url"])
                                                    for k, v in t["facts"][p].items()})
        regions = []
        for e in r["bands"]:
            if e["region"] and e["region"] not in regions:
                regions.append(e["region"])
        specs[p] = dict(
            product=p, series=r["series"], categories=r["categories"], url=r["url"], brochure_url=r["brochure_url"],
            release=dict(value=r["release"], source="product_page"),
            os=dict(value=r["os"], source="product_page"),
            gnss=dict(value=r["gnss"] or None, source="product_page"),
            speeds=dict(value=r["speeds"], source="product_page"),
            packaging=dict(value=r["packaging"], source="product_page"),
            form_factors=dict(value=r["form_factors"], source="product_page"),
            regions=dict(value=regions, source="product_page"),
            bands=dict(value=r["bands"], source="product_page"),
            interfaces=dict(value=r["interfaces"], source="product_page"),
            key_highlights=dict(value=r["highlights"], source="product_page"),
            variants=dict(value=r["variants"], source="product_page"),
            category_card=card, category_table=table.get(p, {}),
            llm_profile={},
        )
    return specs


# ------------------------------------------------------------------ conflicts
SPEED = re.compile(r"(\d+(?:\.\d+)?)\s*(Gbps|Mbps|Kbps)", re.I)
SPEED_CTX = re.compile(r"\b(DL|UL|downlink|uplink|download|upload|peak|data rates?)\b", re.I)
CAT_NAMES = {"5G RedCap", "5G NR", "LTE Cat 1", "LTE Cat 4", "LTE Cat 1bis", "LPWA"}


def mbps(v, u):
    return round(float(v) * {"gbps": 1000, "mbps": 1, "kbps": 0.001}[u.lower()], 3)


def speed_mentions(text):
    for s in re.split(r"(?<=[.!?])\s+|\n", text):
        if SPEED_CTX.search(s):
            for m in SPEED.finditer(s):
                yield mbps(m.group(1), m.group(2)), s.strip()


def bandset(s):
    return frozenset(re.findall(r"(?<!\d)\d+[A-Za-z]?(?!\d)", re.sub(r"\(optional\)", "", s)))


def band_key(e):
    if e["tech"] in ("GSM", "other"):
        return None
    return (e["region"] or "-", "nr" if (e["tech"] or "").upper() in ("NR", "5G") else "lte")


def page_bandsets(entries):
    out = defaultdict(set)
    for e in entries:
        k = band_key(e)
        if k:
            out[k] |= bandset(e["bands"])
    return out


def find_conflicts(products, categories, specs, chunks):
    out = []

    def flag(kind, product, field, note, values, confidence="high"):
        out.append(dict(type=kind, product=product, field=field, note=note, confidence=confidence,
                        values=values, status="unresolved - both values kept, neither chosen"))

    for p, r in products.items():
        sp = specs[p]
        card = sp["category_card"]
        # 1. bands: product page vs category card vs comparison table
        page = page_bandsets(r["bands"])
        if card:
            cb = page_bandsets(card["bands"])
            for k in set(page) & set(cb):
                if page[k] != cb[k]:
                    flag("bands", p, f"bands {k[0]}", "product page and category card list different bands",
                         [dict(source="product_page", url=r["url"], value=sorted(page[k], key=lambda x: int(re.sub(r'\D', '', x)))),
                          dict(source="category_card", url=card["source_url"], value=sorted(cb[k], key=lambda x: int(re.sub(r'\D', '', x))))])
        for label, d in sp["category_table"].items():
            if not label.startswith("Frequency bands"):
                continue
            regs = re.findall(rf"\b({'|'.join(['EAJ', 'EA', 'NA', 'EU', 'IN', 'AN', 'LA', 'WW'])})\b", label.split("/", 1)[-1])
            val = d["value"]
            parts = [x.strip() for x in val.split(";") if x.strip()]
            if any("EU Only" in x for x in parts):
                assign = [(bandset(x), "EU") for x in parts if "EU Only" not in x]
            else:
                assign = []
                for x in parts:
                    m = re.search(r"\((EAJ|EA|NA|EU|IN|AN|LA|WW)\)\s*$", x)
                    assign.append((bandset(x), m.group(1) if m else (regs[0] if len(regs) == 1 else None)))
            for bs, reg in assign:
                if reg and (reg, "lte") in page and page[(reg, "lte")] != bs:
                    flag("bands", p, f"bands {reg}", "category comparison table and product page list different bands",
                         [dict(source="product_page", url=r["url"], value=sorted(page[(reg, 'lte')], key=lambda x: int(re.sub(r'\D', '', x)))),
                          dict(source="category_table", url=d["url"], value=sorted(bs, key=lambda x: int(re.sub(r'\D', '', x))))])
        # 2. speeds: page spec vs card / table / prose that names the product
        spec_nums = {mbps(m.group(1), m.group(2)) for _, v in r["speeds"] for m in SPEED.finditer(v)}
        seen = set()

        def check(text, source, url, own):
            for val, sent in speed_mentions(text):
                if val in spec_nums or (val, sent) in seen:
                    continue
                if own or re.search(rf"\b{p}\b", sent):
                    seen.add((val, sent))
                    flag("speed", p, "peak speed", "a speed figure differs from the product page's Technical Data",
                         [dict(source="product_page", url=r["url"], value="; ".join(f"{l}: {v}" for l, v in r["speeds"])),
                          dict(source=source, url=url, value=sent)], confidence="medium")

        for c in chunks:
            if c["product"] == p and c["chunk_type"] in ("about", "faq", "key_highlights"):
                check(c["text"].split("\n", 1)[1], f"product_page ({c['chunk_type']})", r["url"], True)
            elif c["page_type"] == "category" and p in c["text"] and c["chunk_type"] in (
                    "intro", "explainer", "highlights_advantages", "faq"):
                check(c["text"].split("\n", 1)[1], f"category_page ({c['chunk_type']})", c["url"], False)
        for label, d in sp["category_table"].items():
            if label.startswith("Data transmission") and SPEED.search(d["value"]):
                for m in SPEED.finditer(d["value"]):
                    if mbps(m.group(1), m.group(2)) not in spec_nums and not any(
                            f["product"] == p and f["field"] == "peak speed" and d["value"] in str(f["values"]) for f in out):
                        flag("speed", p, "peak speed", "category comparison table lists a speed figure that is not on the product page (e.g. a different network mode)",
                             [dict(source="product_page", url=r["url"], value="; ".join(f"{l}: {v}" for l, v in r["speeds"])),
                              dict(source="category_table", url=d["url"], value=f"{label}: {d['value']}")], confidence="medium")
                        break
        if card:
            for l, v in card["speeds"]:
                for m in SPEED.finditer(v):
                    if mbps(m.group(1), m.group(2)) not in spec_nums:
                        flag("speed", p, "peak speed", "category card and product page differ",
                             [dict(source="product_page", url=r["url"], value=str(r["speeds"])),
                              dict(source="category_card", url=card["source_url"], value=f"{l}: {v}")])
                        break
        # 3. eSIM: highlights say integrated, but every listed variant SKU is without eSIM
        text_hl = " ".join(r["highlights"] + (card.get("highlights", []) if card else []))
        has_esim_claim = bool(re.search(r"integrated esim", text_hl, re.I))
        v = r["variants"]
        if has_esim_claim and v and v["format"] == "skus" and v["skus"]:
            flags = []
            for s_ in v["skus"]:
                e = s_["attrs"].get("eSIM")
                if e is None:
                    code = [x for x in s_["sku"].split("-")[1:] if x != "mPCIe"][-1]
                    e = "Yes" if code.endswith("H") else ("No" if code.endswith("N") else None)
                flags.append(e)
            if flags and all(f == "No" for f in flags):
                flag("esim", p, "eSIM", "Key Highlights / category card say 'Integrated eSIM' but every variant SKU listed for ordering is without eSIM",
                     [dict(source="product_page key highlights", url=r["url"], value="Integrated eSIM"),
                      dict(source="product_page variants", url=r["url"], value=", ".join(s_["sku"] for s_ in v["skus"]) + " -> eSIM: No")])
        # 4. category badge: a highlight names a category the product is not in
        for h in r["highlights"]:
            if h in CAT_NAMES and h not in r["categories"]:
                flag("category_badge", p, "category", f"Key Highlights shows a '{h}' badge, but the page category is {', '.join(r['categories'])}",
                     [dict(source="product_page key highlights", url=r["url"], value=h),
                      dict(source="product_page hero / category", url=r["url"], value=", ".join(r["categories"]))])
        # 5. interface counts: category table vs product page
        counts = {}
        for it in r["interfaces"]:
            m = re.match(r"^(?:up to\s+)?(\d+)\s*x\s*([A-Za-z()]+)", it, re.I) or re.match(r"^([A-Za-z()]+)\s*x\s*(\d+)", it, re.I)
            if m:
                a, b = m.groups()
                n, nm = (int(a), b) if a.isdigit() else (int(b), a)
                counts[nm.upper()] = counts.get(nm.upper(), 0) + n
        for label, d in sp["category_table"].items():
            if label.startswith("Interfaces / "):
                nm = {"(U)SIM": "USIM"}.get(label.split("/ ", 1)[1].strip(), label.split("/ ", 1)[1].strip()).upper()
                m = re.match(r"^x(\d+)", d["value"])
                if m and nm in counts and counts[nm] != int(m.group(1)):
                    flag("interfaces", p, nm, f"category table says {nm} {d['value']} but the product page lists {counts[nm]}",
                         [dict(source="product_page", url=r["url"], value=f"{counts[nm]}x{nm}"),
                          dict(source="category_table", url=d["url"], value=d["value"])])
    # 6. region code definitions differ between pages (EA)
    defs = defaultdict(list)
    for p, r in products.items():
        v = r["variants"]
        if not v:
            continue
        if v["format"] == "skus":
            for line in v["regional"]:
                m = re.match(r"^EA\s*[–-]\s*(.*)$", line)
                if m:
                    defs[m.group(1).strip().rstrip(".")].append(p)
        else:
            for row in v["rows"]:
                for d in row["decoded"]:
                    m = re.match(r"^EA = (.*)$", d)
                    if m:
                        defs[m.group(1).strip()].append(p)
    if len(defs) > 1:
        flag("region_code", None, "EA", "the region code EA is defined differently on different product pages",
             [dict(source="product pages", url=None, value=f"EA = {k} ({', '.join(v)})") for k, v in defs.items()])
    uniq, seen = [], set()
    for c in out:
        k = (c["type"], c["product"], c["field"], str(c["values"][-1]["value"]))
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq


# ------------------------------------------------------------------ LLM profile (cached)
def _llm_profile(p, r, faq_text, hl):
    from typing import List, Optional
    from pydantic import BaseModel
    from app.store import chat_llm

    class Fact(BaseModel):
        value: Optional[str] = None
        source: Optional[str] = None  # about | key_highlights | technical_data | variants | faq

    class Profile(BaseModel):
        processor: Fact
        gpu: Fact
        wifi_bluetooth: Fact
        esim: Fact
        voice_sms: Fact
        power_saving: Fact
        camera_display: Fact
        fallback: Fact
        applications: Fact
        extra_facts: List[Fact]

    tech = "\n".join([f"GNSS: {r['gnss']}", f"OS: {r['os']}", "Speeds: " + "; ".join(f"{l}: {v}" for l, v in r["speeds"]),
                      "Interfaces: " + ", ".join(r["interfaces"])])
    variants = json.dumps(r["variants"], ensure_ascii=False)[:1800] if r["variants"] else "none"
    src = (f"[about]\n{chr(10).join(r['about'])}\n\n[key_highlights]\n{'; '.join(hl)}\n\n[technical_data]\n{tech}\n\n"
           f"[variants]\n{variants}\n\n[faq]\n{faq_text}")
    llm = chat_llm(timeout=60, max_retries=2).with_structured_output(Profile)
    prompt = (f"Fill a product profile for the Cavli module {p}. Use ONLY the text below; copy numbers exactly; keep each "
              "value to a short phrase. If a field is not stated, leave value null - never guess. 'source' is the tag of the "
              "section the value came from (about, key_highlights, technical_data, variants, faq). fallback = the network "
              "the module falls back to (e.g. 2G, LTE Cat 18). applications = the applications the page names. extra_facts = "
              "specific specifications stated in the FAQ or About that do NOT appear in technical_data (CPU, GPU, Wi-Fi, "
              "Bluetooth, camera, display, eDRX/PSM, VoLTE/VoNR, NG-eCall, security, certifications ...), each as one "
              "short sentence naming the module. processor = a CPU / SoC / MCU name only, never an operating system. Do not repeat "
              "anything already listed in technical_data in extra_facts.\n\n" + src)
    return llm.invoke(prompt).model_dump(), src


def build_profiles(products, specs):
    cache = json.loads(PROFILE_CACHE.read_text()) if PROFILE_CACHE.exists() else {}
    rejected = []
    for p, r in products.items():
        faq_text = "\n".join(f"Q: {f['question']}\nA: {f['answer']}" for f in r["faqs"])
        key = hashlib.sha1(json.dumps([r["about"], r["highlights"], r["speeds"], r["interfaces"], faq_text]).encode()).hexdigest()
        if cache.get(p, {}).get("key") != key:
            prof, src = _llm_profile(p, r, faq_text, r["highlights"])
            cache[p] = dict(key=key, profile=prof, src=src)
            PROFILE_CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
        prof, src = cache[p]["profile"], cache[p]["src"]
        nums_src = set(re.findall(r"\d+(?:\.\d+)?", src))

        def ok(f):  # every number in a value must literally appear in the source text
            return f and f.get("value") and set(re.findall(r"\d+(?:\.\d+)?", f["value"])) <= nums_src

        tech_text = (" ".join(r["interfaces"]) + " " + r["gnss"] + " " + r["os"] + " " + " ".join(f"{l} {v}" for l, v in r["speeds"])
                     + " " + " ".join(r["highlights"])).lower()

        def overlap(value):
            toks = re.findall(r"[a-z0-9.+]{3,}", value.lower())
            return bool(toks) and sum(t_ in tech_text for t_ in toks) / len(toks) >= 0.75

        clean = {}
        for k, f in prof.items():
            if k == "extra_facts":
                keep = []
                for x in f:
                    if x and x.get("value") and overlap(x["value"]):
                        continue  # already in Technical Data / Key Highlights
                    if ok(x) or (x and x.get("value") and not re.search(r"\d", x["value"])):
                        keep.append(x)
                    elif x and x.get("value"):
                        rejected.append((p, k, x["value"]))
                clean[k] = keep
            elif k == "processor" and f and f.get("value") and (f["value"].lower() in r["os"].lower() or r["os"].lower() in f["value"].lower()):
                rejected.append((p, k, f["value"] + "  (is the OS, not a processor)"))
                clean[k] = dict(value=None, source=None)
            elif ok(f) or (f and f.get("value") and not re.search(r"\d", f["value"])):
                clean[k] = f
            else:
                if f and f.get("value"):
                    rejected.append((p, k, f["value"]))
                clean[k] = dict(value=None, source=None)
        specs[p]["llm_profile"] = clean
    return rejected


# ------------------------------------------------------------------ extra chunks
def _fmt_speeds(rows):
    return "; ".join(f"{l}: {v}" for l, v in rows) if rows else "not stated on the site"


def esim_line(r, flagged):
    hl = [h for h in r["highlights"] if re.search("esim", h, re.I)]
    v, parts = r["variants"], []
    if hl:
        parts.append("Key Highlights say: " + "; ".join(hl))
    if v and v["format"] == "skus" and v["skus"]:
        flags = []
        for s_ in v["skus"]:
            e = s_["attrs"].get("eSIM")
            if e is None:
                code = [x for x in s_["sku"].split("-")[1:] if x != "mPCIe"][-1]
                e = "Yes" if code.endswith("H") else ("No" if code.endswith("N") else None)
            flags.append(e)
        known = [f for f in flags if f]
        if known:
            parts.append(f"{sum(f == 'Yes' for f in known)} of {len(known)} listed variant SKUs include eSIM")
    elif v and v["format"] == "decoder":
        parts.append("ordering code has an 'eSIM + Hubble' option (H = with, N = without)")
    if not parts:
        return "not stated on the site"
    return "; ".join(parts) + ("  [CONFLICT between sources - see 'Source conflicts' chunk]" if flagged else "")


def profile_chunk(p, r, sp, conflicts=()):
    pr = sp["llm_profile"]
    v = lambda k: (pr.get(k) or {}).get("value") or "not stated on the site"
    lines = [
        f"- Category: {', '.join(r['categories'])}",
        f"- 3GPP release: {r['release'] or 'not stated on the site'}",
        f"- Processor: {v('processor')}" + (f" (GPU: {v('gpu')})" if (pr.get('gpu') or {}).get('value') else ""),
        f"- Operating system: {r['os'] or 'not stated on the site'}",
        f"- Peak speeds: {_fmt_speeds(r['speeds'])}",
        f"- Fallback: {v('fallback')}",
        f"- GNSS: {r['gnss'] or 'not stated on the site'}",
        f"- Wi-Fi / Bluetooth: {v('wifi_bluetooth')}",
        f"- eSIM: {esim_line(r, any(c['type'] == 'esim' and c['product'] == p for c in conflicts))}",
        f"- Form factor: {', '.join(r['form_factors']) or 'not stated on the product page'}",
        f"- Interfaces: {', '.join(r['interfaces']) or 'not stated on the site'}",
        f"- Regions (band sets listed): {', '.join(sp['regions']['value']) or 'not broken down by region'}",
        f"- Voice / SMS: {v('voice_sms')}",
        f"- Power saving: {v('power_saving')}",
        f"- Applications: {v('applications')}",
    ]
    tbl = sp["category_table"]
    keep = ("Operating temperature", "Extended temperature", "Weight", "Supply voltage", "CPU", "Memory", "Voice",
            "Baseband", "Protocols", "PSM", "Antenna", "Carrier Aggregation", "Regions")
    extra = [f"{k.split(' / ')[-1]}: {d['value']}" for k, d in tbl.items() if any(k.split(" / ")[-1].startswith(x) for x in keep)]
    if extra:
        lines.append("- From the category comparison table: " + "; ".join(extra))
    facts = [x["value"] for x in pr.get("extra_facts", []) if x.get("value")]
    if facts:
        lines.append("- Additional facts (About / FAQ): " + " ".join(facts))
    if any(c["product"] == p for c in conflicts):
        lines.append("- Source conflicts flagged: yes - see the 'Source conflicts' chunk for " + p)
    cats = r["categories"]
    add(cid=f"{p}:profile", header=f"[Product: {p} | Category: {', '.join(cats)} | Section: Product profile]",
        body=f"Normalised product profile of {p} (same fields, same order for every module):\n" + "\n".join(lines),
        product=p, series=r["series"], category=cats, page_type="product", section="Product profile",
        chunk_type="profile", url=r["url"])


def lineup_chunk(cat, products, specs):
    members = [p for p, v in PRODUCTS.items() if cat in v[1]]
    lines = []
    for p in members:
        r, sp = products[p], specs[p]
        sp_ = _fmt_speeds(r["speeds"][:2])
        lines.append(f"- {p} ({r['series']}): {r['release'] or 'release not stated'}; peak speeds {sp_}; OS {r['os'] or 'n/a'}; "
                     f"regions {', '.join(sp['regions']['value']) or 'n/a'}; form factor {', '.join(r['form_factors']) or 'n/a'}.")
    add(cid=f"{CAT_SLUG[cat]}:lineup", header=f"[Category: {cat} | Page: category overview | Section: Module lineup]",
        body=f"Cavli {cat} modules covered here ({len(members)}): {', '.join(members)}.\n" + "\n".join(lines),
        product=None, series=None, category=[cat], page_type="category", section="Module lineup", chunk_type="lineup",
        url=K.category_url(cat))


def conflict_chunks(conflicts, products):
    """One chunk per affected product listing every value from every source; nothing is resolved."""
    by = defaultdict(list)
    for c in conflicts:
        by[c["product"]].append(c)
    for p, cs in by.items():
        lines = []
        for c in cs:
            fmt = lambda x: "/".join(x) if isinstance(x, list) else x
            vals = "\n    ".join(f"{v['source']} says: \"{fmt(v['value'])}\"" for v in c["values"])
            lines.append(f"- {c['field']}: {c['note']}.\n    {vals}")
        if p:
            r = products[p]
            add(cid=f"{p}:conflicts", header=f"[Product: {p} | Category: {', '.join(r['categories'])} | Section: Source conflicts]",
                body=f"Source conflicts for {p} - the site's own sources disagree; both values are kept and neither is chosen:\n" + "\n".join(lines),
                product=p, series=r["series"], category=r["categories"], page_type="product", section="Source conflicts",
                chunk_type="conflict", url=r["url"])
        else:
            add(cid="sitewide:conflicts", header="[Site-wide | Section: Source conflicts]",
                body="Source conflicts across product pages - both values are kept:\n" + "\n".join(lines),
                product=None, series=None, category=[], page_type="product", section="Source conflicts", chunk_type="conflict",
                url=K.BASE + "/iot-modules")
