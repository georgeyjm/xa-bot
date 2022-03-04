import os
import re

import requests
from dotenv import load_dotenv


headers = {'Content-Type': 'application/json; charset=utf-8'}

SPREADSHEET_TOKEN = 'shtcnafMpuvPzIg2LaRXj36PLU2'
BITABLE_APP_TOKEN = 'bascnHLJi8ZpDspC2ooYak3rOgG'
BITABLE_TABLE_ID = 'tblgQXT5MM8mXfU3'

load_dotenv(dotenv_path='bot.env')


def get_jwt():
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    body = {'app_id': os.getenv('APP_ID'), 'app_secret': os.getenv('APP_SECRET')}
    req = requests.post(url, json=body)
    tenant_access_token = req.json()['tenant_access_token']
    headers['Authorization'] = f'Bearer {tenant_access_token}'


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


def update_bitable_from_spreadsheet():
    get_jwt()

    current_emails = set()
    entries = list_bitable_entries(BITABLE_APP_TOKEN, BITABLE_TABLE_ID)
    for entry in entries:
        entry = entry['fields']
        if email := entry.get('邮箱地址'):
            current_emails.add(email)

    sheet_id = get_spreadsheet_metainfo(SPREADSHEET_TOKEN)['sheets'][0]['sheetId']
    values = get_spreadsheet_values(SPREADSHEET_TOKEN, sheet_id, 'F:Z')

    for row in values[1:]: # Skip header row
        remarks = []
        course_preferences = ''
        if 'TechX' in row[8]:
            course_preferences += row[10]
            is_first_preference = True
        elif 'TechX' in row[9]: # Disregard same track preference (maybe needs to change later)
            course_preferences += row[11]
            is_first_preference = False
            remarks.append('首选：' + row[8].split('（')[0])
        else:
            continue

        name, email, wechat, school, year, major = row[1:7]
        if email in current_emails:
            continue
        available_cities = []
        # if row[18].startswith('其他') and (remark := re.match(r'其他(?:\((.*)\))?')).groups()[0] is not None:
        #     remarks.append(remark)
        for item in row[18].split(','):
            if item.startswith('其他'):
                remarks.append('场次：' + item[2:].strip('()'))
            else:
                available_cities.append(re.match(r'(.+)?场（.+）', item).groups()[0])

        resume_files = []
        for url in row[16].split('\n'):
            url = url.strip()
            if not url.startswith('http'):
                continue
            upload_resp = upload_remote_file(url, BITABLE_APP_TOKEN)
            resume_files.append(upload_resp['data'])

        entry = {
            '姓名': name,
            '邮箱地址': email,
            '微信号': wechat,
            '学校': school,
            '年级': year,
            '专业': major,
            '意向课程': course_preferences,
            '招募阶段': '已申请' if is_first_preference else '首选志愿中',
            '简历': resume_files,
            '链接': '',
            '有空场次': available_cities,
            'Why AL?': row[12],
            'Why You?': row[13],
            '自学路径推荐': row[14],
            'Workshop 计划': row[15],
            '备注': '\n'.join(remarks)
        }
        resp = insert_bitable_entry(BITABLE_APP_TOKEN, BITABLE_TABLE_ID, entry)
        if resp['code'] != 0:
            print(resp)
        else:
            print(f'记录了新申请者：{name}')
