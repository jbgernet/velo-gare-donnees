#!/usr/bin/env python3
"""Enregistre l'état des stations de vélos en gare (flux GBFS ouverts).

Services suivis : Vélo Fluo (Grand Est), Vélos BreizhGo (Bretagne) et une sélection de gares OV-fiets (Pays-Bas).
Chaque exécution ajoute une ligne par station dans data/<service>_AAAA-MM.csv.
Une fois par jour, la liste des stations (noms, coordonnées) est aussi sauvegardée.
Données sous licence ouverte (Licence Ouverte 2.0 pour Fluo, CC-BY-4.0 pour BreizhGo).
"""
import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Pour chaque service : adresse du flux, et liste des stations à garder (None = toutes).
OVFIETS_STATIONS = {
    # Équivalents des villes Fluo (sélection du 15 octobre 2026, gares présentes dans les stats NS)
    "ac002": "Abcoude", "bnk001": "Bunnik", "bhv002": "Bilthoven", "tl003": "Tiel",
    "wt003": "Weert", "pt001": "Putten", "hgv003": "Hoogeveen", "Hde001": "'t Harde",
    "swk002": "Steenwijk", "mp002": "Meppel", "zl004": "Zwolle", "apd001": "Apeldoorn",
    # Réserve : déjà suivie depuis le 13 octobre
    "cl003": "Culemborg",
}
SERVICES = {
    "velo_fluo": ("https://gbfs.partners.fifteen.eu/gbfs/velo-fluo/gbfs.json", None),
    "breizhgo": ("https://api.gbfs.v2.2.ecovelo.mobi/breizhgo/gbfs.json", None),
    "ov_fiets": ("http://gbfs.openov.nl/ovfiets/gbfs.json", set(OVFIETS_STATIONS)),
}
OUT = Path(__file__).parent / "data"
COLONNES = ["releve_utc", "station_id", "velos_disponibles", "places_disponibles",
            "location_ouverte", "retour_ouvert", "dernier_rapport_unix"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "etude-usages-velo-gare"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def feed_urls(discovery):
    """Retrouve les adresses des fichiers station_status / station_information (GBFS 2.x)."""
    data = discovery["data"]
    langue = data.get("fr") or data.get("en") or next(iter(data.values()))
    return {f["name"]: f["url"] for f in langue["feeds"]}


def enregistrer(service, url, garder, now):
    urls = feed_urls(fetch(url))
    stations = fetch(urls["station_status"])["data"]["stations"]
    if garder is not None:
        stations = [x for x in stations if x.get("station_id") in garder]
    chemin = OUT / f"{service}_{now[:7]}.csv"
    nouveau = not chemin.exists()
    with chemin.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nouveau:
            w.writerow(COLONNES)
        for s in stations:
            w.writerow([now, s.get("station_id"), s.get("num_bikes_available"),
                        s.get("num_docks_available"), s.get("is_renting"),
                        s.get("is_returning"), s.get("last_reported")])
    info = OUT / f"{service}_stations_{now[:10]}.json"
    if not info.exists() and "station_information" in urls:
        infos = fetch(urls["station_information"])
        if garder is not None:
            infos["data"]["stations"] = [x for x in infos["data"]["stations"]
                                         if x.get("station_id") in garder]
        info.write_text(json.dumps(infos, ensure_ascii=False), encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for service, (url, garder) in SERVICES.items():
        try:  # l'échec d'un service ne doit pas bloquer l'autre
            enregistrer(service, url, garder, now)
        except Exception as e:
            with (OUT / "erreurs.log").open("a", encoding="utf-8") as f:
                f.write(f"{now} {service} {e}\n")


if __name__ == "__main__":
    main()
