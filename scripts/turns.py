import numpy as np
import pandas as pd
import datetime as dt
import boto3, io, json
from botocore.exceptions import ClientError

import logging
import argparse

import IPython

def datearg(date):
	try:
		return dt.datetime.strptime(date, "%Y-%m-%d").date()
	except ValueError as exc:
		raise argparse.ArgumentTypeError(f"Bad date {date}.") from exc

parser = argparse.ArgumentParser(
	description = "Turn ratio candidates and estimates"
)
parser.add_argument('-v', '--verbose', help = 'Verbose logging', action = 'count')
parser.add_argument('-d', '--date', help = 'Date to analyze (YYYY-MM-DD) [default: yesterday]', type = datearg,
	default = dt.date.today() - dt.timedelta(days = 1))
parser.add_argument('--time', metavar = 'INTERVAL', help = 'Time interval to analyze', nargs = '*')

args = parser.parse_args()

log_levels = {
	1: logging.INFO,
	2: logging.DEBUG
}

logging.basicConfig(
	level = log_levels.get(args.verbose, logging.WARNING),
	format = "%(asctime)s.%(msecs)03d [%(levelname)s]: %(message)s",
	datefmt = "%X"
)

intervals = []
for interval in args.time:
	if '-' in interval:
		start, stop = interval.split('-')
	else:
		start, stop = '0:00', interval
	
	if not stop:
		stop = '23:59'
	
	interval = start, stop
	intervals.append(interval)
	
# Util
def get_df(s3, key, **kwds):
	if 'index_col' not in kwds:
		kwds['index_col'] = 0
	
	try:
		store = io.BytesIO()
		s3.download_fileobj('flow-balance', key, store)
		store.seek(0)
		df_store = pd.read_csv(store, **kwds)
	except ClientError as e:
		logging.error(f"No data for {key!r}")
		exit(1)
	finally:
		store.close()
	
	return df_store

def get_cfatv(s3):
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', 'info/fatvs.json', store)
	store.seek(0)
	df_cfatv = pd.read_json(store, orient = 'index').sort_index()
	store.close()
	return df_cfatv

def get_balance(s3, key):
	store = io.BytesIO()
	s3.download_fileobj('flow-balance', key, store)
	store.seek(0)
	labels = json.load(store)
	store.close()
	return labels

def has_all(idx, target):
	return np.all(pd.Series(idx).isin(target))

def interval_str(interval):
	return '-'.join(interval)

# Load data
s3 = boto3.client('s3')
logging.info("Get FATV info")
fatvs = get_cfatv(s3)

logging.info("Get flows info")
flows = get_df(s3, f'data/flows/{args.date:%Y-%m-%d}', parse_dates = ['Timestamp'])
flows.rename(columns = int, inplace = True)

logging.info("Get detector meta info")
detectors = get_df(s3, f'data/detectors/{args.date:%Y-%m-%d}')

logging.info("Get balance labels info")
labels = get_balance(s3, f'data/balance/{args.date:%Y-%m-%d}')

# ignore fatvs with error or singleton detectors
bad = labels['error'] + labels['singleton']
flows[bad] = np.nan

# Evaluate
off = detectors.index[detectors['Type'] == 'Off Ramp']
turns = fatvs['OUT'].apply(lambda out: np.any([off.contains(det) for det in out]))
turns = pd.Series(turns.index[turns])

print(args.date)
for turn in turns:
	inset = fatvs.loc[turn, 'IN']
	outset = fatvs.loc[turn, 'OUT']

	if not has_all(inset + outset, flows):
		logging.debug(f"Some FATV {turn} members are absent.")
		continue

	header = False
	for interval in intervals:
		try:
			flow = flows.between_time(*interval)
		except ValueError as e:
			msg, = e.args
			logging.error(msg)
			continue

		samples = len(flow)
		flow = flow[inset + outset].dropna()
		quality = 100 * len(flow) / samples

		incoming = flow[inset].values.sum()
		outgoing = flow[outset].values.sum()
		sinks = [(sink, flow[sink].values.sum()) for sink in outset]

		if quality > 0:
			if not header:
				print(f"FATV   start-stop quality incoming outgoing" + " ".join(f"{sink:7d}" for sink in outset))
				header = True
			print(f"{turn:4d} {interval_str(interval):>12s} {quality:7.1f} {incoming:8.0f} {outgoing:8.0f}", end = '')
			print(" ".join(f"{100 * volume / outgoing:6.2f}%" for sink, volume in sinks))
	if header:
		print()

