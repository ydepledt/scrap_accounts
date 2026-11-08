SCRAP ACCOUNTS — WINDOWS

Ouvre ScrapAccounts.exe par un double-clic.

1. Choisis Instagram, X ou YouTube.
2. Pour Instagram, colle directement les liens de Reels/publications et clique sur
   « Ajouter les liens à ma collection » OU ouvre le navigateur et collecte des liens
   en te connectant, en naviguant et en cliquant sur « Commencer ».
3. Choisis combien de commentaires demander par publication (0 à 1 000).
4. Clique sur « Télécharger » pour récupérer les médias et les métadonnées.
5. Retrouve analysis_ready.jsonl (une ligne par URL) et analysis_ready.csv
   dans le dossier Instagram/downloads ; les anciens rapports restent présents.

Attention : les liens de profils Instagram ne sont pas directement importables.
Les commentaires peuvent être partiels ou indisponibles suivant Instagram.
Le code ne fait pas d'appel à une API d'intelligence artificielle.

L'option métadonnées récupère les informations sans télécharger les médias.
Les liens sont cumulés entre les sessions. Le maximum s'applique à chaque
récupération, tandis que Télécharger traite le fichier de liens cumulé.
Les commentaires sont désactivés pour garder les téléchargements simples.

« Ouvrir mes fichiers » ouvre les résultats depuis l'Explorateur Windows.
Emplacement WSL : /home/yannd/.local/share/scrap-accounts

Cette application utilise Ubuntu WSL, WSLg et l'installation existante :
/home/yannd/scrap_accounts/.venv
Elle n'est donc pas autonome sur un autre ordinateur.
Chaque réseau possède son propre profil de navigateur persistant.
Les cookies de téléchargement sont exportés dans un fichier temporaire
privé, supprimé à la fin de l'opération normale.

Le code source de l'interface est fourni dans app.py.
Les sites peuvent demander une reconnexion ou changer leur interface.
