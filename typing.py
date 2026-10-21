import re
from html import escape
from pathlib import Path

config = {
    "font": "Inter",
    "size": 20,
    "duration": 125,  # ms per character
    "pause": 1400,
    "color": "F3F3F3",
    "center": True,
    "vCenter": True,
    "width": 435,
    "height": 50,
    "delete": 40,  # ms per character
    "gap": 160,
    "lines": [
        "quit",
        {
            "text": "fakecrime.bio/quit",
            "color": "969BA3",
            "highlight": {"text": "quit", "color": "F3F3F3"},
        },
        "software / os / scripts",
    ],
}

def getColor(value):
    value = str(value).lstrip("#")
    if not re.fullmatch(r"(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value):
        raise ValueError(f"Invalid hex color: {value!r}")
    return "#" + value

def getSegments(line, fallbackColor):
    content = line["text"]
    base = getColor(line.get("color", fallbackColor))
    highlight = line.get("highlight")
    if not highlight or not highlight.get("text"):
        return [(content, base)]
    target = highlight["text"]
    i = content.rfind(target)
    if i < 0:
        raise ValueError(f"highlight {target!r} not found in {content!r}")
    spans = []
    if i:
        spans.append((content[:i], base))
    spans.append((target, getColor(highlight["color"])))
    if i + len(target) < len(content):
        spans.append((content[i + len(target):], base))
    return spans

def getLines(config):
    lines = []
    for entry in config["lines"]:
        line = {"text": entry} if isinstance(entry, str) else dict(entry)
        if not line.get("text"):
            raise ValueError("Empty typing line")
        record = {
            "text": line["text"],
            "segments": getSegments(line, config["color"]),
            "duration": float(line.get("duration", config["duration"])) * len(line["text"]),
            "pause": int(line.get("pause", config["pause"])),
            "delete": float(line.get("delete", config["delete"])) * len(line["text"]),
        }
        if min(record["duration"], record["pause"], record["delete"]) <= 0:
            raise ValueError("Animation timings must be positive")
        lines.append(record)
    if not lines:
        raise ValueError("At least one typing line is required")
    return lines

def percent(ms, total):
    return f"{ms / total * 100:.6f}%"

def buildSvg(config):
    width, height = int(config["width"]), int(config["height"])
    fontSize = int(config["size"])
    if min(width, height, fontSize) <= 0:
        raise ValueError("width, height, or size must be positive")
    fontFamily = str(config["font"]).replace('"', "").replace("'", "")
    lines = getLines(config)
    gap = int(config.get("gap", 160))
    total = sum(x["duration"] + x["pause"] + x["delete"] + gap for x in lines)
    charWidth = fontSize * .6
    baseline = height / 2 + fontSize * .36 if config["vCenter"] else height - fontSize * .22
    styles = []
    elements = []
    elapsed = 0
    for index, line in enumerate(lines):
        characters = len(line["text"])
        textWidth = characters * charWidth
        clipLeft = (width - textWidth) / 2 if config["center"] else 0
        start = elapsed
        typed = start + line["duration"]
        held = typed + line["pause"]
        done = held + line["delete"]
        frames = [
            (0, 0, "linear"),
            (start, 0, f"steps({characters},start)"),
            (typed, textWidth, "steps(1,end)"),
            (held, textWidth, f"steps({characters},start)"),
            (done, 0, "steps(1,end)"),
            (total, 0, "linear"),
        ]
        byTime = {ms: (w, easing) for ms, w, easing in frames}
        keyFrames = "\n".join(
            f"  {percent(ms, total)} {{ width: {w:.3f}px; animation-timing-function: {easing}; }}"
            for ms, (w, easing) in sorted(byTime.items())
        )
        styles.append(f"@keyframes typing{index} {{\n{keyFrames}\n}}")
        styles.append(f"#reveal{index} {{ animation: typing{index} {total}ms linear infinite; }}")
        spans = "".join(
            f'<tspan fill="{escape(color)}">{escape(text)}</tspan>'
            for text, color in line["segments"]
        )
        x = width / 2 if config["center"] else 0
        anchor = "middle" if config["center"] else "start"
        elements.append(f'''
  <clipPath id="clip{index}"><rect id="reveal{index}" x="{clipLeft:.3f}" y="0" width="0" height="{height}"/></clipPath>
  <g clip-path="url(#clip{index})"><text x="{x:.3f}" y="{baseline:.3f}" text-anchor="{anchor}" xml:space="preserve">{spans}</text></g>''')
        elapsed = done + gap
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="quit animated typing profile">
<style>
  text {{ font-family: '{escape(fontFamily)}', Consolas, monospace; font-size: {fontSize}px; font-weight: 400; }}
{chr(10).join(styles)}
</style>
{''.join(elements)}
</svg>
'''

if __name__ == "__main__":
    output = Path(__file__).with_name("typing.svg")
    output.write_text(buildSvg(config), encoding="utf-8")
    print(f"Wrote {output}")
