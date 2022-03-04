import os
import json

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from .utils import decrypt_aes
from .feishu import update_bitable_from_spreadsheet


load_dotenv(dotenv_path='bot.env')

app = Flask(__name__)


@app.route('/')
def main_handle():
    encrypt = request.json.get('encrypt') or request.form.get('encrypt')
    decrypt = decrypt_aes(os.getenv('EVENT_ENCRYPT_KEY'), encrypt)
    data = json.loads(decrypt)

    if data['type'] == 'url_verification':
        challenge = data['challenge']
        return jsonify(challenge=challenge)
