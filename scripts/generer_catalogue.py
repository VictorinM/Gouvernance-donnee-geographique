# -*- coding: utf-8 -*-
# =====================================================================
# Projet Data Steward, brique 2, catalogue et metadonnees.
# Produit, pour chaque jeu de donnees,
#   - une fiche de metadonnees normee ISO 19115 et 19139, conforme INSPIRE, en XML,
#   - une entree dans un catalogue HTML, avec son dictionnaire de donnees.
# Les emprises sont calculees a partir des fichiers sources.
# =====================================================================
import json, gzip, os, html, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "..", "..", "Observatoire foncier ZAN", "data")
OUT = os.path.join(BASE, "..", "catalogue")
os.makedirs(os.path.join(OUT, "metadonnees"), exist_ok=True)
ACCENT = "#1F4E5F"
AUTEUR = "Victorine Maximilienne Djetcheu Toko"
MAIL = "tokomaximilienne@gmail.com"
AUJ = datetime.date.today().isoformat()


def bbox_geojson(path, gz=False):
    op = gzip.open if gz else open
    with op(path, "rt", encoding="utf-8", errors="ignore") as f:
        d = json.load(f)
    W = S = 1e9; E = N = -1e9
    def walk(c):
        nonlocal W, S, E, N
        if isinstance(c[0], (int, float)):
            x, y = c[0], c[1]
            W = min(W, x); E = max(E, x); S = min(S, y); N = max(N, y)
        else:
            for x in c: walk(x)
    for ft in d["features"]:
        g = ft.get("geometry")
        if g: walk(g["coordinates"])
    return round(W, 5), round(E, 5), round(S, 5), round(N, 5), len(d["features"])


# emprises reelles, en WGS84, calculees sur les sources
wC, eC, sC, nC, nbC = bbox_geojson(os.path.join(SRC, "communes_grand_avignon.geojson"))
wP, eP, sP, nP, nbP = bbox_geojson(os.path.join(SRC, "cadastre-84007-parcelles.json.gz"), gz=True)
wB, eB, sB, nB, nbB = bbox_geojson(os.path.join(SRC, "cadastre-84007-batiments.json.gz"), gz=True)

# =====================================================================
# Definition des metadonnees de chaque jeu de donnees
# =====================================================================
JEUX = [
 dict(
   id="communes-grand-avignon",
   table="referentiels.communes",
   titre="Communes du Grand Avignon",
   resume="Limites des 16 communes de la Communaute d'agglomeration du Grand Avignon. "
          "Ce jeu sert de referentiel administratif a l'observatoire foncier, pour rattacher "
          "et agreger les donnees a la commune.",
   theme="Unites administratives", categorie="boundaries",
   genealogie="Donnees issues du referentiel administratif de l'IGN et de l'API Geo, "
              "geo.api.gouv.fr. Reprojetees en Lambert 93 lors de l'integration dans la base PostGIS.",
   frequence="annuelle", debut="2024", fin="2024",
   bbox=(wC, eC, sC, nC), nb=nbC, geom="Polygone",
   champs=[("code","texte","Code INSEE de la commune, 5 caracteres"),
           ("nom","texte","Nom de la commune"),
           ("population","entier","Population municipale"),
           ("geom","geometrie","Contour de la commune, polygone, Lambert 93")]),
 dict(
   id="parcelles-avignon-pci",
   table="referentiels.parcelles_avignon",
   titre="Parcelles cadastrales d'Avignon, Plan Cadastral Informatise",
   resume="Parcelles cadastrales de la commune d'Avignon, issues du Plan Cadastral Informatise "
          "vecteur. Utilisees pour reperer le foncier mobilisable en croisant le parcellaire et le bati.",
   theme="Parcelles cadastrales", categorie="planningCadastre",
   genealogie="PCI vecteur, diffuse par Etalab a partir des donnees de la DGFiP. "
              "Integre en Lambert 93 et fiabilise, geometries rendues valides avec ST_MakeValid.",
   frequence="semestrielle", debut="2010", fin="2019",
   bbox=(wP, eP, sP, nP), nb=nbP, geom="Multipolygone",
   champs=[("id","texte","Identifiant cadastral de la parcelle"),
           ("commune","texte","Code INSEE de la commune"),
           ("prefixe","texte","Prefixe de section"),
           ("section","texte","Section cadastrale"),
           ("numero","texte","Numero de la parcelle"),
           ("contenance","entier","Surface cadastrale en metres carres"),
           ("arpente","booleen","Parcelle arpentee ou non"),
           ("created","date","Date de creation de la donnee"),
           ("updated","date","Date de derniere mise a jour"),
           ("geom","geometrie","Contour de la parcelle, multipolygone, Lambert 93")]),
 dict(
   id="batiments-avignon-pci",
   table="referentiels.batiments_avignon",
   titre="Batiments d'Avignon, Plan Cadastral Informatise",
   resume="Emprises des batiments de la commune d'Avignon, issues du Plan Cadastral Informatise "
          "vecteur. Croisees avec les parcelles pour reperer les dents creuses.",
   theme="Batiments", categorie="structure",
   genealogie="PCI vecteur, diffuse par Etalab a partir des donnees de la DGFiP. "
              "Integre en Lambert 93 dans la base PostGIS.",
   frequence="semestrielle", debut="2008", fin="2018",
   bbox=(wB, eB, sB, nB), nb=nbB, geom="Multipolygone",
   champs=[("type","texte","Type de batiment, code PCI, par exemple 01 pour le dur"),
           ("nom","texte","Nom du batiment, souvent vide"),
           ("commune","texte","Code INSEE de la commune"),
           ("created","date","Date de creation de la donnee"),
           ("updated","date","Date de derniere mise a jour"),
           ("geom","geometrie","Emprise du batiment, multipolygone, Lambert 93")]),
 dict(
   id="consommation-fonciere-grand-avignon",
   table="foncier.conso_annuelle",
   titre="Consommation d'espaces du Grand Avignon, 2012 a 2025",
   resume="Consommation annuelle d'espaces naturels, agricoles et forestiers des 16 communes "
          "du Grand Avignon, par destination. Donnees non geographiques, rattachees aux communes "
          "par le code INSEE.",
   theme="Usage des sols", categorie="planningCadastre",
   genealogie="Portail national de l'artificialisation des sols, produit par le Cerema. "
              "Filtre sur les 16 communes et remis en forme par annee.",
   frequence="annuelle", debut="2012", fin="2025",
   bbox=(wC, eC, sC, nC), nb=224, geom="Aucune, table rattachee par code INSEE",
   champs=[("idcom","texte","Code INSEE de la commune"),
           ("nom","texte","Nom de la commune"),
           ("departement","texte","Nom du departement"),
           ("annee","entier","Annee de la mesure"),
           ("naf_total_ha","decimal","Espaces consommes dans l'annee, en hectares"),
           ("habitat_ha","decimal","Part destinee a l'habitat, en hectares"),
           ("activite_ha","decimal","Part destinee a l'activite, en hectares"),
           ("mixte_ha","decimal","Part mixte, en hectares"),
           ("inconnu_ha","decimal","Part de destination inconnue, en hectares"),
           ("ferroviaire_ha","decimal","Part ferroviaire, en hectares"),
           ("routier_ha","decimal","Part routiere, en hectares")]),
]

LICENCE = "Licence Ouverte 2.0, Etalab"

# =====================================================================
# Fiche de metadonnees ISO 19139
# =====================================================================
def fiche_xml(j):
    w, e, s, n = j["bbox"]
    x = f'''<?xml version="1.0" encoding="UTF-8"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco"
                 xmlns:gml="http://www.opengis.net/gml">
  <gmd:fileIdentifier><gco:CharacterString>{j["id"]}</gco:CharacterString></gmd:fileIdentifier>
  <gmd:language><gco:CharacterString>fre</gco:CharacterString></gmd:language>
  <gmd:characterSet><gmd:MD_CharacterSetCode codeListValue="utf8"
     codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#MD_CharacterSetCode"/></gmd:characterSet>
  <gmd:hierarchyLevel><gmd:MD_ScopeCode codeListValue="dataset"
     codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#MD_ScopeCode"/></gmd:hierarchyLevel>
  <gmd:contact>
    <gmd:CI_ResponsibleParty>
      <gmd:individualName><gco:CharacterString>{AUTEUR}</gco:CharacterString></gmd:individualName>
      <gmd:contactInfo><gmd:CI_Contact><gmd:address><gmd:CI_Address>
        <gmd:electronicMailAddress><gco:CharacterString>{MAIL}</gco:CharacterString></gmd:electronicMailAddress>
      </gmd:CI_Address></gmd:address></gmd:CI_Contact></gmd:contactInfo>
      <gmd:role><gmd:CI_RoleCode codeListValue="pointOfContact"
         codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#CI_RoleCode"/></gmd:role>
    </gmd:CI_ResponsibleParty>
  </gmd:contact>
  <gmd:dateStamp><gco:Date>{AUJ}</gco:Date></gmd:dateStamp>
  <gmd:metadataStandardName><gco:CharacterString>ISO 19115:2003/19139</gco:CharacterString></gmd:metadataStandardName>
  <gmd:metadataStandardVersion><gco:CharacterString>1.0</gco:CharacterString></gmd:metadataStandardVersion>
  <gmd:referenceSystemInfo><gmd:MD_ReferenceSystem><gmd:referenceSystemIdentifier>
    <gmd:RS_Identifier>
      <gmd:code><gco:CharacterString>2154</gco:CharacterString></gmd:code>
      <gmd:codeSpace><gco:CharacterString>EPSG</gco:CharacterString></gmd:codeSpace>
    </gmd:RS_Identifier>
  </gmd:referenceSystemIdentifier></gmd:MD_ReferenceSystem></gmd:referenceSystemInfo>
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation><gmd:CI_Citation>
        <gmd:title><gco:CharacterString>{html.escape(j["titre"])}</gco:CharacterString></gmd:title>
        <gmd:date><gmd:CI_Date>
          <gmd:date><gco:Date>{AUJ}</gco:Date></gmd:date>
          <gmd:dateType><gmd:CI_DateTypeCode codeListValue="publication"
             codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#CI_DateTypeCode"/></gmd:dateType>
        </gmd:CI_Date></gmd:date>
      </gmd:CI_Citation></gmd:citation>
      <gmd:abstract><gco:CharacterString>{html.escape(j["resume"])}</gco:CharacterString></gmd:abstract>
      <gmd:pointOfContact><gmd:CI_ResponsibleParty>
        <gmd:individualName><gco:CharacterString>{AUTEUR}</gco:CharacterString></gmd:individualName>
        <gmd:role><gmd:CI_RoleCode codeListValue="owner"
           codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#CI_RoleCode"/></gmd:role>
      </gmd:CI_ResponsibleParty></gmd:pointOfContact>
      <gmd:descriptiveKeywords><gmd:MD_Keywords>
        <gmd:keyword><gco:CharacterString>{html.escape(j["theme"])}</gco:CharacterString></gmd:keyword>
        <gmd:type><gmd:MD_KeywordTypeCode codeListValue="theme"
           codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#MD_KeywordTypeCode"/></gmd:type>
        <gmd:thesaurusName><gmd:CI_Citation>
          <gmd:title><gco:CharacterString>GEMET - INSPIRE themes, version 1.0</gco:CharacterString></gmd:title>
        </gmd:CI_Citation></gmd:thesaurusName>
      </gmd:MD_Keywords></gmd:descriptiveKeywords>
      <gmd:resourceConstraints><gmd:MD_LegalConstraints>
        <gmd:useLimitation><gco:CharacterString>Reutilisation libre sous {LICENCE}.</gco:CharacterString></gmd:useLimitation>
        <gmd:accessConstraints><gmd:MD_RestrictionCode codeListValue="otherRestrictions"
           codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#MD_RestrictionCode"/></gmd:accessConstraints>
        <gmd:otherConstraints><gco:CharacterString>Pas de restriction d'acces public, {LICENCE}.</gco:CharacterString></gmd:otherConstraints>
      </gmd:MD_LegalConstraints></gmd:resourceConstraints>
      <gmd:language><gco:CharacterString>fre</gco:CharacterString></gmd:language>
      <gmd:topicCategory><gmd:MD_TopicCategoryCode>{j["categorie"]}</gmd:MD_TopicCategoryCode></gmd:topicCategory>
      <gmd:extent><gmd:EX_Extent>
        <gmd:geographicElement><gmd:EX_GeographicBoundingBox>
          <gmd:westBoundLongitude><gco:Decimal>{w}</gco:Decimal></gmd:westBoundLongitude>
          <gmd:eastBoundLongitude><gco:Decimal>{e}</gco:Decimal></gmd:eastBoundLongitude>
          <gmd:southBoundLatitude><gco:Decimal>{s}</gco:Decimal></gmd:southBoundLatitude>
          <gmd:northBoundLatitude><gco:Decimal>{n}</gco:Decimal></gmd:northBoundLatitude>
        </gmd:EX_GeographicBoundingBox></gmd:geographicElement>
        <gmd:temporalElement><gmd:EX_TemporalExtent><gmd:extent>
          <gml:TimePeriod gml:id="T-{j["id"]}">
            <gml:beginPosition>{j["debut"]}</gml:beginPosition>
            <gml:endPosition>{j["fin"]}</gml:endPosition>
          </gml:TimePeriod>
        </gmd:extent></gmd:EX_TemporalExtent></gmd:temporalElement>
      </gmd:EX_Extent></gmd:extent>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
  <gmd:dataQualityInfo><gmd:DQ_DataQuality>
    <gmd:scope><gmd:DQ_Scope><gmd:level><gmd:MD_ScopeCode codeListValue="dataset"
       codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#MD_ScopeCode"/></gmd:level></gmd:DQ_Scope></gmd:scope>
    <gmd:lineage><gmd:LI_Lineage><gmd:statement>
      <gco:CharacterString>{html.escape(j["genealogie"])}</gco:CharacterString>
    </gmd:statement></gmd:LI_Lineage></gmd:lineage>
  </gmd:DQ_DataQuality></gmd:dataQualityInfo>
</gmd:MD_Metadata>
'''
    return x


# =====================================================================
# Catalogue HTML
# =====================================================================
def catalogue_html():
    p = []
    p.append(f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Catalogue de donnees</title><style>
body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1a1a1a;background:#f4f7f8;margin:0;padding:28px 18px 60px}}
.wrap{{max-width:1000px;margin:0 auto}}
h1{{color:{ACCENT};font-size:25px;margin:0 0 2px}}
.sub{{color:#5c6b70;font-size:14px;margin:0 0 24px}}
.card{{background:#fff;border:1px solid #dce4e7;border-radius:12px;padding:20px 24px;margin-bottom:18px}}
.card h2{{font-size:19px;color:{ACCENT};margin:0 0 4px}}
.tab{{font-size:13px;color:#7a8a8f;margin:0 0 10px}}
.meta{{width:100%;border-collapse:collapse;font-size:14px;margin:10px 0 14px}}
.meta td{{padding:5px 8px;border-bottom:1px solid #f0f3f5;vertical-align:top}}
.meta td.k{{color:#5c6b70;width:200px}}
.badge{{display:inline-block;background:#eef4f5;color:{ACCENT};border:1px solid #d4e2e5;border-radius:20px;font-size:12px;padding:2px 10px;margin-right:6px}}
h3{{font-size:14px;margin:12px 0 6px;color:#1a1a1a}}
.dic{{width:100%;border-collapse:collapse;font-size:13px}}
.dic th{{text-align:left;background:#f3f6f7;color:{ACCENT};padding:6px 8px;border-bottom:1px solid #dce4e7}}
.dic td{{padding:5px 8px;border-bottom:1px solid #f0f3f5;vertical-align:top}}
.mono{{font-family:Consolas,Menlo,monospace;color:#1a3a44}}
a{{color:{ACCENT}}}
.foot{{color:#7a8a8f;font-size:12px;margin-top:22px}}
</style></head><body><div class="wrap">''')
    p.append('<h1>Catalogue de donnees, observatoire foncier du Grand Avignon</h1>')
    p.append(f'<p class="sub">Quatre jeux de donnees documentes, avec fiche de metadonnees normee ISO 19115 et 19139, '
             f'conforme INSPIRE, et dictionnaire de donnees. Catalogue tenu par {AUTEUR}.</p>')
    for j in JEUX:
        w, e, s, n = j["bbox"]
        p.append('<div class="card">')
        p.append(f'<h2>{html.escape(j["titre"])}</h2>')
        p.append(f'<p class="tab"><span class="mono">{j["table"]}</span></p>')
        p.append('<table class="meta">')
        def row(k, v): p.append(f'<tr><td class="k">{k}</td><td>{v}</td></tr>')
        row("Resume", html.escape(j["resume"]))
        row("Theme INSPIRE", f'<span class="badge">{html.escape(j["theme"])}</span>')
        row("Nombre d'objets", "{:,}".format(j["nb"]).replace(",", " "))
        row("Geometrie", j["geom"])
        row("Systeme de coordonnees", "RGF93 Lambert 93, EPSG 2154")
        row("Emprise, en degres", f"ouest {w}, est {e}, sud {s}, nord {n}")
        row("Periode", f'{j["debut"]} a {j["fin"]}')
        row("Frequence de mise a jour", j["frequence"])
        row("Genealogie", html.escape(j["genealogie"]))
        row("Licence", LICENCE)
        row("Contact", f'{AUTEUR}, {MAIL}')
        row("Fiche de metadonnees", f'<a href="metadonnees/{j["id"]}.xml">{j["id"]}.xml</a>, ISO 19139')
        p.append('</table>')
        p.append('<h3>Dictionnaire de donnees</h3>')
        p.append('<table class="dic"><tr><th>Champ</th><th>Type</th><th>Description</th></tr>')
        for c, t, d in j["champs"]:
            p.append(f'<tr><td class="mono">{c}</td><td>{t}</td><td>{html.escape(d)}</td></tr>')
        p.append('</table></div>')
    p.append(f'<p class="foot">Catalogue de donnees. Realise par {AUTEUR}. '
             'Metadonnees ISO 19115 et 19139, themes INSPIRE, Licence Ouverte Etalab.</p></div></body></html>')
    return "".join(p)


# ---- ecriture ----
for j in JEUX:
    open(os.path.join(OUT, "metadonnees", j["id"] + ".xml"), "w", encoding="utf-8").write(fiche_xml(j))
open(os.path.join(OUT, "catalogue.html"), "w", encoding="utf-8").write(catalogue_html())
print("ok, fiches XML et catalogue ecrits dans", OUT)
for j in JEUX:
    print("  -", j["id"], "nb", j["nb"], "bbox", j["bbox"])
