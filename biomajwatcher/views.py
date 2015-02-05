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

from crontab import CronTab

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

@view_config(route_name='schedulebank', renderer='json', request_method='GET')
def getschedule(request):
  jobs = []
  user_cron  = CronTab(user=True)
  settings = request.registry.settings
  biomaj_cli = settings['biomaj_cli']
  for job in user_cron:
    if job.command.startswith(biomaj_cli):
      banks = job.command.split('--bank')[1].strip().split(',')
      jobs.append({'comment': job.comment, 'slices': str(job.slices), 'banks': banks})
  return jobs

@view_config(route_name='updateschedulebank', renderer='json', request_method='DELETE')
def unsetschedule(request):
  cron_name = request.matchdict['name']
  cron  = CronTab(user=True)
  cron.remove_all(comment=cron_name)
  cron.write()
  return []

@view_config(route_name='updateschedulebank', renderer='json', request_method='POST')
def setschedule(request):
  jobs = []
  cron_oldname = request.matchdict['name']
  cron = json.loads(request.body)
  cron_time = cron['slices']
  cron_banks = cron['banks']
  cron_newname = cron['comment']
  cron  = CronTab(user=True)
  cron.remove_all(comment=cron_oldname)
  settings = request.registry.settings
  global_properties = settings['global_properties']
  biomaj_cli = settings['biomaj_cli']

  cmd = biomaj_cli+" --config "+global_properties+" --update --bank "+cron_banks
  job = cron.new(command=cmd, comment=cron_newname)
  job.setall(cron_time)
  cron.write()
  return []


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


def can_edit_bank(request, bank):
  '''
  Checks if user can edit bank

  :param request: Request
  :type request: Request
  :param name: Bank
  :type name: :class:`biomaj.bank.Bank.bank`
  '''
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



def get_block(configparser, block):
  '''
  Get blocks
  '''
  blocks = [x.strip() for x in block.split(',')]
  res = []
  for block in blocks:
    res.append({
      'name': block,
      'metas': get_metas(configparser,configparser.get('GENERAL',block+'.db.post.process') )
    })
  return res



def get_metas(configparser, metas):
  '''
  Get meta processes
  '''
  meta_procs = [x.strip() for x in metas.split(',')]
  res = []
  for meta in meta_procs:
    res.append({
     'name': meta,
     'procs': get_procs(configparser, configparser.get('GENERAL',meta))
  })
  return res

def get_option(configparser, option):
  if configparser.has_option('GENERAL', option):
    return configparser.get('GENERAL', option)
  else:
    return None

def get_procs(configparser, proc):
  '''
  Get blocks
  '''
  meta_procs = [x.strip() for x in proc.split(',')]
  res = []
  for proc in meta_procs:
    res.append({
      'name': get_option(configparser, proc+'.name'),
      'desc': get_option(configparser, proc+'.desc'),
      'cluster': get_option(configparser, proc+'.cluster'),
      'native': get_option(configparser, proc+'.native'),
      'docker': get_option(configparser, proc+'.docker'),
      'type': get_option(configparser, proc+'.type'),
      'exe': get_option(configparser, proc+'.exe'),
      'args': get_option(configparser, proc+'.args'),
      'format': get_option(configparser, proc+'.format'),
      'types': get_option(configparser, proc+'.types'),
      'tags': get_option(configparser, proc+'.tags'),
      'files': get_option(configparser, proc+'.files')
    })
  return res

@view_config(route_name='bankconfig', renderer='json', request_method='GET')
def bank_config(request):
  bank = Bank(request.matchdict['id'], no_log=True)
  if not can_edit_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')

  configparser = bank.config.config_bank
  config = {}
  for item,value in configparser.items('GENERAL'):
    if item == 'db.remove.process':
      metas = get_metas(configparser, value)
      config[item] = metas
    elif item == 'db.pre.process':
      metas = get_metas(configparser, value)
      config[item] = metas
    elif item == 'blocks':
      config[item] = get_block(configparser, value)
    elif item == 'depends':
      depends = [x.strip() for x in value.split(',')]
      config[item] = []
      for dep in depends:
        dep_item = { 'name': dep, 'files.move': None }
        files_move = get_option(configparser, dep+'.files.move')
        if files_move:
          dep_item['files.move'] = files_move
        config[item].append(dep_iem)
    elif item == 'no.extract':
      if value == "true" or value == "1":
        config[item] = True
      else:
        config[item] = False
    elif item == 'protocol' and 'multi' == get_option(configparser, 'protocol'):
      config['multi'] = []
      do_match = True
      match = 0
      while(do_match):
        match_path = configparser.get('GENERAL', 'remote.files'+str(match)+'.path')
        if match_path:
          config[item].append({
            'protocol':configparser.get('GENERAL', 'remote.files'+str(match)+'.protocol'),
            'server':configparser.get('GENERAL', 'remote.files'+str(match)+'.server'),
            'path': match_path,
            'name':configparser.get('GENERAL', 'remote.files'+str(match)+'.name'),
            'method':configparser.get('GENERAL', 'remote.files'+str(match)+'.method'),
            'credentials':configparser.get('GENERAL', 'remote.files'+str(match)+'.credentials')
          })
          match += 1
        else:
          do_match = False
    else:
      config[item] = configparser.get('GENERAL', item)
  return config

def set_procs(props, procs):
  proc_names = []
  for proc in procs:
      proc_names.append(proc['name'])
      props[proc['name']+'.name'] =  proc['name']
      props[proc['name']+'.desc'] =  proc['desc']
      props[proc['name']+'.cluster'] =  proc['cluster']
      props[proc['name']+'.native'] =  proc['native']
      props[proc['name']+'.docker'] =  proc['docker']
      props[proc['name']+'.exe'] =  proc['exe']
      props[proc['name']+'.args'] =  proc['args']
      props[proc['name']+'.format'] =  proc['format']
      props[proc['name']+'.types'] =  proc['types']
      props[proc['name']+'.files'] =  ','.join(proc['files'])
  return proc_names

def set_metas(props, metas):
  meta_names = []
  for meta in metas:
      meta_names.append(meta['name'])
      proc_names = set_procs(props, meta['procs'])
      props[meta['name']] = ','.join(meta_names)
  return meta_names


def set_blocks(props, blocks):
    block_name = []
    for block in blocks:
        block_name.append(block['name'])
        meta_names = set_metas(props, block['metas'])
        props[block['name']] = ','.join(meta_names)
    return block_names

@view_config(route_name='bankconfig', renderer='json', request_method='POST')
def update_bank_config(request):
  props = json.loads(request.body)

  bank = Bank(request.matchdict['id'], no_log=True)
  if not can_edit_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')

  configparser = bank.config.config_bank
  if key == 'no.extract':
    if props['no.extract']:
      props['no.extract'] = 'true'
    else:
      props['no.extract'] = 'false'
  if 'depends' in props and props['depends']:
    depnames = []
    for dep in props['depends']:
      depnames.append(dep['name'])
      props[dep['name']+'.files.move'] = dep['files.move']
    props['depends'] = ','.join(depnames)
  if 'multi' in props and props['multi']:
    count = 0
    for m in props['multi']:
      props['remote.file.'+str(count)+'name'] = m['name']
      props['remote.file.'+str(count)+'method'] = m['method']
      props['remote.file.'+str(count)+'protocol'] = m['protocol']
      props['remote.file.'+str(count)+'server'] = m['server']
      props['remote.file.'+str(count)+'path'] = m['path']
      props['remote.file.'+str(count)+'credentials'] = m['credentials']
      count += 1
    del props['multi']
  if 'db.pre.process' in props and props['db.pre.process']:
      metas = set_metas(props, props['db.pre.process'])
      props['db.pre.process'] = ','.join(metas)
  if 'db.remove.process' in props and props['db.remove.process']:
      metas = set_metas(props, props['db.remove.process'])
      props['db.remove.process'] = ','.join(metas)
  if 'blocks' in props and props['blocks']:
      blocks = set_blocks(props, props['blocks'])
      props['blocks'] = ','.join(blocks)

  # loop over key/values and update configparser, then write to file


  print str(props)
  return {'msg': 'bank created/updated'}


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
