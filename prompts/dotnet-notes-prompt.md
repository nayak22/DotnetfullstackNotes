# Reusable Prompt — .NET Full-Stack Day-wise HTML Notes

Use this in a new chat whenever this session fills up. Attach these files with it:

1. `week01-template.html` — the finished Week 1 notes page (the UI to copy exactly).
2. `Daily Plan.md` — export it from the roadmap doc: open the **Daily Plan** tab → Export → Markdown.

Then paste the prompt below and change only the `WEEK` line.

---

## PROMPT (copy from here)

```
You are my .NET full-stack tutor. Create detailed day-wise study notes as ONE self-contained HTML artifact.

WEEK: 2            <-- change this (1–74)

INPUTS I ATTACHED
- week01-template.html: the reference page. Reuse its HTML structure, CSS, JavaScript, fonts and
  colour tokens EXACTLY (copy the <style> and <script> blocks verbatim). Only change the content,
  the <title>, the rail labels, the localStorage key and the header.
- Daily Plan.md: my 74-week day-by-day curriculum. Read the 7 days listed for the WEEK above and
  write one section per day in that order (Mon–Sun). Don't add or drop topics.

ABOUT ME
- Study time: ~2 hrs on weekdays, ~4 hrs on Sat/Sun.
- Target stack: .NET 8 LTS / .NET 9, C# 12, ASP.NET Core, EF Core, SQL Server 2022,
  Angular or React, Docker, Azure.
- Skip DSA entirely.

UI REQUIREMENTS (same as template)
- <title>: ".NET Notes · Week N"
- Left sticky rail with 7 day links (MON…SUN + short topic), progress bar "x of 7 days done";
  collapses to a horizontal scroll strip under 860px.
- One day visible at a time, routed by #day1…#day7; Previous/Next buttons at the bottom.
- "Done" checkbox per day saved in localStorage key "dotnet-weekN-done" (wrapped in try/catch).
- Code blocks: <div class="code"><div class="fname">File.cs</div><pre><code class="language-csharp">…
  (use class "code nofile" when there is no file name). Copy button on every block.
  Syntax highlighting via highlight.js 11.9.0 from cdnjs, coloured with the template's tokens.
- Escape < > & inside code (List&lt;T&gt;).
- Light and dark theme via the template's CSS tokens. Fonts: Space Grotesk / IBM Plex Sans / IBM Plex Mono.

HOME PAGE (default view, #home)
- Chips (Phase · Week N of 74 · stack · hours), week title, 2–3 sentence intro.
- A grid of 7 day cards (DAY n · MON, title, one-line summary, hours, "✓ done" when ticked)
  linking to #day1…#day7. "Home" is the first rail link; Previous on Day 1 returns home.

CONTENT STRUCTURE FOR EVERY WEEKDAY (Mon–Fri, ~2 hrs)
1. Day header: "DAY n · MON" + topic title + Done checkbox
2. Goal box: one sentence on what I can do by the end of the day
3. Key definitions: 8–15 terms as <dl class="defs"> rows (term → precise one-to-two-line definition)
4. Quick notes: 5–6 bullet revision summary in the <div class="notes"> box
5. 4–6 numbered concept sections (h3), each with:
   - a short plain-English explanation (why it exists, when to use it)
   - at least one realistic, compilable C# (or SQL/TS/YAML as the topic needs) code example
     with inline comments showing output or behaviour
   - tables for comparisons (e.g. X vs Y, lifetimes, status codes)
   - "Tip" (green) and "Rule/Avoid" (amber) callouts where useful
6. Common mistakes (3–5 bullets)
7. Exercise (30–40 min, 2–3 numbered tasks)
8. Self-check questions as <details> with answers (2–4)
9. Interview questions: 6 per weekday (4 on weekend days) as <details class="iq"> with a
   level badge <span class="lvl basic|intermediate">, full model answers an interviewer would accept.
   Add "advanced" level questions from Phase 4 onward.

WEEKEND DAYS
- Saturday (micro-project day, ~4 hrs): requirements list, `dotnet` CLI commands to scaffold
  the solution, folder tree, then step-by-step FULL working code split into files
  (logic in a class library / proper layers, I/O separate), how to run it with sample output,
  and stretch goals.
- Sunday (~4 hrs): finish/harden the project (validation table of bad inputs + improved code),
  a README.md template for the repo, git commit/push commands, a revision checklist for the
  whole week, and a 5-question "predict the output / does it compile" quiz with answers.
- If the plan lists a revision or buffer day instead, make it a structured revision page:
  summary of the week's key ideas, a mini cheat-sheet table, and the quiz.

QUALITY BAR
- Detailed, accurate, current (.NET 8/9 APIs; mention version where a feature is new).
- Real-world examples (orders, invoices, employees, bookings) over foo/bar.
- Every code sample must compile as written or be clearly marked as a fragment.
- End Sunday with a "Next week:" tip naming next week's topic from the plan.

OUTPUT
- Publish it as an artifact (one HTML file, no external files except Google Fonts + cdnjs).
- In chat, reply with one line only; don't repeat the notes.
```

---

## Short follow-up prompts

- **Next week in the same chat:** `Same format, now Week 3.`
- **Two weeks at once (shorter per day):** `Same format for Weeks 3 and 4 as two separate artifacts.`
- **Go deeper on one day:** `Expand Day 4 of Week 3 with 3 more code examples and 5 more self-check questions; keep the layout.`
- **Fix a page:** `In the Week 3 artifact, the code on Day 2 doesn't compile because ___; fix it and republish to the same URL.`

## Links from the original session

- Roadmap + Daily Plan doc: https://claude.ai/artifact/D7htNU1ta3xLMECwCUtxWp
- Week 1 notes: https://claude.ai/artifact/4BkE6Jj4swPZb5B6N37amC
