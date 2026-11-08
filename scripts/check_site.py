#!/usr/bin/env python3
"""Dependency-free checks for the AFFIADS GitHub Pages static build."""

from collections import Counter
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

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


def relative_luminance(hex_color):
    """Calculate WCAG relative luminance for a six-digit sRGB color."""
    value = hex_color.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError(f"Couleur hexadécimale invalide : {hex_color}")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast_ratio(foreground, background):
    """Return the WCAG contrast ratio between two sRGB colors."""
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def main():
    index_path = ROOT / "index.html"
    css_path = ROOT / "styles.css"
    js_path = ROOT / "script.js"
    icon_path = ROOT / "apple-touch-icon.png"
    workflow_path = ROOT / ".github" / "workflows" / "pages.yml"
    privacy_path = ROOT / "confidentialite.html"
    legal_path = ROOT / "mentions-legales.html"
    manifest_path = ROOT / "manifest.webmanifest"
    api_path = ROOT / "functions" / "api" / "devis.js"
    api_test_path = ROOT / "scripts" / "test_devis.mjs"

    for path in (index_path, css_path, js_path, icon_path, workflow_path, privacy_path, legal_path, manifest_path, api_path, api_test_path):
        require(path.is_file(), f"fichier requis présent : {path.relative_to(ROOT)}")

    html = index_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")
    api = api_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    parser = SiteParser()
    parser.feed(html)

    require('lang="fr"' in html, "document déclaré en français")
    require("<title>" in html and "</title>" in html, "titre SEO présent")
    require('name="description"' in html, "meta description présente")

    # WCAG AA contrast checks for visible text and keyboard focus.
    require("--muted: #626b78" in css
            and contrast_ratio("#626b78", "#edf1f5") >= 4.5,
            "texte secondaire lisible sur le fond contact (WCAG AA 4.5:1)")
    require("--muted-on-dark: #aeb9c8" in css
            and ".service-card-ai .service-number, .service-card-ai .service-tag { color: var(--muted-on-dark); }" in css
            and contrast_ratio("#aeb9c8", "#111214") >= 4.5
            and contrast_ratio("#aeb9c8", "#172233") >= 4.5,
            "numéros et tags de la carte IA gardent un contraste AA sur fond sombre")
    require("--muted-strong: #667085" in css
            and contrast_ratio("#667085", "#ffffff") >= 4.5
            and contrast_ratio("#667085", "#fbfcfd") >= 4.5,
            "petits textes et placeholders lisibles sur les champs et cartes (WCAG AA 4.5:1)")
    require("--muted-soft: #596678" in css
            and contrast_ratio("#596678", "#e5eaf0") >= 4.5,
            "texte de la note de confidentialité lisible sur son fond (WCAG AA 4.5:1)")
    require("--focus-ring: #5c53ff" in css
            and all(contrast_ratio("#5c53ff", background) >= 3.0
                    for background in ("#ffffff", "#f7f7fa", "#edf1f5", "#111214", "#101827", "#172233", "#ffc12e")),
            "indicateur de focus clavier contrasté sur les surfaces claires, sombres et accentuées (WCAG 3:1)")
    require(re.search(
        r"\.quote-form input:focus-visible\s*,\s*\.quote-form select:focus-visible\s*,\s*\.quote-form textarea:focus-visible\s*\{\s*outline:\s*3px solid var\(--focus-ring\);\s*outline-offset:\s*3px",
        css
    ) is not None,
            "champs du formulaire conservent un contour de focus clavier visible malgré outline:none")
    require("fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html,
            "aucune police externe Google Fonts chargée par la page d’accueil")
    require("--font-body:" in css and "--font-heading:" in css
            and "font-family: var(--font-body)" in css
            and "font-family: var(--font-heading)" in css,
            "polices système centralisées dans des variables CSS")
    require("body, button, input, select, textarea { font-family: var(--font-body); }" in css
            and "body, button, input, select, textarea { font-family: \"DM Sans\"" not in css,
            "texte et contrôles utilisent la pile de polices système sans ancienne surcharge")
    require('font: 800 1rem var(--font-heading)' in css
            and 'font: 800 1.12rem/1.12 var(--font-heading)' in css
            and "Manrope" not in css,
            "illustrations et cartes utilisent la variable de police de titre sans police externe codée en dur")
    privacy_html = privacy_path.read_text(encoding="utf-8")
    require("n’importe plus de polices depuis Google Fonts" in privacy_html
            and "fonts.googleapis.com" in privacy_html,
            "politique de confidentialité cohérente avec le retrait des polices distantes")

    stylesheet_versions = []
    for page_path in (index_path, privacy_path, legal_path):
        page_html = page_path.read_text(encoding="utf-8")
        page_name = page_path.name
        stylesheet_match = re.search(r'href="\./styles\.css\?v=([^"]+)"', page_html)
        require(stylesheet_match is not None, f"version de cache CSS présente dans {page_name}")
        if stylesheet_match:
            stylesheet_versions.append(stylesheet_match.group(1))
        require('rel="manifest" href="./manifest.webmanifest"' in page_html,
                f"manifest PWA lié dans {page_name}")
        require('name="apple-mobile-web-app-capable" content="yes"' in page_html,
                f"mode application iOS déclaré dans {page_name}")

    require(len(stylesheet_versions) == 3 and len(set(stylesheet_versions)) == 1,
            "version de cache CSS identique sur la page d’accueil et les pages juridiques")

    require(manifest.get("display") == "standalone", "manifest prévu pour l’affichage autonome")
    require(manifest.get("start_url") == "./index.html" and manifest.get("scope") == "./",
            "start_url et scope relatifs au sous-répertoire GitHub Pages")
    require(manifest.get("theme_color") == "#101827" and manifest.get("background_color") == manifest.get("theme_color"),
            "couleurs PWA cohérentes avec l’identité AFFIADS")
    manifest_icons = manifest.get("icons", [])
    require(any(icon.get("src") == "./assets/brand/affiads-icon.svg" and icon.get("sizes") == "any"
                for icon in manifest_icons), "icône SVG officielle présente dans le manifest")
    require(any(icon.get("src") == "./apple-touch-icon.png" and icon.get("sizes") == "180x180"
                for icon in manifest_icons), "icône iOS PNG présente dans le manifest")
    require(any(icon.get("src") == "./assets/brand/affiads-icon-maskable.svg"
                and icon.get("sizes") == "any" and icon.get("purpose") == "maskable"
                for icon in manifest_icons), "icône PWA maskable dédiée présente dans le manifest")
    for icon in manifest_icons:
        icon_path = urlsplit(icon.get("src", "")).path
        require(bool(icon_path) and not icon_path.startswith("/") and (ROOT / icon_path).is_file(),
                f"fichier d’icône PWA présent : {icon.get('src', '')}")

    # Chaque SVG exposé comme image doit pointer aria-labelledby vers un ID réel.
    svg_icon_paths = (
        ROOT / "assets" / "brand" / "favicon.svg",
        ROOT / "assets" / "brand" / "affiads-icon.svg",
        ROOT / "assets" / "brand" / "affiads-icon-maskable.svg",
    )
    for svg_path in svg_icon_paths:
        require(svg_path.is_file(), f"icône SVG présente : {svg_path.relative_to(ROOT)}")
        try:
            svg_root = ElementTree.parse(svg_path).getroot()
        except ElementTree.ParseError:
            require(False, f"SVG valide : {svg_path.relative_to(ROOT)}")
            continue

        labelled_by = svg_root.attrib.get("aria-labelledby", "").split()
        svg_ids = {
            element.attrib["id"]
            for element in svg_root.iter()
            if "id" in element.attrib
        }
        require(
            svg_root.attrib.get("role") == "img"
            and bool(labelled_by)
            and all(label in svg_ids for label in labelled_by),
            f"nom accessible SVG relié à un ID existant : {svg_path.relative_to(ROOT)}"
        )

    canonical_url = "https://mansstyle59.github.io/AFFIADS/"
    require(f'<link rel="canonical" href="{canonical_url}">' in html,
            "URL canonique correspondant au site GitHub Pages actuel")
    require(f'<meta property="og:url" content="{canonical_url}">' in html,
            "URL Open Graph cohérente avec l’URL canonique")
    require('name="twitter:card" content="summary"' in html,
            "carte de partage Twitter/X configurée")

    required_ids = {"accueil", "contenu", "services", "exemples", "approche", "contact", "confidentialite"}
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

    # Les pages juridiques sont contrôlées elles aussi, et pas seulement l'accueil.
    for page_path in (privacy_path, legal_path):
        page_html = page_path.read_text(encoding="utf-8")
        page_parser = SiteParser()
        page_parser.feed(page_html)
        page_name = page_path.name

        require('lang="fr"' in page_html, f"{page_name} déclaré en français")
        require("<title>" in page_html and "</title>" in page_html,
                f"titre présent dans {page_name}")
        require('name="description"' in page_html,
                f"meta description présente dans {page_name}")

        page_duplicates = [
            item for item, count in Counter(page_parser.ids).items() if count > 1
        ]
        require(not page_duplicates, f"identifiants uniques dans {page_name}")

        page_broken_fragments = sorted(
            set(page_parser.fragments).difference(page_parser.ids)
        )
        require(not page_broken_fragments,
                f"liens d'ancrage internes valides dans {page_name}")

        page_missing_resources = []
        page_absolute_resources = []
        for tag, attr, original, path in page_parser.resources:
            if path.startswith("/"):
                page_absolute_resources.append(original)
            elif not (ROOT / path).is_file():
                page_missing_resources.append(original)

        require(not page_absolute_resources,
                f"chemins relatifs compatibles dans {page_name}")
        require(not page_missing_resources,
                f"ressources locales présentes dans {page_name}")

    require('href="./confidentialite.html"' in html,
            "l'accueil pointe vers la politique de confidentialité")
    require('href="./mentions-legales.html"' in html,
            "l'accueil pointe vers les mentions légales")

    required_services = (
        "Site vitrine essentiel",
        "Site vitrine avancé",
        "Outil numérique",
        "Application web",
        "Automatisation IA",
    )
    require(all(service in html for service in required_services), "les cinq prestations AFFIADS sont présentées")
    require("concepts fictifs" in html and "ni des clients" in html and "ni des réalisations livrées" in html,
            "exemples de démonstration clairement distingués de réalisations client")
    require("workflow-steps" in html and "Validation humaine" in html,
            "schéma d’automatisation IA avec validation humaine présenté")
    require(".concept-grid" in css and ".workflow-steps" in css,
            "styles responsive des exemples et du schéma présents")

    require("form-unavailable" in html and 'type="submit" disabled' in html,
            "formulaire de devis clairement désactivé tant que le backend n’est pas raccordé")
    form_match = re.search(r'<form\b[^>]*id="quote-form"[^>]*>(.*?)</form>', html, re.S)
    form_opening = re.search(r'<form\b[^>]*id="quote-form"[^>]*>', html, re.S)
    require(form_opening is not None and 'action="./api/devis"' in form_opening.group(0),
            "formulaire prêt à cibler la Cloudflare Pages Function /api/devis")
    require(form_opening is not None and 'aria-disabled="true"' in form_opening.group(0),
            "formulaire de devis annoncé comme indisponible aux technologies d’assistance")
    form_controls = re.findall(r'<(?:input|select|textarea)\b([^>]*)>', form_match.group(1), re.I) if form_match else []
    require(bool(form_controls) and all(re.search(r'\bdisabled\b', attrs, re.I) for attrs in form_controls),
            "champs personnels et champ honeypot désactivés sans backend")
    require(".form-unavailable" in js and "preventDefault()" in js,
            "soumission du formulaire statique bloquée côté navigateur")
    require("RESEND_API_KEY" not in html and "RESEND_API_KEY" not in js,
            "aucune clé Resend exposée dans le frontend")
    require("TURNSTILE_EXPECTED_HOSTNAME" in api
            and "if (!expectedHostname || !/^[a-z0-9.-]+$/.test(expectedHostname))" in api,
            "hostname Turnstile de production obligatoire : échec fermé si absent ou invalide")
    require('const mediaType = contentType.split(";", 1)[0].trim().toLowerCase();' in api
            and 'if (mediaType !== "application/json")' in api,
            "Content-Type limité au media type application/json, avec paramètres MIME tolérés")
    require("typeof result.hostname === \"string\"" in api
            and "result.hostname.toLowerCase().replace(/\\.$/, \"\") === expectedHostname" in api,
            "hostname Turnstile renvoyé par Cloudflare comparé exactement après normalisation")
    api_tests = api_test_path.read_text(encoding="utf-8")
    require("application/jsonp" in api_tests and "text/application/json" in api_tests
            and "application/json; charset=utf-8" in api_tests,
            "tests couvrant les media types JSON incorrects et le charset valide")
    require("node scripts/test_devis.mjs" in workflow,
            "tests fonctionnels de la Cloudflare Pages Function exécutés dans CI")

    require("@media" in css and "--safe-top" in css,
            "CSS responsive et prise en compte de la safe area iOS")

    require("cp index.html styles.css script.js apple-touch-icon.png manifest.webmanifest _site/" in workflow,
            "fichiers principaux et manifest inclus dans le déploiement statique")
    require("cp confidentialite.html mentions-legales.html _site/" in workflow,
            "pages juridiques incluses dans le déploiement GitHub Pages")
    require("manifest.webmanifest _site/" in workflow,
            "manifest PWA inclus dans l’artefact GitHub Pages")
    require("path: _site" in workflow, "artefact GitHub Pages issu du dossier _site")

    print("\nAFFIADS : contrôles statiques terminés avec succès.")


if __name__ == "__main__":
    main()
