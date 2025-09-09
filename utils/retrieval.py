import json, pickle, numpy as np, faiss, os
from utils.llm import embed_text

DATA_DIR = "data"
FAISS_PATH = os.path.join(DATA_DIR, "recipes.faiss")
META_PATH  = os.path.join(DATA_DIR, "recipe_meta.pkl")
JSON_PATH  = os.path.join(DATA_DIR, "recipes.json")

def load_recipes():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_index():
    data = load_recipes()
    vecs = []
    meta = []
    for r in data:
        text = f"{r['title']} | {', '.join(r['ingredients'])} | {', '.join(r['tags'])} | {'. '.join(r['steps'])}"
        vecs.append(np.array(embed_text(text), dtype='float32'))
        meta.append(r["id"])
    xb = np.vstack(vecs)
    dim = xb.shape[1]
    index = faiss.IndexFlatIP(dim)
    # normalize for cosine sim
    faiss.normalize_L2(xb)
    index.add(xb)
    faiss.write_index(index, FAISS_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump(meta, f)

def search(query: str, k: int = 5):
    import numpy as np, pickle
    # lazy load
    index = faiss.read_index(FAISS_PATH)
    with open(META_PATH, "rb") as f:
        meta = pickle.load(f)
    q = np.array(embed_text(query), dtype='float32')[None, :]
    faiss.normalize_L2(q)
    D, I = index.search(q, k)
    ids = [meta[i] for i in I[0]]
    return ids, D[0]
