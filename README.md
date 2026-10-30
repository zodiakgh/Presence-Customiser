# Presence Customiser

Une **Rich Presence Discord entièrement personnalisable** : profils, pages qui défilent, règles automatiques,
variables en direct, plugins Python, confidentialité, configuration 100 % en JSON.

[**⬇ Download Presence Customiser**](https://github.com/zodiakgh/Presence-Customiser/releases/latest) (Windows 10/11)

## Démarrage rapide

1. Télécharge `PresenceCustomiser.exe` dans les [releases](https://github.com/zodiakgh/Presence-Customiser/releases/latest) et lance-le.
2. Va sur <https://discord.com/developers/applications>, crée une application et copie son **Application ID**.
   Son **nom** est celui qui s'affichera sur ton profil (« Joue à *nom* »).
3. Colle l'ID dans **Réglages → Client ID**, enregistre.
4. Clique sur **Activer la présence**. Discord doit être ouvert sur ton PC (l'application, pas le navigateur).

Pour afficher des images : sur le portail développeur, **Rich Presence → Art Assets**, uploade tes images, puis
utilise leur nom (ou une URL `https://`) dans « Grande image » / « Petite image ».

## Lancer depuis le code

```bash
pip install -r requirements.txt
python main.py              # interface
python main.py --minimized  # démarre dans la barre système
python main.py --headless   # sans interface, dans le terminal
python main.py --once       # affiche la présence calculée, sans rien envoyer
```

## Ce que tu peux personnaliser

**Profils et frames.** Un profil = un type d'activité (joue / écoute / regarde / participe), un chrono
(aucun, depuis le profil, depuis le lancement, depuis le démarrage du PC, compte à rebours), et une liste de
**frames** qui défilent (rotation ≥ 15 s, ordre aléatoire possible). Chaque frame a deux lignes de texte, deux images
avec texte au survol, un groupe (`1/4`), jusqu'à 2 boutons et une condition d'affichage (`show_if`).
Un profil peut avoir son propre Client ID, donc son propre nom d'application affiché.

**Templates.** `{variable}`, `{variable?défaut}`, `{variable?défaut|filtre:arg|filtre2}`

| Filtre | Effet |
|---|---|
| `upper` `lower` `title` `cap` | casse |
| `trunc:N` | coupe à N caractères avec « … » |
| `round:N` `pad:N` | arrondi, zéros devant |
| `bar:N` | barre de progression `▰▰▰▱▱` pour un pourcentage |
| `noext` `clean` | enlève l'extension / les puces `●` |
| `prefix:x` `suffix:x` | ajoute du texte si la valeur n'est pas vide |
| `replace:a=b` `default:x` `strip` | remplacement, valeur par défaut, espaces |

**Variables intégrées.** `time` `date` `hour` `minute` `weekday` `weekday_num` `day_part` `cpu` `ram` `battery`
`uptime` `session` `process` `window` `app` `file` `project` `idle` `idle_min` `spotify` `os` `profile`
`profile_time`. `file` et `project` sont extraits des titres VS Code, Cursor, PyCharm, etc. Tu peux en ajouter
(onglet **Variables**, `nom = valeur`, avec chaînage possible) et via des **plugins**.

**Règles automatiques.** Le profil change tout seul. Une règle = un profil + une priorité + des conditions
(toutes celles remplies doivent correspondre) : `process`, `window_contains`, `window_regex`, `time_between`
(`22:00-06:00`), `weekdays`, `cpu_above`, `ram_above`, `battery_below`, `idle_over` et `expr` (condition libre :
`cpu > 80`, `app == Chrome and hour >= 22`, `window contains youtube`, `spotify`, `!project`).

**Plugins.** Un fichier `.py` dans le dossier `plugins` (bouton « Ouvrir le dossier ») qui définit
`get_variables(vars)` et retourne un `dict`. Un exemple est créé au premier lancement. Les plugins sont du code
Python exécuté tel quel : n'installe que ceux que tu as écrits ou relus.

**Confidentialité.** Si un processus (`KeePass.exe`…) ou un mot (`banque`, `password`…) apparaît dans la fenêtre
active, l'appli bascule sur le profil de confidentialité et masque `process`, `window`, `app`, `file`, `project`
et `spotify`. À adapter dans **Réglages**.

**JSON avancé.** L'onglet du même nom édite toute la configuration (import / export pour la partager).
Elle est stockée dans `%APPDATA%\Presence Customiser\config.json`.

## Limites de Discord

- L'application Discord de bureau doit tourner sur le même PC.
- Les boutons ne sont pas visibles sur ton propre profil, seulement par les autres.
- Discord limite la fréquence des mises à jour : minimum 15 s entre deux envois.
- Texte : 128 caractères max par ligne, 2 minimum (géré automatiquement).

## Publier une version

Le dépôt est <https://github.com/zodiakgh/Presence-Customiser>.

1. Pousse le code sur `main`.
2. Publie une version : `git tag v1.0.0 && git push origin v1.0.0`. L'action `.github/workflows/release.yml`
   construit `PresenceCustomiser.exe` et l'ajoute à la page **Releases** : c'est ce que télécharge le bouton
   « Download Presence Customiser ».
3. Page web (optionnel) : **Settings → Pages → Branch `main`, dossier `/docs`**. Elle contient le même bouton,
   qui pointe vers la dernière release.

Construire l'exe à la main : `build_exe.bat` (sort `dist\PresenceCustomiser.exe`).
L'exe n'est pas signé : Windows SmartScreen peut afficher un avertissement au premier lancement
(« Informations complémentaires → Exécuter quand même »).

## Tests

```bash
python tests/test_engine.py       # moteur : templates, règles, confidentialité, envoi, validation
python tests/test_ui_smoke.py     # logique de l'interface avec un faux toolkit
```

*Projet communautaire, non affilié à Discord Inc.*
