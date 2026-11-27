"""Evidence contracts for public research. No model-generated URL is trusted.
Search snippets are observations, not verified full pages or publication dates.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import ipaddress
import re
from urllib.parse import urlsplit
from founder_jarvis.persistent_memory import safe_text

TOPICS = {
    'market': 'Uzbekistan Umrah travel Saudi Arabia visa direct flights market news',
    'competitors': 'Узбекистан индивидуальная семейная умра предложения туроператоров цены',
    'marketing': 'Uzbekistan tourism travel marketing Instagram Reels consumer trends',
    'platforms': 'Booking.com Expedia travel booking product updates travel technology',
    'demand': 'Узбекистан выездной туризм Саудовская Аравия статистика спрос умра',
    'hajj': 'Saudi Ministry Hajj Umrah Nusuk pilgrimage official news regulations',
    'customer': 'Uzbekistan travel consumer behavior online booking family travel research',
    'social': 'Instagram official creators Reels travel content marketing trends',
    'risks': 'Uzbekistan Saudi Arabia travel advisories aviation pilgrimage official updates',
}

# Public market comparables, not a claim about current licensing or availability.
# Reviewed public offer pages 2026-11-27. Search queries are domain-scoped;
# no private data, logins, scraping of private accounts or arbitrary URL fetch.
WATCHLIST = {
    'watch-centrum': ('Centrum Holidays / Centrum Air', 'https://umra.centrum-air.com/?lang=ru'),
    'watch-umrabor': ('UMRABOR', 'https://umrabor.uz/ru'),
    'watch-platforma': ('Umra Platformasi', 'https://umraplatforma.uz/ru/umra'),
    'watch-safarga': ('Safarga', 'https://safarga.com/en'),
    'watch-hikmat': ('Hikmat Umra Travel', 'https://hikmatumra.uz/'),
}
GENERAL_TOPICS=tuple(TOPICS)
for key,(_,url) in WATCHLIST.items():
    TOPICS[key]='site:'+urlsplit(url).hostname+' umra paket narx safar Uzbekistan'

def host_allowed(url,topic):
    if topic not in WATCHLIST:return True
    target=urlsplit(WATCHLIST[topic][1]).hostname.removeprefix('www.')
    return (urlsplit(url).hostname or '').removeprefix('www.')==target


def public_url(url):
    try:
        p=urlsplit(url)
        try:
            ipaddress.ip_address(p.hostname or '')
            return False
        except ValueError:pass
        return (p.scheme in ('https','http') and bool(p.hostname) and '.' in p.hostname
                and not p.username and not p.password and p.hostname not in ('localhost',)
                and len(url)<=1200 and safe_text(url) and not any(c.isspace() for c in url))
    except ValueError:return False


def observations(raw, topic, stamp=None):
    """Parse upstream DDGS's actual result contract. Never fetch URLs here."""
    stamp=stamp or dt.datetime.now(dt.timezone.utc).isoformat()
    results=[]; seen=set()
    for block in str(raw).split('\n\n---\n\n')[:10]:
        m=re.search(r'^### ([^\n]+)\nSource: ([^\n]+)\nSummary: (.+)$',block.strip(),re.S)
        if not m:continue
        title,url,snippet=(x.strip() for x in m.groups())
        snippet=snippet[:1000];title=title[:240]
        if not public_url(url) or not host_allowed(url,topic) or not safe_text(title+' '+snippet) or len(snippet)<12:continue
        key=hashlib.sha256((topic+'\0'+url+'\0'+snippet).encode()).hexdigest()[:24]
        if key in seen:continue
        seen.add(key);results.append({'id':key,'url':url,'title':title,'snippet':snippet,'topic':topic,'observed_at':stamp,'verification':'search_snippet_only'})
    return results[:5]


def validate_report(data, sources):
    """Only verbatim, source-linked observations enter the facts section.
    Interpretations remain expressly unverified hypotheses. No invented citations.
    """
    if not isinstance(data,dict) or not {'findings','recommendation','measure','risk'}<=set(data) or set(data)-{'findings','recommendation','measure','risk','next_topic'}:raise ValueError('Invalid research structure')
    by_id={s['id']:s for s in sources}; found=[]; seen=set()
    if not isinstance(data['findings'],list) or len(data['findings'])>3:raise ValueError('Invalid findings')
    for item in data['findings']:
        if not isinstance(item,dict) or set(item)!={'source_id','quote','implication'}:raise ValueError('Invalid finding')
        sid,quote,imp=item['source_id'],item['quote'],item['implication']
        if not all(isinstance(v,str) for v in (sid,quote,imp)):raise ValueError('Invalid finding fields')
        if sid not in by_id or sid in seen or not 20<=len(quote)<=400 or quote not in by_id[sid]['snippet'] or not 1<=len(imp)<=500 or not safe_text(imp) or re.search(r'https?://',imp):raise ValueError('Unsupported finding')
        seen.add(sid);found.append({'source_id':sid,'quote':quote,'implication':imp})
    if not found:raise ValueError('No supported findings')
    rest={}
    for key in ('recommendation','measure','risk'):
        val=data[key]
        if not isinstance(val,str) or not 1<=len(val.strip())<=500 or not safe_text(val) or re.search(r'https?://',val):raise ValueError('Invalid recommendation')
        rest[key]=val.strip()
    if 'next_topic' in data:
        if not isinstance(data['next_topic'],str) or data['next_topic'] not in (*GENERAL_TOPICS,''):raise ValueError('Unknown follow-up topic')
        rest['next_topic']=data['next_topic']
    return {'findings':found,**rest}


def render_report(topic, sources, report):
    by_id={s['id']:s for s in sources}
    lines=['Исследование: '+(WATCHLIST[topic][0] if topic in WATCHLIST else topic),'Источники — поисковые выдержки; страницы и даты публикации независимо не проверены.']
    for item in report['findings']:
        src=by_id[item['source_id']]
        lines += ['\n'+src['title'], 'Выдержка: '+item['quote'], 'Гипотеза для iumrah: '+item['implication'],src['url'],'Получено: '+src['observed_at']]
    lines += ['\nРекомендация (предложение, не решение): '+report['recommendation'],'Как измерить: '+report['measure'],'Риск / неизвестное: '+report['risk']]
    return '\n'.join(lines)
