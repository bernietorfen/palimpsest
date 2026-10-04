"""Check the deployed catalogs and observer downloads without fetching large bodies."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen


class ObserverLinks(HTMLParser):
    def __init__(self):super().__init__();self.inside=False;self.links=[]
    def handle_starttag(self,tag,attributes):
        attrs=dict(attributes)
        if tag=='section' and attrs.get('id')=='observer':self.inside=True
        if self.inside and tag=='a':self.links.append(attrs['href'])
    def handle_endtag(self,tag):
        if tag=='section':self.inside=False


def request(url,method='GET'):
    return urlopen(Request(url,method=method,headers={'User-Agent':'palimpsest-exhibition-verification'}),timeout=90)


def main(args):
    output=Path(args.report)
    if output.exists():raise FileExistsError(output)
    base=args.base.rstrip('/');entries=[];catalogs=[]
    for path,count in (('/choir-edition.json',14),('/edition.json',12)):
        with request(base+path) as response:catalog=json.load(response)
        assert len(catalog['downloads'])==count,path
        catalogs.append({'path':path,'entries':count})
        for entry in catalog['downloads']:entries.append({'title':entry['title'],'url':urljoin(base,entry['url'])})
    with request(base+'/') as response:markup=response.read().decode()
    observer=ObserverLinks();observer.feed(markup);assert len(observer.links)==2
    assert all('/v2.1.0/' in href and href.endswith('.pdf') for href in observer.links)
    known={item['url'] for item in entries}
    for href in observer.links:
        if href not in known:entries.append({'title':'Observer artwork link','url':href})
    def check(item):
        assert urlparse(item['url']).scheme in ('https','http')
        with request(item['url'],'HEAD') as response:
            assert response.status==200,(item['title'],response.status)
            return {**item,'status':response.status,'content_type':response.headers.get('Content-Type'),'content_length':response.headers.get('Content-Length')}
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,entries))
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'base':base,'catalogs':catalogs,'observer_links':observer.links,'links':results,'large_bodies_downloaded':False,'scope':'Every current catalog destination and both new observer PDFs return HTTP 200. Separate browser and byte-hash checks cover the actual experience and release contents.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'links':len(results),'catalogs':catalogs,'all_http_200':True,'report':str(output)}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',default='https://site-inky-eight-42.vercel.app');p.add_argument('--report',required=True);main(p.parse_args())
