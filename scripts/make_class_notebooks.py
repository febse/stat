"""Create stripped class versions of all notebooks in the root folder and of
the notebooks listed in _quarto.yml.

Code cells are kept unless they contain an ``#ex-no-class`` comment. Selected
markdown content is kept: headings, attribute-marked fenced divs, and solution
divs. The ``.ex-class`` class is removed from retained divs. The results are
written to ./class under the original file names. Relative figure paths are
replaced by raw URLs on the main branch of the repository in _variables.yml.
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "class"

OPEN_DIV = re.compile(r"^\s*:{3,}\s*\{.*\}\s*$|^\s*:{3,}\s*\S+\s*$")
CLOSE_DIV = re.compile(r"^\s*:{3,}\s*$")
ATTR_DIV = re.compile(r"^(\s*:{3,}\s*)\{([^}]*)\}(\s*)$")
EX_CLASS_TOKEN = re.compile(r"(?<!\S)\.ex-class(?=\s|$)")
CLASS_TOKEN = re.compile(r"(?<!\S)\.([A-Za-z_][\w-]*)")


IMAGE = re.compile(r"(!\[[^\]]*\]\()([^)\s]+)")
HTML_SRC = re.compile(r"""(<img\b[^>]*?\bsrc=["'])([^"']+)""")
SCHEME = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//|#)")


def raw_base_url():
    variables = yaml.safe_load((ROOT / "_variables.yml").read_text(encoding="utf-8"))
    return variables["github"].rstrip("/") + "/raw/main/"


def absolutize_figures(text, base_url, notebook_dir):
    def repl(match):
        target = match.group(2)
        if SCHEME.match(target):
            return match.group(0)
        rel = (notebook_dir / target).resolve().relative_to(ROOT).as_posix()
        return match.group(1) + base_url + rel

    return HTML_SRC.sub(repl, IMAGE.sub(repl, text))


def source_text(cell):
    src = cell["source"]
    return "".join(src) if isinstance(src, list) else src


def to_source_lines(text):
    lines = text.splitlines(keepends=True)
    return lines


HEADING = re.compile(r"^#{1,6}\s+\S")
FENCE = re.compile(r"^\s*(```|~~~)")
SOLUTION_HEADING = re.compile(r"^##[ \t]+Solution(?:[ \t]+.*)?[ \t]*$")


def extract_kept_parts(text):
    """Keep top-level headings, attribute divs, and divs headed as solutions."""
    lines = text.splitlines(keepends=True)

    def find_div_end(start):
        depth, in_code = 1, False
        for index in range(start + 1, len(lines)):
            stripped = lines[index].rstrip("\n")
            if FENCE.match(stripped):
                in_code = not in_code
            elif not in_code:
                if CLOSE_DIV.match(stripped):
                    depth -= 1
                    if depth == 0:
                        return index
                elif OPEN_DIV.match(stripped):
                    depth += 1
        return None

    def has_solution_heading(block):
        in_code = False
        for line in block:
            stripped = line.rstrip("\n")
            if FENCE.match(stripped):
                in_code = not in_code
            elif not in_code and SOLUTION_HEADING.match(stripped):
                return True
        return False

    def collect(start, nested=False):
        parts, index, in_code = [], start, False
        while index < len(lines):
            stripped = lines[index].rstrip("\n")
            if FENCE.match(stripped):
                in_code = not in_code
                index += 1
                continue
            if in_code:
                index += 1
                continue
            if nested and CLOSE_DIV.match(stripped):
                return parts, index + 1
            if OPEN_DIV.match(stripped):
                end = find_div_end(index)
                if end is None:
                    return parts, len(lines)
                block = lines[index:end + 1]
                if ATTR_DIV.match(stripped) or has_solution_heading(block):
                    parts.append("".join(block))
                else:
                    inner_parts, _ = collect(index + 1, nested=True)
                    parts.extend(inner_parts)
                index = end + 1
                continue
            if not nested and HEADING.match(stripped):
                parts.append(lines[index])
            index += 1
        return parts, index

    return collect(0)[0]


def strip_ex_class_divs(text):
    """Remove ex-class from retained divs, unwrapping divs with no other classes."""
    lines, div_stack, in_code = [], [], False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if FENCE.match(stripped):
            in_code = not in_code
            lines.append(line)
            continue
        if in_code:
            lines.append(line)
            continue

        match = ATTR_DIV.match(stripped)
        if match:
            prefix, attrs, suffix = match.groups()
            if EX_CLASS_TOKEN.search(attrs):
                other_classes = [name for name in CLASS_TOKEN.findall(attrs) if name != "ex-class"]
                if not other_classes:
                    div_stack.append(True)
                    continue
                attrs = EX_CLASS_TOKEN.sub("", attrs)
                attrs = re.sub(r"\s{2,}", " ", attrs).strip()
                line = f"{prefix}{{{attrs}}}{suffix}" + ("\n" if line.endswith("\n") else "")
                div_stack.append(False)
                lines.append(line)
                continue
        if OPEN_DIV.match(stripped):
            div_stack.append(False)
        elif CLOSE_DIV.match(stripped) and div_stack:
            if div_stack.pop():
                continue
        lines.append(line)
    return "".join(lines)


def is_ex_no_class_code(cell):
    return re.search(r"(?m)^[ \t]*#[ \t]*ex-no-class(?![\w-])", source_text(cell)) is not None


def strip_notebook(nb, base_url, notebook_dir):
    cells = []
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            if not is_ex_no_class_code(cell):
                cells.append(cell)
        elif cell["cell_type"] == "markdown":
            blocks = extract_kept_parts(source_text(cell))
            if blocks:
                cell = dict(cell)
                text = "\n".join(strip_ex_class_divs(block) for block in blocks).rstrip("\n")
                text = absolutize_figures(text, base_url, notebook_dir)
                cell["source"] = to_source_lines(text)
                cells.append(cell)
    return {**nb, "cells": cells}


def notebooks_from_quarto():
    config = yaml.safe_load((ROOT / "_quarto.yml").read_text(encoding="utf-8"))
    chapters = config.get("book", {}).get("chapters", [])

    def walk(items):
        for item in items:
            if isinstance(item, str):
                yield item
            elif isinstance(item, dict):
                if "file" in item:
                    yield item["file"]
                yield from walk(item.get("chapters", []))

    return [ROOT / p for p in walk(chapters) if p.endswith(".ipynb")]


def all_notebooks():
    found = {p.resolve() for p in ROOT.glob("*.ipynb")}
    found.update(p.resolve() for p in notebooks_from_quarto())
    return sorted(found)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    base_url = raw_base_url()
    for path in all_notebooks():
        nb = json.loads(path.read_text(encoding="utf-8"))
        stripped = strip_notebook(nb, base_url, path.parent)
        out = OUT_DIR / path.name
        out.write_text(json.dumps(stripped, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path.name}: kept {len(stripped['cells'])} of {len(nb['cells'])} cells -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
