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
        "milvus-cluster-default",
        "milvus-m-16-ef-128",
        "milvus-cluster-m-16-ef-128",
        "milvus-m-32-ef-128",
        "milvus-cluster-m-32-ef-128",
        "milvus-m-32-ef-256",
        "milvus-cluster-m-32-ef-256",
        "milvus-m-32-ef-512",
        "milvus-cluster-m-32-ef-512",
        "milvus-m-64-ef-256",
        "milvus-cluster-m-64-ef-256",
        "milvus-m-64-ef-512",
        "milvus-cluster-m-64-ef-512",
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
        "sift-128-euclidean",
        "gist-960-euclidean",
        "dbpedia-openai-100K-1536-angular",
        "dbpedia-openai-1M-1536-angular",
        "h-and-m-2048-angular-no-filters",
        "h-and-m-2048-angular-filters",
        "random-match-keyword-100-angular-filters",
        "random-match-keyword-100-angular-no-filters",
        "arxiv-titles-384-angular-no-filters",
        "arxiv-titles-384-angular-filters"
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

                    # If a file with the same name already exists in the
                    # target directory, avoid overwriting by appending a
                    # timestamp to the incoming filename.
                    if os.path.exists(dst_path):
                        base, ext = os.path.splitext(file_name)
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        new_filename = f"{base}-{timestamp}{ext}"
                        dst_path = os.path.join(target_dir, new_filename)
                        print(f"Destination exists, renaming {file_name} -> {new_filename}")

                    shutil.move(src_path, dst_path)
                    print(f"Moved {os.path.basename(dst_path)} -> {os.path.relpath(target_dir, cur_dir)}/")
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

