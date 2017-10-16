from __future__ import print_function

print('Loading numpy')
import numpy

print('Loading function')

def lambda_handler(event, context):
    print('Printing something')
    numpy.show_config()
    return "return value"