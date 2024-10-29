from flask import Flask, request, jsonify, redirect, url_for, session, render_template
import os
import base64
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from deadline_extractor import extract_deadlines

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'your_secret_key'

CLIENT_SECRETS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

@app.route('/')
def index():
    return render_template('index.html')  # Render the index HTML file

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=url_for('oauth2callback', _external=True))
    authorization_url, state = flow.authorization_url(access_type='offline')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=url_for('oauth2callback', _external=True))
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('email_list'))

@app.route('/email_list')
def email_list():
    credentials = session.get('credentials')
    if not credentials:
        return redirect(url_for('login'))  # If not logged in, redirect to login

    credentials = Credentials(**credentials)
    service = build('gmail', 'v1', credentials=credentials)

    # Fetch the latest 10 emails
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])

    email_list = []
    if messages:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()

            # Extract the email subject and snippet
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            snippet = msg.get('snippet', '')

            email_list.append({
                'id': message['id'],
                'subject': subject,
                'snippet': snippet
            })

    return render_template('email_list.html', emails=email_list)

@app.route('/email/<email_id>')
def email_detail(email_id):
    credentials = session.get('credentials')
    if not credentials:
        return redirect(url_for('login'))

    credentials = Credentials(**credentials)
    service = build('gmail', 'v1', credentials=credentials)

    msg = service.users().messages().get(userId='me', id=email_id).execute()
    
    # Extract email details
    payload = msg.get('payload', {})
    headers = payload.get('headers', [])
    body = ""

    # Extract the plain text body if available
    if 'parts' in payload:  # multipart email
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                body = part['body']['data']
                break
    else:  # single-part email
        body = payload['body'].get('data', '')

    # Decode the body from base64url encoding
    body = base64.urlsafe_b64decode(body).decode('utf-8')

    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')

    return render_template('email_detail.html', email={'id': email_id, 'subject': subject, 'body': body})

@app.route('/extract_deadline', methods=['POST'])
def extract_deadline():
    data = request.get_json()
    if 'body' not in data:
        return jsonify({'error': 'No email body provided.'}), 400
    
    email_body = data['body']  # Get the email body sent from the HTML
    sent_date = datetime.now()  # Use current date as the sent date
    
    # Call the function from `deadline_extractor.py`
    deadlines = extract_deadlines(email_body, sent_date)
    
    # Format the deadlines as a list of strings
    deadline_list = [deadline.strftime('%Y-%m-%d') for deadline in deadlines if deadline > sent_date]  # Only future deadlines
    
    return jsonify({'deadlines': deadline_list})

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

if __name__ == '__main__':
    app.run(debug=True)
