#!/usr/bin/env python3
"""Dependency-free checks for the AFFIADS GitHub Pages static build."""
from collections import Counter
from html.parser import HTMLParser
import json, re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.ids=[]; self.fragments=[]; self.resources=[]; self.attributes={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        for k,v in attrs.items():
            if v is not None:self.attributes.setdefault((tag,k),[]).append(v)
        if attrs.get("id"):self.ids.append(attrs["id"])
        if tag=="a":
            href=attrs.get("href","")
            if href.startswith("#") and len(href)>1:self.fragments.append(href[1:])
        for attr in ("href","src"):
            value=attrs.get(attr,"")
            if not value:continue
            parsed=urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith("#"):continue
            if parsed.path:self.resources.append((tag,attr,value,parsed.path))
def require(ok,msg):
    if not ok:raise SystemExit("ÉCHEC — "+msg)
    print("OK — "+msg)
def main():
    paths=["index.html","styles.css","script.js","apple-touch-icon.png",".github/workflows/pages.yml","confidentialite.html","mentions-legales.html","manifest.webmanifest","sitemap.xml","functions/api/devis.js","scripts/test_devis.mjs"]
    for name in paths:require((ROOT/name).is_file(),"fichier requis présent : "+name)
    html=(ROOT/"index.html").read_text(encoding="utf-8"); css=(ROOT/"styles.css").read_text(encoding="utf-8"); js=(ROOT/"script.js").read_text(encoding="utf-8")
    workflow=(ROOT/".github/workflows/pages.yml").read_text(encoding="utf-8"); api=(ROOT/"functions/api/devis.js").read_text(encoding="utf-8")
    parser=SiteParser();parser.feed(html)
    require('lang="fr"' in html,"document français")
    require("<title>" in html and 'name="description"' in html,"title et meta description SEO")
    require('role="img"' in html and 'aria-label="Illustration de l’univers digital AFFIADS"' in html,"illustration hero accessible")
    require('name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"' in html,"viewport iPhone avec viewport-fit")
    require("--safe-top:env(safe-area-inset-top,0px)" in css and "--safe-bottom:env(safe-area-inset-bottom,0px)" in css and "body::before" in css,"safe areas iOS intégrées")
    require(".site-header{position:sticky" in css and "background:#0b0d14" in css and "backdrop-filter" not in css,"header opaque et sans effet translucide")
    require("@media(max-width:760px)" in css and ".menu-toggle{display:flex" in css and ".main-navigation.is-open{display:flex}" in css,"navigation responsive avec menu mobile")
    require("prefers-reduced-motion:reduce" in css,"respect de la réduction des animations")
    require("--container:1180px" in css and "grid-template-columns" in css and "minmax(0,1fr)" in css,"grilles adaptatives")
    require("fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html,"aucune police distante Google Fonts")
    require("Site vitrine" in html and "Application web" in html and "Automatisation IA" in html and "Conseil digital" in html,"expertises principales AFFIADS présentées")
    require("indépendants" in html and "TPE" in html and "porteurs de projet" in html,"public cible identifié")
    require("mailto:affiadspro@gmail.com" in html,"contact direct fonctionnel")
    require("CONCEPT" in html and "pas des réalisations clients" in html,"concepts clairement distingués de références clients")
    require("Validation humaine" in html,"présence du principe de validation humaine pour l’IA")
    require("quote-form" not in html and "Parlons de votre projet" in html,"contact vitrine sans faux formulaire inutilisable")
    required={"accueil","contenu","expertises","realisations","methode","apropos","faq","contact"}
    require(required.issubset(set(parser.ids)),"sections principales présentes")
    require(not [i for i,n in Counter(parser.ids).items() if n>1],"identifiants HTML uniques")
    require(not set(parser.fragments).difference(parser.ids),"ancres internes valides")
    missing=[];absolute=[]
    for tag,attr,original,path in parser.resources:
        if path.startswith("/"):absolute.append(original)
        elif not (ROOT/path).is_file():missing.append(original)
    require(not absolute,"ressources locales compatibles GitHub Pages sous-répertoire")
    require(not missing,"ressources locales référencées présentes")
    require('href="./confidentialite.html"' in html and 'href="./mentions-legales.html"' in html,"pages légales reliées depuis la vitrine")
    versions=[]
    for name in ("index.html","confidentialite.html","mentions-legales.html"):
        page=(ROOT/name).read_text(encoding="utf-8")
        m=re.search(r'href="\./styles\.css\?v=([^"]+)"',page)
        require(m is not None,"version cache CSS dans "+name)
        if m:versions.append(m.group(1))
        require('rel="manifest" href="./manifest.webmanifest"' in page,"manifest lié dans "+name)
        require('name="apple-mobile-web-app-capable" content="yes"' in page,"mode PWA iOS dans "+name)
    require(len(set(versions))==1,"version CSS commune aux pages")
    manifest=json.loads((ROOT/"manifest.webmanifest").read_text(encoding="utf-8"))
    require(manifest.get("display")=="standalone" and manifest.get("start_url")=="./index.html" and manifest.get("scope")=="./","manifest PWA cohérent")
    require(manifest.get("theme_color")==manifest.get("background_color"),"couleurs du manifest PWA cohérentes")
    sitemap=ElementTree.parse(ROOT/"sitemap.xml").getroot(); ns="{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locs=[n.text.strip() for n in sitemap.findall(ns+"url/"+ns+"loc") if n.text]
    canonical="https://mansstyle59.github.io/AFFIADS/"
    expected={canonical,canonical+"confidentialite.html",canonical+"mentions-legales.html"}
    require(set(locs)==expected and len(locs)==len(expected),"sitemap avec les 3 URLs officielles")
    for name in ("confidentialite.html","mentions-legales.html"):
        page=(ROOT/name).read_text(encoding="utf-8");p=SiteParser();p.feed(page)
        require('lang="fr"' in page and "<title>" in page,"page légale française et titrée : "+name)
        require(not set(p.fragments).difference(p.ids),"ancres légales valides : "+name)
    require("n’importe plus de polices depuis Google Fonts" in (ROOT/"confidentialite.html").read_text(encoding="utf-8"),"politique confidentialité cohérente avec ressources système")
    require("RESEND_API_KEY" not in html and "RESEND_API_KEY" not in js,"aucun secret Resend exposé dans le frontend")
    require("TURNSTILE_EXPECTED_HOSTNAME" in api and "hostname" in api,"validation hostname Turnstile côté backend")
    require("node scripts/test_devis.mjs" in workflow,"tests backend devis exécutés dans CI")
    require("cp index.html styles.css script.js apple-touch-icon.png manifest.webmanifest sitemap.xml _site/" in workflow,"fichiers principaux copiés dans le site statique")
    require("cp confidentialite.html mentions-legales.html _site/" in workflow and "path: _site" in workflow,"pages légales et artefact Pages configurés")
    print("\nAFFIADS : contrôles statiques terminés avec succès.")
if __name__=="__main__":main()
