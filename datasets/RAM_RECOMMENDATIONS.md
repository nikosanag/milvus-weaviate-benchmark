# RAM Recommendations for Vector DB Benchmark

**System:** 30 GB RAM  
**Recommended Docker RAM:** 16–20 GB (leave ~10–14 GB for OS + apps)

---

## Dataset Overview

| Dataset | Vectors | Dim | Distance | Filters | Est. RAM |
|:--------|--------:|----:|:--------:|:-------:|:--------:|
| glove-25-angular | 1.2M | 25 | cosine | ✗ | ~2 GB |
| glove-100-angular | 1.2M | 100 | cosine | ✗ | ~4 GB |
| sift-128-euclidean | 1M | 128 | L2 | ✗ | ~4 GB |
| random-match-keyword-100-angular-no-filters | 1M | 100 | cosine | ✗ | ~4 GB |
| random-match-keyword-100-angular-filters | 1M | 100 | cosine | ✓ | ~4 GB |
| arxiv-titles-384-angular-no-filters | 2.2M | 384 | cosine | ✗ | ~6 GB |
| arxiv-titles-384-angular-filters | 2.2M | 384 | cosine | ✓ | ~6 GB |
| dbpedia-openai-100K-1536-angular | 100K | 1536 | cosine | ✗ | ~4 GB |
| h-and-m-2048-angular-no-filters | 105K | 2048 | cosine | ✗ | ~4 GB |
| h-and-m-2048-angular-filters | 105K | 2048 | cosine | ✓ (24) | ~5 GB |
| gist-960-euclidean | 1M | 960 | L2 | ✗ | ~10 GB |
| dbpedia-openai-1M-1536-angular | 1M | 1536 | cosine | ✗ | ~12 GB |

---

## Run Phases

### Phase 1 — Light (~2–4 GB peak) ✅ Safe to run both DBs

```
glove-25-angular          # Fast baseline, ~2 min upload
glove-100-angular         # Medium cosine test
sift-128-euclidean        # L2/Euclidean distance test
```

### Phase 2 — Medium (~4–6 GB peak) ✅ Safe to run both DBs

```
random-match-keyword-100-angular-no-filters
random-match-keyword-100-angular-filters    # Keyword filter test
arxiv-titles-384-angular-no-filters
arxiv-titles-384-angular-filters            # Category + date filters
dbpedia-openai-100K-1536-angular            # OpenAI embeddings (lighter)
h-and-m-2048-angular-no-filters             # High-dim baseline
h-and-m-2048-angular-filters                # Complex: 24 filter fields!
```

### Phase 3 — Heavy (~10 GB peak) ⚠️ Run ONE DB at a time

```
gist-960-euclidean        # 1M × 960D — RAM intensive!
```

### Phase 4 — Very Heavy (~12 GB peak) ⚠️ Run ONE DB at a time

```
dbpedia-openai-1M-1536-angular    # 1M × 1536D — biggest dataset
```

---

## RAM Estimation Formula

```
HNSW RAM ≈ vectors × dim × 4 bytes × (1 + M/16) × 1.5
```

Where:
- `vectors` = number of vectors
- `dim` = vector dimension  
- `4 bytes` = float32 storage
- `M` = HNSW parameter (typically 16–64)
- `1.5` = overhead factor (metadata, filters, etc.)

**Example (glove-100-angular, M=32):**
```
1,200,000 × 100 × 4 × (1 + 32/16) × 1.5 ≈ 2.2 GB
```

---

## Docker Memory Settings

### Light/Medium Datasets (Phase 1–2)

**Milvus** (`engine/servers/milvus-single-node/docker-compose.yaml`):
```yaml
services:
  standalone:
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          memory: 3G
```

**Weaviate** (`engine/servers/weaviate-single-node/docker-compose.yaml`):
```yaml
services:
  weaviate:
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          memory: 3G
    environment:
      LIMIT_RESOURCES: 'true'
      GOMEMLIMIT: '5GiB'
      GOMAXPROCS: '4'
```

### Heavy Datasets (Phase 3–4)

**Milvus** (heavy):
```yaml
services:
  standalone:
    deploy:
      resources:
        limits:
          memory: 14G
        reservations:
          memory: 8G
```

**Weaviate** (heavy):
```yaml
services:
  weaviate:
    deploy:
      resources:
        limits:
          memory: 14G
        reservations:
          memory: 8G
    environment:
      GOMEMLIMIT: '12GiB'
```

---

## Safety Tips

1. **Before heavy datasets:**
   - Stop other Docker containers
   - Close browser tabs
   - Check `free -h` (aim for 20+ GB available)

2. **Monitor during benchmark:**
   ```bash
   docker stats
   ```
   If RAM > 90%, stop and reduce parallelism.

3. **If OOM occurs:**
   - Reduce `upload_params.parallel`: 16 → 8
   - Reduce `search_params.parallel`: 100 → 50
   - Run datasets one at a time

4. **Skip if limited RAM:**
   - `gist-960-euclidean` (3.6 GB download, ~10 GB RAM)
   - `dbpedia-openai-1M-1536-angular` (~12 GB RAM)

---

## Adding New Datasets

When adding a new dataset to `datasets.json`, estimate RAM usage:

1. **Calculate base memory:**
   ```
   Base = vectors × dim × 4 bytes
   ```

2. **Apply HNSW multiplier:**
   ```
   HNSW = Base × 3 (typical for M=32)
   ```

3. **Add filter overhead (if applicable):**
   - No filters: +0%
   - Simple filters (1-2 fields): +10%
   - Complex filters (10+ fields): +20-30%

4. **Classify the dataset:**
   | Est. RAM | Phase | Run Strategy |
   |:--------:|:-----:|:-------------|
   | < 4 GB | Light | Both DBs OK |
   | 4–6 GB | Medium | Both DBs OK |
   | 6–10 GB | Heavy | One DB at a time |
   | > 10 GB | Very Heavy | One DB at a time |

5. **Required JSON fields:**
   ```json
   {
     "name": "my-dataset-DIM-angular",
     "vector_size": DIM,
     "distance": "cosine",
     "type": "h5",
     "path": "folder/file",
     "link": "https://..."
   }
   ```

6. **Optional (for filtered datasets):**
   ```json
   {
     "schema": {
       "field_name": "keyword",
       ...
     }
   }
   ```

---

## Estimated Benchmark Time

| Phase | Datasets | Upload Time | Search Time |
|:-----:|:--------:|:-----------:|:-----------:|
| 1 | 3 | ~10 min | ~15 min |
| 2 | 7 | ~30 min | ~35 min |
| 3 | 1 | ~20 min | ~10 min |
| 4 | 1 | ~30 min | ~15 min |

**Total (all 12 datasets × 2 engines):**
- Optimistic: 4–6 hours
- Realistic: 8–12 hours
- With retries/issues: 12–16 hours

**Tip:** Run overnight; verify setup with `glove-25-angular` first.

---

## Quick Reference Commands

```bash
# Verify setup with fastest dataset
python3 run.py --datasets "glove-25*" --engines "weaviate-default"

# Run all light datasets
python3 run.py --datasets "glove*,sift*" --engines "*"

# Run filtered datasets only
python3 run.py --datasets "*-filters" --engines "*"

# Skip search (upload only)
python3 run.py --datasets "*" --engines "*" --skip-search

# Skip upload (search only, requires prior upload)
python3 run.py --datasets "*" --engines "*" --skip-upload
```

---

_Generated for Milvus/Weaviate benchmark on 30GB RAM system._
