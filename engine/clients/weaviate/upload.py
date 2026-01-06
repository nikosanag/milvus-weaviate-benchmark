import uuid
from typing import List

from weaviate import WeaviateClient
from weaviate.classes.data import DataObject
from weaviate.connect import ConnectionParams

from dataset_reader.base_reader import Record
from engine.base_client.upload import BaseUploader
from engine.clients.weaviate.config import WEAVIATE_CLASS_NAME, WEAVIATE_DEFAULT_PORT


class WeaviateUploader(BaseUploader):
    client: WeaviateClient = None
    upload_params = {}
    collection = None
    _vector_dim = None

    @classmethod
    def init_client(cls, host, distance, connection_params, upload_params):
        url = f"http://{host}:{connection_params.get('port', WEAVIATE_DEFAULT_PORT)}"
        cls.client = WeaviateClient(
            ConnectionParams.from_url(url, 50051), skip_init_checks=True
        )
        cls.client.connect()
        cls.upload_params = upload_params
        cls.connection_params = connection_params
        cls.collection = cls.client.collections.get(
            WEAVIATE_CLASS_NAME, skip_argument_validation=True
        )
        cls._vector_dim = None

    @classmethod
    def upload_batch(cls, batch: List[Record]):
        objects = []
        for record in batch:
            _id = uuid.UUID(int=record.id)
            _property = record.metadata or {}
            objects.append(
                DataObject(properties=_property, vector=record.vector, uuid=_id)
            )
            # Capture vector dimension from first record
            if cls._vector_dim is None and record.vector is not None:
                cls._vector_dim = len(record.vector)
        if len(objects) > 0:
            cls.collection.data.insert_many(objects)

    @classmethod
    def post_upload(cls, distance):
        """Collect collection stats after upload completes."""
        post = {}

        # Get total object count via aggregate
        try:
            agg_result = cls.collection.aggregate.over_all(total_count=True)
            post["num_entities"] = agg_result.total_count
        except Exception as e:
            post["aggregate_error"] = str(e)
            post["num_entities"] = None

        # Get cluster/node stats for storage info
        try:
            nodes = cls.client.cluster.nodes(
                collection=WEAVIATE_CLASS_NAME,
                output="verbose"
            )
            node_info = []
            total_object_count = 0
            total_shard_count = 0

            for node in nodes:
                node_data = {}
                try:
                    node_data["name"] = node.name
                    node_data["status"] = node.status
                    node_data["version"] = node.version
                    if hasattr(node, "stats") and node.stats:
                        node_data["stats"] = {
                            "object_count": node.stats.object_count,
                            "shard_count": node.stats.shard_count,
                        }
                        total_object_count += node.stats.object_count
                        total_shard_count += node.stats.shard_count
                    if hasattr(node, "shards") and node.shards:
                        shard_info = []
                        for shard in node.shards:
                            shard_data = {
                                "name": shard.name,
                                "object_count": shard.object_count,
                                "vector_indexing_status": shard.vector_indexing_status,
                                "vector_queue_length": shard.vector_queue_length,
                                "compressed": shard.compressed,
                            }
                            if hasattr(shard, "loaded"):
                                shard_data["loaded"] = shard.loaded
                            shard_info.append(shard_data)
                        node_data["shards"] = shard_info
                except Exception:
                    pass
                node_info.append(node_data)

            post["cluster_nodes"] = node_info
            post["total_object_count"] = total_object_count
            post["total_shard_count"] = total_shard_count
        except Exception as e:
            post["cluster_error"] = str(e)

        # Get collection config for index info
        try:
            config = cls.client.collections.export_config(WEAVIATE_CLASS_NAME)
            if config:
                # Convert to dict if possible
                try:
                    post["collection_config"] = config.to_dict() if hasattr(config, "to_dict") else str(config)
                except Exception:
                    post["collection_config"] = str(config)
        except Exception as e:
            post["config_error"] = str(e)

        # Estimate storage based on vector dimension and count
        try:
            if post.get("num_entities") and cls._vector_dim:
                # Estimate: num_vectors * dim * 4 bytes (float32) for raw vectors
                raw_vector_bytes = post["num_entities"] * cls._vector_dim * 4
                post["estimated_raw_vector_bytes"] = raw_vector_bytes
                post["vector_dimension"] = cls._vector_dim
        except Exception:
            pass

        return post

    @classmethod
    def delete_client(cls):
        if cls.client is not None:
            cls.client.close()

