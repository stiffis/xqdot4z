"""Read the built PDFs the way a person does and refuse a layout that misleads.

Two faults reach the page without LaTeX saying anything. A table wider than its
column silently overprints the neighbouring text, and floats can be typeset in a
different order than they are numbered, so Table IV arrives before Table II and
the reader has to hunt. Neither shows up in the log, and neither is visible in
the sources, so this measures the finished PDF instead: words are placed in
two-column reading order and compared against the numbering LaTeX assigned.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDFS = ["paper/main_es.pdf", "paper/main_en.pdf"]
CAPTION = re.compile(r"^(TABLA|TABLE|Fig\.|Figura)$")
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}
SPILL_TOLERANCE = 4.0
TITLE_BAND = 140.0


def require(condition, message):
    if not condition: raise SystemExit(f"FAIL: {message}")


def pages(pdf):
    with tempfile.NamedTemporaryFile(suffix=".xml") as handle:
        subprocess.run(["pdftotext", "-bbox", str(pdf), handle.name],
                       check=True, capture_output=True)
        document = Path(handle.name).read_text()
    for number, page in enumerate(re.split(r"<page ", document)[1:], 1):
        yield number, [(float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4))
                       for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" '
                                            r'xMax="([\d.]+)"[^>]*>([^<]*)</word>', page)]


def columns(words):
    """Split a page into its two columns, left first."""
    middle = (min(w[0] for w in words) + max(w[2] for w in words)) / 2
    for name in ("left", "right"):
        chosen = [w for w in words if (w[0] < middle) == (name == "left")]
        if chosen: yield name, sorted(chosen, key=lambda w: (w[1], w[0]))


def caption_number(column, index):
    """The float number a caption announces, or None if this is a cross-reference."""
    kind = column[index][3]
    if not CAPTION.match(kind) or index + 1 >= len(column): return None
    following = column[index + 1][3]
    if kind in ("TABLA", "TABLE"):
        return "table", ROMAN.get(following.rstrip("."))
    # A caption writes "Fig. 2." with the period; a cross-reference does not.
    if following.endswith(".") and following[:-1].isdigit():
        return "figure", int(following[:-1])
    return None


def inspect(pdf):
    spills, order = [], []
    for number, words in pages(pdf):
        if not words: continue
        for name, column in columns(words):
            edges = sorted(w[2] for w in column)
            edge = edges[int(len(edges) * 0.97)]
            for left, top, right, text in column:
                # The title block spans both columns by design.
                if right > edge + SPILL_TOLERANCE and not (number == 1 and top < TITLE_BAND):
                    spills.append((number, name, round(right - edge, 1), text))
            for index in range(len(column)):
                found = caption_number(column, index)
                if found and found[1]:
                    order.append((number, name, column[index][1], *found))
    return spills, order


def check(pdf):
    path = ROOT / pdf
    require(path.is_file(), f"{pdf} is not built; run make paper first")
    spills, order = inspect(path)
    require(not spills, f"{pdf}: content leaves its column: " + "; ".join(
        f"{text!r} by {amount}pt on page {page}" for page, _, amount, text in
        sorted(spills, key=lambda s: -s[2])[:4]))
    reading = sorted(order, key=lambda entry: (entry[0], entry[1] == "right", entry[2]))
    seen = {}
    for page, _, _, kind, index in reading:
        expected = seen.get(kind, 0) + 1
        require(index == expected,
                f"{pdf}: {kind} {index} is typeset on page {page} where {kind} "
                f"{expected} was expected; floats read out of their numbering")
        seen[kind] = index
    print(f"OK: {pdf}, {len(reading)} floats in reading order, nothing outside its column.")
    return len(reading)


def main():
    require(__import__("shutil").which("pdftotext"), "pdftotext is required")
    total = sum(check(pdf) for pdf in PDFS)
    print(f"OK: {total} float placements verified against the rendered pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
