# AFFIADS — Conseil IA & création digitale

Site vitrine AFFIADS pour présenter les prestations de création digitale et de conseil en intelligence artificielle.

## Prestations présentées

- Site vitrine essentiel
- Site vitrine avancé
- Outils numériques
- Applications web
- Automatisations IA

## Structure

\`\`\`
.
├── index.html
├── styles.css
├── script.js
└── functions/
    └── api/
        └── devis.js
\`\`\`

Le site est volontairement léger : HTML, CSS et JavaScript natifs, sans framework ni dépendance à installer. Les fonctions serveur utilisent l’environnement Cloudflare Pages Functions.

## Déploiement Cloudflare Pages

1. Connecter le dépôt GitHub \`mansstyle59/AFFIADS\` à Cloudflare Pages.
2. Choisir le framework **None** (site statique).
3. Laisser le répertoire de sortie vide ou utiliser le répertoire racine du dépôt selon l’écran de configuration Cloudflare.
4. Déployer depuis la branche \`main\`.
5. Vérifier la route \`/api/devis\` après déploiement.

Les fichiers dans \`functions/\` sont détectés automatiquement par Cloudflare Pages. Ne pas publier le site en production avant d’avoir renseigné les paramètres d’envoi et finalisé les informations légales.

## Formulaire de devis — configuration requise

Le formulaire envoie les demandes à une Cloudflare Pages Function, qui utilise l’API Resend pour notifier le propriétaire. Aucun secret n’est stocké dans le dépôt.

Dans **Cloudflare Pages → Settings → Variables and Secrets**, définir les variables suivantes pour l’environnement de production (et en prévisualisation si nécessaire) :

| Variable | Description |
|---|---|
| \`RESEND_API_KEY\` | Clé API Resend, à garder secrète |
| \`QUOTE_TO_EMAIL\` | Adresse qui reçoit les demandes de devis |
| \`QUOTE_FROM_EMAIL\` | Adresse expéditrice validée par Resend |

Le domaine expéditeur doit être vérifié dans Resend. Ces paramètres ne sont pas inclus dans le code et doivent être configurés par le propriétaire. Sans eux, l’API renvoie une erreur explicite et aucune demande n’est envoyée.

### Protection et validation

- Méthode POST uniquement (route Cloudflare Pages Function).
- Validation côté navigateur et côté serveur.
- Limites de longueur des champs et validation des valeurs autorisées.
- Champ honeypot anti-spam.
- Secrets uniquement dans les variables Cloudflare.
- Réponses d’erreur génériques, sans divulguer les détails du fournisseur.

Le honeypot est une protection de base, pas une solution complète contre les abus. Avant une mise en production publique, ajouter une limitation de débit ou un service anti-spam adapté si nécessaire.

## Vérifications avant mise en production

- [ ] Configurer les variables Resend dans Cloudflare Pages.
- [ ] Envoyer une demande test et vérifier la réception par le propriétaire.
- [ ] Tester le formulaire sur iPhone Safari et ordinateur.
- [ ] Ajouter une politique de confidentialité complète : responsable du traitement, finalités, base légale, durée de conservation, destinataires/sous-traitants et droits RGPD.
- [ ] Ajouter les coordonnées professionnelles validées et les mentions légales requises.
- [ ] Définir l’URL officielle pour les métadonnées sociales et le canonical SEO.
- [ ] Vérifier le déploiement Cloudflare et les logs de la Function.

## Tests locaux

Le site statique peut être servi avec n’importe quel serveur HTTP local. Pour tester la Function en local avec le runtime Cloudflare, utiliser Wrangler et configurer les variables dans un fichier local non versionné ou via les secrets de développement.

Aucun test d’envoi e-mail ne peut réussir avant la configuration des variables et la vérification du domaine expéditeur.

## Licence

À définir par le propriétaire avant une diffusion ou réutilisation publique du code.