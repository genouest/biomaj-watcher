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
parser.add_argument('--user')
parser.add_argument('--pwd')
parser.add_argument('--email')
args = parser.parse_args()

if not args.config:
    print "config argument is missing"
    sys.exit(2)

BiomajConfig.load_config(args.config)

from biomaj.user import BmajUser
from hashlib import sha1

if not args.user:
    print 'user parameter is missing'
    sys.exit(1)

rootuser = BmajUser(args.user)

if args.pwd:
    pwd = args.pwd
else:
    pwd = sha1("%s" % randint(1, 1e99)).hexdigest()

if not args.email:
  rootuser.create(pwd)
else:
  rootuser.create(pwd,args.email)



