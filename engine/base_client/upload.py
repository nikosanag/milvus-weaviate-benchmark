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
        # completion_events: list of tuples (completion_time_since_start, batch_size, batch_latency)
        completion_events = []
        start = time.perf_counter()
        parallel = self.upload_params.get("parallel", 1)
        batch_size = self.upload_params.get("batch_size", 64)

        if parallel == 1:
            # Initialize client in parent process for serial uploads
            self.init_client(
                self.host, distance, self.connection_params, self.upload_params
            )
            for batch in iter_batches(tqdm.tqdm(records), batch_size):
                bs = len(batch)
                records_per_batch.append(bs)
                batch_latency = self._upload_batch(batch)
                latencies.append(batch_latency)
                completion_events.append((time.perf_counter() - start, bs, batch_latency))
        else:
            ctx = get_context(self.get_mp_start_method())

            def _batched_records():
                for batch in iter_batches(tqdm.tqdm(records), batch_size):
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
                # Submit tasks and record completion times in callbacks in the parent process.
                async_jobs = []

                def make_cb(bs):
                    def _cb(batch_latency):
                        # Record wall-clock completion time and the batch latency reported by worker
                        completion_events.append((time.perf_counter() - start, bs, batch_latency))
                    return _cb

                for batch in _batched_records():
                    bs = len(batch)
                    records_per_batch.append(bs)
                    job = pool.apply_async(self.__class__._upload_batch, args=(batch,), callback=make_cb(bs))
                    async_jobs.append(job)

                # Wait for all jobs to finish
                for j in async_jobs:
                    j.wait()

            # Initialize client in parent process for post-upload operations
            self.init_client(
                self.host, distance, self.connection_params, self.upload_params
            )

            # Extract latencies in completion order
            latencies = [e[2] for e in completion_events]

        upload_time = time.perf_counter() - start

        total_records = sum(records_per_batch)
        progress_times = {}
        if total_records > 0 and completion_events:
            # Fractions: 10%, 20%, ..., 90%
            fractions = [i / 10.0 for i in range(1, 10)]
            thresholds = {f: total_records * f for f in fractions}
            remaining = set(fractions)
            # Ensure completion events are ordered by actual wall-clock completion
            completion_events.sort(key=lambda x: x[0])
            processed = 0
            for completion_time, bs, _batch_latency in completion_events:
                processed += bs
                for fraction in sorted(list(remaining)):
                    if processed >= thresholds[fraction]:
                        progress_times[fraction] = completion_time
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
