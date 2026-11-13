import os
phases = [
("Phase 1 — C# and .NET fundamentals", 1, ["Setup and C# basics","OOP part 1","Modern C# and exceptions","Collections and generics","Delegates, lambdas and LINQ","File I/O and serialization","Async and concurrency",".NET internals","SOLID and design patterns","Git and Phase 1 exit check"]),
("Phase 2 — SQL Server, EF Core, Web API", 11, ["SQL Server foundations","Advanced T-SQL","Programmability and transactions","Indexing and performance","ADO.NET, Dapper, EF Core basics","EF Core in depth","ASP.NET Core fundamentals","REST API design","Cross-cutting concerns","Authentication and authorization","Background jobs and real-time","Phase 2 exit check"]),
("Phase 3 — Frontend and integration", 23, ["HTML and CSS","JavaScript","TypeScript","Framework basics","Forms and HTTP","Auth in the SPA","State and performance","Blazor and Razor","Real-time and testing","Deploy and Phase 3 exit check"]),
("Capstone 1 — Clinic Management System", 33, ["Backend foundation","Backend features","Frontend features","Ship it"]),
("Phase 4 — Architecture, testing, DevOps, Azure", 37, ["Clean Architecture","Domain-Driven Design","Unit testing","Integration testing","Caching and performance","Security","Resilience and observability","Docker","CI/CD","Azure core","Serverless and IaC","Phase 4 exit check"]),
("Capstone 2 — Multi-tenant SaaS task platform", 49, ["Core domain","Features","SaaS concerns","Frontend completion","DevOps and observability","Ship it"]),
("Phase 5 — Microservices and system design", 55, ["Microservices fundamentals","API Gateway and gRPC","Messaging","Distributed data","Event sourcing and CQRS at scale","Kubernetes","System design fundamentals","Data at scale","Reliability patterns","Classic designs I","Classic designs II and leadership","Phase 5 exit check"]),
("Capstone 3 — Microservices e-commerce platform", 67, ["Identity, Catalog, Basket","Ordering and Payment","Delivery, Notification, Search, Reviews","Customer web app","Admin panel (Blazor)","Kubernetes deployment","Load and chaos testing","Ship it"]),
]
avail = {int(f[4:6]) for f in os.listdir('.') if f.startswith('week') and f.endswith('.html') and f[4:6].isdigit()}
secs=[]
for name,start,titles in phases:
    items=[]
    for i,t in enumerate(titles):
        w=start+i
        if w in avail:
            items.append(f'<a class="wk ready" href="notes/week{w:02d}.html"><span class="n">W{w:02d}</span><span class="t">{t}</span><span class="s" data-week="{w}">Open →</span></a>')
        else:
            items.append(f'<div class="wk"><span class="n">W{w:02d}</span><span class="t">{t}</span><span class="s">Not yet</span></div>')
    secs.append(f'<section><h2>{name}</h2><div class="grid">{"".join(items)}</div></section>')
html=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>.NET Full-Stack Notes</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Space+Grotesk:wght@500;700&display=swap">
<style>
:root{{--bg:#f6f7f9;--surface:#fff;--fg:#1a2230;--muted:#5b6676;--line:#dfe3ea;--accent:#2c6e8f;--accent-soft:#e3eff5;--good:#2f7a4a;
--display:"Space Grotesk","Segoe UI",system-ui,sans-serif;--body:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Consolas,monospace}}
@media (prefers-color-scheme:dark){{:root{{--bg:#11151b;--surface:#171c24;--fg:#dde3eb;--muted:#93a0b1;--line:#2a313c;--accent:#6fb4d4;--accent-soft:#1c2c37;--good:#79c796;color-scheme:dark}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 var(--body)}}
.wrap{{max-width:1100px;margin:0 auto;padding:40px 16px 80px}}
h1{{font:700 clamp(30px,4.4vw,44px)/1.1 var(--display);margin:0 0 10px}}
.lead{{color:var(--muted);max-width:62ch;margin:0}}
h2{{font:600 18px var(--display);margin:40px 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}}
.wk{{display:grid;grid-template-columns:auto 1fr;grid-template-rows:auto auto;column-gap:12px;padding:12px 14px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--muted);text-decoration:none}}
.wk .n{{font:500 12px var(--mono);grid-row:span 2;padding-top:2px}}
.wk .t{{font-size:14.5px}}
.wk .s{{font:500 12px var(--mono)}}
.wk.ready{{color:var(--fg);border-color:var(--accent)}}
.wk.ready .n,.wk.ready .s{{color:var(--accent)}}
.wk.ready:hover{{background:var(--accent-soft)}}
.wk .s.done{{color:var(--good)}}
</style></head><body><div class="wrap">
<h1>.NET Full-Stack Notes</h1>
<p class="lead">74 weeks from C# basics to microservices and system design. Weeks with notes are highlighted; progress you tick inside each week shows here.</p>
{"".join(secs)}
</div>
<script>
document.querySelectorAll('[data-week]').forEach(function(el){{
  try {{ var s=JSON.parse(localStorage.getItem('dotnet-week'+el.dataset.week+'-done')||'{{}}'); var n=Object.values(s).filter(Boolean).length;
    if(n){{ el.textContent = n===7 ? '✓ Complete' : n+'/7 done'; if(n===7) el.classList.add('done'); }} }} catch(e){{}}
}});
</script></body></html>'''
open('index.html','w').write(html); print('hub', sorted(avail))
