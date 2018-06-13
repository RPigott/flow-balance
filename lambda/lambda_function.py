import numpy as np
import pandas as pd
import boto3
from pems.download import PemsDownloader as PDR

def handler(event, context):
    pdr = PDR()
    day, df_day = pdr.download('station_5min')
    df_day = df_day.pivot('Timestamp', 'Station', 'Flow')
    return [int(n) for n in df_day.columns]
