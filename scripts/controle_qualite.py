# -*- coding: utf-8 -*-
# =====================================================================
# Projet Data Steward, brique 1, outil de controle qualite de la donnee.
# Se branche sur la base PostGIS, controle chaque jeu de donnees,
# et produit un tableau de bord en HTML dans le dossier qualite.
#
# A lancer sur ta machine, la ou tournent PostgreSQL et Python.
# Avant de lancer, installe le connecteur une seule fois,
#   pip install psycopg2-binary
# Puis renseigne ton mot de passe ci dessous, et lance,
#   python controle_qualite.py
# =====================================================================

import os, sys, datetime

# --- 1. Connexion a la base. Mets ton mot de passe. ---
DB = dict(
    host="localhost",
    port=5432,
    dbname="Observatoire_foncier",
    user="postgres",
    password="A_REMPLIR",   # mets ton mot de passe pgAdmin ici
)

# --- 2. Les jeux de donnees a controler. ---
# geom, le nom de la colonne geometrie, ou None s'il n'y en a pas.
# cle, les colonnes qui doivent etre uniques, pour chercher les doublons.
# colonnes, les champs ou on verifie les valeurs manquantes.
TABLES = [
    dict(schema="referentiels", table="communes",
         label="Communes du Grand Avignon",
         geom="geom", cle=["code"], colonnes=["code", "nom"]),
    dict(schema="referentiels", table="parcelles_avignon",
         label="Parcelles cadastrales d'Avignon, PCI",
         geom="geom", cle=None, colonnes=[]),
    dict(schema="referentiels", table="batiments_avignon",
         label="Batiments d'Avignon, PCI",
         geom="geom", cle=None, colonnes=[]),
    dict(schema="foncier", table="conso_annuelle",
         label="Consommation fonciere annuelle",
         geom=None, cle=["idcom", "annee"],
         colonnes=["idcom", "nom", "annee", "naf_total_ha"]),
]

ACCENT = "#1F4E5F"

# =====================================================================
try:
    import psycopg2
except ImportError:
    print("Il manque le connecteur. Lance d'abord, pip install psycopg2-binary")
    sys.exit(1)


def un(cur, sql, params=None):
    """Renvoie la premiere valeur d'une requete, ou None."""
    cur.execute(sql, params or [])
    r = cur.fetchone()
    return r[0] if r else None


def exists(cur, schema, table):
    return un(cur, """SELECT count(*) FROM information_schema.tables
                      WHERE table_schema=%s AND table_name=%s""", [schema, table]) > 0


def colonnes_table(cur, schema, table):
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema=%s AND table_name=%s""", [schema, table])
    return [r[0] for r in cur.fetchall()]


def controler_table(cur, t):
    """Renvoie (liste de controles, score sur 100)."""
    sc, tb, lab = t["schema"], t["table"], t["label"]
    fq = '"%s"."%s"' % (sc, tb)
    checks = []

    if not exists(cur, sc, tb):
        checks.append(("Existence de la table", "erreur", "la table est absente de la base"))
        return checks, 0

    nb = un(cur, "SELECT count(*) FROM %s" % fq)
    checks.append(("Nombre de lignes", "info", "{:,}".format(nb).replace(",", " ")))

    cols = colonnes_table(cur, sc, tb)

    # --- controles geometriques ---
    g = t.get("geom")
    if g and g in cols:
        srid = un(cur, "SELECT ST_SRID(%s) FROM %s WHERE %s IS NOT NULL LIMIT 1" % (g, fq, g))
        if srid in (None, 0):
            checks.append(("Systeme de coordonnees", "alerte", "SRID absent ou inconnu, %s" % srid))
        else:
            checks.append(("Systeme de coordonnees", "ok", "SRID %s" % srid))

        nul = un(cur, "SELECT count(*) FROM %s WHERE %s IS NULL" % (fq, g))
        checks.append(("Geometries vides", "ok" if nul == 0 else "alerte",
                       "aucune" if nul == 0 else "%s geometries sans forme" % nul))

        inv = un(cur, "SELECT count(*) FROM %s WHERE %s IS NOT NULL AND NOT ST_IsValid(%s)" % (fq, g, g))
        checks.append(("Geometries valides", "ok" if inv == 0 else "erreur",
                       "toutes valides" if inv == 0 else "%s geometries invalides" % inv))

    # --- doublons sur la cle ---
    cle = t.get("cle")
    if cle and all(c in cols for c in cle):
        cols_cle = ", ".join('"%s"' % c for c in cle)
        dup = un(cur, "SELECT count(*) FROM (SELECT %s FROM %s GROUP BY %s HAVING count(*)>1) d"
                 % (cols_cle, fq, cols_cle))
        checks.append(("Doublons sur la cle (%s)" % ", ".join(cle), "ok" if dup == 0 else "alerte",
                       "aucun doublon" if dup == 0 else "%s cles en double" % dup))

    # --- valeurs manquantes ---
    manquantes = []
    for c in t.get("colonnes", []):
        if c in cols:
            n = un(cur, 'SELECT count(*) FROM %s WHERE "%s" IS NULL' % (fq, c))
            if n > 0:
                manquantes.append("%s, %s vides" % (c, n))
    if t.get("colonnes"):
        checks.append(("Valeurs manquantes", "ok" if not manquantes else "alerte",
                       "aucune" if not manquantes else " ; ".join(manquantes)))

    # --- integrite referentielle, conso vers communes ---
    if sc == "foncier" and tb == "conso_annuelle" and "idcom" in cols:
        if exists(cur, "referentiels", "communes"):
            orphelins = un(cur, """SELECT count(DISTINCT a.idcom) FROM foncier.conso_annuelle a
                                   WHERE NOT EXISTS (SELECT 1 FROM referentiels.communes c
                                   WHERE c.code = a.idcom)""")
            checks.append(("Integrite, codes communes connus", "ok" if orphelins == 0 else "alerte",
                           "tous les codes existent dans communes" if orphelins == 0
                           else "%s codes INSEE sans commune" % orphelins))

    # --- score, part des controles reussis parmi les controles notes ---
    notes = [s for _, s, _ in checks if s in ("ok", "alerte", "erreur")]
    if notes:
        poids = {"ok": 1.0, "alerte": 0.5, "erreur": 0.0}
        score = round(100 * sum(poids[s] for s in notes) / len(notes))
    else:
        score = 100
    return checks, score


def couleur(statut):
    return {"ok": "#1a7f5a", "alerte": "#c77f0a", "erreur": "#b5281e", "info": "#6b7b80"}[statut]


def pastille(statut):
    return {"ok": "Conforme", "alerte": "A verifier", "erreur": "Anomalie", "info": "Info"}[statut]


def html(resultats, score_global):
    d = datetime.date.today().strftime("%d/%m/%Y")
    parts = []
    parts.append("""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Qualite des donnees</title><style>
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1a1a1a;background:#f4f7f8;margin:0;padding:28px 18px 60px}
.wrap{max-width:980px;margin:0 auto}
h1{color:%s;font-size:24px;margin:0 0 2px}
.sub{color:#5c6b70;font-size:14px;margin:0 0 22px}
.global{display:flex;align-items:center;gap:16px;background:#fff;border:1px solid #dce4e7;border-radius:12px;padding:18px 22px;margin-bottom:22px}
.big{font-size:40px;font-weight:800;color:%s}
.card{background:#fff;border:1px solid #dce4e7;border-radius:12px;padding:16px 20px;margin-bottom:16px}
.ct{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #eef2f4;padding-bottom:8px;margin-bottom:8px}
.ct h2{font-size:17px;margin:0;color:#1a1a1a}
.sc{font-weight:700}
table{width:100%%;border-collapse:collapse;font-size:14px}
td{padding:7px 6px;border-bottom:1px solid #f0f3f5;vertical-align:top}
.tag{display:inline-block;min-width:78px;text-align:center;font-size:12px;font-weight:600;color:#fff;border-radius:20px;padding:2px 8px}
.foot{color:#7a8a8f;font-size:12px;margin-top:24px}
</style></head><body><div class="wrap">""" % (ACCENT, ACCENT))
    parts.append('<h1>Tableau de bord de la qualite des donnees</h1>')
    parts.append('<p class="sub">Base PostGIS Observatoire_foncier. Controle automatique de la qualite. Reproductible a volonte.</p>')
    parts.append('<div class="global"><div class="big">%s sur 100</div>'
                 '<div>Score global de qualite, moyenne des jeux de donnees controles.</div></div>' % score_global)

    for lab, checks, score in resultats:
        parts.append('<div class="card"><div class="ct"><h2>%s</h2>'
                     '<span class="sc" style="color:%s">%s sur 100</span></div><table>'
                     % (lab, ACCENT, score))
        for nom, statut, detail in checks:
            parts.append('<tr><td style="width:34%%">%s</td>'
                         '<td style="width:120px"><span class="tag" style="background:%s">%s</span></td>'
                         '<td>%s</td></tr>' % (nom, couleur(statut), pastille(statut), detail))
        parts.append('</table></div>')

    parts.append('<p class="foot">Outil de controle qualite. Realise par Victorine Djetcheu Toko. '
                 'Python et PostGIS.</p></div></body></html>')
    return "".join(parts)


def main():
    if DB["password"] == "A_REMPLIR":
        print("Ouvre le fichier et mets ton mot de passe dans DB, puis relance.")
        sys.exit(1)
    try:
        conn = psycopg2.connect(**DB)
    except Exception as e:
        print("Connexion impossible. Verifie le mot de passe et que PostgreSQL tourne.")
        print(e); sys.exit(1)

    cur = conn.cursor()
    resultats, scores = [], []
    for t in TABLES:
        try:
            checks, score = controler_table(cur, t)
        except Exception as e:
            checks, score = [("Controle", "erreur", "echec, %s" % e)], 0
            conn.rollback()
        resultats.append((t["label"], checks, score))
        scores.append(score)
        print("  %-42s %3s/100" % (t["label"][:42], score))
    cur.close(); conn.close()

    score_global = round(sum(scores) / len(scores)) if scores else 0
    base = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(base, "..", "qualite", "rapport_qualite.html")
    out = os.path.abspath(out)
    try:
        open(out, "w", encoding="utf-8").write(html(resultats, score_global))
    except Exception:
        out = os.path.join(base, "rapport_qualite.html")
        open(out, "w", encoding="utf-8").write(html(resultats, score_global))
    print("\nScore global, %s sur 100." % score_global)
    print("Tableau de bord ecrit ici, %s" % out)


if __name__ == "__main__":
    main()
