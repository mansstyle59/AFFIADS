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

Le site est volontairement léger : HTML, CSS et JavaScript natifs, sans framework ni dépendance à installer. Les fonctions serveur utilisent l’environnement Cloudflare Pages Functions.

## Configuration Cloudflare Pages

Le dépôt contient désormais un fichier Wrangler pour préparer le déploiement AFFIADS :

- Nom Cloudflare Pages prévu : affiads (les noms Pages sont en minuscules).
- Répertoire de sortie : racine du dépôt, car index.html est à la racine.
- Date de compatibilité : 2026-11-07.
- Le fichier wrangler.toml devient la source de vérité de la configuration Pages lorsqu’il est utilisé pour un déploiement.

Important : avant d’utiliser ce fichier sur un projet Pages déjà existant, télécharger d’abord sa configuration actuelle avec Wrangler et la comparer. Cloudflare indique que le fichier Wrangler peut remplacer les paramètres précédemment définis dans le tableau de bord. La configuration Pages par fichier Wrangler nécessite le système de build V2 ou supérieur.

La Rate Limiting API nécessite Wrangler 4.36.0 ou supérieur. Vérifier la version Wrangler utilisée par Cloudflare Pages avant le premier déploiement AFFIADS. Le projet AFFIADS n’est pas encore présent parmi les projets Pages du compte Cloudflare inspecté : aucune publication n’a donc été déclenchée.

## Formulaire de devis — configuration requise

Le formulaire envoie les demandes à une Cloudflare Pages Function, qui utilise l’API Resend pour notifier le propriétaire. Aucun secret n’est stocké dans le dépôt.

Dans Cloudflare Pages → Settings → Variables and Secrets, définir les variables suivantes pour l’environnement de production (et en prévisualisation si nécessaire) :

| Variable | Description |
|---|---|
| RESEND_API_KEY | Clé API Resend, à garder secrète |
| QUOTE_TO_EMAIL | Adresse qui reçoit les demandes de devis |
| QUOTE_FROM_EMAIL | Adresse expéditrice validée par Resend |

Le domaine expéditeur doit être vérifié dans Resend. Ces paramètres ne sont pas inclus dans le code et doivent être configurés par le propriétaire. Sans eux, l’API renvoie une erreur explicite et aucune demande n’est envoyée.

## Protection et validation

- Méthode POST uniquement (route Cloudflare Pages Function).
- Validation côté navigateur et côté serveur.
- Limites de longueur des champs et validation des valeurs autorisées.
- Taille du corps de requête limitée à 16 Ko, contrôlée avant et pendant la lecture.
- Champ honeypot anti-spam.
- Nettoyage des caractères de contrôle dans les champs.
- Rate limiting Cloudflare natif via le binding QUOTE_RATE_LIMITER : 5 requêtes par client et par période de 60 secondes.
- Le compteur utilise l’adresse cf-connecting-ip fournie par Cloudflare, avec la clé quote:<IP>.
- Si le binding ou l’adresse client manque, la Function échoue temporairement de manière fermée (HTTP 503) au lieu de contourner la protection.
- Les requêtes dépassant le seuil reçoivent HTTP 429 et Retry-After: 60.
- Secrets uniquement dans les variables Cloudflare.
- Réponses d’erreur génériques, sans divulguer les détails du fournisseur.

### Limites de la protection

Le Rate Limiting API Cloudflare est approximatif et les compteurs sont séparés par centre de données Cloudflare. Il ne constitue pas une limite stricte mondiale. La limitation par IP peut également toucher plusieurs personnes partageant une même adresse IP (réseau d’entreprise, foyer ou opérateur mobile). Le seuil devra être ajusté si des faux positifs sont constatés.

Cette protection complète le honeypot, mais ne remplace pas une solution anti-spam plus avancée en cas d’abus importants.

## Vérifications avant mise en production

- [ ] Créer le projet Cloudflare Pages AFFIADS relié au dépôt GitHub.
- [ ] Vérifier le build system Pages (V2 ou supérieur) et Wrangler 4.36.0 ou supérieur.
- [ ] Vérifier que le binding QUOTE_RATE_LIMITER est disponible en preview et en production via wrangler.toml.
- [ ] Vérifier que le namespace_id 20261107 est unique dans le compte Cloudflare.
- [ ] Configurer les variables Resend dans Cloudflare Pages.
- [ ] Envoyer une demande test et vérifier la réception par le propriétaire.
- [ ] Tester le formulaire sur iPhone Safari et ordinateur.
- [ ] Ajouter une politique de confidentialité complète : responsable du traitement, finalités, base légale, durée de conservation, destinataires/sous-traitants et droits RGPD.
- [ ] Ajouter les coordonnées professionnelles validées et les mentions légales requises.
- [ ] Définir l’URL officielle pour les métadonnées sociales et le canonical SEO.
- [ ] Vérifier le déploiement Cloudflare et les logs de la Function.

## Tests locaux

Le site statique peut être servi avec n’importe quel serveur HTTP local. Pour tester la Function en local avec le runtime Cloudflare, utiliser Wrangler et configurer les variables dans un fichier local non versionné ou via les secrets de développement.

Le Rate Limiting API doit être validé dans un environnement Cloudflare. Les tests unitaires avec un binding simulé vérifient les réponses 429/503, mais ne reproduisent pas les compteurs distribués en production.

Aucun test d’envoi e-mail ne peut réussir avant la configuration des variables et la vérification du domaine expéditeur.

## Licence

À définir par le propriétaire avant une diffusion ou réutilisation publique du code.