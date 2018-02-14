"""
Seeding file for flow-balance intermediate database.
Run daily to classify flow-balance errors based on 
local imbalance property.

Usage:
  seed.py -h | --help
  seed.py [--day=<date>]

Options:
  -h --help     Show this help message
  --day=<date>  Update the db for the given day  [default: yesterday]
"""
from docopt import docopt
args = docopt(__doc__)

import numpy as np
import pandas as pd
import datetime, dateparser
import os, sys

import logging
logging.basicConfig(
    level = logging.INFO,
    format = "%(levelname)s: [%(name)s] %(message)s",
    stream = sys.stdout
)

ldir = os.path.dirname(__file__)

from dash.models import *
from pems.download import PemsDownloader as PDR
pdr = PDR()
from dash.scripts.utils import revise_meta, rename_locations, fwys
from dash.scripts.parsekml import df_locations
from dash.scripts.balance import diagnose

import IPython

# Handle args
day = args['--day']
date = dateparser.parse(day, languages = ['en'])

# Acquire data frames meta, station_5min, and cfatv
mday, df_meta = pdr.download('meta')

day, df_day = pdr.download('station_5min', date = date.date(), parse_dates = True)
df_day.drop(['District', 'Freeway', 'Direction', 'Lane Type', 'Station Length'], axis = 1, inplace = True)

df_cfatv = pd.read_json(os.path.join(ldir, 'dash', 'scripts', 'model', 'fatvs.json'), orient = 'index').sort_index()

# Handle the meta
df_meta = revise_meta(df_meta) # reorient and drop useless cols
rename_locations(df_meta) # Fill in location names from numeric codes
for fwy, info in fwys.items(): # Filter only detectors in useful corridor
	df_meta.drop(df_meta[(df_meta['Fwy'] == fwy) & (df_meta['Abs PM'] < info['range'][0])].index, inplace = True)
	df_meta.drop(df_meta[(df_meta['Fwy'] == fwy) & (df_meta['Abs PM'] > info['range'][1])].index, inplace = True)

# Remove detectors that do not belong to a freeway of interest
df_meta.drop(df_meta[~df_meta['Fwy'].isin(fwys.keys())].index, inplace = True)

# Update the meta to include hand located latlons from map kml
df_meta.update(df_locations)

# Update df_meta to include fatv data
df_meta['FATV IN'] = None
df_meta['FATV OUT'] = None
for fid, fatv in df_cfatv.iterrows():
	df_meta.loc[df_meta.index & fatv['IN'], 'FATV IN'] = fid
	df_meta.loc[df_meta.index & fatv['OUT'], 'FATV OUT'] = fid


db.create_all()
# Serialize the meta into the DB
# meta_types = {
	# 'dir': db.String(1),
	# 'name': db.String(40),
	# 'county': db.String(40),
	# 'ltype': db.String(25),
	# 'capm': db.String(10)
# }
meta_types = {c.name : c.type for c in Detector.__table__.columns}
del df_meta['City'] # No unicode support at the moment
df_meta.to_sql('detectors', con = db.engine, dtype = meta_types, index = True, if_exists = 'append')
# IPython.embed(); exit()

# Handle the 5min data

# Serialize the 'raw' data to the DB
df_day.to_sql('data', con = db.engine, index = False, if_exists = 'append')

# Handle Diagnoses
imp2, miscount = diagnose(df_meta, df_day, df_cfatv)

df_diag = pd.DataFrame({
	'DET_ID': imp2,
	'Date': date.date(),
	'Miscount': miscount,
	'Comment': ['' for idx in imp2]
})
# diag_types = {
	# 'ID': db.Integer,
	# 'Date': db.DateTime,
	# 'Miscount': db.Integer,
	# 'Comment': db.String(140)
# }
diag_types = {c.name : c.type for c in Diagnosis.__table__.columns}
df_diag.to_sql('diagnosis', con = db.engine, dtype = diag_types, if_exists = 'append')


fatvs = [FATV(int(n)) for n in df_cfatv.index]
db.session.add_all(fatvs)

log = Log(date = date.date())
db.session.add(log)

db.session.commit()
