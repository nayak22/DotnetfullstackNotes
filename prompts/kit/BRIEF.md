# Brief: generate one week of .NET study notes (HTML)

You are writing ONE week of day-wise study notes for Samrath's 74-week .NET full-stack roadmap.
Weeks 1–4 already exist and set the quality bar. Match them exactly in structure and depth.

## Files (all in /home/claude/build)
- `lib.py` — helper functions: `C(src, fname=None, lang="csharp")` code block (auto-escapes HTML),
  `defs`, `notes`, `iq`, `tip`, `warn`, `table`, `ul`, `day(...)`, `build(...)`. READ IT FIRST. Do not edit it.
- `week04.py` — the reference implementation of a full week. READ IT FULLY before writing.
  Copy its structure: d1..d7 = day(...), `cards`, then `build("/home/claude/build/week04.html", "/home/claude/build/weekNN.html", NN, ...)`.
  Always use week04.html as the template argument.
- `week03.py` — second reference (another style of content; also read at least Day 4 and Day 6).
- `postfix.py` — run after building: `python3 postfix.py weekNN.html` (adds the "All weeks" link + local diagram rendering).

## Your output
1. Write `/home/claude/build/weekNN.py` (NN two digits, e.g. week05.py) and run it with `python3 weekNN.py`.
2. Run `python3 postfix.py weekNN.html`.
3. Validate:
   - extract the last `<script>` block and run `node --check` on it
   - `grep -c 'class="def"'`, `class="iq"`, `<section class="day"` (expect 8 sections: home + 7 days)
   - confirm `<title>.NET Notes · Week NN</title>` and `KEY='dotnet-weekN-done'` (N without leading zero) are correct
   - no literal `QQQ` remains in the html
   - take ONE Playwright screenshot (chromium is preinstalled; `require('playwright')`) of a code-heavy day
     and look at it with the Read tool to confirm it renders; check console has no page errors.
4. Reply with a SHORT report: file path, per-day title list, counts (defs, interview questions), any concerns.
   Do NOT paste the HTML or the python back.

## Content requirements (per day) — same as Weeks 1–4
- Weekdays (Mon–Fri, ~2 hrs): goal sentence; 10–15 key definitions; 5–6 quick notes; 4–6 numbered `<h3>`
  concept sections, each with a plain-English explanation AND at least one realistic, compilable C# example
  (or SQL/bash/json as the topic needs) with comments showing output; comparison tables where useful;
  tip/warn callouts; 4–5 common mistakes; a 30–40 min exercise with 3 tasks; 3 self-check Q&As;
  6 interview questions with full model answers (mix of "Basic" and "Intermediate"; you may add "Advanced"
  only if the topic genuinely warrants it — if so it renders with no badge colour, so prefer Basic/Intermediate).
- Saturday (~4 hrs): micro-project. Requirements list, `dotnet new` scaffold commands, folder tree,
  step-by-step FULL working code split into files (Core class library + App console), how to run with sample
  output, stretch goals, 4 project-focused interview questions.
- Sunday (~4 hrs): finish/extend the project, a "try to break it" table, README.md template, git commands,
  a week revision checklist, a 5-question "predict the output / does it compile" quiz with answers
  (use `<details><summary>Q1. ...</summary> code ... <b>answer.</b> explanation</details>` like week03/04),
  and a final `<div class="note tip"><b>Next week:</b> ...</div>`, plus 4 interview questions.
- Real-world, Indian-context-friendly examples (₹, INR, GST, PIN codes, Indian names/cities) as in earlier weeks.
  Prefer business domains: orders, invoices, employees, bookings, students, payments. Avoid foo/bar.
- Target .NET 8 LTS / .NET 9, C# 12. Mention the version when a feature is newer than .NET 6.
- Every code sample must compile as written or be clearly a fragment. Be technically precise — this is
  interview prep; wrong facts are worse than missing ones.
- Continuity: earlier projects are Toolkit (W1 calculator), City Library (W2, refactored to IRepository<T> in W4),
  Bank simulator (W3). Reference them where natural.
- Home page: `build(...)` args: title "Week N — <topic>", chips list like week04
  ["Phase 1 · Week N of 74", ".NET 8 LTS / 9", "C# 12", "~18 hrs", "<project chip>"], a 2–3 sentence intro,
  and 7 cards: (n, "MON", full title, short rail label, one-line summary, "2 hrs"/"4 hrs").

## Python gotchas (these bit previous weeks)
- Day bodies are f-strings delimited by ''' and code goes in `{C(r"""...""")}`.
  Any literal `{` or `}` in PROSE inside the f-string must be doubled `{{ }}`. Code inside C(...) is fine.
- C# raw string literals `"""` inside code would close the Python string: write `QQQ` instead; `C()` converts it.
- In prose, HTML-escape generics: `List&lt;T&gt;`. Inside `C(...)` write normal `<T>` (auto-escaped).
- Avoid mermaid diagrams unless they truly help. If you use one: put it in `<pre class="mermaid">`,
  escape `<` `>` in it as `&lt;` `&gt;`, write generics in labels as `#lt;T#gt;`, and line breaks as `&lt;br/&gt;`.
- Keep the file self-contained; no new external libraries.
