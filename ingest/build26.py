"""Build / index the 26-page corpus.

  uv run python -m ingest.build26                 # parse + chunk + spec + conflicts (cached HTML), no LLM
  uv run python -m ingest.build26 --refresh       # re-download the 26 pages first
  uv run python -m ingest.build26 --profile       # + LLM product profiles and lineup chunks (cached, ~19 calls)
  uv run python -m ingest.build26 --upsert        # + embed everything and write the new Qdrant collection
"""
import json, sys, uuid
from collections import Counter

from dotenv import load_dotenv

from ingest import cavli26 as K
from ingest import cavli26_spec as S

load_dotenv()


def main(argv):
    products, categories = K.build(refresh="--refresh" in argv)
    specs = S.build_specs(products, categories)
    conflicts = S.find_conflicts(products, categories, specs, K.CHUNKS)
    if "--profile" in argv or "--upsert" in argv:
        rejected = S.build_profiles(products, specs)
        for p in products:
            S.profile_chunk(p, products[p], specs[p], conflicts)
        for cat in K.CATEGORIES.values():
            S.lineup_chunk(cat[0], products, specs)
        S.conflict_chunks(conflicts, products)
        K.write_json("profile_rejected.json", rejected)
        print(f"profile fields rejected by the checks: {len(rejected)}")
    K.write_json("products.json", products)
    K.write_json("categories.json", categories)
    K.write_json("specs.json", specs)
    K.write_json("conflicts.json", conflicts)
    K.write_json("chunks.json", K.CHUNKS)
    K.write_json("normalizations.json", dict(K.NORMALIZATIONS))
    K.report()
    print("conflicts:", dict(Counter(c["type"] for c in conflicts)))
    if "--upsert" in argv:
        upsert(K.CHUNKS)


def upsert(chunks):
    from langchain_openai import OpenAIEmbeddings
    from qdrant_client import QdrantClient, models
    from app import config
    from app.store import ROOT

    emb = OpenAIEmbeddings(model=config.EMBED_MODEL)
    vectors = emb.embed_documents([c["text"] for c in chunks])
    kw = dict(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY) if config.QDRANT_URL else dict(path=str(ROOT / "qdrant_data"))
    client = QdrantClient(**kw)
    if client.collection_exists(K.COLLECTION):
        client.delete_collection(K.COLLECTION)
    client.create_collection(K.COLLECTION, vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE))
    points = []
    for c, v in zip(chunks, vectors):
        meta = {k: c[k] for k in ("id", "product", "series", "category", "page_type", "section", "chunk_type", "region", "topic",
                                  "question", "purchase_faq", "mentions", "legacy_mentions", "url", "tokens")}
        points.append(models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, c["id"])), vector=v,
                                         payload={"page_content": c["text"], "metadata": meta}))
    for i in range(0, len(points), 64):
        client.upsert(K.COLLECTION, points[i:i + 64])
    for f in ("product", "chunk_type", "region", "page_type"):
        client.create_payload_index(K.COLLECTION, f"metadata.{f}", models.PayloadSchemaType.KEYWORD)
    print(f"upserted {len(points)} points into '{K.COLLECTION}' ({'cloud' if config.QDRANT_URL else 'local'})")


if __name__ == "__main__":
    main(sys.argv[1:])
