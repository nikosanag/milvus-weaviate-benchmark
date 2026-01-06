import time
from multiprocessing import get_context
from typing import Iterable, List

import tqdm

from dataset_reader.base_reader import Record
from engine.base_client.utils import iter_batches


class BaseUploader:
    client = None

    def __init__(self, host, connection_params, upload_params):
        self.host = host
        self.connection_params = connection_params
        self.upload_params = upload_params

    @classmethod
    def get_mp_start_method(cls):
        return None

    @classmethod
    def init_client(cls, host, distance, connection_params: dict, upload_params: dict):
        raise NotImplementedError()

    def upload(
        self,
        distance,
        records: Iterable[Record],
    ) -> dict:
        latencies = []
        records_per_batch = []
        start = time.perf_counter()
        parallel = self.upload_params.get("parallel", 1)
        batch_size = self.upload_params.get("batch_size", 64)

        if parallel == 1:
            # Initialize client in parent process for serial uploads
            self.init_client(
                self.host, distance, self.connection_params, self.upload_params
            )
            for batch in iter_batches(tqdm.tqdm(records), batch_size):
                records_per_batch.append(len(batch))
                latencies.append(self._upload_batch(batch))
        else:
            ctx = get_context(self.get_mp_start_method())

            def _batched_records():
                for batch in iter_batches(tqdm.tqdm(records), batch_size):
                    records_per_batch.append(len(batch))
                    yield batch

            with ctx.Pool(
                processes=int(parallel),
                initializer=self.__class__.init_client,
                initargs=(
                    self.host,
                    distance,
                    self.connection_params,
                    self.upload_params,
                ),
            ) as pool:
                latencies = list(
                    pool.imap(
                        self.__class__._upload_batch,
                        _batched_records(),
                    )
                )
            # Initialize client in parent process for post-upload operations
            self.init_client(
                self.host, distance, self.connection_params, self.upload_params
            )

        upload_time = time.perf_counter() - start

        total_records = sum(records_per_batch)
        progress_times = {}
        if total_records > 0:
            # Fractions: 10%, 20%, ..., 90%
            fractions = [i / 10.0 for i in range(1, 10)]
            thresholds = {f: total_records * f for f in fractions}
            remaining = set(fractions)
            processed = 0
            elapsed_for_fraction = 0.0
            for batch_size_count, batch_latency in zip(records_per_batch, latencies):
                processed += batch_size_count
                elapsed_for_fraction += batch_latency

                for fraction in sorted(remaining):
                    if processed >= thresholds[fraction]:
                        progress_times[fraction] = elapsed_for_fraction
                        remaining.remove(fraction)

                if not remaining:
                    break

        print("Upload time: {}".format(upload_time))

        post_upload_stats = self.post_upload(distance)

        total_time = time.perf_counter() - start

        print(f"Total import time: {total_time}")

        self.delete_client()

        result = {
            "post_upload": post_upload_stats,
            "upload_time": upload_time,
            "total_time": total_time,
            "latencies": latencies,
        }

        # Add progress times for 10%, 20%, ..., 90% if available
        for i in range(1, 10):
            fraction = i / 10.0
            key = f"{i * 10}% uploaded"
            result[key] = progress_times.get(fraction)

        return result

    @classmethod
    def _upload_batch(cls, batch: List[Record]) -> float:
        start = time.perf_counter()
        cls.upload_batch(batch)
        return time.perf_counter() - start

    @classmethod
    def post_upload(cls, distance):
        return {}

    @classmethod
    def upload_batch(cls, batch: List[Record]):
        raise NotImplementedError()

    @classmethod
    def delete_client(cls):
        pass
