import numpy as np
import pandas as pd

import datetime as dt
from dateutil.parser import parse as parse_date
import boto3, json, io

from operator import itemgetter, attrgetter
import logging
logger = logging.getLogger(__name__)

s3 = boto3.client('s3')

def lambda_handler(event, context):
	"""
	Proxy responses for API Gateway HTTP requests from the flow-balance page.
	"""
	proxy = event['pathParameters']['proxy']
	method = event['requestContext']['httpMethod']
	query = event['queryStringParameters'] or {}
	logger.info("Handling {} {}".format(method, proxy))

	path = proxy.split('/')
	if path[0] == 'detectors':
		return handle_detectors(path, query)
	elif path[0] == 'latest':
		return handle_latest(path, query)
	elif path[0] == 'diagnosis':
		return handle_diagnosis(path, query)
	elif path[0] == 'plot':
		return handle_plot(path, query)

def handle_latest(path, query):
	latest = sorted(ls_key('data/detectors'))[-1]
	date = latest.split('/')[-1]
	return proxy_response(json.dumps({'date': date}))

def handle_detectors(path, query):
	if query.get("date", ""):
		date = query['date']
		target = 'data/detectors/' + date
	else:
		latest = sorted(ls_key('data/detectors/'))[-1]
		target = latest
	
	df_meta = get_df(target)
	df_meta.rename(
		columns =  {
			'FATV IN': 'fatv_in',
			'FATV OUT': 'fatv_out',
			'Latitude': 'lat',
			'Longitude': 'lon'
		},
		inplace = True
	)
		
	body = df_meta.to_json(orient = 'index')
	return proxy_response(body)

def handle_diagnosis(path, query):
	if query.get("date", ""):
		date = query['date']
		target = 'data/balance/' + date
	else:
		latest = sorted(ls_key('data/balance/'))[-1]
		target = latest
	
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', target, store)

	body = store.getvalue()
	return proxy_response(body)

def handle_plot(path, query):
	if query.get("date", ""):
		date = query['date']
		target = 'data/flows/' + date
	else:
		latest = sorted(ls_key('data/flows/'))[-1]
		target = latest
	
	df_piv = get_df(target)
	df_piv.columns = pd.to_numeric(df_piv.columns) # df_piv has ids as cols
	df_piv.index = pd.to_datetime(df_piv.index) # df_piv has timestamp as index

	fatv = int(path[1])
	df_cfatv = get_cfatv()

	fd_in, fd_out = df_cfatv.loc[fatv]
	in_data = df_piv[fd_in].sum(axis = 1, skipna = False)
	out_data = df_piv[fd_out].sum(axis = 1, skipna = False)

	body = {
		'IN': {
			'detectors': fd_in,
			'data': {
				'name': 'IN',
				'mode': 'lines',
				'x': [str(time) for time in in_data.index],
				'y': [n if not np.isnan(n) else None for n in in_data.values]
			}
		},
		'OUT': {
			'detectors': fd_out,
			'data': {
				'name': 'OUT',
				'mode': 'lines',
				'x': [str(time) for time in out_data.index],
				'y': [n if not np.isnan(n) else None for n in out_data.values]
			}
		}
	}

	body = json.dumps(body)
	return proxy_response(body)

def proxy_response(body):
	# AWS apigateway CORS is broken AF for some reason... manually added ACAO header
	return {
		'statusCode': 200,
		'headers': {'access-control-allow-origin': '*'}, # dirty hack
		'body': body
	}

def ls_key(key):
	ls = s3.list_objects(Bucket = 'flow-balance', Prefix = key)
	return [item['Key'] for item in ls['Contents']]

def put_str(s, key):
	store = io.BytesIO(s)
	s3.upload_fileobj(store, 'flow-balance', key)

def get_df(key):
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', key, store)
	store.seek(0)
	df_store = pd.read_csv(store, index_col = 0)
	return df_store

def put_df(df, key):
	store = io.BytesIO()
	df.to_csv(store)
	store.seek(0)
	s3.upload_fileobj(store, 'flow-balance', key)

def get_cfatv():
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', 'info/fatvs.json', store)
	store.seek(0)
	df_cfatv = pd.read_json(store, orient = 'index').sort_index()
	return df_cfatv
