import os
import json
import base64
import sqlite3
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the scope and credentials file path
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Database configuration
DB_FILE = 'emails.db'

# Load Gmail credentials
creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# Authenticate and authorize the user if credentials do not exist
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

# Connect to the database
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Create a table for storing emails if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS emails (
        id TEXT PRIMARY KEY,
        from_address TEXT,
        to_address TEXT,
        subject TEXT,
        message TEXT,
        received_date TEXT,
        is_read INTEGER DEFAULT 0
    )
''')
conn.commit()

# Fetch emails using Gmail API
service = build('gmail', 'v1', credentials=creds)
results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
emails = results.get('messages', [])

# Process and store emails in the database
for email in emails:
    msg = service.users().messages().get(userId='me', id=email['id']).execute()
    headers = msg['payload']['headers']
    email_data = {
        'id': msg['id'],
        'from_address': '',
        'to_address': '',
        'subject': '',
        'message': '',
        'received_date': ''
    }
    for header in headers:
        name = header['name']
        value = header['value']
        if name.lower() == 'from':
            email_data['from_address'] = value
        elif name.lower() == 'to':
            email_data['to_address'] = value
        elif name.lower() == 'subject':
            email_data['subject'] = value
        elif name.lower() == 'date':
            email_data['received_date'] = value
    # Store the email in the database
    cursor.execute('INSERT INTO emails VALUES (:id, :from_address, :to_address, :subject, :message, :received_date, 0)',
                   email_data)
    conn.commit()

# Load rules from JSON file
with open('rules.json') as file:
    rules = json.load(file)

# Process emails based on rules
for rule in rules:
    field = rule['field']
    predicate = rule['predicate']
    value = rule['value']
    actions = rule['actions']

    # Construct the SQL query based on the rule
    sql_query = 'SELECT * FROM emails WHERE '
    if field == 'Received Date/Time':
        if predicate == 'less than':
            sql_query += "received_date < '{}'".format(value)
        elif predicate == 'greater than':
            sql_query += "received_date > '{}'".
