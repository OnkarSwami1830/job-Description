"""Batch CLI for extracting structured job data from the supplied CSV."""

import argparse
import csv
import json
from pathlib import Path

from .extractors import extract_record


def load_taxonomy(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def process_file(input_path: Path, output_path: Path, taxonomy_path: Path) -> int:
    taxonomy = load_taxonomy(taxonomy_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = ["job_id", "job_title", "company", "job_role", "experience", "education", "skills"]
        with output_path.open("w", encoding="utf-8", newline="") as destination:
            writer = csv.DictWriter(destination, fieldnames=fieldnames)
            writer.writeheader()
            count = 0
            for row in reader:
                record = extract_record(row, taxonomy)
                record["skills"] = json.dumps(record["skills"], ensure_ascii=True)
                writer.writerow(record)
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract roles, skills, experience, and education from job descriptions.")
    parser.add_argument("--input", type=Path, default=Path("job_title_des.csv"))
    parser.add_argument("--output", type=Path, default=Path("output/extracted_jobs.csv"))
    parser.add_argument("--taxonomy", type=Path, default=Path("data/skill_taxonomy.json"))
    args = parser.parse_args()
    count = process_file(args.input, args.output, args.taxonomy)
    print(f"Extracted {count} job descriptions to {args.output}")


if __name__ == "__main__":
    main()
