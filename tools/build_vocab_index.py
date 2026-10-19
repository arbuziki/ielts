"""Build vocabulary/README.md and sanity-check the generated files.

Usage:  python tools/build_vocab_index.py
"""
import csv, re, sys, pathlib, collections

root = pathlib.Path(__file__).resolve().parent.parent / "vocabulary"
lines = ["# Topic vocabulary", "",
         "Topic vocabulary for IELTS General Training writing, aimed at Band 7.5–8.",
         "Each sub-topic file has a vocabulary table, two model texts with notes and practice prompts.",
         "", "## Anki flashcards (type-in)", "",
         "- **All topics in one file:** [anki-all-topics.apkg](anki-all-topics.apkg), or use the per-topic `.apkg` files listed below.",
         "- **AnkiDroid:** download the `.apkg` (in the GitHub app or browser: open the file → Download), then tap it and choose AnkiDroid,",
         "  or in AnkiDroid tap ⋮ → Import and pick the file. **Anki desktop:** File → Import.",
         "- **Card layout:** each card shows a meaning hint and a sentence with a gap. Type the missing words (for 2–3 gaps, type them in order separated by spaces).",
         "  The back shows a letter-by-letter comparison, the dictionary form, the example and notes.",
         "- **Organization:** deck tree *IELTS Vocabulary → topic → sub-topic*, note type *IELTS Chunk (type in)*.",
         "  Re-importing an updated file updates existing cards and keeps your review history.",
         "- **Rebuild after editing the vocabulary:** `pip install genanki`, then `python tools/build_anki.py`. The `.csv` files are the source for the decks.", "",
         "**American English throughout:** spelling (*organize, behavior, center, traveled*), vocabulary",
         "(*trash, apartment, sidewalk, résumé*) and letter conventions (*Sincerely,* / *Best regards,* / *Take care,*).",
         "IELTS accepts British or American English in writing, as long as you use one consistently.",
         "British equivalents are given in the Notes (\"BrE: rubbish\") because IELTS Reading and Listening often use British English.", "",
         "**How to use:** learn the *chunks* (2–5 words) and grammar frames, not whole sentences.",
         "Then write the Practice prompts using 6 or more chunks, and bring them for grading.", ""]
problems, total_items, total_rows = [], 0, 0
bold_counter = collections.Counter()
for topic in sorted(p for p in root.iterdir() if p.is_dir()):
    files = sorted(topic.glob("[0-9][0-9]-*.md"))
    csvs = list(topic.glob("anki-*.csv"))
    title = topic.name.replace("-", " ").title().replace(" And ", " & ")
    lines += [f"## {title}", ""]
    for f in files:
        t = f.read_text(encoding="utf-8")
        h = re.search(r"^# (.+)$", t, re.M)
        items = len(re.findall(r"^\| (?!Chunk|---)", t, re.M))
        total_items += items
        for need in ["## Vocabulary", "## Text 1", "## Text 2"]:
            if need not in t:
                problems.append(f"{f.relative_to(root)}: missing '{need}'")
        for b in re.findall(r"\*\*([^*]+)\*\*", t.split("## Text 1", 1)[-1]):
            if not b.endswith(":") and len(b) < 40:
                bold_counter[b.lower()] += 1
        lines.append(f"- [{h.group(1) if h else f.stem}]({topic.name}/{f.name}) ({items} items)")
    for c in csvs:
        rows = [r for r in csv.reader(open(c, encoding="utf-8")) if r and not r[0].startswith("#")]
        bad = [i for i, r in enumerate(rows) if len(r) != 3 or "_____" not in r[0]]
        total_rows += len(rows)
        if bad:
            problems.append(f"{c.relative_to(root)}: {len(bad)} malformed rows")
        apkg = topic / f"anki-{topic.name}.apkg"
        if apkg.exists():
            lines.append(f"- Anki deck: [{apkg.name}]({topic.name}/{apkg.name}) ({len(rows)} cards; source: [{c.name}]({topic.name}/{c.name}))")
        else:
            lines.append(f"- Anki deck source: [{c.name}]({topic.name}/{c.name}) ({len(rows)} cards)")
    lines.append("")
(root / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("items", total_items, "cards", total_rows)
print("most repeated bold items:", [(k, v) for k, v in bold_counter.most_common(15)])
print("\n".join(problems) or "no structural problems")
