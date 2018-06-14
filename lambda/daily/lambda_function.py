import numpy as np
import pandas as pd

import datetime as dt
from dateutil.parser import parse as parse_date

from pems.download import PemsDownloader as PDR
from pems.util import revise_meta, rename_locations, fwys 

import boto3, io

DATA_BUCKET = 'flow-balance'

def lambda_handler(event, context):
    date = parse_date(event['time']).date()
    date = date - dt.timedelta(days = 1) # Always work from yesterday
    pdr = PDR()

    # data/detectors update
    # Get the active station_meta from pems
    pdr.update_meta('meta', years = [date.year, date.year - 1]) # Look for entries with same and previous year
    rdate = max(filter(lambda d: d < date, pdr.meta['meta'].keys())) # Choose the latest meta
    day, df_meta = pdr.download('meta', date = rdate)
    
    # Only one source for locations
    df_locations = get_df('info/locations.csv')

    # Only one source for fatvs
    df_cfatv = get_cfatv()

    df_meta = revise_meta(df_meta) # Reorient and drop useless cols
    rename_locations(df_meta) # Fill in location names from numeric codes
    for fwy, info in fwys.items(): # Filter only detectors in useful corridor
        range_min, range_max = info['range']
        df_meta.drop(df_meta[(df_meta['Fwy'] == fwy) & (df_meta['Abs PM'] < range_min)].index, inplace = True)
        df_meta.drop(df_meta[(df_meta['Fwy'] == fwy) & (df_meta['Abs PM'] > range_max)].index, inplace = True)

    # Remove detectors that do not belong to a freeway of interest
    df_meta.drop(df_meta[~df_meta['Fwy'].isin(fwys.keys())].index, inplace = True)

    # Update the meta to include hand located latlons, record exactness
    df_meta['Exact'] = False
    df_locations['Exact'] = True
    df_meta.update(df_locations)

    # Update df_meta to include fatv data
    df_meta['FATV IN'] = None
    df_meta['FATV OUT'] = None
    for fid, fatv in df_cfatv.iterrows():
            df_meta.loc[df_meta.index & fatv['IN'], 'FATV IN'] = fid
            df_meta.loc[df_meta.index & fatv['OUT'], 'FATV OUT'] = fid

    put_df(df_meta, 'data/detectors/{:%Y-%m-%d}'.format(date))

    # data/flows update
    day, df_day = pdr.download('station_5min', date = date)
    put_df(df_day, 'data/raw/{:%Y-%m-%d}'.format(date))


def get_df(key):
    s3 = boto3.client('s3')
    store = io.BytesIO()
    s3.download_fileobj(DATA_BUCKET, key, store)
    store.seek(0)
    df_store = pd.read_csv(store, index_col = 0)
    return df_store

def put_df(df, key):
    s3 = boto3.client('s3')
    store = io.BytesIO()
    df.to_csv(store)
    store.seek(0)
    s3.upload_fileobj(store, DATA_BUCKET, key)

def get_cfatv():
    s3 = boto3.client('s3')
    store = io.BytesIO()
    s3.download_fileobj(DATA_BUCKET, 'info/fatvs.json', store)
    store.seek(0)
    df_cfatv = pd.read_json(store, orient = 'index').sort_index()
    return df_cfatv
