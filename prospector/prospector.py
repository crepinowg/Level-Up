#!/usr/bin/env python3
"""
Prospector - trouve des entreprises sans site web ou avec un site de mauvaise
qualite, a partir de l'API Google Places, et exporte une liste qualifiee en CSV.

Usage:
    export GOOGLE_PLACES_API_KEY="votre_cle"
    python3 prospector.py --query "restaurant" --location "Lome, Togo"
    python3 prospector.py --query "boutique" --location "Kara, Togo" --output kara.csv

La cle API doit avoir acces a la "Places API" (legacy) dans Google Cloud Console.
"""

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

DETAILS_FIELDS = "name,formatted_address,formatted_phone_number,international_phone_number,website,rating,user_ratings_total,url"

VIEWPORT_RE = re.compile(r"<meta[^>]+name=[\"']viewport[\"']", re.IGNORECASE)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass
class Prospect:
    name: str
    address: str
    phone: str
    rating: Optional[float]
    reviews: Optional[int]
    website: str
    maps_url: str
    status: str
    issues: list = field(default_factory=list)
    score: int = 0


def search_places(query: str, location: str, api_key: str, max_results: int, delay: float):
    """Cherche des entreprises via Places Text Search, avec pagination."""
    places = []
    params = {"query": f"{query} {location}", "key": api_key}
    while True:
        resp = requests.get(TEXTSEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            raise RuntimeError(f"Google Places API error: {status} - {data.get('error_message', '')}")

        places.extend(data.get("results", []))
        if len(places) >= max_results:
            return places[:max_results]

        next_token = data.get("next_page_token")
        if not next_token:
            return places

        # Google exige un court delai avant que le token de pagination soit valide.
        time.sleep(2)
        params = {"pagetoken": next_token, "key": api_key}
        time.sleep(delay)


def fetch_details(place_id: str, api_key: str) -> dict:
    params = {"place_id": place_id, "fields": DETAILS_FIELDS, "key": api_key}
    resp = requests.get(DETAILS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        return {}
    return data.get("result", {})


def audit_website(url: str, timeout: float = 10.0) -> tuple[list, int]:
    """Audit basique d'un site web. Retourne (liste_de_problemes, score_de_gravite)."""
    issues = []
    score = 0

    if not url.lower().startswith("https://"):
        issues.append("Pas de HTTPS")
        score += 2

    try:
        start = time.monotonic()
        resp = requests.get(url, timeout=timeout, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (ProspectorAudit/1.0)"})
        elapsed = time.monotonic() - start
    except requests.exceptions.RequestException as exc:
        issues.append(f"Site inaccessible ({exc.__class__.__name__})")
        return issues, 10

    if resp.status_code >= 400:
        issues.append(f"Erreur HTTP {resp.status_code}")
        score += 5
        return issues, score

    if elapsed > 3.0:
        issues.append(f"Lent ({elapsed:.1f}s)")
        score += 1

    html = resp.text or ""

    if not VIEWPORT_RE.search(html):
        issues.append("Pas adapte au mobile (pas de meta viewport)")
        score += 3

    title_match = TITLE_RE.search(html)
    title = title_match.group(1).strip() if title_match else ""
    if not title:
        issues.append("Pas de balise <title>")
        score += 1

    if len(html) < 2000:
        issues.append("Page tres pauvre en contenu")
        score += 2

    return issues, score


def classify(website: str, issues: list, audit_score: int) -> tuple[str, int]:
    if not website:
        return "PAS_DE_SITE", 10
    if "Site inaccessible" in " ".join(issues) or any("Erreur HTTP" in i for i in issues):
        return "SITE_HORS_LIGNE", 8
    if audit_score >= 4:
        return "SITE_A_AMELIORER", audit_score
    if audit_score > 0:
        return "SITE_PERFECTIBLE", audit_score
    return "SITE_OK", 0


def run(query: str, location: str, api_key: str, max_results: int, delay: float, output: str):
    print(f"Recherche: '{query}' pres de '{location}' (max {max_results} resultats)...", file=sys.stderr)
    places = search_places(query, location, api_key, max_results, delay)
    print(f"{len(places)} entreprises trouvees. Analyse en cours...", file=sys.stderr)

    prospects = []
    for i, place in enumerate(places, 1):
        place_id = place.get("place_id")
        details = fetch_details(place_id, api_key) if place_id else {}
        name = details.get("name") or place.get("name", "")
        address = details.get("formatted_address") or place.get("formatted_address", "")
        phone = details.get("formatted_phone_number") or details.get("international_phone_number") or ""
        rating = details.get("rating")
        reviews = details.get("user_ratings_total")
        website = details.get("website", "")
        maps_url = details.get("url", "")

        print(f"  [{i}/{len(places)}] {name}", file=sys.stderr)

        if website:
            issues, audit_score = audit_website(website)
        else:
            issues, audit_score = [], 0

        status, score = classify(website, issues, audit_score)

        prospects.append(Prospect(
            name=name, address=address, phone=phone, rating=rating, reviews=reviews,
            website=website, maps_url=maps_url, status=status, issues=issues, score=score,
        ))

        time.sleep(delay)

    # Priorite: pas de site d'abord, puis site le plus problematique.
    prospects.sort(key=lambda p: -p.score)

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Nom", "Adresse", "Telephone", "Note", "Nb avis", "Site web",
                          "Statut", "Problemes", "Score priorite", "Lien Google Maps"])
        for p in prospects:
            writer.writerow([
                p.name, p.address, p.phone, p.rating or "", p.reviews or "",
                p.website, p.status, "; ".join(p.issues), p.score, p.maps_url,
            ])

    no_site = sum(1 for p in prospects if p.status == "PAS_DE_SITE")
    poor_site = sum(1 for p in prospects if p.status in ("SITE_A_AMELIORER", "SITE_HORS_LIGNE"))
    print(f"\nTermine. {no_site} sans site, {poor_site} avec site a ameliorer/hors ligne.", file=sys.stderr)
    print(f"Resultats exportes vers: {output}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", required=True, help="Secteur ou type d'entreprise (ex: 'restaurant', 'boutique de vetements')")
    parser.add_argument("--location", required=True, help="Ville/zone (ex: 'Lome, Togo')")
    parser.add_argument("--api-key", default=None, help="Cle API Google Places (sinon lue depuis GOOGLE_PLACES_API_KEY)")
    parser.add_argument("--max-results", type=int, default=60, help="Nombre maximum d'entreprises a analyser (par defaut 60)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delai (s) entre les requetes, pour rester raisonnable (par defaut 0.5)")
    parser.add_argument("--output", default="prospects.csv", help="Fichier CSV de sortie (par defaut prospects.csv)")
    args = parser.parse_args()

    import os
    api_key = args.api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        parser.error("Cle API manquante. Utilisez --api-key ou la variable d'environnement GOOGLE_PLACES_API_KEY.")

    run(args.query, args.location, api_key, args.max_results, args.delay, args.output)


if __name__ == "__main__":
    main()
