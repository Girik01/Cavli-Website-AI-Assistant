"""Retrieval accuracy on the 26-page corpus: dense only vs hybrid (dense + BM25, reciprocal-rank fusion).

  uv run python -m eval.retrieval26 --build   # (re)generate the frozen question set eval/questions26.json (LLM paraphrases FAQs)
  uv run python -m eval.retrieval26           # score dense vs hybrid on the frozen set

A question passes at k when EVERY requirement is met; a requirement is a set of acceptable chunk ids and is met when
any of them is in the top-k. (e.g. "compare X and Y speeds" = two requirements, one per product.)
"""
import hashlib, json, re, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

from app import config
from app.rag import _tokens
from ingest import cavli26 as K

load_dotenv()
HERE = Path(__file__).resolve().parent
QFILE = HERE / "questions26.json"
CHUNKS = json.loads((K.DATA / "chunks.json").read_text())
BYID = {c["id"]: c for c in CHUNKS}
PRODUCTS = json.loads((K.DATA / "products.json").read_text())
RN = {"WW": "worldwide", "NA": "North America", "EAJ": "Eurasia and Japan", "EA": "East Asia", "EU": "Europe", "IN": "India",
      "AN": "Australia and New Zealand", "LA": "Latin America"}


def ids(pred):
    return {c["id"] for c in CHUNKS if pred(c)}


def pick(p, options):
    return options[int(hashlib.md5(p.encode()).hexdigest(), 16) % len(options)]


def templated():
    qs = []

    def q(kind, text, *reqs):
        reqs = [set(r) & set(BYID) for r in reqs]
        if text and all(reqs):
            qs.append(dict(kind=kind, q=text, req=[sorted(r) for r in reqs]))

    for p in PRODUCTS:
        regs = [c["region"] for c in CHUNKS if c["id"].startswith(f"{p}:bands:") and c["region"]]
        if regs:
            r = regs[int(hashlib.md5(p.encode()).hexdigest(), 16) % len(regs)]
            q("bands", pick(p, [f"Which LTE bands does the {p} support in {RN[r]}?", f"{p} band list for {RN[r]}",
                                 f"what frequency bands are available on {p} for {RN[r]}"]), {f"{p}:bands:{r}"})
        else:
            q("bands", f"Which cellular bands does the {p} support?", ids(lambda c, p=p: c["id"].startswith(f"{p}:bands:")))
        q("speeds", pick(p, [f"What is the maximum download speed of the {p}?", f"{p} peak uplink and downlink throughput",
                              f"how fast is the {p} module"]), {f"{p}:speeds", f"{p}:profile"})
        q("interfaces", pick(p, [f"How many UART interfaces does the {p} have?", f"What interfaces and GPIOs does {p} offer?",
                                  f"does {p} have USB and SPI"]), {f"{p}:interfaces", f"{p}:profile"})
        q("gnss", pick(p, [f"Which GNSS constellations does the {p} support?", f"does {p} have GPS", f"{p} positioning support"]),
          {f"{p}:gnss_os", f"{p}:profile"})
        q("os", pick(p, [f"Which operating system does the {p} run?", f"{p} OS", f"is {p} Linux or Android based"]),
          {f"{p}:gnss_os", f"{p}:profile"})
        q("dimensions", pick(p, [f"What are the dimensions of the {p}?", f"{p} size and form factor", f"how big is the {p} module"]),
          {f"{p}:packaging", f"{p}:profile"})
        q("variants", pick(p, [f"What ordering variants of the {p} are available?", f"{p} SKU part numbers",
                                f"which memory options can I order for {p}"]), {f"{p}:variants"})
        q("use_cases", pick(p, [f"What use cases is the {p} suited for?", f"which applications can I build with {p}",
                                 f"{p} industries"]), {f"{p}:use_cases", f"{p}:about", f"{p}:profile"})
        q("about", pick(p, [f"Tell me about the Cavli {p}", f"What is the {p} module?", f"give me an overview of {p}"]),
          {f"{p}:about", f"{p}:profile", f"{p}:highlights"})
    # comparisons: one requirement per product
    pairs = [("CQM212", "CQM215"), ("CQ16", "C16QS"), ("CQS290", "CQS291"), ("C10QM", "CQ10"), ("AQ62", "AQ65"),
             ("CQM211", "CQM212"), ("CQS315", "CQS292"), ("C20QM", "CQ20"), ("CQM220", "CQS315"), ("C11QM", "C10QM")]
    for a, b in pairs:
        for what, kinds in (("download speed", ("speeds", "profile")), ("operating system", ("gnss_os", "profile")),
                            ("interfaces", ("interfaces", "profile"))):
            q("comparison", f"Compare the {what} of {a} and {b}", *[{f"{x}:{k}" for k in kinds} for x in (a, b)])
    # technology / category questions
    cats = {"5G RedCap": "5g-redcap", "LTE Cat 4": "lte-cat4", "LTE Cat 1": "lte-cat1", "5G NR": "5g-nr", "LPWA": "lpwa",
            "Automotive": "automotive", "LTE Cat 1bis": "lte-cat1bis"}
    for cat, slug in cats.items():
        q("category", pick(cat, [f"What is {cat} and what is it good for?", f"Explain {cat} IoT modules", f"when should I choose {cat}"]),
          ids(lambda c, s=slug: c["id"].startswith(f"{s}:") and c["chunk_type"] in ("intro", "explainer", "highlights_advantages", "lineup")))
    q("category", "RedCap vs LTE Cat 4 vs full 5G NR", ids(lambda c: c["chunk_type"] == "table" and "RedCap" in c["text"]))
    q("category", "Which Cavli modules are in the LTE Cat 1bis family?", {"lte-cat1bis:lineup"})
    q("category", "List the Cavli 5G NR modules", {"5g-nr:lineup"})
    # filter / selection questions (answer sets computed from the data)
    def has(text, types=None):
        return ids(lambda c: re.search(text, c["text"], re.I) and (types is None or c["chunk_type"] in types))
    q("filter", "Which module supports Wi-Fi 6 and Bluetooth 5.4?", {"P16QS:highlights", "P16QS:profile", "P16QS:about"})
    q("filter", "Which Cavli module is meant for NB-IoT?", has(r"NB-?IoT|NB2", ("about", "highlights", "profile", "bands", "speeds")) & ids(lambda c: c["product"] == "C41QS"))
    q("filter", "Which module has the highest 5G download speed?", {"CQM215:speeds", "CQM215:profile", "5g-nr:table:2", "5g-nr:lineup"})
    q("filter", "Which modules are automotive grade?", {"AQ62:about", "AQ65:about", "automotive:lineup", "AQ62:highlights", "AQ65:highlights"})
    q("filter", "Which Cavli module has a magnetic stripe reader?", {"P16QS:interfaces", "P16QS:profile"})
    q("filter", "Which modules run Android?", ids(lambda c: c["chunk_type"] in ("gnss_os", "profile") and re.search(r"Android", c["text"])))
    q("filter", "Which module has an Octa-core Kryo CPU?", {"CQS315:about", "CQS315:profile", "CQS315:faq:1"})
    q("filter", "Which modules support band 71?", ids(lambda c: c["chunk_type"] == "bands" and re.search(r"(?<!\d)71(?!\d)", c["text"])))
    q("filter", "Which modules support VoNR?", ids(lambda c: re.search(r"VoNR", c["text"]) and c["chunk_type"] in ("profile", "table", "faq", "highlights")))
    q("filter", "Which modules support NG-eCall?", ids(lambda c: re.search(r"eCall", c["text"]) and c["chunk_type"] in ("profile", "highlights", "faq")))
    q("filter", "Which module has PCIe 4.0?", ids(lambda c: re.search(r"PCIe ?(Gen ?)?4", c["text"]) and c["chunk_type"] in ("interfaces", "profile", "table")))
    q("filter", "Which Cavli modules have a built-in eSIM?", ids(lambda c: re.search(r"eSIM", c["text"], re.I) and c["chunk_type"] in ("profile", "highlights", "variants", "lineup")))
    q("conflict", "What is the peak data rate of the CQM220?", {"CQM220:speeds", "CQM220:conflicts", "CQM220:profile"}, {"CQM220:conflicts"})
    q("conflict", "Does the CQS315 have eSIM?", {"CQS315:conflicts"})
    q("conflict", "Is the CQS315 a 5G RedCap module?", {"CQS315:conflicts", "CQS315:highlights"})
    return qs


def faq_paraphrases():
    from app.store import chat_llm
    llm = chat_llm(max_retries=2)
    faqs = [c for c in CHUNKS if c["chunk_type"] == "faq"]

    def one(c):
        msg = ("Rewrite this website FAQ question the way a real customer would type it into a chatbot. Use different words "
               "and a different sentence shape, keep the module name if there is one, do not copy phrases from the question "
               "or invent facts. Reply with the question only.\n\n" + c["question"])
        return dict(kind="faq_paraphrase", q=llm.invoke(msg).content.strip().strip('"'), req=[[c["id"]]])

    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(one, faqs))


# ------------------------------------------------------------------ retrieval
class Retriever:
    def __init__(self):
        from app.store import get_embeddings
        self.emb = get_embeddings()
        self.client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
        self.docs = CHUNKS
        self.bm25 = BM25Okapi([_tokens(c["text"]) for c in self.docs])
        # body-only index: the header (product / category / section) repeats on every chunk of a product, which makes
        # BM25 match "any chunk of that product" instead of the chunk with the asked-for fact
        self.bm25b = BM25Okapi([_tokens(c["text"].split("\n", 1)[1] if "\n" in c["text"] else c["text"]) for c in self.docs])

    def embed(self, qs):
        return self.emb.embed_documents(qs)

    def dense(self, vec, k=30):
        res = self.client.query_points(K.COLLECTION, query=vec, limit=k, with_payload=["metadata.id"]).points
        return [r.payload["metadata"]["id"] for r in res]

    def keyword(self, q, k=30, body=False):
        s = (self.bm25b if body else self.bm25).get_scores(_tokens(q))
        return [self.docs[i]["id"] for i in np.argsort(-s)[:k] if s[i] > 0]

    @staticmethod
    def rrf(*lists, k=60, w=None):
        w = w or [1] * len(lists)
        sc = defaultdict(float)
        for lst, wt in zip(lists, w):
            for r, i in enumerate(lst):
                sc[i] += wt / (k + r + 1)
        return [i for i, _ in sorted(sc.items(), key=lambda x: -x[1])]


def passed(req, ranked, k):
    top = set(ranked[:k])
    return all(set(r) & top for r in req)


def rank_of(req, ranked):
    """1-based rank at which every requirement is first met (None if never within the list)."""
    worst = 0
    for r in req:
        pos = [i + 1 for i, x in enumerate(ranked) if x in set(r)]
        if not pos:
            return None
        worst = max(worst, min(pos))
    return worst


def main():
    if "--build" in sys.argv:
        qs = templated() + faq_paraphrases()
        QFILE.write_text(json.dumps(qs, indent=1, ensure_ascii=False))
        print(len(qs), "questions frozen to", QFILE)
        return
    qs = json.loads(QFILE.read_text())
    R = Retriever()
    vecs = R.embed([x["q"] for x in qs])
    variants = {"dense": lambda q, v: R.dense(v), "keyword (BM25)": lambda q, v: R.keyword(q),
                "hybrid (RRF dense+BM25)": lambda q, v: R.rrf(R.dense(v), R.keyword(q)),
                "hybrid, dense x2": lambda q, v: R.rrf(R.dense(v), R.keyword(q), w=[2, 1]),
                "hybrid, BM25 body-only": lambda q, v: R.rrf(R.dense(v), R.keyword(q, body=True)),
                "hybrid, body-only, dense x3": lambda q, v: R.rrf(R.dense(v), R.keyword(q, body=True), w=[3, 1])}
    results = {name: [fn(x["q"], v) for x, v in zip(qs, vecs)] for name, fn in variants.items()}
    kinds = sorted({x["kind"] for x in qs})
    ks = (3, 5, 8, 12)
    print(f"{len(qs)} questions\n")
    print(f"{'pass@k (all requirements in top-k)':<38}" + "".join(f"{'k=' + str(k):>8}" for k in ks) + f"{'MRR':>8}")
    for name, rk in results.items():
        row = [sum(passed(x["req"], r, k) for x, r in zip(qs, rk)) / len(qs) for k in ks]
        mrr = np.mean([1 / rank_of(x["req"], r) if rank_of(x["req"], r) else 0 for x, r in zip(qs, rk)])
        print(f"{name:<38}" + "".join(f"{v * 100:7.1f}%" for v in row) + f"{mrr:8.3f}")
    print(f"\nby question type, pass@8 (n)")
    print(f"{'type':<16}{'n':>4}" + "".join(f"{n[:14]:>16}" for n in results))
    for kd in kinds:
        idx = [i for i, x in enumerate(qs) if x["kind"] == kd]
        print(f"{kd:<16}{len(idx):>4}" + "".join(f"{sum(passed(qs[i]['req'], rk[i], 8) for i in idx) / len(idx) * 100:15.0f}%" for rk in results.values()))
    out = [dict(q=x["q"], kind=x["kind"], req=x["req"], **{n: rk[i][:12] for n, rk in results.items()}) for i, x in enumerate(qs)]
    (HERE / "retrieval26_results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
