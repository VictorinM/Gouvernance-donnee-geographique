# Gouvernance de la donnée géographique

Chaîne complète d'un Data Steward, du contrôle qualité à l'open data.

## Le projet

Ce projet applique à des données géographiques la chaîne complète d'un Data Steward,
produire et fiabiliser, documenter et cataloguer, diffuser dans les règles.
Il s'appuie sur une base PostGIS avec les communes, le cadastre PCI et la consommation
d'espaces du Grand Avignon.

## Les trois briques

### 1. Produire et fiabiliser, l'outil qualité
Un outil en Python branché sur la base PostGIS contrôle chaque jeu de données,
les géométries, le système de coordonnées, les doublons, les valeurs manquantes,
et produit un tableau de bord. Il a repéré une parcelle invalide sur 32 840,
corrigée avec ST_MakeValid, puis la colonne a été remise en multi polygone.
Score final, 100 sur 100.

Fichier, `scripts/controle_qualite.py`.

### 2. Documenter et cataloguer, les métadonnées
Quatre jeux de données décrits dans un catalogue, avec pour chacun une fiche de
métadonnées normée ISO 19115 et 19139, conforme INSPIRE, et un dictionnaire de données.
Les fiches sont générées par un script, donc reproductibles.

Fichiers, `catalogue/catalogue.html`, `catalogue/metadonnees/`, `scripts/generer_catalogue.py`.

### 3. Diffuser dans les règles, l'open data
Un jeu publié en open data avec sa Licence Ouverte d'Etalab et sa fiche de diffusion,
prêt pour data.gouv.fr. Et une note sur le cadre juridique de la donnée, la directive
INSPIRE, les licences ouvertes, le RGPD et la propriété intellectuelle.

Fichiers, `diffusion/`.

## Compétences
PostgreSQL et PostGIS, SQL, Python, contrôle qualité des données, catalogage,
métadonnées ISO 19115 et 19139, INSPIRE, diffusion open data, cadre juridique de la donnée,
gouvernance de la donnée.

## Lancer l'outil qualité
1. Installer le connecteur, `pip install psycopg2-binary`.
2. Ouvrir `scripts/controle_qualite.py` et renseigner le mot de passe de la base.
3. Lancer, `python controle_qualite.py`. Le tableau de bord est écrit dans `qualite/`.

## Auteur
Victorine Maximilienne Djetcheu Toko.
Portfolio, https://portfolio-victorine-djetcheu.netlify.app
