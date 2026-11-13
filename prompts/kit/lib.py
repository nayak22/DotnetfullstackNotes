import html as _h
def esc(s): return _h.escape(s, quote=False)
def C(src, fname=None, lang="csharp"):
    src = src.strip("\n").replace("QQQ", chr(34)*3)
    if fname:
        return f'<div class="code"><div class="fname">{esc(fname)}</div><pre><code class="language-{lang}">{esc(src)}</code></pre></div>'
    return f'<div class="code nofile"><pre><code class="language-{lang}">{esc(src)}</code></pre></div>'
def defs(items):
    rows = "".join(f'<div class="def"><dt>{t}</dt><dd>{d}</dd></div>' for t,d in items)
    return f'<h3>Key definitions</h3><dl class="defs">{rows}</dl>'
def notes(items):
    return '<div class="notes"><strong>Quick notes</strong><ul>' + "".join(f"<li>{i}</li>" for i in items) + '</ul></div>'
def iq(items):
    b = "".join(f'<details class="iq"><summary><span class="lvl {l.lower()}">{l}</span>{q}</summary><div>{a}</div></details>' for l,q,a in items)
    return f'<h3>Interview questions</h3><p class="muted">Answer out loud first, then open each one to compare.</p>{b}'
def tip(t): return f'<div class="note tip"><b>Tip.</b> {t}</div>'
def warn(t, label="Avoid"): return f'<div class="note warn"><b>{label}.</b> {t}</div>'
def table(head, rows):
    th = "".join(f"<th>{x}</th>" for x in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><tr>{th}</tr>{tr}</table></div>'
def ul(items): return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
def day(n, dn, title, goal, d, nt, body, mistakes=None, exercise=None, selfcheck=None, iqs=None, tail=""):
    out = [f'<section class="day" id="day{n}"><div class="dayhead"><span class="num">DAY {n} · {dn}</span><h2>{title}</h2><label><input type="checkbox" id="done{n}" data-done="{n}"> Done</label></div>',
           f'<div class="goal"><strong>Goal</strong>{goal}</div>', defs(d), notes(nt), body]
    if mistakes: out.append("<h3>Common mistakes</h3>" + ul(mistakes))
    if exercise: out.append(f'<h3>Exercise ({exercise[0]})</h3><ol class="ex">' + "".join(f"<li>{e}</li>" for e in exercise[1]) + "</ol>")
    if selfcheck: out.append("<h3>Self-check questions</h3>" + "".join(f"<details><summary>{q}</summary>{a}</details>" for q,a in selfcheck))
    out.append(tail)
    if iqs: out.append(iq(iqs))
    out.append("</section>")
    return "\n".join(out)

def build(template_path, out_path, week, title, phase_label, hours, chips, intro, cards, days_html):
    h = open(template_path, encoding="utf-8").read()
    pre = h[:h.index('<nav class="rail"')]
    suf = h[h.index('<div class="pager">'):]
    import re as _re
    pre = _re.sub(r"<title>.NET Notes · Week \d+</title>", f"<title>.NET Notes · Week {week}</title>", pre)
    suf = _re.sub(r"var KEY='dotnet-week\d+-done';", f"var KEY='dotnet-week{week}-done';", suf)
    rail = [f'<nav class="rail" aria-label="Days">\n  <div class="brand"><b>.NET</b> Full-Stack · Week {week}</div>',
            '  <a href="#home" data-day="0" class="homelink"><span class="d">◆</span><span class="t">Home</span></a>']
    for n,dn,t,short,s,hr in cards:
        rail.append(f'  <a href="#day{n}" data-day="{n}"><span class="d">{dn}</span><span class="t">{short}</span></a>')
    rail.append('  <div class="progress"><span id="pcount">0 of 7 days done</span><div class="bar"><i id="pbar"></i></div></div>\n</nav>')
    cardhtml = "".join(f'<a class="daycard" href="#day{n}" data-card="{n}"><span class="k"><span>DAY {n} · {dn}</span><span class="ok" data-ok="{n}"></span></span><h3>{t}</h3><p>{s}</p><span class="hrs">{hr}</span></a>' for n,dn,t,short,s,hr in cards)
    chiphtml = "".join(f'<span class="chip">{c}</span>' for c in chips)
    home = f'''<section class="day" id="home">
<div class="home-hero">
  <div class="meta" style="margin-top:0">{chiphtml}</div>
  <h1>{title}</h1>
  <p>{intro}</p>
</div>
<div class="daygrid">{cardhtml}</div>
<div class="legend"><span><b>Every day has:</b> Key definitions · Quick notes · Concepts with code · Common mistakes · Exercise · Self-check · Interview questions</span></div>
</section>'''
    out = pre + "\n".join(rail) + "\n\n<main>\n" + home + "\n" + days_html + "\n\n" + suf
    open(out_path, "w", encoding="utf-8").write(out)
    return out
