import os
import shutil
import time
from datetime import datetime

def get_hardware_info():
    """Prompt user for hardware specifications."""
    print("\n" + "="*60)
    print("HARDWARE ANALYTICS SETUP")
    print("="*60)
    
    hardware_name = input("Enter hardware name (e.g., 'workstation-30gb', 'server-gpu'): ").strip()
    
    if not hardware_name:
        hardware_name = "unknown-hardware"
    
    # Sanitize hardware name for folder
    hardware_name = hardware_name.replace(" ", "-").replace("/", "-").lower()
    
    print(f"\n✓ Hardware name set to: {hardware_name}")
    print("="*60 + "\n")
    
    return hardware_name

def organizer(hardware_dir):
    cur_dir = os.getcwd()

    files = [f for f in os.listdir(cur_dir) if os.path.isfile(f)]

    # Engine names to recognize in filenames
    engine_names = [
        "milvus-default",
        "milvus-m-16-ef-128",
        "milvus-m-32-ef-128",
        "milvus-m-32-ef-256",
        "milvus-m-32-ef-512",
        "milvus-m-64-ef-256",
        "milvus-m-64-ef-512",
        "milvus-m-100-ef-256",
        "milvus-m-100-ef-512",
        "weaviate-default",
        "qdrant-default",
        "elasticsearch-default",
        "pgvector-default",
        "redis-default",
        "opensearch-default",
    ]

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

                # Find dataset position
                ds_idx = file_name.find(ds_name)
                
                # Extract engine name from the part before dataset
                engine_name = None
                part_before_ds = file_name[:ds_idx].rstrip('_-')
                
                for eng_name in sorted(engine_names, key=lambda x: -len(x)):
                    if eng_name in part_before_ds:
                        engine_name = eng_name
                        break
                
                if not engine_name:
                    # Fallback: treat whole prefix as variant
                    variant = part_before_ds
                    parent_dir = os.path.join(cur_dir, hardware_dir, variant)
                else:
                    # Extract variant (everything before the engine name)
                    eng_idx = part_before_ds.find(engine_name)
                    variant = part_before_ds[:eng_idx].rstrip('_-')
                    
                    if variant:
                        parent_dir = os.path.join(cur_dir, hardware_dir, engine_name, variant)
                    else:
                        parent_dir = os.path.join(cur_dir, hardware_dir, engine_name)

                target_dir = os.path.join(parent_dir, ds_name)

                try:
                    os.makedirs(target_dir, exist_ok=True)
                    rel_path = os.path.relpath(parent_dir, cur_dir)
                    print(f"Created folder: {rel_path}")

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
    hardware_name = get_hardware_info()
    print("Dataset Organizer Service Started (Checking every 15 seconds)...")
    print(f"Organizing results under: {hardware_name}/\n")
    try:
        while True:
            organizer(hardware_name)
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nService stopped by user.")

