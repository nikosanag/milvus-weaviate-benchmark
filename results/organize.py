import os
import shutil
import time
from datetime import datetime

def organizer():
    cur_dir = os.getcwd()

    files = [f for f in os.listdir(cur_dir) if os.path.isfile(f)]

    dataset_names = [
        "glove-25-angular",
        "glove-100-angular",
        "deep-image-96-angular",
        "gist-960-euclidean",
        "h-and-m-2048-angular-filters",
        "h-and-m-2048-angular-no-filters",
        "gist-960-angular",
        "laion-small-clip",
        "dbpedia-openai-1M-1536-angular",
        "dbpedia-openai-100K-1536-angular",
        "arxiv-titles-384-angular-no-filters",
        "random-match-keyword-100-angular-filters",
        "random-match-keyword-100-angular-no-filters",
        "random-match-int-100-angular-filters",
        "random-match-int-100-angular-no-filters",
        "random-range-100-angular-no-filters",
        "random-geo-radius-100-angular-filters",
        "random-geo-radius-100-angular-no-filters",
        "random-match-keyword-2048-angular-filters",
        "random-match-keyword-2048-angular-no-filters",
        "random-match-int-2048-angular-filters",
        "random-match-int-2048-angular-no-filters",
        "random-range-2048-angular-filters",
        "random-range-2048-angular-no-filters",
        "random-geo-radius-2048-angular-filters",
        "random-geo-radius-2048-angular-no-filters",
        "random-100",
        "random-100-euclidean",
        "random-100-match-kw-small-vocab-filters",
        "random-768-100-tenants",
        "random-100-match-kw-small-vocab-no-filters",
        "laion-small-clip-no-filters-1",
        "laion-small-clip-no-filters-2",
        "cohere-wiki-1m",
        "laion-1m-no-filters",
        "yandex-t2i-gt-100k",
        "msmarco-sparse-100K",
        "msmarco-sparse-1M",
        "arxiv-titles-384-angular-filters",
        "cohere-wiki-50m-test-only",
        "cohere-wiki-100k-no-filters",
        "cohere-wiki-100k-no-filters-2",
        "laion-1m"
    ]

    found_files = False
    for file_name in files:
        if file_name == 'organize.py' or file_name.startswith('.'):
            continue

        for ds_name in sorted(dataset_names, key=lambda x: -len(x)):
            if ds_name in file_name:
                found_files = True

                # Determine grouping prefix (everything before the dataset name)
                idx = file_name.find(ds_name)
                prefix = file_name[:idx].rstrip('_-')

                if prefix:
                    parent_dir = os.path.join(cur_dir, prefix)
                else:
                    parent_dir = cur_dir

                target_dir = os.path.join(parent_dir, ds_name)

                try:
                    os.makedirs(target_dir, exist_ok=True)
                    if parent_dir != cur_dir:
                        print(f"Created folder: {os.path.relpath(parent_dir, cur_dir)}")
                    else:
                        print(f"Created folder: {ds_name}")

                    src_path = os.path.join(cur_dir, file_name)
                    dst_path = os.path.join(target_dir, file_name)

                    shutil.move(src_path, dst_path)
                    print(f"Moved {file_name} -> {os.path.relpath(target_dir, cur_dir)}/")
                except Exception as e:
                    print(f"Error moving {file_name}: {e}")

                break

    if not found_files:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No new files found. Waiting...")

if __name__ == "__main__":
    print("Dataset Organizer Service Started (Checking every 5 minutes)...")
    try:
        while True:
            organizer()
            time.sleep(300)
    except KeyboardInterrupt:
        print("\nService stopped by user.")

