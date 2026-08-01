import re, os

s = open('tpl.html', encoding='utf-8').read()
old = [l for l in s.split('\n') if 'fmt(n) { return Math' in l][0]
s = s.replace(old, "  fmt(n) { return Math.round(n).toLocaleString('uk-UA').replace(/\\u00a0/g, '\\u2009'); }")
import datetime, json
BUILD = datetime.datetime.now().strftime('%d.%m %H:%M')
# Конфіг знімку, зібраний тим самим кодером, що й у Apps Script.
CFG = json.load(open('cfg_snapshot.json', encoding='utf-8'))
CFG['build'] = BUILD
assert "'" not in CFG['data'] and '\\' not in CFG['data']
CFG_TAG = '<script>window.__LIPSS = ' + json.dumps(CFG, ensure_ascii=False) + ';</script>\n'
s = s.replace('<script src="./support.js"></script>', '<script src="./support.js"></script>\n' + CFG_TAG)
open('LIPSS Dashboard.dc.html', 'w', encoding='utf-8').write(s)

# --- standalone ---
src = s
i = src.index('<x-dc>') + len('<x-dc>'); j = src.rindex('</x-dc>')
tpl = src[i:j]
h1 = tpl.index('<helmet>'); h2 = tpl.index('</helmet>') + len('</helmet>')
helmet = tpl[h1:h2]
tpl = (tpl[:h1] + tpl[h2:]).strip()
page_css = re.search(r'<style>(.*?)</style>', helmet, re.S).group(1)
script_tag = re.search(r'<script type="text/x-dc" data-dc-script data-props="[^"]*">.*?</script>', src, re.S).group(0)

ds_css = open('styles.css', encoding='utf-8').read()
support = open('support.js', encoding='utf-8').read()
support = support.replace(r'/<x-dc(?:\s[^>]*)?>/', r'/<x\-dc(?:\s[^>]*)?>/')
support = support.replace('"has no <x-dc> block', '"has no <x-" + "dc> block')
support = support.replace('lastIndexOf("</x-dc>")', 'lastIndexOf("</x-" + "dc>")')
assert '<x-dc' not in support and '</x-dc' not in support


# Браузер під час парсингу виштовхує <sc-for> за межі <thead>/<tbody> (foster
# parenting), тому DOM-розбір шаблону губить усі цикли в таблицях і вони
# рендеряться одним порожнім рядком. Рантайм лікує це тим, що добирає власний
# URL через fetch і переразбирає СИРИЙ текст, де <sc-for> уцілів. У самодостатній
# збірці мережі немає (а з file:// fetch і зовсім заборонений), тож віддаємо
# рантайму сирий шаблон напряму через його ж API __dcUpdate.
assert '</script' not in tpl, 'template must not contain a script close tag'
RAW_BLOB = ('<script type="text/plain" id="__dc_raw">\n' + tpl + '\n</script>\n')
REPAIR = """<script>
(function () {
  function repair() {
    try {
      var raw = document.getElementById('__dc_raw');
      if (raw && window.__dcUpdate && window.__dcRootName) {
        window.__dcUpdate(window.__dcRootName(), 'html', raw.textContent, false);
      }
    } catch (e) {
      console.error('[lipss] не вдалося перезібрати шаблон:', e);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', repair);
  else repair();
})();
</script>
"""

html = ''.join([
  '<!DOCTYPE html>\n<html lang="uk">\n<head>\n<meta charset="utf-8">\n'
  '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
  '<title>LIPSS · B2B Export — дашборд</title>\n',
  '<!-- Самодостатня версія дашборда LIPSS. Шрифт, React, рантайм і всі 2287 лідів\n'
  '     вшиті у цей файл: працює офлайн, нічого не тягне з мережі.\n'
  '     Знімок таблиці LIPSS_B2B_воронка станом на 31.07.2026. -->\n',
  '<style>\n' + open('vendor/archivo_inline.css', encoding='utf-8').read() + '\n</style>\n',
  '<style>\n' + ds_css + '\n</style>\n',
  '<style>\n' + page_css + '\n</style>\n',
  '<script>\n' + open('vendor/react.js', encoding='utf-8').read() + '\n</script>\n',
  '<script>\n' + open('vendor/react-dom.js', encoding='utf-8').read() + '\n</script>\n',
  CFG_TAG,
  '<script>window.__resources = {};</script>\n',
  '<script>\n' + support + '\n</script>\n',
  REPAIR,
  '</head>\n<body>\n<x-dc>\n' + tpl + '\n</x-dc>\n' + script_tag + '\n',
  RAW_BLOB,
  '</body>\n</html>\n',
])
assert html.count('<x-dc>') == 1 and html.count('</x-dc>') == 1
open('LIPSS-dashboard-standalone.html', 'w', encoding='utf-8').write(html)


# --- artifact (без власної обгортки: <!doctype>/<html>/<head>/<body> додає платформа) ---
ah = open('LIPSS-dashboard-standalone.html', encoding='utf-8').read()
head = ah[ah.index('<title>'):ah.index('</head>')]
bodyc = ah[ah.index('<body>') + len('<body>'):ah.index('</body>')]
ground = """
<style>
  /* Оболонка артефакта проставляє color-scheme інлайном за темою глядача —
     !important лишає системні контроли світлими під ідентичність Modernist. */
  :root { color-scheme: light !important; }
  html, body { background: var(--color-bg); color: var(--color-text); }
</style>
"""
art = head + ground + bodyc
for bad in ['<!DOCTYPE', '<html', '<head>', '<body>', '</html>']:
    assert bad not in art, bad
# Той самий вміст пишемо в обидва шляхи: artifact.html і той файл, що
# прив'язаний до опублікованої адреси. Інакше легко опублікувати стару копію.
for _p in ('artifact.html', 'lipss-dashboard-v2.html'):
    open(_p, 'w', encoding='utf-8').write(art)
print('artifact', round(os.path.getsize('lipss-dashboard-v2.html')/1024), 'KB')


# --- варіант для Google Apps Script -------------------------------------------
# Редактор Apps Script давиться великими вставками, тому ріжемо на частини
# по ~70 КБ. Code.gs збирає їх докупи, шаблон більше не дублюється в коді —
# сиру копію для полагодження таблиць робить сам Code.gs.
os.makedirs('appsscript', exist_ok=True)

parts = {
  'Styles': (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;800&display=swap">\n'
    '<style>\n:root { color-scheme: light; }\nhtml, body { background: var(--color-bg); color: var(--color-text); }\n</style>\n'
    '<style>\n' + ds_css + '\n</style>\n'
    '<style>\n' + page_css + '\n</style>\n'
  ),
  'Runtime': (
    '<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>\n'
    '<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>\n'
    '<script>window.__resources = {};</script>\n'
    '<script>\n' + support + '\n</script>\n'
  ),
  'Tpl': tpl,
  'Logic': script_tag,
}
for name, body in parts.items():
    open('appsscript/%s.html' % name, 'w', encoding='utf-8').write(body)
    print('  %-8s %5d KB' % (name, len(body.encode()) / 1024))
# --- jsc harness ---
i = s.index('class Component extends DCLogic'); j = s.rindex('</script>')
h = open('harness.js', encoding='utf-8').read()
k = h.index('function dump(state, title)')
open('harness.js', 'w', encoding='utf-8').write(
  "class DCLogic { constructor(p){this.props=p||{};this.state={};} setState(u){const d=typeof u==='function'?u(this.state):u; Object.assign(this.state,d);} }\n"
  + s[i:j] + "\n" + h[k:])
print('built', round(os.path.getsize('LIPSS-dashboard-standalone.html')/1024), 'KB · збірка', BUILD)
