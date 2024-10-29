import spacy
from transformers import pipeline
from dateutil import parser
from datetime import datetime, timedelta
import re

# Load spaCy's pre-trained model
nlp = spacy.load("en_core_web_sm")

# Initialize Hugging Face's transformers pipeline for NER
transformer_ner = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

# Function to calculate deadlines from relative phrases like "in 15 days"
def calculate_relative_deadline(text, sent_date):
    day_match = re.search(r'(\d+)\s+day|days', text)
    week_match = re.search(r'(\d+)\s+week|weeks', text)
    month_match = re.search(r'(\d+)\s+month|months', text)

    if day_match:
        days_to_add = int(day_match.group(1))
        return sent_date + timedelta(days=days_to_add)
    elif week_match:
        weeks_to_add = int(week_match.group(1))
        return sent_date + timedelta(weeks=weeks_to_add)
    elif month_match:
        months_to_add = int(month_match.group(1))
        return sent_date + timedelta(days=months_to_add * 30)  # Approximate 30 days per month
    return None

# Function to extract specific dates and relative deadlines from email
def extract_deadlines(email_text, sent_date):
    deadlines = []

    # Process the text with spaCy's model
    doc = nlp(email_text)

    # Extract explicit dates using spaCy NER
    for ent in doc.ents:
        if ent.label_ == "DATE":
            try:
                deadline = parser.parse(ent.text)
                if deadline > sent_date:  # Ensure future deadlines only
                    deadlines.append(deadline)
            except Exception:
                pass  # Ignore parsing errors

    # Use Hugging Face's NER transformer model for better context understanding
    transformer_results = transformer_ner(email_text)
    for entity in transformer_results:
        if entity['entity'] == 'B-DATE':
            try:
                date_entity = entity['word']
                deadline = parser.parse(date_entity)
                if deadline > sent_date:  # Ensure future deadlines only
                    deadlines.append(deadline)
            except Exception:
                pass  # Ignore parsing errors

    # Handle relative deadlines (like "in 10 days")
    relative_deadline = calculate_relative_deadline(email_text, sent_date)
    if relative_deadline and relative_deadline > sent_date:
        deadlines.append(relative_deadline)

    return deadlines
