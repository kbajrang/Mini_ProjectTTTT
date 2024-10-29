let GoogleAuth;
const SCOPE = 'https://www.googleapis.com/auth/gmail.readonly';

function initClient() {
    gapi.client.init({
        'apiKey': 'YOUR_API_KEY',
        'clientId': 'YOUR_CLIENT_ID',
        'discoveryDocs': ['https://www.googleapis.com/discovery/v1/apis/gmail/v1/rest'],
        'scope': SCOPE
    }).then(function () {
        GoogleAuth = gapi.auth2.getAuthInstance();
        document.getElementById('signInButton').style.display = 'block';
    });
}

gapi.load('client:auth2', initClient);

function handleAuthClick() {
    GoogleAuth.signIn().then(function () {
        listMessages();
    });
}

function listMessages() {
    gapi.client.gmail.users.messages.list({
        'userId': 'me',
        'labelIds': ['INBOX'],
        'maxResults': 10 // Limiting to 10 for testing purposes
    }).then(function (response) {
        const messages = response.result.messages;
        let emailListHtml = ''; 
        const emailListContainer = document.getElementById('emailsList');
        
        // Display a loading indicator while emails are fetched
        emailListContainer.innerHTML = '<p>Loading emails...</p>';
        
        if (messages && messages.length > 0) {
            emailListHtml = '<h3>Your Recent Emails:</h3>';
            messages.forEach(message => {
                gapi.client.gmail.users.messages.get({
                    'userId': 'me',
                    'id': message.id
                }).then(function (msg) {
                    const subject = getHeader(msg.result.payload.headers, 'Subject');
                    emailListHtml += `<div class="emailItem">
                        <a href="#" onclick="viewEmailContent('${message.id}')">View Mail: ${subject}</a>
                    </div>`;
                    emailListContainer.innerHTML = emailListHtml;
                });
            });
        } else {
            emailListContainer.innerHTML = '<p>No emails found.</p>';
        }
    });
}

function viewEmailContent(messageId) {
    gapi.client.gmail.users.messages.get({
        'userId': 'me',
        'id': messageId
    }).then(function (response) {
        const emailBody = getBody(response.result.payload);
        document.getElementById('emailsList').innerHTML = `
            <div class="emailItem">
                <p><strong>Full Email Content:</strong></p>
                <p>${emailBody}</p>
                <button onclick="processEmail('${messageId}')">Select Mail to Extract Deadline</button>
            </div>`;
    });
}

function processEmail(messageId) {
    gapi.client.gmail.users.messages.get({
        'userId': 'me',
        'id': messageId
    }).then(function (response) {
        const emailBody = getBody(response.result.payload);
        // Send email body to Python backend for deadline extraction
        fetch('/extract_deadline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ body: emailBody })
        })
        .then(response => response.json())
        .then(data => {
            alert(`Detected deadlines: ${data.deadlines}`);
        });
    });
}

function getHeader(headers, name) {
    for (let i = 0; i < headers.length; i++) {
        if (headers[i].name === name) {
            return headers[i].value;
        }
    }
    return '';
}

function getBody(message) {
    let encodedBody = '';
    if (typeof message.parts === 'undefined') {
        encodedBody = message.body.data;
    } else {
        encodedBody = getHTMLPart(message.parts);
    }
    return decodeURIComponent(escape(atob(encodedBody.replace(/-/g, '+').replace(/_/g, '/'))));
}

function getHTMLPart(parts) {
    for (let i = 0; i < parts.length; i++) {
        if (parts[i].mimeType === 'text/plain') {
            return parts[i].body.data;
        } else if (typeof parts[i].parts === 'object') {
            return getHTMLPart(parts[i].parts);
        }
    }
    return '';
}
