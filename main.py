import os
import re
import json

import requests
from dotenv import load_dotenv


headers = {'Content-Type': 'application/json; charset=utf-8'}

SPREADSHEET_TOKEN = 'shtcnafMpuvPzIg2LaRXj36PLU2'
BITABLE_APP_TOKEN = 'bascnHLJi8ZpDspC2ooYak3rOgG'
BITABLE_TABLE_ID = 'tblgQXT5MM8mXfU3'


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


def upload_file(filepath, filename, parent_node):
    url = 'https://open.feishu.cn/open-apis/drive/v1/medias/upload_all'
    assert os.path.isfile(filepath)
    body = {
        'file_name': filename,
        'parent_node': parent_node,
        'parent_type': 'bitable_file',
        'size': os.path.getsize(filepath),
    }
    files = {'file': open(filepath, 'rb')}
    req = requests.post(url, headers=headers, json=body, files=files)
    return req.json()


load_dotenv(dotenv_path='bot.env')
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
    course_preferences = ''
    if 'TechX' in row[8]:
        course_preferences += row[10]
    elif 'TechX' in row[9]: # Disregard same track preference (maybe needs to change later)
        course_preferences += row[11]
    else:
        continue

    name, email, wechat, school, year, major = row[1:7]
    if email in current_emails:
        continue
    remarks = []
    available_cities = []
    # if row[18].startswith('其他') and (remark := re.match(r'其他(?:\((.*)\))?')).groups()[0] is not None:
    #     remarks.append(remark)
    for item in row[18].split(','):
        if item.startswith('其他'):
            remarks.append('场次：' + item[2:].strip('()'))
        else:
            available_cities.append(re.match(r'(.+)?场（.+）', item).groups()[0])

    entry = {
        '姓名': name,
        '邮箱地址': email,
        '微信号': wechat,
        '学校': school,
        '年级': year,
        '专业': major,
        '意向课程': course_preferences,
        '招募阶段': '已申请',
        '简历': [],
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
