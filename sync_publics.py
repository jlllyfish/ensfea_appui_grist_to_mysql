import os

import requests
from dotenv import load_dotenv

load_dotenv()

GRIST_URL = os.getenv("GRIST_SERVER") + "/api"
DOC_ID = os.getenv("GRIST_DOC_1_ID")
headers = {
    "Authorization": f"Bearer {os.getenv('GRIST_API_KEY')}",
    "Content-Type": "application/json",
}

SOURCE_TABLE = "Catalogue_2026_2027"

# (colonne source, table cible, nom du champ valeur dans la table cible)
SYNC_CONFIG = [
    ("Public", "Publics_2026_2027", "Public"),
    ("Statut", "Statuts_2026_2027", "Statut"),
    ("Discipline", "Disciplines_2026_2027", "Discipline"),
]


def get_records(table):
    r = requests.get(
        f"{GRIST_URL}/docs/{DOC_ID}/tables/{table}/records", headers=headers
    )
    r.raise_for_status()
    return r.json()["records"]


def add_records(table, records):
    r = requests.post(
        f"{GRIST_URL}/docs/{DOC_ID}/tables/{table}/records",
        json={"records": records},
        headers=headers,
    )
    r.raise_for_status()
    print(f"{len(records)} lignes ajoutées dans {table}")


def delete_records(table, ids):
    r = requests.post(
        f"{GRIST_URL}/docs/{DOC_ID}/tables/{table}/data/delete",
        json=ids,
        headers=headers,
    )
    r.raise_for_status()
    print(f"{len(ids)} lignes supprimées dans {table}")


def extract_values(raw):
    """Gère valeurs Text (CSV) ou ChoiceList (["L", v1, v2, ...])."""
    if isinstance(raw, str):
        return [v.strip() for v in raw.split(",") if v.strip()]
    if isinstance(raw, list):
        if raw and raw[0] == "L":
            raw = raw[1:]
        return [v for v in raw if v]
    return []


def sync_split_column(rows, source_col, target_table, value_field):
    # État cible
    cible = set()
    for row in rows:
        id_stage = row["id"]
        for val in extract_values(row["fields"].get(source_col, "")):
            cible.add((id_stage, val))

    # État actuel
    existants = get_records(target_table)
    existant_index = {
        (rec["fields"].get("id_stage"), rec["fields"].get(value_field)): rec["id"]
        for rec in existants
    }
    existant_set = set(existant_index.keys())

    a_ajouter = cible - existant_set
    a_supprimer = existant_set - cible

    print(
        f"{target_table} — à ajouter : {len(a_ajouter)}, "
        f"à supprimer : {len(a_supprimer)}, inchangés : {len(cible & existant_set)}"
    )

    if a_supprimer:
        delete_records(target_table, [existant_index[key] for key in a_supprimer])

    if a_ajouter:
        records = [
            {"fields": {"id_stage": id_stage, value_field: val}}
            for id_stage, val in a_ajouter
        ]
        add_records(target_table, records)


# Lecture unique de la table source
rows = get_records(SOURCE_TABLE)

for source_col, target_table, value_field in SYNC_CONFIG:
    sync_split_column(rows, source_col, target_table, value_field)
