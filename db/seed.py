'''
Initialise database content
'''


import argparse
import sys
from hashlib import sha1
from random import randint
import bcrypt

from biomaj.config import BiomajConfig

parser = argparse.ArgumentParser(description='Initialize database content.')
parser.add_argument('--config')
parser.add_argument('--rootpwd')
args = parser.parse_args()

if not args.config:
    print "config argument is missing"
    sys.exit(2)

BiomajConfig.load_config(args.config)

from biomaj.user import BmajUser
from hashlib import sha1

rootuser = BmajUser('admin')

if args.rootpwd:
    pwd = args.rootpwd
else:
    pwd = sha1("%s" % randint(1, 1e99)).hexdigest()

rootuser.create(pwd)



