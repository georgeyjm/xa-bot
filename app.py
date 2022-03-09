import os
import json
import atexit

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler

from utils import decrypt_aes
from feishu import update_bitable_from_spreadsheet
from constants import SPREADSHEET_TOKEN


load_dotenv(dotenv_path='bot.env')

app = Flask(__name__)

scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()

scheduler.add_job(id='check_for_update', func=update_bitable_from_spreadsheet, trigger='interval', hours=3)
update_bitable_from_spreadsheet()


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
