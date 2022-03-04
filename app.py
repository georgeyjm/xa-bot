import os
import json

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from utils import decrypt_aes
from feishu import update_bitable_from_spreadsheet
from constants import SPREADSHEET_TOKEN


load_dotenv(dotenv_path='bot.env')

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def main_handle():
    data = request.json or request.form
    print(data)
    try:
        encrypt = data['encrypt']
        decrypt = decrypt_aes(os.getenv('EVENT_ENCRYPT_KEY'), encrypt)
        data = json.loads(decrypt)
    except Exception as e:
        print('Encountered exception', e)
        return jsonify({'msg': str(e)})

    if data.get('type') == 'url_verification':
        challenge = data['challenge']
        return jsonify({'challenge': challenge})
    
    if data['header'] != os.getenv('EVENT_VERIFICATION_TOKEN'):
        return jsonify({'msg': 'Byebye'})
    
    if data['header']['event_type'] == 'drive.file.edit_v1':
        if data['event']['file_token'] == SPREADSHEET_TOKEN:
            update_bitable_from_spreadsheet()


if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))

    app.run(host=host, port=port, threaded=True, use_reloader=False)
