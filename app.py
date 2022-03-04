import os
import json

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from utils import decrypt_aes
from feishu import update_bitable_from_spreadsheet


load_dotenv(dotenv_path='bot.env')

app = Flask(__name__)


@app.route('/')
def main_handle():
    data = request.json or request.form
    encrypt = data.get('encrypt')
    decrypt = decrypt_aes(os.getenv('EVENT_ENCRYPT_KEY'), encrypt)
    data = json.loads(decrypt)

    if data['type'] == 'url_verification':
        challenge = data['challenge']
        return json.dumps({'challenge': challenge})


if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))

    app.run(host=host, port=port, threaded=True, use_reloader=False)
