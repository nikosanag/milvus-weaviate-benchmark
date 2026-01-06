import os
import time
from typing import List

from qdrant_client import QdrantClient
from qdrant_client._pydantic_compat import construct
from qdrant_client.http.models import (
    Batch,
    CollectionStatus,
    OptimizersConfigDiff,
    SparseVector,
)

from dataset_reader.base_reader import Record
from engine.base_client.upload import BaseUploader
from engine.clients.qdrant.config import QDRANT_API_KEY, QDRANT_COLLECTION_NAME


class QdrantUploader(BaseUploader):
    client = None
    upload_params = {}

    @classmethod
    def init_client(cls, host, distance, connection_params, upload_params):
        os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "true"
        os.environ["GRPC_POLL_STRATEGY"] = "epoll,poll"
        cls.client = QdrantClient(
            url=host, prefer_grpc=True, api_key=QDRANT_API_KEY, **connection_params
        )
        cls.upload_params = upload_params

    @classmethod
    def upload_batch(cls, batch: List[Record]):
        ids, vectors, payloads = [], [], []
        for point in batch:
            if point.sparse_vector is None:
                vector = point.vector
            else:
                vector = {
                    "sparse": construct(
                        SparseVector,
                        indices=point.sparse_vector.indices,
                        values=point.sparse_vector.values,
                    )
                }

            ids.append(point.id)
            vectors.append(vector)
            payloads.append(point.metadata or {})

        _ = cls.client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=Batch.model_construct(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            ),
            wait=False,
        )

    @classmethod
    def post_upload(cls, _distance):
        # If index building is disabled through the collection settings, enable it
        collection = cls.client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
        if collection.config.optimizer_config.max_optimization_threads == 0:
            cls.client.update_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                optimizer_config=OptimizersConfigDiff(
                    # indexing_threshold=10_000,
                    # Set to a high number to not apply limits, already limited by CPU budget
                    max_optimization_threads=100_000,
                ),
            )

        cls.wait_collection_green()

        post = {}

        # Get collection info with storage stats
        try:
            coll_info = cls.client.get_collection(collection_name=QDRANT_COLLECTION_NAME)

            # Extract key metrics explicitly
            post["num_entities"] = coll_info.points_count
            post["vectors_count"] = coll_info.vectors_count
            post["indexed_vectors_count"] = coll_info.indexed_vectors_count
            post["status"] = str(coll_info.status)
            post["segments_count"] = coll_info.segments_count

            # Get vector dimension from config
            try:
                if coll_info.config and coll_info.config.params:
                    vectors_config = coll_info.config.params.vectors
                    if hasattr(vectors_config, "size"):
                        post["vector_dimension"] = vectors_config.size
                    elif isinstance(vectors_config, dict):
                        # Named vectors case
                        for name, cfg in vectors_config.items():
                            if hasattr(cfg, "size"):
                                post["vector_dimension"] = cfg.size
                                break
            except Exception:
                pass

            # Estimate raw storage if we have dimension and count
            if post.get("num_entities") and post.get("vector_dimension"):
                raw_vector_bytes = post["num_entities"] * post["vector_dimension"] * 4
                post["estimated_raw_vector_bytes"] = raw_vector_bytes

            # Include full collection info as dict for reference
            try:
                info = coll_info.dict() if hasattr(coll_info, "dict") else coll_info.model_dump()
                post["collection_info"] = info
            except Exception:
                try:
                    post["collection_info"] = str(coll_info)
                except Exception:
                    pass

        except Exception as e:
            post["collection_info_error"] = str(e)

        return post

    @classmethod
    def wait_collection_green(cls):
        wait_time = 5.0
        total = 0
        while True:
            time.sleep(wait_time)
            total += wait_time
            collection_info = cls.client.get_collection(QDRANT_COLLECTION_NAME)
            if collection_info.status != CollectionStatus.GREEN:
                continue
            time.sleep(wait_time)
            collection_info = cls.client.get_collection(QDRANT_COLLECTION_NAME)
            if collection_info.status == CollectionStatus.GREEN:
                break
        return total

    @classmethod
    def delete_client(cls):
        if cls.client is not None:
            del cls.client
