import os
import re
import json

import requests
from dotenv import load_dotenv

from constants import SPREADSHEET_TOKEN, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, GROUPCHAT_ID


load_dotenv(dotenv_path='bot.env')

headers = {'Content-Type': 'application/json; charset=utf-8'}
RETRIES = 3


def get_jwt():
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    body = {'app_id': os.getenv('APP_ID'), 'app_secret': os.getenv('APP_SECRET')}
    req = requests.post(url, json=body)
    tenant_access_token = req.json()['tenant_access_token']
    headers['Authorization'] = f'Bearer {tenant_access_token}'


def get_chats():
    url = 'https://open.feishu.cn/open-apis/im/v1/chats'
    req = requests.get(url, headers=headers)
    return req.json()['data']


def send_message(content, msg_type='text'):
    assert msg_type in ('text', 'post')
    url = 'https://open.feishu.cn/open-apis/im/v1/messages'
    params = {'receive_id_type': 'chat_id'}
    if msg_type == 'text':
        content = json.dumps({'text': content})
    elif msg_type == 'post':
        content = json.dumps(content)
    body = {
        'receive_id': GROUPCHAT_ID,
        'msg_type': msg_type,
        'content': content,
    }
    req = requests.post(url, params=params, headers=headers, json=body)
    return req.json()


def subscribe_to_file():
    url = f'https://open.feishu.cn/open-apis/drive/v1/files/{SPREADSHEET_TOKEN}/subscribe'
    subscribe_headers = headers.copy()
    subscribe_headers['Content-Type'] = 'application/x-www-form-urlencoded'
    params = {'file_type': 'sheet'}
    req = requests.post(url, params=params)
    return req.json()['data']


def get_spreadsheet_metainfo(spreadsheet_token):
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/metainfo'
    req = requests.get(url, headers=headers)
    return req.json()['data']


def get_spreadsheet_values(spreadsheet_token, sheet_id, value_range):
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{sheet_id}!{value_range}'
    req = requests.get(url, headers=headers)
    return req.json()['data']['valueRange']['values']


def list_bitable_entries(app_token, table_id):
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records'
    req = requests.get(url, headers=headers)
    # ['data']['has_more'] & ['data']['page_token']
    return req.json()['data']['items'] or []


def insert_bitable_entry(app_token, table_id, entry: dict):
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records'
    body = {'fields': entry}
    req = requests.post(url, headers=headers, json=body)
    return req.json()


def upload_remote_file(remote_url, parent_node, filename=None):
    url = 'https://open.feishu.cn/open-apis/drive/v1/medias/upload_all'
    if filename is None:
        filename = remote_url.rsplit('/', 1)[1]
    file_req = requests.get(remote_url, headers=headers)
    file_raw = file_req.content
    body = {
        'file_name': filename,
        'parent_node': parent_node,
        'parent_type': 'bitable_file',
        'size': len(file_raw),
    }
    files = {'file': file_raw}
    upload_headers = headers.copy()
    del upload_headers['Content-Type']
    req = requests.post(url, headers=upload_headers, data=body, files=files)
    return req.json()


def enforce_plain_text(raw_text):
    if not isinstance(raw_text, list):
        return raw_text
    return ''.join(map(lambda l: l.get('text', ''), raw_text))


def generate_templated_message(name, courses, school, year, is_first_preference):
    title = '?????? TechX ?????????????????????'
    if not is_first_preference:
        title += '???????????????'
    return {
        'zh_cn': {
            'title': title,
            'content': [
                [
                    {
                        'tag': 'text',
                        'text': f'?????????{name}???{school} {year}???'
                    },
                ],
                [
                    {
                        'tag': 'text',
                        'text': f'???????????????{courses}'
                    },
                ],
                [
                    {
                        'tag': 'a',
                        'href': 'https://techx.feishu.cn/base/bascnHLJi8ZpDspC2ooYak3rOgG?table=tblgQXT5MM8mXfU3&view=vew6Byn1ak',
                        'text': '??????????????????'
                    },
                ],
            ]
        },
    }


def update_bitable_from_spreadsheet():
    get_jwt()

    current_emails = set()
    entries = list_bitable_entries(BITABLE_APP_TOKEN, BITABLE_TABLE_ID)
    for entry in entries:
        entry = entry['fields']
        if email := entry.get('????????????'):
            current_emails.add(email)

    sheet_id = get_spreadsheet_metainfo(SPREADSHEET_TOKEN)['sheets'][0]['sheetId']
    values = get_spreadsheet_values(SPREADSHEET_TOKEN, sheet_id, 'F:Z')

    for row in values[1:]: # Skip header row
        row = list(map(enforce_plain_text, row))
        remarks = []
        course_preferences = ''
        if 'TechX' in row[8]:
            course_preferences += row[10]
            is_first_preference = True
        elif 'TechX' in row[9]: # Disregard same track preference (maybe needs to change later)
            course_preferences += row[11]
            is_first_preference = False
            remarks.append('?????????' + row[8].split('???')[0])
        else:
            continue

        name, email, wechat, school, year, major = row[1:7]
        if email in current_emails:
            continue
        available_cities = []
        # if row[18].startswith('??????') and (remark := re.match(r'??????(?:\((.*)\))?')).groups()[0] is not None:
        #     remarks.append(remark)
        for item in row[18].split(','):
            if item.startswith('??????'):
                remarks.append('?????????' + item[2:].strip('()'))
            else:
                available_cities.append(re.match(r'(.+)???????.+???', item).groups()[0])

        resume_files = []
        urls = row[16].split('\n')
        for url in urls:
            url = url.strip()
            if not url.startswith('http'):
                continue
            for i in range(RETRIES):
                upload_resp = upload_remote_file(url, BITABLE_APP_TOKEN)
                if upload_resp['code'] == 0:
                    break
            else:
                remarks.append('???????????????????????????')
                break
            resume_files.append(upload_resp['data'])

        entry = {
            '??????': name,
            '????????????': email,
            '?????????': wechat,
            '??????': school,
            '??????': year,
            '??????': major,
            '????????????': course_preferences,
            '????????????': '?????????' if is_first_preference else '???????????????',
            '??????': resume_files,
            '??????': '',
            '????????????': available_cities,
            'Why AL?': row[12],
            'Why You?': row[13],
            '??????????????????': row[14],
            'Workshop ??????': row[15],
            '??????': '\n'.join(remarks)
        }
        resp = insert_bitable_entry(BITABLE_APP_TOKEN, BITABLE_TABLE_ID, entry)
        if resp['code'] != 0:
            print(resp)
        else:
            print(f'????????????????????????{name}')
            # send_message(f'???????????? TechX AL ????????????{name}???')
            msg = generate_templated_message(name, course_preferences, school, year, is_first_preference)
            send_message(msg, msg_type='post')
