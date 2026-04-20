import requests
import base64
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# These should be loaded from your Render Environment Variables
CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
SHORTCODE = os.environ.get('MPESA_SHORTCODE')
PASSKEY = os.environ.get('MPESA_PASSKEY')

# Use sandbox URLs for development, switch to production URLs on deployment
AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
STK_PUSH_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

def get_mpesa_access_token():
    try:
        response = requests.get(AUTH_URL, auth=(CONSUMER_KEY, CONSUMER_SECRET), timeout=10)
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Failed to get M-Pesa token: {e}")
        return None

def generate_mpesa_password():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    data_to_encode = SHORTCODE + PASSKEY + timestamp
    encoded_string = base64.b64encode(data_to_encode.encode())
    return encoded_string.decode('utf-8'), timestamp