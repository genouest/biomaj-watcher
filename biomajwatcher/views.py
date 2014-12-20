from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPForbidden
from pyramid.security import remember, forget
from pyramid.renderers import render_to_response
from pyramid.response import Response, FileResponse

import os
import json
from bson import json_util
from bson.objectid import ObjectId
from bson.errors import InvalidId
import bcrypt


from biomaj.bank import Bank
from biomaj.config import BiomajConfig
from biomaj.user import BmajUser

import background


def load_config(request):
  if BiomajConfig.global_config is None:
    settings = request.registry.settings
    global_properties = settings['global_properties']
    BiomajConfig.load_config(global_properties)

def is_admin(request):
  settings = request.registry.settings
  user = is_authenticated(request)
  is_admin = False
  if user:
      if user['id'] in settings['admin'].split(','):
        is_admin = True
  return is_admin


def get_session_from_release(bank, release):
  '''
  Find matching session for release
  '''
  session = None
  # Search production release matching release
  for prod in bank['production']:
    if prod['release'] == release or prod['prod_dir'] == release:
      # Search session related to this production release
      for s in bank['sessions']:
        if s['id'] == prod['session']:
          session = s
          break
      break
  return session

def get_files_matching_request(banks, selectedformat=None, selectedtype=None):
  '''
  Parse bank lists and production releases, and return a list of production releases with files per format
  '''
  res = []
  for bank in banks:
    for prod in bank['production']:
      session = get_session_from_release(bank, prod['release'])
      for sformat in session['formats'].keys():
        if selectedformat is not None and sformat != selectedformat:
          del session['formats'][sformat]
        else:
          if selectedtype is not None:
            for files in session['formats'][sformat]:
              if selectedtype not in files['types']:
                del files

      prod['files'] = session['formats']
      prod['bank'] = bank['name']
      res.append(prod)
  return res

@view_config(route_name='search_format_type', renderer='json', request_method='GET')
def search_format_type(request):
  bank_format = request.matchdict['format']
  bank_type = request.matchdict['type']
  banks = Bank.search([bank_format], [bank_type],True)
  return get_files_matching_request(banks, bank_format, bank_type)

@view_config(route_name='search_format', renderer='json', request_method='GET')
def search_format(request):
  bank_format = request.matchdict['format']
  banks = Bank.search([bank_format], [],True)
  return get_files_matching_request(banks, bank_format, None)

@view_config(route_name='search_type', renderer='json', request_method='GET')
def search_type(request):
  bank_type = request.matchdict['type']
  banks = Bank.search([], [bank_type],True)
  return get_files_matching_request(banks, None, bank_type)

@view_config(route_name='search', renderer='json', request_method='GET')
def search(request):
  req = request.params.get('q')
  return Bank.searchindex(req)

@view_config(route_name='stat', renderer='json', request_method='GET')
def stat(request):
  stats = Bank.get_banks_disk_usage()
  return stats

@view_config(route_name='home')
def my_view(request):
  #return {'project': 'biomaj-watcher'}
  return HTTPFound(request.static_url('biomajwatcher:webapp/app/'))

def can_read_bank(request, bank):
  '''
  Checks if anonymous or authenticated user can read bank

  :param request: Request
  :type request: Request
  :param name: Bank
  :type name: :class:`biomaj.bank.Bank.bank`
  '''
  if bank['properties']['visibility'] == 'public':
    return True
  user_id = request.authenticated_userid
  if user_id is None:
    return False
  settings = request.registry.settings
  if user_id in settings['admin'].split(',') or user_id == bank['properties']['owner']:
    return True
  return False


def is_authenticated(request):
  user_id = request.authenticated_userid
  if user_id:
    return BmajUser(user_id).user
  else:
    return None

def check_user_pw(username, password):
    """checks for plain password vs hashed password in database"""
    if not password or password == '':
        return None
    user = BmajUser(username)
    if not user:
        return False
    if user.check_password(password):
        return user.user
    else:
        return None

@view_config(route_name='banklocked', renderer='json', request_method='GET')
def bank_locked(request):
  bank = Bank(request.matchdict['id'], no_log=True)
  if not can_read_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')

  if bank.is_locked():
    return {'status': 1}
  else:
    return {'status': 0}

@view_config(route_name='bankstatus', renderer='json', request_method='GET')
def bank_status(request):
  bank = Bank(request.matchdict['id'], no_log=True)
  if not can_read_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')

  if 'status' not in bank.bank:
    return HTTPNotFound('no current status')
  return bank.get_status()


@view_config(route_name='is_auth', renderer='json', request_method='GET')
def is_auth_user(request):
  settings = request.registry.settings
  user = is_authenticated(request)
  is_admin = False
  if user:
      if user['id'] in settings['admin'].split(','):
        is_admin = True
  return { 'user': user, 'is_admin': is_admin }

@view_config(route_name='auth', renderer='json', request_method='POST')
def auth_user(request):
  #load_config(request)
  settings = request.registry.settings
  user_id = request.matchdict['id']
  try:
    form = json.loads(request.body, encoding=request.charset)
    password = form['password']
    user = check_user_pw(user_id, password)
  except Exception as e:
    user = is_authenticated(request)
  is_admin = False
  if user:
      if user['id'] in settings['admin'].split(','):
        is_admin = True
      headers = remember(request, user['id'])
      request.response.headerlist.extend(headers)
  return { 'user': user, 'is_admin': is_admin }

@view_config(route_name='logout', renderer='json', request_method='GET')
def logout(request):
  headers = forget(request)
  request.response.headerlist.extend(headers)
  return { 'user': None, 'is_admin': False }

@view_config(route_name='bankreleaseremove', renderer='json', request_method='DELETE')
def bank_release_remove(request):
  background.remove.delay(request.matchdict['id'], request.matchdict['release'])
  return {'msg': 'Remove operation in progress'}

@view_config(route_name='bankdetails', renderer='json', request_method='PUT')
def bank_update(request):
  options = {}
  try:
    fromscratch = json.loads(request.body)
    fromscratch = fromscratch['fromscratch']
    if int(fromscratch) == 1:
      options['fromscratch'] = True
    else:
      options['fromscratch'] = False
  except:
    options['fromscratch'] = False
  background.update.delay(request.matchdict['id'],options=options)
  return {'msg': 'Update operation in progress'}

@view_config(route_name='bankdetails', renderer='json', request_method='GET')
def bank_details(request):
  '''
  Get a bank

  :param request: HTTP params
              matchdict keys:
                'id' Bank name
  :type request: IMultiDict
  :return: json - Bank
  '''
  #load_config(request)
  bank = Bank(request.matchdict['id'], no_log=True)
  if not can_read_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')
  return bank.bank

@view_config(route_name='bank', renderer='json', request_method='GET')
def bank_list(request):
  #load_config(request)
  banks = Bank.list()
  bank_list = []
  for bank in banks:
    if can_read_bank(request, bank):
        bank_list.append(bank)
  return bank_list

@view_config(route_name='user', renderer='json', request_method='GET')
def user_list(request):
  if not is_admin(request):
    return HTTPForbidden('Not authorized to access this resource')
  users = BmajUser.list()
  user_list = []
  for user in users:
    user_list.append(user)
  return user_list

@view_config(route_name='user_banks', renderer='json', request_method='GET')
def user_banks(request):
  if not is_admin(request):
    return HTTPForbidden('Not authorized to access this resource')
  banks = BmajUser.user_banks(request.matchdict['id'])
  bank_list = []
  for bank in banks:
    bank_list.append(bank)
  return bank_list

@view_config(route_name='sessionlog', request_method='GET')
def session_log(request):
  bank = Bank(request.matchdict['id'], no_log=True)
  if not can_read_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')
  log_file = None
  last_update = bank.bank['last_update_session']

  for session in bank.bank['sessions']:
    if session['id'] == float(request.matchdict['session']):
      log_file = session['log_file']
      break
  if log_file is None or not os.path.exists(log_file):
    return HTTPNotFound('No matching log file found')
  else:
    response = FileResponse(log_file,
                                request=request,
                                content_type='text/plain')
    return response
