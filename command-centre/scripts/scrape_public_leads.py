#!/usr/bin/env python3
"""Public-safe AI King lead scraper: public listings + public homepages only."""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; DATA_DIR=ROOT/'data'; DEFAULT_OUTPUT=DATA_DIR/'leads.json'; DEFAULT_STATE=DATA_DIR/'run_state.json'; DEFAULT_SEEDS=DATA_DIR/'lead_seeds.json'
UA='AIKingCommandCentre/1.0 (+https://aiking.info; public metadata scraper)'
OVERPASS_ENDPOINTS=['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']
CITY_BBOX={'Brisbane':(-27.72,152.65,-27.05,153.55),'Gold Coast':(-28.25,153.05,-27.65,153.70)}
STATUS_ORDER=['new','researched','scored','draft_ready','approval_queue','approved_to_contact','contacted','follow_up_due','warm','booked_call','proposal_sent','won','lost']
EMAIL_RE=re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',re.I); PHONE_RE=re.compile(r'(?:\+?61|0)[\s().-]*(?:2|3|4|7|8)[\d\s().-]{7,14}')
BOOKING_RE=re.compile(r'\b(book\s*(?:now|online|appointment|consult)|online\s*booking|schedule|calendly|hotdoc|healthengine|zocdoc)\b',re.I); FORM_RE=re.compile(r'<form\b',re.I); AI_RE=re.compile(r'\b(ai|automation|chatbot|virtual assistant|workflow)\b',re.I)
BAD_EMAIL_TLDS={'png','jpg','jpeg','gif','webp','svg','css','js'}; BAD_EMAIL_MARKERS=('sentry','wixpress','sansoxygen','example.com','localhost')
def clean_emails(values):
    out=[]
    for email in values:
        email=email.lower().strip('.;, )]}>')
        domain=email.split('@')[-1] if '@' in email else ''
        tld=domain.rsplit('.',1)[-1] if '.' in domain else ''
        if tld in BAD_EMAIL_TLDS or any(m in email for m in BAD_EMAIL_MARKERS) or '@2x.' in email:
            continue
        out.append(email)
    return sorted(set(out))[:3]
def clean_phones(values):
    out=[]
    for raw in values:
        digits=re.sub(r'\D+','',raw)
        if digits.startswith('61') and len(digits)==11:
            norm='+'+digits
        elif digits.startswith('0') and len(digits)==10:
            norm=digits
        else:
            continue
        out.append(norm)
    return sorted(set(out))[:3]
def safe_channel(raw):
    raw=(raw or '').strip()
    if not raw or '*' in raw or any(m in raw.lower() for m in ('sentry','wixpress','sansoxygen','@2x.','.png')):
        return ''
    return raw
class PageParser(HTMLParser):
    def __init__(self): super().__init__(); self.title_parts=[]; self.in_title=False; self.meta={}; self.links=[]
    def handle_starttag(self,tag,attrs):
        d={k.lower():v or '' for k,v in attrs}
        if tag.lower()=='title': self.in_title=True
        if tag.lower()=='meta':
            key=(d.get('name') or d.get('property') or '').lower()
            if key and d.get('content'): self.meta[key]=html.unescape(d['content'])
        if tag.lower()=='a' and d.get('href'): self.links.append(d['href'])
    def handle_endtag(self,tag):
        if tag.lower()=='title': self.in_title=False
    def handle_data(self,data):
        if self.in_title: self.title_parts.append(data.strip())
    @property
    def title(self): return ' '.join(p for p in self.title_parts if p).strip()
def now_iso(): return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
def stable_id(name,city,website=''):
    raw=(website or f'{name}-{city}').lower().encode('utf-8','ignore'); return 'AK-'+hashlib.sha1(raw).hexdigest()[:8].upper()
def fetch_url(url,data=None,timeout=20):
    req=urllib.request.Request(url,data=data,headers={'User-Agent':UA,'Accept':'text/html,application/json;q=0.9,*/*;q=0.7'})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        charset=resp.headers.get_content_charset() or 'utf-8'; return int(resp.status), resp.read(1500000).decode(charset,errors='replace')
def normalize_url(raw,base=''):
    if not raw: return ''
    raw=html.unescape(str(raw)).strip().strip('"\'')
    if raw.startswith('//'): raw='https:'+raw
    if base: raw=urllib.parse.urljoin(base,raw)
    if raw and not re.match(r'^[a-z]+://',raw,re.I): raw='https://'+raw
    p=urllib.parse.urlparse(raw)
    if p.scheme not in {'http','https'} or not p.netloc: return ''
    return urllib.parse.urlunparse((p.scheme,p.netloc.lower(),p.path.rstrip('/') or '/', '', '', ''))
def overpass_query(city,niche):
    s,w,n,e=CITY_BBOX[city]; bbox=f'({s},{w},{n},{e})'
    if niche.lower().startswith('dent'):
        body=(f'node["amenity"="dentist"]{bbox};way["amenity"="dentist"]{bbox};relation["amenity"="dentist"]{bbox};'
              f'node["healthcare"="dentist"]{bbox};way["healthcare"="dentist"]{bbox};relation["healthcare"="dentist"]{bbox};')
    else:
        pat='aesthetic|cosmetic|skin|laser|inject|dermal|medi.?spa|beauty'
        body=(f'node["shop"="beauty"]{bbox};way["shop"="beauty"]{bbox};relation["shop"="beauty"]{bbox};'
              f'node["healthcare"="clinic"]["name"~"{pat}",i]{bbox};way["healthcare"="clinic"]["name"~"{pat}",i]{bbox};relation["healthcare"="clinic"]["name"~"{pat}",i]{bbox};'
              f'node["name"~"{pat}",i]{bbox};way["name"~"{pat}",i]{bbox};relation["name"~"{pat}",i]{bbox};')
    return f'[out:json][timeout:25];({body});out center tags 80;'
def query_overpass(city,niche):
    payload=urllib.parse.urlencode({'data':overpass_query(city,niche)}).encode(); errors=[]
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            status,body=fetch_url(endpoint,data=payload,timeout=35)
            if status==200: return json.loads(body).get('elements',[]),errors
            errors.append(f'{endpoint} HTTP {status}')
        except Exception as exc: errors.append(f'{endpoint}: {type(exc).__name__}: {exc}')
    return [],errors
def element_to_candidate(el,city,niche):
    tags=el.get('tags') or {}; name=(tags.get('name') or tags.get('operator') or '').strip()
    if not name: return None
    if any(tags.get(k) for k in ('highway','public_transport','railway','route')):
        return None
    if niche.lower().startswith('aesthetic') and re.search(r'\b(superstore|supplies|supply|trade supplier|wholesale)\b', name, re.I):
        return None
    website=normalize_url(tags.get('website') or tags.get('contact:website') or tags.get('url'))
    channel=tags.get('contact:email') or tags.get('email') or tags.get('phone') or tags.get('contact:phone') or 'public web listing'
    return {'business_name':name,'city':city,'niche':'Dental' if niche.lower().startswith('dent') else 'Aesthetics / skin clinic','website':website,'contact_channel':channel,'source':'OpenStreetMap public listing','osm_id':str(el.get('id',''))}
def load_json(path,default):
    try: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except Exception: return default
def parse_page(url):
    d={'website_status':'not_fetched','title':'','description':'','emails':[],'phones':[],'socials':[],'has_booking':False,'has_form':False,'mentions_ai':False}
    if not url: return d
    try:
        status,body=fetch_url(url,timeout=15); d['website_status']=f'HTTP {status}'; parser=PageParser(); parser.feed(body[:1200000])
        d['title']=parser.title[:180]; d['description']=(parser.meta.get('description') or parser.meta.get('og:description') or '')[:300]
        d['emails']=clean_emails(EMAIL_RE.findall(body)); d['phones']=clean_phones(PHONE_RE.findall(body))
        socials=[]
        for link in parser.links:
            full=normalize_url(link,url)
            if full and any(host in full for host in ('instagram.com','facebook.com','linkedin.com')): socials.append(full)
        d['socials']=sorted(set(socials))[:5]; d['has_booking']=bool(BOOKING_RE.search(body)); d['has_form']=bool(FORM_RE.search(body)); d['mentions_ai']=bool(AI_RE.search(body))
    except urllib.error.HTTPError as exc: d['website_status']=f'HTTP {exc.code}'
    except Exception as exc: d['website_status']=f'fetch_failed: {type(exc).__name__}'
    return d
def score_and_enrich(c,page):
    niche=c.get('niche') or 'Local business'; name=c.get('business_name') or 'Unknown business'; city=c.get('city') or 'Australia'; website=c.get('website') or ''; score=55; leaks=[]
    if website: score+=10
    else: leaks.append('No website found in public listing, so the first-step enquiry path may be fragmented.')
    if page.get('emails') or page.get('phones') or safe_channel(c.get('contact_channel')): score+=8
    else: leaks.append('Contact path was not obvious from the first public page.')
    if not page.get('has_booking'): score+=10; leaks.append('No obvious instant booking / consult scheduling path detected on the homepage.')
    if page.get('has_form'): score+=6; leaks.append('Lead capture likely relies on manual form follow-up speed.')
    if not page.get('mentions_ai'): score+=5; leaks.append('No visible AI-assisted enquiry or follow-up workflow positioning.')
    if 'Dental' in niche or 'Aesthetics' in niche: score+=8
    if str(page.get('website_status','')).startswith('fetch_failed'): score-=8; leaks.append('Website fetch failed during public scan; manually verify before outreach.')
    score=max(40,min(96,score)); leaks=leaks or ['Homepage has a contact path; still worth checking reply speed, recall/follow-up, and owner visibility.']
    if 'Dental' in niche: angle='AI Revenue Leakage Audit for enquiry speed, recall follow-up and treatment-plan reactivation.'; value='$300-$8,000+ per patient depending treatment'
    elif 'Aesthetics' in niche: angle='Lead Response Agent + consult follow-up queue to recover paid-lead leakage.'; value='$900-$2,500+ per consult/client'
    else: angle='AI Revenue Leakage Audit to find slow follow-up and owner-dependent sales execution.'; value='varies'
    bits=[]
    if page.get('emails'): bits.append(page['emails'][0])
    if page.get('phones'): bits.append(page['phones'][0])
    if page.get('socials'): bits.append(page['socials'][0])
    bits=[b for b in bits if safe_channel(b)]
    return {'id':stable_id(name,city,website),'business_name':name,'is_demo':False,'niche':niche,'city':city,'website':website,'contact_name':'Owner / Practice Manager','contact_channel':', '.join(bits) or safe_channel(c.get('contact_channel')) or 'public website','score':score,'status':'scored' if score>=70 else 'researched','estimated_customer_value':value,'visible_leak':leaks[0],'ai_king_angle':angle,'next_action':'Manually review fit, then draft personalised approval-first outreach.' if score>=75 else 'Review later; lower confidence from public scan.','last_contacted':'','follow_up_date':'','drafts':{},'source':c.get('source','public website scrape'),'website_status':page.get('website_status',''),'page_title':page.get('title',''),'page_description':page.get('description',''),'last_scraped':now_iso()}
def merge_preserving_status(new,existing):
    oldmap={}
    for lead in existing:
        if lead.get('is_demo'): continue
        key=(lead.get('website') or f"{lead.get('business_name','')}|{lead.get('city','')}").lower(); oldmap[key]=lead
    merged=[]
    for lead in new:
        key=(lead.get('website') or f"{lead.get('business_name','')}|{lead.get('city','')}").lower(); old=oldmap.get(key)
        if old:
            lead['id']=old.get('id',lead['id'])
            if old.get('status') in STATUS_ORDER and old.get('status') not in {'new','researched','scored'}: lead['status']=old['status']
            for field in ('last_contacted','follow_up_date','notes'):
                if old.get(field): lead[field]=old[field]
        merged.append(lead)
    return sorted(merged,key=lambda x:(int(x.get('score') or 0),x.get('business_name','')),reverse=True)
def collect_candidates(cities,niches,limit):
    candidates=[]; errors=[]
    for city in cities:
        if city not in CITY_BBOX: errors.append(f'Unsupported city: {city}'); continue
        for niche in niches:
            elements,errs=query_overpass(city,niche); errors.extend(errs[:2])
            for el in elements:
                c=element_to_candidate(el,city,niche)
                if c: candidates.append(c)
            time.sleep(1.0)
    for seed in load_json(DEFAULT_SEEDS,[]):
        if isinstance(seed,dict) and seed.get('business_name'):
            seed=dict(seed); seed['website']=normalize_url(seed.get('website')); seed.setdefault('source','manual seed'); candidates.append(seed)
    dedup={}
    for c in candidates:
        key=(c.get('website') or f"{c.get('business_name','')}|{c.get('city','')}").lower()
        if key and key not in dedup: dedup[key]=c
    return sorted(dedup.values(),key=lambda c:(bool(c.get('website')),c.get('business_name','')),reverse=True)[:limit],errors
def main():
    p=argparse.ArgumentParser(description='Scrape public prospect metadata for AI King Command Centre'); p.add_argument('--cities',default='Brisbane,Gold Coast'); p.add_argument('--niches',default='dentist,aesthetic'); p.add_argument('--limit',type=int,default=30); p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT); p.add_argument('--state',type=Path,default=DEFAULT_STATE); p.add_argument('--no-merge',action='store_true'); args=p.parse_args()
    cities=[c.strip() for c in args.cities.split(',') if c.strip()]; niches=[n.strip() for n in args.niches.split(',') if n.strip()]; existing=load_json(args.output,[])
    candidates,errors=collect_candidates(cities,niches,args.limit); leads=[]
    for i,c in enumerate(candidates,1):
        leads.append(score_and_enrich(c,parse_page(c.get('website',''))))
        if i%4==0: time.sleep(.8)
    if not args.no_merge: leads=merge_preserving_status(leads,existing)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(leads,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    state={'last_run_at':now_iso(),'mode':'GitHub Actions cloud scraper' if os.environ.get('GITHUB_ACTIONS') else 'local scraper verification','status':'ok' if leads else 'empty','source':'OpenStreetMap public listings + public website homepage scan','cities':cities,'niches':niches,'found':len(candidates),'saved':len(leads),'errors':errors[:8] if not leads else [],'safety':'Public website/contact metadata only. No login, no bypassing, no private data, no automatic outbound.'}
    args.state.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps({'saved':len(leads),'found':len(candidates),'errors':len(errors),'output':str(args.output)},indent=2)); return 0 if leads else 2
if __name__=='__main__': raise SystemExit(main())
