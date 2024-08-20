from flask import Flask, render_template, request, send_file
import requests
import pandas as pd
import io
from bs4 import BeautifulSoup

app = Flask(__name__)

# APIキーとURL
API_KEY = '634c407235d16f2b'
URL = 'http://webservice.recruit.co.jp/hotpepper/gourmet/v1/'

def get_data(keywords, start, count=100):
    keyword_str = ' '.join(keywords)
    params = {
        'key': API_KEY,
        'keyword': keyword_str,
        'format': 'json',
        'count': count,
        'start': start
    }
    results = []
    response = requests.get(URL, params=params)
    datum = response.json()

    if response.status_code != 200 or 'results' not in datum or 'shop' not in datum['results']:
        return results

    stores = datum['results']['shop']
    results = [{
        '店舗名': store.get('name', 'N/A'),
        '電話番号のURL': store.get('urls', {}).get('pc', 'N/A').split('?')[0].rstrip('/') + "/tel" if store.get('urls', {}).get('pc', 'N/A') != 'N/A' else 'N/A',
        'サービスエリア名': store.get('service_area', {}).get('name', 'N/A'),
        '住所': store.get('address', 'N/A'),
        '口コミ': store.get('catch', 'N/A'),
        '営業時間': store.get('open', 'N/A'),
        '定休日': store.get('close', 'N/A'),
        'ディナー予算': store.get('budget', {}).get('average', 'N/A'),
        'お店キャッチ': store.get('catch', 'N/A'),
        '総席数': store.get('capacity', 'N/A'),
        'ジャンル名': store.get('genre', {}).get('name', 'N/A'),
        'サブジャンル名': store.get('sub_genre', {}).get('name', 'N/A'),
        'PC向けURL': store.get('urls', {}).get('pc', 'N/A'),
        '口コミ数': 'N/A'
    } for store in stores]

    return results

def get_review_count(url):
    review_count_text = "口コミ数なし"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            li_element = soup.select_one('li.recommendReport > a')
            if li_element:
                p_element = li_element.find_next('p', class_='recommendReportNum')
                if p_element:
                    review_count_text = p_element.find('span').get_text()
    except Exception:
        pass
    return review_count_text

def get_phone_number(url):
    phone_number_text = "電話番号なし"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            phone_number_tag = soup.select_one('div.storeTelephoneWrap > p.telephoneNumber')
            if phone_number_tag:
                phone_number_text = phone_number_tag.get_text().strip()
    except Exception:
        pass
    return phone_number_text

def create_excel_file(results):
    df = pd.DataFrame(results)
    df['電話番号'] = df['電話番号のURL'].apply(get_phone_number)
    df['口コミ数'] = df['PC向けURL'].apply(get_review_count)
    columns_order = ['店舗名', '電話番号', '住所', '口コミ', '営業時間', '定休日', 'ディナー予算', 
                     'お店キャッチ', '総席数', 'ジャンル名', 'サブジャンル名', 'PC向けURL', '口コミ数', 
                     'サービスエリア名']
    df = df[columns_order]
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keywords = request.form.get('keywords', '').split()
        count = request.form.get('count')
        count = int(count) if count else None
        results = []
        start = 1
        step = 100

        while True:
            batch_results = get_data(keywords, start, count=step)
            if not batch_results:
                break
            results.extend(batch_results)
            if count and len(batch_results) < step:
                break
            start += step

        if results:
            excel_file = create_excel_file(results)
            return send_file(excel_file, as_attachment=True, download_name='store_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else:
            return render_template('form.html', error='データが見つかりませんでした。')
    
    return render_template('form.html')

if __name__ == '__main__':
    app.run(debug=True)
