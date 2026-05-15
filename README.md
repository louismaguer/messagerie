# Note explicative du projet de messagerie simple – Louis Maguer

## 0. Lancement de la messagerie

Pour lancer la messagerie, exécuter la commande suivante dans le terminal (dans le dossier principal du projet) :

```bash
fastapi dev main.py
```

Puis ouvrir le fichier `index.html` dans un navigateur pour accéder à l'interface utilisateur.

## 1. Choix de modélisation

La modélisation de ce projet repose sur **FastAPI**, **Pydantic**,  **SQLModel** et **SQLite**.
*   **Séparation des modèles et des schémas** : Nous avons séparé les modèles de base de données (SQLModel) des schémas de validation (Pydantic). Cela permet d'éviter d'exposer inutilement tous les champs de la base.
*   **Entité Utilisateur (`User`)** : Elle contient un identifiant unique (`id`), un nom d'utilisateur (`name` unique pour éviter les doublons) et un `email`.
*   **Entité Message (`Message`)** : Elle est liée aux utilisateurs par deux clés étrangères ; `sender_id` (l'expéditeur) et `receiver_id` (le destinataire). Elle intègre également un `id` unique, un `subject`, un `body`, une `date` d'envoi générée automatiquement, et un booléen `is_read` pour suivre le statut de lecture, avec une valeur par défaut à `False`.

## 2. Routes disponibles

Les routes disponibles sont les suivantes :

**Gestion des utilisateurs :**
*   `POST /users/` : Créer un nouvel utilisateur.
*   `GET /users/` : Lister tous les utilisateurs.
*   `GET /users/{user_id}` : Récupérer les détails d'un utilisateur spécifique.
*   `GET /users/{user_id}/unread_count` : Récupérer le nombre de messages non lus d'un utilisateur.

**Gestion des messages :**
*   `POST /messages/` : Envoyer un nouveau message.
*   `GET /messages/` : Lister tous les messages, ou seulement une certaine tranche.
*   `GET /users/{user_id}/inbox` : Consulter la boîte de réception d'un utilisateur. Cette route supporte des paramètres de requête pour le filtrage : `unread_only`, `search`, `limit` et `offset`.
*   `GET /users/{user_id}/sent` : Consulter les messages envoyés par un utilisateur.
*   `GET /messages/{message_id}` : Consulter le détail d'un message donné.
*   `PATCH /messages/{message_id}/read` : Marquer un message comme lu.
*   `DELETE /messages/{message_id}` : Supprimer un message.

**Temps réel :**
*   `WS /ws/users/{user_id}` : Endpoint WebSocket permettant de notifier un utilisateur en direct de la réception d'un nouveau message.

## 3. Limites de la solution HTTP et évolution

Le protocole HTTP (requête/réponse) est adapté pour les actions ponctuelles comme s'inscrire, envoyer ou lire un message.

Cependant, HTTP est unidirectionnel : le serveur ne peut pas notifier le client spontanément. Pour vérifier les nouveaux messages, le client doit interroger le serveur en boucle, ce qui empêche un véritable temps réel.

L'utilisation des **WebSockets** permet de pallier cela. Cette technologie maintient une connexion bidirectionnelle ouverte en permanence. Dès réception d'un message, le serveur peut "pousser" instantanément la notification au destinataire, sans requêtes HTTP répétitives.