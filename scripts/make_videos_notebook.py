"""Collect all videos used in the notebooks listed in _quarto.yml and write
them to a single notebook (also listed in _quarto.yml).

Videos are found as Quarto ``{{< video path >}}`` shortcodes in markdown cells.
Each video is listed under the heading of the notebook it comes from, together
with the nearest preceding section heading and a link to the source notebook.
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = "99-Videos.ipynb"

VIDEO = re.compile(r"\{\{<\s*video\s+(\S+?)(?:\s[^>]*)?>\}\}")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
EXPLICIT_ID = re.compile(r"\s*\{[^}]*?#([\w:.-]+)[^}]*\}\s*$")


def slugify(text):
    """Approximate pandoc's auto-identifier for a heading."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^\w\s.-]", "", text.lower()).strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"^[^a-z]+", "", text)
    return text or "section"


def chapter_notebooks():
    config = yaml.safe_load((ROOT / "_quarto.yml").read_text(encoding="utf-8"))
    chapters = config["book"]["chapters"]
    return [c for c in chapters if isinstance(c, str) and c.endswith(".ipynb") and c != OUTPUT]


def find_videos(path):
    """Return (heading, anchor, video path) triples in document order."""
    nb = json.loads((ROOT / path).read_text(encoding="utf-8"))
    found = []
    heading = anchor = None
    seen = {}
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        source = cell["source"]
        text = source if isinstance(source, str) else "".join(source)
        previous = ""
        for line in text.splitlines():
            match = HEADING.match(line)
            # A heading right after a ":::{...}" line is a callout title, not a section.
            if match and not previous.startswith(":::"):
                heading = match.group(2)
                explicit = EXPLICIT_ID.search(heading)
                if explicit:
                    anchor = explicit.group(1)
                    heading = heading[: explicit.start()]
                else:
                    anchor = slugify(heading)
                    count = seen.get(anchor, 0)
                    seen[anchor] = count + 1
                    if count:
                        anchor = f"{anchor}-{count}"
            for video in VIDEO.findall(line):
                found.append((heading, anchor, video))
            if line.strip():
                previous = line.strip()
    return found


def markdown_cell(text):
    lines = text.split("\n")
    source = [line + "\n" for line in lines[:-1]] + [lines[-1]]
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def build_notebook(videos_by_notebook):
    cells = [markdown_cell("# Videos\n\nAll videos used in the notebooks, collected in one place.")]
    for path, videos in videos_by_notebook.items():
        if not videos:
            continue
        cells.append(markdown_cell(f"## {Path(path).stem}"))
        for heading, anchor, video in videos:
            title = f"### {heading}\n\n" if heading else ""
            target = f"{path}#{anchor}" if anchor else path
            label = f"{Path(path).stem}, section \"{heading}\"" if heading else Path(path).stem
            link = f"\n\n[Go to this video in the chapter: {label}]({target})"
            cells.append(markdown_cell(f"{title}{{{{< video {video} >}}}}{link}"))
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def update_quarto_config():
    """Add the notebook to the chapters, before the references page."""
    path = ROOT / "_quarto.yml"
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^\s*-\s*{re.escape(OUTPUT)}\s*$", text, re.M):
        return False
    references = re.search(r"^(\s*)-\s*references\.qmd\s*$", text, re.M)
    if references:
        entry = f"{references.group(1)}- {OUTPUT}\n"
        text = text[: references.start()] + entry + text[references.start():]
    else:
        last = list(re.finditer(r"^(\s*)-\s*\S+\.(?:ipynb|qmd)\s*$", text, re.M))[-1]
        text = text[: last.end()] + f"\n{last.group(1)}- {OUTPUT}" + text[last.end():]
    path.write_text(text, encoding="utf-8")
    return True


def main():
    videos = {path: find_videos(path) for path in chapter_notebooks()}
    result = json.dumps(build_notebook(videos), indent=1, ensure_ascii=False) + "\n"
    target = ROOT / OUTPUT
    if not target.exists() or target.read_text(encoding="utf-8") != result:
        target.write_text(result, encoding="utf-8")
    update_quarto_config()


if __name__ == "__main__":
    main()
