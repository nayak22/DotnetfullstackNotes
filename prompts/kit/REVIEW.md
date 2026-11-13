# Brief: technical review of ONE week of .NET study notes

You are a senior .NET engineer and technical editor. The notes are interview prep for a learner, so
**a wrong fact is worse than a missing one**. Your job: find and FIX errors in the week's source
(`/home/claude/build/weekNN.py`), rebuild, and report. Do not rewrite for style; fix correctness.

## Files
- `/home/claude/build/weekNN.py` — the source. Edit THIS (never hand-edit the .html).
- `/home/claude/build/lib.py` — helpers (read-only). `C(src, fname, lang)` renders code blocks.
- Rebuild: `cd /home/claude/build && python3 weekNN.py && python3 postfix.py weekNN.html`
  (postfix prints nothing / skips if already applied — that's fine).
- Python gotchas: prose inside the f-strings needs `{{ }}` for literal braces; C# `"""` raw strings are
  written as `QQQ` in the source; prose generics are HTML-escaped (`List&lt;T&gt;`), code inside C() is not.

## 1. Compile the code (most important)
A .NET 8 SDK is installed (`dotnet`), but there is NO internet: NuGet restore fails unless you use an
offline source. For every project, put this `nuget.config` next to the .csproj/.sln first:
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration><packageSources><clear /><add key="local" value="/tmp/claude-0/emptyfeed" /></packageSources></configuration>
```
(`mkdir -p /tmp/claude-0/emptyfeed`.) Work under `/tmp/claude-0/review-weekNN/`.
- Rebuild the Saturday/Sunday micro-project exactly as the notes describe (all files, final Sunday state),
  `dotnet build`, and run it with scripted stdin where practical (e.g. `printf '1\n0\n' | dotnet run`).
- Compile the weekday code samples: paste self-contained samples (or groups of them) into scratch console
  projects. Fragments clearly marked as fragments can be checked by wrapping them minimally.
- Check stated outputs in comments (`// prints 3`) by actually running them where feasible.
- Packages NOT available offline (Microsoft.Extensions.Logging/Configuration/DependencyInjection/Hosting,
  xUnit, BenchmarkDotNet, Polly, etc.): you cannot compile those — review them carefully by reading
  against your knowledge of the real APIs (exact method names, namespaces, overloads, package names).
  EXCEPTION: the ASP.NET Core shared framework IS installed. Adding
  `<FrameworkReference Include="Microsoft.AspNetCore.App" />` to a scratch csproj gives offline
  Microsoft.Extensions.Logging/Configuration/Options/Hosting/DependencyInjection and ASP.NET Core itself —
  so compile those samples rather than read-only reviewing them. Note in your report which samples were read-only reviewed.
- Use `<TargetFramework>net8.0</TargetFramework>`. If the notes use a .NET 9-only API (e.g. `System.Threading.Lock`,
  `Task.WhenEach`, LINQ `CountBy`/`AggregateBy`/`Index`), make sure the text says it's .NET 9; you can't compile it here.

## 2. Check technical claims
Every definition, table cell, note, "output" comment, interview answer and quiz answer. Typical issues:
wrong API names, wrong version attributions (C# 8 vs 9 etc.), oversimplified-to-wrong statements,
wrong Big-O, wrong defaults, quiz answers that don't match what the code does.
If a claim depends on post-2024 facts you can't verify, soften it ("as of .NET 8/9…") rather than guess.

## 3. Fix, rebuild, re-validate
- Make minimal edits in weekNN.py. Rebuild. Then re-run:
  last `<script>` block → `node --check`; counts of `class="def"`, `class="iq"`, `<section class="day"` (8);
  title `.NET Notes · Week N`, `KEY='dotnet-weekN-done'`, no `QQQ`, exactly one `id="allweeks"`.
- Do NOT change the page structure, styling, lib.py or other weeks' files.

## 4. Report (short, plain text)
- Counts: samples compiled OK / fixed / read-only reviewed; projects built and run.
- A bullet list of every fix you made (day, what was wrong, what it is now). Be specific.
- Anything you were unsure about and left as is.
Do not paste the HTML or Python back.

## Notes for this review round
- Week 1 has NO .py source (it was built by enrich.py/home.py). For Week 1 only, edit
  `/home/claude/build/week01.html` directly with careful Python read-modify-write replacements
  (exact old→new strings, assert each matches once). Keep HTML escaping correct inside code blocks
  (`&lt;` `&gt;` `&amp;`). Do not run postfix again on week01 (already applied).
- Weeks 5–10 were already reviewed once. If you are reviewing one of them, this is a SECOND pass with fresh
  eyes: re-verify everything, don't assume the first pass was right, and look especially at things the
  first pass marked "read-only" or "left as is". Also check the samples now compile with the
  Microsoft.AspNetCore.App FrameworkReference trick above where relevant.
