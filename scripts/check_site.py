#!/usr/bin/env python3
"""Dependency-free checks for the AFFIADS GitHub Pages static build."""

from collections import Counter
from html.parser import HTMLParser
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.fragments = []
        self.resources = []
        self.attributes = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key, value in attrs.items():
            if value is not None:
                self.attributes.setdefault((tag, key), []).append(value)

        element_id = attrs.get("id")
        if element_id:
            self.ids.append(element_id)

        if tag == "a":
            href = attrs.get("href", "")
            if href.startswith("#") and len(href) > 1:
                self.fragments.append(href[1:])

        for attr in ("href", "src"):
            value = attrs.get(attr, "")
            if not value:
                continue
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith("#"):
                continue
            if parsed.path:
                self.resources.append((tag, attr, value, parsed.path))


def require(condition, message):
    if not condition:
        raise SystemExit(f"ÉCHEC — {message}")
    print(f"OK — {message}")


def main():
    index_path = ROOT / "index.html"
    css_path = ROOT / "styles.css"
    js_path = ROOT / "script.js"
    icon_path = ROOT / "apple-touch-icon.png"
    workflow_path = ROOT / ".github" / "workflows" / "pages.yml"

    for path in (index_path, css_path, js_path, icon_path, workflow_path):
        require(path.is_file(), f"fichier requis présent : {path.relative_to(ROOT)}")

    html = index_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")

    parser = SiteParser()
    parser.feed(html)

    require('lang="fr"' in html, "document déclaré en français")
    require("<title>" in html and "</title>" in html, "titre SEO présent")
    require('name="description"' in html, "meta description présente")

    canonical_url = "https://mansstyle59.github.io/AFFIADS/"
    require(f'<link rel="canonical" href="{canonical_url}">' in html,
            "URL canonique correspondant au site GitHub Pages actuel")
    require(f'<meta property="og:url" content="{canonical_url}">' in html,
            "URL Open Graph cohérente avec l’URL canonique")
    require('name="twitter:card" content="summary"' in html,
            "carte de partage Twitter/X configurée")

    required_ids = {"accueil", "contenu", "services", "approche", "contact", "confidentialite"}
    missing_ids = required_ids.difference(parser.ids)
    require(not missing_ids, f"sections principales présentes : {sorted(required_ids)}")

    duplicates = [item for item, count in Counter(parser.ids).items() if count > 1]
    require(not duplicates, "identifiants HTML uniques")

    broken_fragments = sorted(set(parser.fragments).difference(parser.ids))
    require(not broken_fragments, "liens internes valides")

    missing_resources = []
    absolute_resources = []
    for tag, attr, original, path in parser.resources:
        if path.startswith("/"):
            absolute_resources.append(original)
        elif not (ROOT / path).is_file():
            missing_resources.append(original)

    require(not absolute_resources, "ressources locales compatibles avec le sous-répertoire GitHub Pages")
    require(not missing_resources, "ressources locales référencées présentes")

    required_services = (
        "Site vitrine essentiel",
        "Site vitrine avancé",
        "Outil numérique",
        "Application web",
        "Automatisation IA",
    )
    require(all(service in html for service in required_services), "les cinq prestations AFFIADS sont présentées")

    require("form-unavailable" in html and 'type="submit" disabled' in html,
            "formulaire de devis clairement désactivé tant que le backend n’est pas raccordé")
    form_match = re.search(r'<form\b[^>]*id="quote-form"[^>]*>(.*?)</form>', html, re.S)
    form_opening = re.search(r'<form\b[^>]*id="quote-form"[^>]*>', html, re.S)
    require(form_opening is not None and 'aria-disabled="true"' in form_opening.group(0),
            "formulaire de devis annoncé comme indisponible aux technologies d’assistance")
    form_controls = re.findall(r'<(?:input|select|textarea)\b([^>]*)>', form_match.group(1), re.I) if form_match else []
    require(bool(form_controls) and all(re.search(r'\bdisabled\b', attrs, re.I) for attrs in form_controls),
            "champs personnels et champ honeypot désactivés sans backend")
    require(".form-unavailable" in js and "preventDefault()" in js,
            "soumission du formulaire statique bloquée côté navigateur")
    require("RESEND_API_KEY" not in html and "RESEND_API_KEY" not in js,
            "aucune clé Resend exposée dans le frontend")

    require("@media" in css and "--safe-top" in css,
            "CSS responsive et prise en compte de la safe area iOS")

    require("cp index.html styles.css script.js apple-touch-icon.png _site/" in workflow,
            "workflow limité aux quatre fichiers statiques autorisés")
    require("path: _site" in workflow, "artefact GitHub Pages issu du dossier _site")

    print("\nAFFIADS : contrôles statiques terminés avec succès.")


if __name__ == "__main__":
    main()
