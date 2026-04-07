from pathlib import Path


def download_input_files(driver) -> None:
    print("=== Starting input download ===")
    input_dir = Path(__file__).resolve().parent.parent / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    print(f"Input directory: {input_dir}")
    print("TODO: Implement menu navigation and input-file download logic.")
    print("=== Input download completed ===\n")
