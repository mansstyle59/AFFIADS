# AFFIADS — Conseil IA & création digitale

Site vitrine AFFIADS pour présenter les prestations de création digitale et de conseil en intelligence artificielle.

## Prestations présentées

- Site vitrine essentiel
- Site vitrine avancé
- Outils numériques
- Applications web
- Automatisations IA

## Structure

- index.html
- styles.css
- script.js
- apple-touch-icon.png
- functions/api/devis.js
- wrangler.toml

Le site est volontairement léger : HTML, CSS et JavaScript natifs, sans framework ni dépendance à installer. Les fonctions serveur utilisent Cloudflare Pages Functions.

## Installation PWA / iPhone

- `manifest.webmanifest` décrit le nom AFFIADS, le lancement autonome et le périmètre relatif `./`, compatible avec le sous-répertoire GitHub Pages `/AFFIADS/`.
- Le manifest réutilise l’icône SVG officielle et l’Apple Touch Icon PNG 180 × 180. iOS s’appuie également sur les métadonnées Apple présentes dans les pages.
- Sur iPhone, l’installation se fait depuis Safari via **Partager → Sur l’écran d’accueil**. Le manifest ne remplace pas cette action utilisateur.
- Aucun service worker ni cache hors ligne n’est configuré à ce stade : cela évite les mises à jour bloquées par un cache PWA ancien. La vitrine nécessite une connexion réseau.

## Configuration Cloudflare Pages

Le fichier wrangler.toml prépare le projet AFFIADS pour Cloudflare Pages :

- Nom Cloudflare Pages prévu : affiads (les noms Pages sont en minuscules).
- Répertoire de sortie : racine du dépôt, car index.html est à la racine.
- Date de compatibilité : 2026-11-07.

Le fichier Wrangler devient la source de vérité de la configuration Pages lorsqu’il est utilisé pour déployer le projet. Avant d’utiliser ce fichier sur un projet Pages déjà existant, télécharger et comparer sa configuration actuelle avec Wrangler afin de ne pas remplacer involontairement des paramètres du tableau de bord.

La configuration Pages via Wrangler nécessite le système de build V2 ou supérieur et Wrangler 3.45.0 ou supérieur.

Le projet AFFIADS n’est pas encore présent parmi les projets Pages du compte Cloudflare inspecté : aucune publication n’a donc été déclenchée.

## Formulaire de devis — configuration requise

Le formulaire envoie les demandes à une Cloudflare Pages Function, qui utilise l’API Resend pour notifier le propriétaire. Aucun secret n’est stocké dans le dépôt.

Le formulaire utilise `action="./api/devis"`, qui cible `/api/devis` lorsque Cloudflare Pages publie le site à la racine. Sur GitHub Pages (site hébergé sous `/AFFIADS/`), le formulaire reste désactivé : les Pages Functions Cloudflare n’y sont pas exécutées. Ne pas retirer les attributs `disabled` ni le message d’indisponibilité avant d’avoir configuré et testé le projet Cloudflare Pages.

### Protection anti-spam Cloudflare Turnstile

Turnstile est une solution gratuite de Cloudflare adaptée aux formulaires Pages. La vérification serveur est obligatoire : un widget côté navigateur seul ne protège pas l’endpoint.

1. Créer un widget Turnstile dans le tableau de bord Cloudflare.
2. Autoriser le hostname du site AFFIADS dans ce widget.
3. Copier la clé publique (sitekey) dans index.html à la place de YOUR_TURNSTILE_SITE_KEY.
4. Ajouter la clé secrète TURNSTILE_SECRET_KEY dans Cloudflare Pages → Settings → Variables and Secrets.
5. Renseigner obligatoirement TURNSTILE_EXPECTED_HOSTNAME avec le hostname exact de production (par exemple `affiads.pages.dev` ou le domaine personnalisé, sans protocole ni chemin).

La Function vérifie le token avec l’API Siteverify de Cloudflare, exige une validation réussie, l’action `quote` et une correspondance exacte du hostname retourné (comparaison insensible à la casse et normalisation d’un point final). Si TURNSTILE_EXPECTED_HOSTNAME est absent ou invalide, la Function refuse l’envoi avec HTTP 503. La clé secrète ne doit jamais être placée dans HTML, JavaScript client ou Git.

Si la clé publique ou la clé secrète n’est pas configurée, l’envoi de devis est refusé avec une réponse explicite : le formulaire échoue fermé au lieu d’accepter les demandes sans protection.

### Variables Resend

Dans Cloudflare Pages → Settings → Variables and Secrets, définir les variables suivantes en production (et en prévisualisation si nécessaire) :

| Variable | Description |
|---|---|
| RESEND_API_KEY | Clé API Resend, à garder secrète |
| QUOTE_TO_EMAIL | Adresse qui reçoit les demandes de devis |
| QUOTE_FROM_EMAIL | Adresse expéditrice validée par Resend |

Le domaine expéditeur doit être vérifié dans Resend. Ces paramètres ne sont pas inclus dans le code et doivent être configurés par le propriétaire.

## Protection et validation

- Méthode POST uniquement (route Cloudflare Pages Function).
- Validation côté navigateur et côté serveur.
- Limites de longueur des champs et validation des valeurs autorisées.
- Taille du corps de requête limitée à 16 Ko, contrôlée avant et pendant la lecture.
- Champ honeypot anti-spam.
- Nettoyage des caractères de contrôle dans les champs.
- Validation serveur du token Turnstile avant tout envoi e-mail.
- Vérification de l’action Turnstile quote et du hostname de production obligatoire (échec fermé si la variable manque).
- Aucun secret dans le dépôt.
- Réponses d’erreur génériques, sans divulguer les détails du fournisseur.

### Limitation de fréquence

Le Rate Limiting binding documenté pour Cloudflare Workers n’est pas explicitement listé parmi les bindings Pages Functions pris en charge dans la documentation Pages consultée. Je ne l’ai donc pas ajouté à la configuration Pages pour éviter un déploiement potentiellement invalide.

Une règle de rate limiting WAF pourra être ajoutée plus tard si AFFIADS utilise un domaine personnalisé géré par Cloudflare. Le compte Cloudflare inspecté ne contient actuellement aucune zone DNS, et le projet Pages AFFIADS n’est pas encore créé.

Turnstile protège contre une partie des soumissions automatisées, mais ne remplace pas une limitation de fréquence stricte en cas d’attaque ciblée.

## Vérifications avant mise en production

- [ ] Créer le projet Cloudflare Pages AFFIADS relié au dépôt GitHub.
- [ ] Vérifier le système de build Pages (V2 ou supérieur).
- [ ] Créer le widget Turnstile et autoriser le hostname de production.
- [ ] Remplacer YOUR_TURNSTILE_SITE_KEY dans index.html par la clé publique réelle.
- [ ] Ajouter TURNSTILE_SECRET_KEY dans les variables secrètes Cloudflare.
- [ ] Définir obligatoirement TURNSTILE_EXPECTED_HOSTNAME avec le hostname exact de production.
- [ ] Configurer les variables Resend dans Cloudflare Pages.
- [ ] Envoyer une demande test et vérifier la réception par le propriétaire.
- [ ] Tester les tokens Turnstile valides, expirés et invalides.
- [ ] Tester le formulaire sur iPhone Safari et ordinateur.
- [ ] Ajouter une politique de confidentialité complète : responsable du traitement, finalités, base légale, durée de conservation, destinataires/sous-traitants et droits RGPD.
- [ ] Ajouter les coordonnées professionnelles validées et les mentions légales requises.
- [ ] Définir l’URL officielle pour les métadonnées sociales et le canonical SEO.
- [ ] Vérifier le déploiement Cloudflare et les logs de la Function.

## Tests locaux

Le site statique peut être servi avec n’importe quel serveur HTTP local. Pour tester la Function en local avec le runtime Cloudflare, utiliser Wrangler et configurer les variables dans un fichier local non versionné ou via les secrets de développement.

Les tests locaux avec Siteverify simulé vérifient les chemins de validation, mais ne remplacent pas un test avec un widget et des clés Cloudflare réelles.

Aucun test d’envoi e-mail ne peut réussir avant la configuration des variables et la vérification du domaine expéditeur.

## Licence

À définir par le propriétaire avant une diffusion ou réutilisation publique du code.

## Identité visuelle AFFIADS

Les logos SVG officiels sont centralisés dans `assets/brand/` :

- [Icône officielle](assets/brand/affiads-icon.svg) — symbole seul, utilisé dans l’en-tête et le footer.
- [Logo horizontal clair](assets/brand/affiads-logo-light.svg) — fond clair.
- [Logo horizontal sombre](assets/brand/affiads-logo-dark.svg) — fond sombre.
- [Favicon SVG](assets/brand/favicon.svg) — icône de navigateur.
- `apple-touch-icon.png` — icône iOS 180 × 180.

Palette officielle : bleu électrique `#4D4AFF`, violet `#713CF4`, jaune `#FFC12E`, blanc `#FFFFFF`, noir profond `#111214`.
