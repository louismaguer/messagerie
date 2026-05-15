const API_BASE = "http://localhost:8000";
let usersMap = {};

// Créer un nouvel utilisateur
async function createUser() {
    const name = document.getElementById("new-username").value;
    const email = document.getElementById("new-email").value;
    const status = document.getElementById("create-user-status");

    try {
        const response = await fetch(`${API_BASE}/users/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name, email: email })
        });

        if (response.ok) {
            const data = await response.json();
            status.innerText = "Utilisateur créé avec succès";
            status.style.color = "green";
            document.getElementById("new-username").value = "";
            document.getElementById("new-email").value = "";
            await listUsers();
        } else {
            const data = await response.json();
            status.innerText = "Erreur : " + data.detail;
            status.style.color = "red";
        }
    } catch {
        status.innerText = "Erreur de connexion";
        status.style.color = "red";
    }
}

// Lister tous les utilisateurs (pour les menus déroulants)
async function listUsers() {
    const response = await fetch(`${API_BASE}/users/`);
    const users = await response.json();
    const currentUserSelect = document.getElementById("current-user");
    const receiverSelect = document.getElementById("receiver-id");

    let optionsHtml = '';
    users.forEach(user => {
        usersMap[user.id] = user.name;
        optionsHtml += `<option value="${user.id}">${user.name}</option>`;
    });

    currentUserSelect.innerHTML = optionsHtml;
    receiverSelect.innerHTML = optionsHtml;

    const savedUserId = localStorage.getItem("currentUserId");
    if (savedUserId && usersMap[savedUserId]) {
        currentUserSelect.value = savedUserId;
    }
}

// Créer un nouveau message : formatage HTML
function createInboxMessageHTML(msg) {
    return `
        <div class="message ${msg.is_read ? '' : 'unread'}" id="message-${msg.id}">
            <div class="message-meta">
                <span>De : ${usersMap[msg.sender_id]} | ${new Date(msg.date).toLocaleString()}</span>
                <div>${!msg.is_read ? `<button style="padding: 5px 10px; font-size: 0.9em;" onclick="markAsRead(${msg.id})">Marquer comme lu</button>` : '<span style="margin-right: 10px;">✓ Lu</span>'}
                <button style="padding: 5px 10px; font-size: 0.9em; background: #dc3545;" onclick="deleteMessage(${msg.id})">Supprimer</button>
                </div>
            </div>
            <strong>${msg.subject}</strong>
            <p style="margin: 5px 0 0 0;">${msg.body}</p>
        </div>
    `;
}

// Mettre à jour le nombre de messages non lus d'un utilisateur
async function updateUnreadCount(userId) {
    const response = await fetch(`${API_BASE}/users/${userId}/unread_count`);
    const data = await response.json();
    document.getElementById("unread-count").innerText = `${data.unread_count} message(s) non lu(s)`;
}

// Charger la boîte de réception d'un utilisateur, avec d'éventuels paramètres de filtrage
async function loadInbox() {
    const userId = document.getElementById("current-user").value;
    const inboxDiv = document.getElementById("inbox");

    document.getElementById("filters").style.display = "block";
    updateUnreadCount(userId);

    const unreadOnly = document.getElementById("filter-unread").checked;
    const search = document.getElementById("filter-search").value;
    const limit = document.getElementById("filter-limit").value;
    const offset = document.getElementById("filter-offset").value;

    let url = new URL(`${API_BASE}/users/${userId}/inbox`);
    if (unreadOnly) url.searchParams.append("unread_only", "true");
    if (search) url.searchParams.append("search", search);
    if (limit) url.searchParams.append("limit", limit);
    if (offset) url.searchParams.append("offset", offset);

    try {
        const response = await fetch(url);
        const messages = await response.json();
        if (messages.length === 0) {
            inboxDiv.innerHTML = "<p>Aucun message dans la boîte de réception.</p>";
            return;
        }
        document.getElementById("messages-title").innerText = "Boîte de réception";
        inboxDiv.innerHTML = messages.map(msg => createInboxMessageHTML(msg)).join("");
    } catch {
        inboxDiv.innerHTML = `<p style="color: red;">Erreur de connexion</p>`;
    }
}

// Charger la liste des messages envoyés d'un utilisateur
async function loadSent() {
    const userId = document.getElementById("current-user").value;
    const inboxDiv = document.getElementById("inbox");

    document.getElementById("filters").style.display = "none";
    updateUnreadCount(userId);

    try {
        const response = await fetch(`${API_BASE}/users/${userId}/sent`);
        const messages = await response.json();
        if (messages.length === 0) {
            inboxDiv.innerHTML = "<p>Aucun message envoyé.</p>";
            return;
        }

        document.getElementById("messages-title").innerText = "Messages envoyés";
        inboxDiv.innerHTML = messages.map(msg => `
            <div class="message" id="message-${msg.id}">
                <div class="message-meta">
                    <span>À : ${usersMap[msg.receiver_id]} | ${new Date(msg.date).toLocaleString()}</span>
                    <button style="padding: 5px 10px; font-size: 0.9em; background: #dc3545;" onclick="deleteMessage(${msg.id})">Supprimer</button>
                </div>
                <strong>${msg.subject}</strong>
                <p style="margin: 5px 0 0 0;">${msg.body}</p>
            </div>
        `).join("");
    } catch {
        inboxDiv.innerHTML = `<p style="color: red;">Erreur de connexion</p>`;
    }
}

// Marquer un message comme lu
async function markAsRead(msgId) {
    await fetch(`${API_BASE}/messages/${msgId}/read`, { method: "PATCH" });
    loadInbox();
}

// Supprimer un message
async function deleteMessage(msgId) {
    const response = await fetch(`${API_BASE}/messages/${msgId}`, { method: "DELETE" });
    if (document.getElementById("messages-title").innerText === "Boîte de réception") loadInbox();
    else loadSent();
}

// Envoyer un message
async function sendMessage() {
    const senderId = document.getElementById("current-user").value;
    const receiverId = document.getElementById("receiver-id").value;
    const subject = document.getElementById("subject").value;
    const body = document.getElementById("body").value;
    const status = document.getElementById("send-status");

    if (!receiverId || !subject || !body) {
        status.innerText = "Veuillez remplir tous les champs.";
        status.style.color = "red";
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/messages/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sender_id: parseInt(senderId),
                receiver_id: parseInt(receiverId),
                subject: subject,
                body: body
            })
        });

        if (response.ok) {
            status.innerText = "Message envoyé avec succès";
            status.style.color = "green";
            document.getElementById("subject").value = "";
            document.getElementById("body").value = "";
        } else {
            const data = await response.json();
            status.innerText = "Erreur : " + (data.detail);
            status.style.color = "red";
        }
    } catch {
        status.innerText = "Erreur de connexion";
        status.style.color = "red";
    }
}

// Logique WebSocket
let socket = null;

function setupWebSocket(userId) {
    if (!userId) return;
    if (socket) {
        socket.close();
    }

    const wsUrl = API_BASE.replace("http", "ws") + `/ws/users/${userId}`;
    socket = new WebSocket(wsUrl);

   socket.onmessage = (event) => {
            const messageData = JSON.parse(event.data);

            const currentUserId = document.getElementById('current-user').value;
            updateUnreadCount(currentUserId);

            const boxTitle = document.getElementById("messages-title").innerText;

            if (boxTitle === "Boîte de réception") {
                const inboxDiv = document.getElementById("inbox");

                if (!inboxDiv.querySelector('.message')) {
                    inboxDiv.innerHTML = '';
                }
                
                const messageHtml = createInboxMessageHTML(messageData);
                inboxDiv.insertAdjacentHTML('afterbegin', messageHtml);

            } else {
                alert("Nouveau message reçu");
            }
    };
}

// Changer d'utilisateur actif
document.getElementById('current-user').addEventListener('change', (e) => {
    localStorage.setItem("currentUserId", e.target.value);
    setupWebSocket(e.target.value);
    loadInbox();
});

// Initialiser la messagerie au chargement de la page
window.addEventListener('DOMContentLoaded', async () => {
    await listUsers();
    const userId = document.getElementById('current-user').value;
    if (userId) {
        setupWebSocket(userId);
        loadInbox();
    }
});