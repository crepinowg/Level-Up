# Prospector

Trouve des entreprises (au Togo par defaut, mais utilisable pour n'importe
quelle zone) qui n'ont pas de site web, ou dont le site existant a des
problemes (lent, pas adapte au mobile, hors ligne, pas en HTTPS...), afin de
constituer une liste de prospects qualifies pour une offre de creation ou de
refonte de site.

## Installation

```bash
cd prospector
pip install -r requirements.txt
```

## Prerequis

Une cle API Google avec acces a la **Places API** (legacy), activee dans
Google Cloud Console. La cle doit avoir un mode de facturation actif cote
Google (l'API Places facture a l'usage au-dela du quota gratuit mensuel).

```bash
export GOOGLE_PLACES_API_KEY="votre_cle"
```

## Utilisation

```bash
python3 prospector.py --query "restaurant" --location "Lome, Togo"
python3 prospector.py --query "boutique de vetements" --location "Kara, Togo" --output kara.csv
python3 prospector.py --query "hotel" --location "Lome, Togo" --max-results 100 --delay 1
```

### Options

| Option | Description | Defaut |
|---|---|---|
| `--query` | Secteur ou type d'entreprise recherche | requis |
| `--location` | Ville/zone recherchee | requis |
| `--api-key` | Cle API (sinon lue depuis `GOOGLE_PLACES_API_KEY`) | - |
| `--max-results` | Nombre max d'entreprises analysees | 60 |
| `--delay` | Delai entre requetes (s), a augmenter si limite de debit atteinte | 0.5 |
| `--output` | Fichier CSV de sortie | `prospects.csv` |

## Sortie

Un fichier CSV trie par priorite (les entreprises sans site d'abord, puis les
sites les plus problematiques), avec les colonnes :

`Nom, Adresse, Telephone, Note, Nb avis, Site web, Statut, Problemes, Score priorite, Lien Google Maps`

Statuts possibles : `PAS_DE_SITE`, `SITE_HORS_LIGNE`, `SITE_A_AMELIORER`,
`SITE_PERFECTIBLE`, `SITE_OK`.

## A savoir

- L'audit de site est volontairement simple (HTTPS, temps de reponse,
  presence d'une meta viewport mobile, balise `<title>`, volume de contenu).
  Il sert a prioriser, pas a remplacer un audit complet.
- Respectez les conditions d'utilisation de Google Places (volume de
  requetes, usage des donnees) et la reglementation locale sur la
  prospection commerciale avant d'utiliser cette liste pour du demarchage.
- Ne commitez jamais votre cle API dans le depot : utilisez toujours la
  variable d'environnement `GOOGLE_PLACES_API_KEY`.
