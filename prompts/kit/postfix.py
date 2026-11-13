import sys
for p in sys.argv[1:]:
    h=open(p).read()
    if 'id="allweeks"' in h: continue
    h=h.replace('<div class="progress">','<a href="../index.html" id="allweeks" hidden><span class="d">↩</span><span class="t">All weeks</span></a>\n  <div class="progress">',1)
    js = """
  // Local-file extras: link back to the weeks hub, render mermaid diagrams
  if (location.protocol === 'file:') {
    var aw = document.getElementById('allweeks'); if (aw) aw.hidden = false;
    if (document.querySelector('pre.mermaid')) {
      var ms = document.createElement('script');
      ms.src = 'https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js';
      ms.onload = function(){ try { mermaid.initialize({ startOnLoad:false, theme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'default' }); mermaid.run(); } catch(e){} };
      document.head.appendChild(ms);
    }
  }
"""
    h=h.replace("  render();\n})();", "  render();\n"+js+"})();",1)
    assert 'allweeks' in h and 'mermaid.run' in h, p
    open(p,'w').write(h); print('patched',p)
