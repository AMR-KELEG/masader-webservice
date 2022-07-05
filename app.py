import json

from multiprocessing import Process
from typing import Dict, List, Optional, Union

import pandas as pd
import redis

from flask import Flask, jsonify, request
from flask_cors import CORS

from utils.common_utils import dict_filter
from utils.dataset_utils import refresh_masader_and_tags


app = Flask(__name__)
app.config.from_object('config.Config')
CORS(app)


db = redis.from_url(app.config['REDIS_URL'])
masader: Optional[List[Dict[str, Union[str, int]]]] = None
tags: Dict[str, List[Union[str, int]]] = None


@app.route('/datasets/schema')
def datasets_schema():
    global masader

    return jsonify(list(masader[0].keys()))


@app.route('/datasets')
def get_datasets():
    global masader

    page = request.args.get('page', default=1, type=int)
    size = request.args.get('size', default=len(masader), type=int)
    features = list(filter(None, request.args.get('features', default='', type=str).split(',')))
    query = request.args.get('query', default='', type=str)

    masader_page = masader[(page - 1) * size : page * size]

    if not masader_page:
        return jsonify('Page not found.'), 404

    masader_page = pd.DataFrame(masader_page)

    if query:
        masader_page = masader_page.query(query)

    if features:
        masader_page = masader_page[features]

    return jsonify(masader_page.to_dict('records'))


@app.route('/datasets/<int:index>')
def get_dataset(index: int):
    global masader

    features = list(filter(None, request.args.get('features', default='', type=str).split(',')))

    if not (1 <= index <= len(masader)):
        return jsonify(f'Dataset index is out of range, the index should be between 1 and {len(masader)}.'), 404

    return jsonify(dict_filter(masader[index - 1], features))


@app.route('/datasets/tags')
def get_tags():
    global tags

    features = list(filter(None, request.args.get('features', default='', type=str).split(',')))

    return jsonify(dict_filter(tags, features))


@app.route('/refresh')
def refresh():
    global db, masader, tags

    print('Refreshing globals...')

    Process(name='refresh_globals', target=refresh_masader_and_tags, args=(db,)).start()

    masader = json.loads(db.get('masader'))
    tags = json.loads(db.get('tags'))

    return jsonify(f'The datasets updated successfully! The current number of available datasets is {len(masader)}.')


with app.app_context():
    refresh()
