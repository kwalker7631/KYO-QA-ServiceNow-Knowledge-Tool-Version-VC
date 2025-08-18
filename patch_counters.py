# patch_counters2.py
import re
from pathlib import Path

APP_PATH = Path(r"C:\Users\kenw\Downloads\KYO-QA-ServiceNow-Knowledge-Tool-Version-VC-main\main_app.py")

clean_list = [
    '("Total:", self.count_total, self.colors["FRAME_BG"]),',
    '("Done:", self.count_done, self.colors["FRAME_BG"]),',
    '("Pass:", self.count_pass, self.colors["SUCCESS_GREEN"]),',
    '("Fail:", self.count_fail, self.colors["PASTEL_RED"]),',
    '("Review:", self.count_review, self.colors["WARN_ORANGE"]),',
    '("OCR:", self.count_ocr, self.colors["PASTEL_YELLOW"]),',
    '("Digital:", self.count_digital, self.colors["PASTEL_GREEN"]),',
]
def build_block(indent: str) -> str:
    inner = ("\n" + indent + "    ").join(clean_list)
    return f"{indent}counters = [\n{indent}    {inner}\n{indent}]\n"

src = APP_PATH.read_text(encoding="utf-8")

# Strategy A: single-line counters with trailing junk  -> replace the whole line
pat_a = re.compile(r'^(?P<indent>\s*)counters\s*=\s*\[.*\]\s*,.*$', re.M)
m = pat_a.search(src)
if m:
    indent = m.group("indent")
    fixed = pat_a.sub(build_block(indent), src, count=1)
    APP_PATH.write_text(fixed, encoding="utf-8")
    print("Patched (strategy A: single-line with trailing junk).")
    raise SystemExit(0)

# Strategy B: multi-line block (replace from counters=[ through the matching closing ] on its own line)
# This matches counters=[ ... ] even if there are comments after the closing bracket.
pat_b = re.compile(
    r'^(?P<indent>\s*)counters\s*=\s*\[(?:.|\n)*?\n(?P=indent)\]\s*(?:#.*)?$', re.M
)
m = pat_b.search(src)
if m:
    indent = m.group("indent")
    fixed = src[:m.start()] + build_block(indent) + src[m.end():]
    APP_PATH.write_text(fixed, encoding="utf-8")
    print("Patched (strategy B: multi-line block).")
    raise SystemExit(0)

# Strategy C: fallback — replace from the 'counters =' line until we see a ']' on any subsequent line
lines = src.splitlines(keepends=True)
for i, line in enumerate(lines):
    if re.match(r'^\s*counters\s*=\s*\[', line):
        indent = re.match(r'^(\s*)', line).group(1)
        # find the next line that contains ']' at the same or greater indent
        end = None
        for j in range(i, len(lines)):
            if ']' in lines[j]:
                end = j
                break
        if end is None:
            # if we can't find a closing bracket, just insert a clean block and keep going
            end = i
        new_block = build_block(indent)
        lines[i:end+1] = [new_block]
        fixed = "".join(lines)
        APP_PATH.write_text(fixed, encoding="utf-8")
        print("Patched (strategy C: fallback scan).")
        raise SystemExit(0)

print("No counters block found. No changes made.")
