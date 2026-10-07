from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "revision_output" / "clean" / "applsci-4556799-revised.tex"
HIGHLIGHTED = ROOT / "revision_output" / "highlighted" / "applsci-4556799-revised.tex"


def unwrap_hl(text: str) -> str:
    marker = r"\hl{"
    while marker in text:
        start = text.index(marker)
        depth = 1
        cursor = start + len(marker)
        while cursor < len(text) and depth:
            if text[cursor] == "{" and (cursor == 0 or text[cursor - 1] != "\\"):
                depth += 1
            elif text[cursor] == "}" and (cursor == 0 or text[cursor - 1] != "\\"):
                depth -= 1
            cursor += 1
        if depth:
            raise ValueError("Unbalanced highlight wrapper")
        text = text[:start] + text[start + len(marker):cursor - 1] + text[cursor:]
    return text


def normalize(text: str) -> str:
    text = unwrap_hl(text)
    text = text.replace(r"\rowcolor{yellow!28}", "")
    text = re.sub(
        r"\n\\sethlcolor\{yellow\}.*?\\begin\{document\}",
        lambda _match: "\n" + r"\begin{document}",
        text,
        count=1,
        flags=re.S,
    )
    return re.sub(r"\s+", " ", text).strip()


clean = normalize(CLEAN.read_text(encoding="utf-8"))
highlighted = normalize(HIGHLIGHTED.read_text(encoding="utf-8"))
if clean != highlighted:
    for index, (left, right) in enumerate(zip(clean, highlighted)):
        if left != right:
            print("Clean context:", clean[max(0, index - 120):index + 240])
            print("Highlighted context:", highlighted[max(0, index - 120):index + 240])
            break
    raise SystemExit("FAIL: clean and highlighted scientific content differ")
print("PASS: clean and highlighted scientific content are identical after removing visual markup")
