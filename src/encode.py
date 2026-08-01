# Кодування таблиці LIPSS у компактний рядок для дашборда.
# Дзеркало функції buildConfig() в Apps Script — правити треба обидві.
import datetime

COUNTRIES = ['Польща', 'Чехія', 'Словаччина', 'Угорщина', 'Болгарія', 'Румунія',
             'Німеччина', 'Австрія', 'Нідерланди', 'Бельгія', 'Італія',
             'Іспанія', 'Португалія', 'Франція']

# Код дії — за змістом, а не за позицією в Довіднику.
# 0 мовчить 14+ · 1 мовчить тиждень · 2 дій не треба · 3 оплата без картки · 4 інше
def acode(txt):
    t = (txt or '').lower()
    if 'мовчить 14' in t: return 0
    if 'мовчить тиждень' in t: return 1
    if 'дій не потрібно' in t or 'лід відпав' in t or 'більше нічого не треба' in t: return 2
    if 'оплата без ліда' in t or 'оплата без картки' in t: return 3
    return 4

# Причина зупинки: 0 інша · 1 не наш профіль · 2 не зацікавлений / тільки тестери
def rcode(txt):
    t = (txt or '').strip().lower()
    if not t: return None
    if 'не наш профіль' in t: return 1
    if 'не зацікавлен' in t or 'тестери' in t: return 2
    return 0


def build(rows_by_country, today):
    """rows_by_country: {країна: [rowdict, ...]}, today: datetime.date."""
    src_list, typ_list = [], ['Без типу']
    dates = [r['a'] for rs in rows_by_country.values() for r in rs if r['a']]
    day0 = min(dates) if dates else today

    def off(d):
        return '' if d is None else str((d - day0).days)

    def num(x):
        return '' if not x else ('%.2f' % x).rstrip('0').rstrip('.')

    def idx(lst, val):
        if val not in lst: lst.append(val)
        return lst.index(val)

    out = []
    for ci, country in enumerate(COUNTRIES):
        for r in rows_by_country.get(country, []):
            typ = (r['typ'] or '').strip() or 'Без типу'
            srcv = (r['src'] or '').strip()
            rs = ''
            if r['a'] and r['j'] and (r['j'] - r['a']).days >= 0:
                rs = str((r['j'] - r['a']).days)
            rn = rcode(r['reason'])
            out.append(','.join([
                str(ci),
                str(idx(src_list, srcv)) if srcv else '',
                str(idx(typ_list, typ)),
                str(int(r['stage'] or 1)),
                off(r['a']), off(r['payd']), num(r['pay']),
                off(r['repd']), num(r['rep']), rs,
                str(acode(r['act'])),
                '' if rn is None else str(rn),
                '1' if r['dup'] else '',
            ]))

    first = (min(dates) - day0).days if dates else 0
    span = (today - day0).days - first
    nw = max(4, min(12, span // 7 + 1))
    return {
        'data': ';'.join(out),
        'today': (today - day0).days,
        'nw': nw,
        'day0': [day0.year, day0.month, day0.day],
        'src': src_list,
        'typ': typ_list,
    }
