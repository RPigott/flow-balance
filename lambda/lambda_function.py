from __future__ import print_function

print('Loading numpy')
import numpy
import pandas

print('Loading function')

def lambda_handler(event, context):
    print('Printing something')
    pandas.np.show_config()
    return "return value"