from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.security import authenticated_userid, remember, forget
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

def load_config(request):
  if BiomajConfig.global_config is None:
    settings = request.registry.settings
    global_properties = settings['global_properties']
    BiomajConfig.load_config(global_properties)

@view_config(route_name='home')
def my_view(request):
  #return {'project': 'biomaj-watcher'}
  return HTTPFound(request.static_url('biomajwatcher:webapp/app/'))

def is_authenticated(request):
  user_id = authenticated_userid(request)
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
  bank = Bank(request.matchdict['id'])
  return bank.bank

@view_config(route_name='bank', renderer='json', request_method='GET')
def bank_list(request):
  #load_config(request)
  banks = Bank.list()
  bank_list = []
  for bank in banks:
    bank_list.append(bank)
  return bank_list

@view_config(route_name='sessionlog', request_method='GET')
def session_log(request):
  bank = Bank(request.matchdict['id'])
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
