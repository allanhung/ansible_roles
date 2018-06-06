#!/bin/python

import urllib
import sys

host = sys.argv[3]
http_code = urllib.urlopen("http://{}:{}".format(host, "9200")).getcode()
if http_code == 200:
    sys.exit(0)
else:
    sys.exit(1)
