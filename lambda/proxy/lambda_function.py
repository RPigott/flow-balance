import numpy as np
import pandas as pd

import datetime as dt
from dateutil.parser import parse as parse_date
import boto3, json, io

from operator import itemgetter, attrgetter
import logging
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
	date = event['pathParameters']['date']
	if date == 'latest':
		latest = sorted(ls_key('data/raw/'))[-1]
		date = latest.split('/')[-1]
	
	df_meta = get_df('data/detectors/{}'.format(date))
	df_meta.rename(
		columns =  {'FATV IN': 'fatv_in', 'FATV OUT': 'fatv_out'},
		inplace = True
		)
		
	dd = {id: dict(row) for id, row in df_meta.iterrows()}
	for d in dd.values():
		d['loc'] = [d['Latitude'], d['Longitude']]
	
	return {
		'statusCode': 200,
		'headers': {},
		'body': json.dumps(dd)
	}

def ls_key(key):
	s3 = boto3.client('s3')
	ls = s3.list_objects(Bucket = 'flow-balance', Prefix = key)
	return [item['Key'] for item in ls['Contents']]

def put_str(s, key):
	s3 = boto3.client('s3')
	store = io.BytesIO(s)
	s3.upload_fileobj(store, 'flow-balance', key)

def get_df(key):
	s3 = boto3.client('s3')
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', key, store)
	store.seek(0)
	df_store = pd.read_csv(store, index_col = 0)
	return df_store

def put_df(df, key):
	s3 = boto3.client('s3')
	store = io.BytesIO()
	df.to_csv(store)
	store.seek(0)
	s3.upload_fileobj(store, 'flow-balance', key)

def get_cfatv():
	s3 = boto3.client('s3')
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', 'info/fatvs.json', store)
	store.seek(0)
	df_cfatv = pd.read_json(store, orient = 'index').sort_index()
	return df_cfatv
