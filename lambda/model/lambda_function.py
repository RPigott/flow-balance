import numpy as np
import pandas as pd
import networkx as nx

import boto3, json, re
from zipfile import ZipFile

import logging
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
	s3 = boto3.client('s3')
	s3.download_file('flow-balance', 'info/model.zip', '/tmp/model.zip')
	
	good_ptn = r'^7\d+$'
	bad_ptn = r'^7131'
	with ZipFile('/tmp/model.zip') as zm:
		with zm.open('detectors.json') as dets:
			dets = json.load(dets)
			tracked = [int(det) for det in dets if re.match(good_ptn, det) and not re.match(bad_ptn, det)]
	
	with open('/tmp/tracked.json', 'w') as file:
		json.dump(tracked, file)

	s3.upload_file('/tmp/tracked.json', 'flow-balance', 'info/tracked.json')
