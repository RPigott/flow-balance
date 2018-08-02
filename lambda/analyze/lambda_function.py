import numpy as np
import pandas as pd

import datetime as dt
from dateutil.parser import parse as parse_date
import boto3, json, io

from operator import itemgetter, attrgetter
import logging
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
	record, = event['Records']
	key = record['s3']['object']['key']
	key = key.split('/')[-1]

	date = parse_date(key).date()

	df_meta = get_df('data/detectors/{}'.format(key))
	df_day = get_df('data/raw/{}'.format(key))

	df_piv = df_day.pivot('Timestamp', 'Station', 'Flow')

	obv = df_day.pivot('Timestamp', 'Station', 'Observed').mean() > 50
	unobv = obv[~obv].index
	df_piv[unobv] = np.nan

	df_cfatv = get_cfatv()
	
	# Identify imbalanced detectors
	df_cfatv['ERR'] = np.nan
	df_cfatv['VOL'] = np.nan
	df_cfatv['DIF'] = np.nan
	for idx in df_cfatv.index:
		ins, outs = df_cfatv.loc[idx, ['IN', 'OUT']]
		try:
			ins = df_piv[ins].sum(skipna = False).sum(skipna = False)
			outs = df_piv[outs].sum(skipna = False).sum(skipna = False)
		except KeyError as e:
			logger.debug("Cannot account FATV {}, illformed FATV or bad meta?".format(idx))
			ins = np.nan
			outs = np.nan
	
		df_cfatv.loc[idx, 'DIF'] = ins - outs
		df_cfatv.loc[idx, 'VOL'] = ins + outs
		df_cfatv.loc[idx, 'ERR'] = abs(ins - outs) / (ins + outs)
	imb = df_cfatv[df_cfatv['ERR'] > 0.05] # TODO: magic
	
	imp1, imp2 = [], []
	for idx, fatv in df_cfatv[df_cfatv['ERR'] > 0.025].iterrows(): # TODO: magic
		neighbors = {}
		for det in fatv['IN']:
			for nidx in df_cfatv[df_cfatv['OUT'].map(lambda ds: det in ds)].index:
				neighbors[det] = nidx
		for det in fatv['OUT']:
			for nidx in df_cfatv[df_cfatv['IN'].map(lambda ds: det in ds)].index:
				neighbors[det] = nidx
	
		for det, neighbor in neighbors.items():
			pair = df_cfatv.loc[[idx, neighbor]]
			if pair.loc[neighbor]['ERR'] < 0.01: # TODO: magic
				continue
			temp = pair.sum()
			temp['ERR'] = abs(temp['DIF'])/temp['VOL']
	
			if temp['ERR'] < 0.15 * fatv['ERR']: # TODO: magic
				if det in imp1:
					imp2.append(det)
				imp1.append(det)
				logger.info("{} implicates {} from {}".format(neighbor, det, idx))

	infatvs = df_meta.loc[imp2, 'FATV IN']
	outfatvs = df_meta.loc[imp2, 'FATV OUT']

	invals = df_cfatv.loc[infatvs, 'DIF'].values
	outvals = df_cfatv.loc[outfatvs, 'DIF'].values

	miscount = (outvals - invals)

	# diagnosis = [{"detector": det, "diagnosis": "error", "miscount": m, "comment": ""} for det, m in zip(imp2, miscount)]
	# diagnosis += [{"detector": det, "diagnosis": "unobv", "comment": ""} for det in (df_meta.index & unobv)]

	# diagnosis += [{"detector": det, "diagnosis": "unknown", "comment": ""} for det in unknown]

	tracked = json.loads(get_str('info/tracked.json')) # Detectors that appear in the model

	unknown = set(df_cfatv[df_cfatv['ERR'].isnull()][['IN', 'OUT']].sum().sum())
	diagnosis = {
		'error': imp2, # Diagnosed to be in error
		'unobv': list(df_meta.index & unobv), # Not providing sufficient data
		'unknown': list(unknown), # Neighbors not providing sufficient data
		'untracked': list(set(df_meta.index) - set(tracked)) # Appear in PeMS but not model
	}

	put_str(json.dumps(diagnosis), 'data/balance/{}'.format(key))

def put_str(s, key):
	s3 = boto3.client('s3')
	store = io.BytesIO(s)
	s3.upload_fileobj(store, 'flow-balance', key)

def get_str(key):
	s3 = boto3.client('s3')
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', key, store)
	store.seek(0)
	return store.getvalue()

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
