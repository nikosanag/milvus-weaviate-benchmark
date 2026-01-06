import json
import os
from datetime import datetime
from typing import Dict, List, Optional

try:
    import resource
except ImportError:  # pragma: no cover - resource is not available on all platforms
    resource = None

from benchmark import ROOT_DIR
from benchmark.dataset import Dataset
from engine.base_client.configure import BaseConfigurator
from engine.base_client.search import BaseSearcher
from engine.base_client.upload import BaseUploader

RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DETAILED_RESULTS = bool(int(os.getenv("DETAILED_RESULTS", False)))


class BaseClient:
    def __init__(
        self,
        name: str,  # name of the experiment
        engine: str,  # name of the engine
        configurator: BaseConfigurator,
        uploader: BaseUploader,
        searchers: List[BaseSearcher],
    ):
        self.name = name
        self.configurator = configurator
        self.uploader = uploader
        self.searchers = searchers
        self.engine = engine

    @property
    def sparse_vector_support(self):
        return self.configurator.SPARSE_VECTOR_SUPPORT

    @staticmethod
    def _snapshot_system_metrics() -> Dict[str, Dict[str, float]]:
        """Collect a lightweight snapshot of host and client resource usage.

        This is intentionally simple and dependency-free so that every
        benchmark run records at least some system context (CPU/load/memory)
        alongside latency/throughput numbers.
        """

        metrics: Dict[str, Dict[str, float]] = {}

        # Host load averages (Unix only).
        try:
            load1, load5, load15 = os.getloadavg()  # type: ignore[attr-defined]
            metrics["loadavg"] = {"1m": load1, "5m": load5, "15m": load15}
        except (AttributeError, OSError):
            # Not available on this platform; ignore.
            pass

        # Per-process CPU time and RSS (Unix-only via resource module).
        try:
            if resource is not None:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                metrics["cpu_time"] = {
                    "user_s": float(usage.ru_utime),
                    "system_s": float(usage.ru_stime),
                }
                metrics["memory"] = {
                    # ru_maxrss is kilobytes on Linux, bytes on some BSDs;
                    # we store it as-is and document the unit in analysis.
                    "max_rss": float(usage.ru_maxrss),
                }
        except Exception:
            # Best-effort only; do not break benchmarks on metrics failure.
            pass

        return metrics

    def save_search_results(
        self, dataset_name: str, results: dict, search_id: int, search_params: dict
    ):
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
        experiments_file = (
            f"{self.name}-{dataset_name}-search-{search_id}-{timestamp}.json"
        )
        result_path = RESULTS_DIR / experiments_file
        with open(result_path, "w") as out:
            out.write(
                json.dumps(
                    {
                        "params": {
                            "dataset": dataset_name,
                            "experiment": self.name,
                            "engine": self.engine,
                            **search_params,
                        },
                        "results": results,
                    },
                    indent=2,
                )
            )
        return result_path

    def save_upload_results(
        self, dataset_name: str, results: dict, upload_params: dict
    ):
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
        experiments_file = f"{self.name}-{dataset_name}-upload-{timestamp}.json"
        with open(RESULTS_DIR / experiments_file, "w") as out:
            upload_stats = {
                "params": {
                    "experiment": self.name,
                    "engine": self.engine,
                    "dataset": dataset_name,
                    **upload_params,
                },
                "results": results,
            }
            out.write(json.dumps(upload_stats, indent=2))

    def run_experiment(
        self,
        dataset: Dataset,
        skip_upload: bool = False,
        skip_search: bool = False,
        skip_if_exists: bool = True,
        skip_configure: Optional[bool] = False,
    ):
        execution_params = self.configurator.execution_params(
            distance=dataset.config.distance, vector_size=dataset.config.vector_size
        )

        reader = dataset.get_reader(execution_params.get("normalize", False))

        if skip_if_exists:
            glob_pattern = f"{self.name}-{dataset.config.name}-search-*-*.json"
            existing_results = list(RESULTS_DIR.glob(glob_pattern))
            if len(existing_results) == len(self.searchers):
                print(
                    f"Skipping run for {self.name} since it already ran {len(self.searchers)} search configs previously"
                )
                return

        if not skip_upload:
            if not skip_configure:
                print("Experiment stage: Configure")
                self.configurator.configure(dataset)

            print("Experiment stage: Upload")
            upload_metrics_before = self._snapshot_system_metrics()
            upload_stats = self.uploader.upload(
                distance=dataset.config.distance, records=reader.read_data()
            )

            upload_metrics_after = self._snapshot_system_metrics()
            upload_stats["system_metrics"] = {
                "before": upload_metrics_before,
                "after": upload_metrics_after,
            }

            if not DETAILED_RESULTS:
                # Remove verbose stats from upload results
                upload_stats.pop("latencies", None)

            self.save_upload_results(
                dataset.config.name,
                upload_stats,
                upload_params={
                    **self.uploader.upload_params,
                    **self.configurator.collection_params,
                },
            )

        if not skip_search:
            print("Experiment stage: Search")
            for search_id, searcher in enumerate(self.searchers):

                if skip_if_exists:
                    glob_pattern = (
                        f"{self.name}-{dataset.config.name}-search-{search_id}-*.json"
                    )
                    existing_results = list(RESULTS_DIR.glob(glob_pattern))
                    print("Pattern", glob_pattern, "Results:", existing_results)
                    if len(existing_results) >= 1:
                        print(
                            f"Skipping search {search_id} as it already exists",
                        )
                        continue

                search_params = {**searcher.search_params}
                search_metrics_before = self._snapshot_system_metrics()
                search_stats = searcher.search_all(
                    dataset.config.distance, reader.read_queries()
                )
                search_metrics_after = self._snapshot_system_metrics()
                search_stats["system_metrics"] = {
                    "before": search_metrics_before,
                    "after": search_metrics_after,
                }
                if not DETAILED_RESULTS:
                    # Remove verbose stats from search results
                    search_stats.pop("latencies", None)
                    search_stats.pop("precisions", None)

                self.save_search_results(
                    dataset.config.name, search_stats, search_id, search_params
                )
        print("Experiment stage: Done")
        print("Results saved to: ", RESULTS_DIR)

    def delete_client(self):
        self.uploader.delete_client()
        self.configurator.delete_client()

        for s in self.searchers:
            s.delete_client()
