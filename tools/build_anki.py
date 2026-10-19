"""Build type-in Anki decks (.apkg) from vocabulary/*/anki-*.csv.

Usage:  python tools/build_anki.py            (needs: pip install genanki)

Writes vocabulary/<topic>/anki-<topic>.apkg (one per topic) and
vocabulary/anki-all-topics.apkg (everything). Note and deck IDs are stable,
so re-importing an updated deck updates existing cards instead of duplicating them.
"""
import csv, hashlib, html, pathlib, re, sys

import genanki

ROOT = pathlib.Path(__file__).resolve().parent.parent / "vocabulary"
GAP = "_____"


def stable_id(*parts):
    return int(hashlib.sha1("|".join(parts).encode()).hexdigest()[:12], 16) % (1 << 31) + (1 << 30)


CSS = """
.card { font-family: system-ui, -apple-system, Roboto, sans-serif; font-size: 20px; line-height: 1.45;
        text-align: left; color: #1f2328; background: #ffffff; padding: 4px 6px; }
.nightMode .card, .card.nightMode, .night_mode .card { color: #e6e6e6; background: #1e1e1e; }
.hint { color: #57606a; font-size: 0.9em; margin-bottom: 10px; }
.nightMode .hint, .night_mode .hint { color: #a8b0b8; }
.gaps { color: #8250df; font-size: 0.8em; margin-top: 6px; }
.sentence { margin: 6px 0 12px; }
.chunk { font-size: 1.15em; font-weight: 700; margin: 10px 0 6px; }
.example { margin-bottom: 8px; }
.notes { color: #57606a; font-size: 0.85em; font-style: italic; }
.nightMode .notes, .night_mode .notes { color: #a8b0b8; }
input#typeans { font-size: 20px; width: 100%; box-sizing: border-box; }
"""

FRONT = """<div class="hint">{{Hint}}</div>
<div class="sentence">{{Sentence}}</div>
{{#Gaps}}<div class="gaps">{{Gaps}}</div>{{/Gaps}}
{{type:Answer}}"""

BACK = """<div class="hint">{{Hint}}</div>
<div class="sentence">{{Sentence}}</div>
{{type:Answer}}
<hr id="answer">
<div class="chunk">{{Chunk}}</div>
<div class="example">{{Example}}</div>
<div class="notes">{{Notes}}</div>"""

MODEL = genanki.Model(
    stable_id("ielts-chunk-type-in-model"),
    "IELTS Chunk (type in)",
    fields=[{"name": n} for n in ["Hint", "Sentence", "Answer", "Gaps", "Chunk", "Example", "Notes"]],
    templates=[{"name": "Type the chunk", "qfmt": FRONT, "afmt": BACK}],
    css=CSS,
)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def norm(s):
    return re.sub(r"\s+", " ", html.unescape(strip_tags(s))).strip()


def answers(front_sentence, back_example):
    """Return the words that fill each gap, by aligning the gapped sentence with the full one."""
    segments = [re.escape(norm(x)) for x in front_sentence.split(GAP)]
    pattern = r"\s*(.+?)\s*".join(segments)
    m = re.fullmatch(pattern, norm(back_example))
    return [g.strip() for g in m.groups()] if m else None


def subtopic_titles(topic_dir):
    titles = {}
    for md in topic_dir.glob("[0-9][0-9]-*.md"):
        h = re.search(r"^# (.+)$", md.read_text(encoding="utf-8"), re.M)
        titles[md.stem[3:]] = (md.stem[:2], h.group(1).strip() if h else md.stem[3:])
    return titles


def topic_title(slug):
    return slug.replace("-", " ").title().replace(" And ", " & ")


def main():
    all_decks, failures, total = [], [], 0
    for topic_dir in sorted(p for p in ROOT.iterdir() if p.is_dir()):
        csvs = list(topic_dir.glob("anki-*.csv"))
        if not csvs:
            continue
        slug, titles, decks = topic_dir.name, subtopic_titles(topic_dir), {}
        for row in csv.reader(open(csvs[0], encoding="utf-8")):
            if not row or row[0].startswith("#"):
                continue
            front, back, tags = row
            hint, sentence = front.split("<br><br>", 1)
            chunk, example, notes = (back.split("<br>", 2) + ["", ""])[:3]
            sub = tags.split()[-1]
            gaps = answers(sentence, example)
            if gaps:
                pieces = sentence.split(GAP)
                example = pieces[0] + "".join(f"<b>{g}</b>{p}" for g, p in zip(gaps, pieces[1:]))
            else:
                failures.append(f"{slug}/{sub}: {strip_tags(chunk)}")
                gaps = [norm(chunk)]
            num, sub_title = titles.get(sub, ("99", sub))
            deck_name = f"IELTS Vocabulary::{topic_title(slug)}::{num} {sub_title}"
            if deck_name not in decks:
                decks[deck_name] = genanki.Deck(stable_id(deck_name), deck_name)
            decks[deck_name].add_note(genanki.Note(
                model=MODEL,
                fields=[hint, sentence.replace(GAP, "<b>_____</b>"), " ".join(gaps),
                        f"{len(gaps)} gaps: type the words in order, separated by spaces" if len(gaps) > 1 else "",
                        chunk, example, notes],
                tags=tags.split(),
                guid=genanki.guid_for(slug, sub, norm(chunk)),
            ))
            total += 1
        topic_decks = [decks[k] for k in sorted(decks)]
        genanki.Package(topic_decks).write_to_file(str(topic_dir / f"anki-{slug}.apkg"))
        all_decks += topic_decks
    genanki.Package(all_decks).write_to_file(str(ROOT / "anki-all-topics.apkg"))
    print(f"{total} notes in {len(all_decks)} sub-decks; {len(failures)} answers fell back to the chunk")
    for f in failures:
        print("  fallback:", f)


if __name__ == "__main__":
    sys.exit(main())
