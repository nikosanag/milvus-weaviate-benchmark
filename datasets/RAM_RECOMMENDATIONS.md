================================================================================
# RAM Recommendations for Benchmark
================================================================================

**System:** 30 GB RAM

**Recommended Docker RAM allocation:** 16–20 GB (leave ~10–14 GB for the OS and other apps)

---

## Dataset RAM Requirements

### Phase 1 — Light (safe to run both DBs, ~6–8 GB peak)

| Dataset                       | Vectors | Dim  | Index RAM | Build RAM |
|------------------------------:|:-------:|:----:|:---------:|:---------:|
| glove-25-angular              | 1.2M    | 25   | ~1.5 GB   | ~2 GB     |
| glove-100-angular             | 1.2M    | 100  | ~3 GB     | ~4 GB     |
| sift-128-euclidean            | 1M      | 128  | ~3 GB     | ~4 GB     |
| random-match-keyword-100-*    | 1M      | 100  | ~3 GB     | ~4 GB     |

### Phase 2 — Medium (safe to run both DBs, ~8-10 GB peak)

| Dataset                         | Vectors | Dim  | Index RAM | Build RAM |
|--------------------------------:|:-------:|:----:|:---------:|:---------:|
| dbpedia-openai-100K-1536-angular| 100K    | 1536 | ~2 GB     | ~4 GB     |
| h-and-m-2048-angular-no-filters | 105K    | 2048 | ~2.5 GB   | ~4 GB     |
| h-and-m-2048-angular-filters    | 105K    | 2048 | ~3 GB     | ~5 GB     |

### Phase 3 — Heavy (run ONE DB at a time, ~10–12 GB peak)

| Dataset              | Vectors | Dim | Index RAM | Build RAM |
|---------------------:|:-------:|:---:|:---------:|:---------:|
| gist-960-euclidean   | 1M      | 960 | ~8 GB     | ~10 GB    |

### Phase 4 — Very Heavy (run ONE DB at a time, ~12–14 GB peak)

| Dataset                         | Vectors | Dim  | Index RAM | Build RAM |
|--------------------------------:|:-------:|:----:|:---------:|:---------:|
| dbpedia-openai-1M-1536-angular  | 1M      | 1536 | ~10 GB    | ~12 GB    |

---

## RAM Calculation (approximation)

HNSW index memory ≈ vectors × dim × 4 bytes × (1 + M/16)

Where:
- `vectors` = number of vectors
- `dim` = vector dimension
- `4 bytes` = float32
- `M` = HNSW parameter (common values: 16, 32, 64)

Example (glove-100-angular, M=32):

1,183,514 × 100 × 4 × (1 + 32/16) ≈ 1.4 GB (just vectors) + HNSW overhead (≈50–100%) → ~2.1–2.8 GB total

---

## Recommended Run Order

1. START SMALL — verify everything works
   - `glove-25-angular` (fast upload, ~2 min)
2. MEDIUM TESTS
   - `glove-100-angular`
   - `sift-128-euclidean` (L2)
   - `random-match-keyword-100-angular` (with/without filters)
3. HIGH-DIMENSION TESTS
   - `dbpedia-openai-100K-1536-angular`
   - `h-and-m-2048-angular` (no-filters / filters)
4. HEAVY TESTS (one DB at a time)
   - `gist-960-euclidean`
   - `dbpedia-openai-1M-1536-angular`

---

## Docker memory settings (recommended snippets)

### Phase 1–2 (light/medium datasets)

MILVUS (`engine/servers/milvus-single-node/docker-compose.yaml`):

```yaml
services:
  standalone:
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          memory: 3G
    environment:
      - MILVUS_GPU_MEM_POOL_SIZE=0
      - KNOWHERE_GPU_MEM_POOL_SIZE=0

  etcd:
    deploy:
      resources:
        limits:
          memory: 512M

  minio:
    deploy:
      resources:
        limits:
          memory: 512M
```

WEAVIATE (`engine/servers/weaviate-single-node/docker-compose.yaml`):

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
      - LIMIT_RESOURCES=true
      - GOMEMLIMIT=5GiB
      - GOMAXPROCS=4
```

### Phase 3–4 (heavy datasets)

MILVUS (heavy):

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

WEAVIATE (heavy):

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
      - GOMEMLIMIT=12GiB
```

### Quick copy-paste

For MILVUS `standalone` service under the `standalone:` key:

```yaml
deploy:
  resources:
    limits:
      memory: 6G
    reservations:
      memory: 3G
```

For WEAVIATE `weaviate` service under the `weaviate:` key:

```yaml
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

---

## Safety tips

1. BEFORE heavy datasets:
   - Stop other Docker containers
   - Close browser tabs
   - Check `free -h` (aim for 20+ GB available before heavy runs)
2. MONITOR during benchmark:
   - `docker stats`
   - If RAM > 90%, stop and reduce parallelism
3. IF OOM:
   - Reduce `upload_params.parallel` from 16 → 8
   - Reduce `search_params.parallel` from 100 → 50
   - Run datasets one at a time
4. OPTIONAL (skip if limited):
   - `gist-960-euclidean` and `dbpedia-openai-1M-1536-angular` are heavy downloads + high RAM

---

## Estimated total benchmark time

- Per dataset, per engine, per config (7 configs):
  - Upload: 2–30 min (depending on size)
  - Search (8 params): ~5 min
- All 10 datasets × 2 engines × 7 configs:
  - Optimistic: 8–12 hours
  - Realistic: 16–24 hours
  - With heavy datasets: 24–36 hours

Tip: run overnight; start with light datasets during the day to verify setup.

---

_Generated and curated recommendations for running the Milvus/Weaviate benchmark on a 30GB system._
