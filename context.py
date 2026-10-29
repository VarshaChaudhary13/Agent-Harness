from __future__ import annotations

import argparse
import json
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
}

SKIP_EXTENSIONS = {
    ".xes",  # event logs
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".rar",
    ".7z",
    ".pkl",
    ".pickle",
    ".joblib",
    ".onnx",
    ".pt",
    ".pth",
    ".h5",
    ".mp4",
    ".mp3",
    ".wav",
}


def is_text_file(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def build_tree(root: Path) -> str:
    lines = [root.name + "/"]

    def walk(directory: Path, prefix: str = ""):
        entries = [
            p
            for p in sorted(
                directory.iterdir(),
                key=lambda x: (x.is_file(), x.name.lower()),
            )
            if p.name not in SKIP_DIRS
            and p.suffix.lower() not in SKIP_EXTENSIONS
        ]

        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(prefix + connector + entry.name)

            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                walk(entry, prefix + extension)

    walk(root)
    return "\n".join(lines)


def directory_to_json(root: Path) -> dict:
    items = []

    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue

        if any(part in SKIP_DIRS for part in path.parts):
            continue

        if path.suffix.lower() in SKIP_EXTENSIONS:
            continue

        relative_path = path.relative_to(root).as_posix()

        item = {
            "path": relative_path,
        }

        if is_text_file(path):
            try:
                item["content"] = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except Exception as e:
                item["content"] = f"<<ERROR READING FILE: {e}>>"
        else:
            item["binary"] = True
            item["content"] = None

        items.append(item)

    return {
        "root": root.name,
        "dir_tree": build_tree(root),
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert a directory into an LLM-friendly JSON context."
    )

    parser.add_argument(
        "directory",
        help="Directory to serialize",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="context.json",
        help="Output JSON file",
    )

    args = parser.parse_args()

    root = Path(args.directory).resolve()

    if not root.exists():
        raise FileNotFoundError(root)

    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")

    data = directory_to_json(root)

    output_path = Path(args.output)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Wrote {len(data['items'])} files")
    print(f"✓ Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()