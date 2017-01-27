from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPForbidden
from pyramid.security import remember, forget
from pyramid.response import FileResponse

import os
import sys
import json
from bson import json_util
import copy
import hashlib
import datetime
import requests
import logging

from biomaj.bank import Bank
from biomaj_core.config import BiomajConfig

if sys.version < '3':
    import ConfigParser as configparser
else:
    import configparser


class Options(object):
    def __init__(self, d):
        self.__dict__ = d

    def get_option(self, option):
        """
        Gets an option if present, else return None
        """
        if hasattr(self, option):
            return getattr(self, option)
        return None


def load_config(request):
    if BiomajConfig.global_config is None:
        settings = request.registry.settings
        global_properties = settings['global_properties']
        BiomajConfig.load_config(global_properties)


def is_admin(request, user=None):
    # settings = request.registry.settings
    if not user:
        user = is_authenticated(request)
    is_user_admin = False
    if user:
        admins = BiomajConfig.global_config.get('GENERAL', 'admin')
        if admins and user['id'] in admins.split(','):
            is_user_admin = True
    return is_user_admin


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


@view_config(route_name='ping', renderer='json', request_method='GET')
def ping(request):
    return {'msg': 'pong'}


@view_config(route_name='schedulebank', renderer='json', request_method='GET')
def getschedule(request):
    r = requests.get(request.registry.settings['watcher_config']['web']['local_endpoint'] + '/api/cron/jobs')
    if not r.status_code == 200:
        logging.error("Failed to contact cron service")
        return []
    cron_jobs = r.json()
    return cron_jobs['cron']


@view_config(route_name='updateschedulebank', renderer='json', request_method='DELETE')
def unsetschedule(request):
    if not is_admin(request):
        return HTTPForbidden()
    r = requests.delete(request.registry.settings['watcher_config']['web']['local_endpoint'] + '/api/cron/jobs/' + request.matchdict['name'])
    if not r.status_code == 200:
        logging.error("Failed to contact cron service")
    return []


@view_config(route_name='updateschedulebank', renderer='json', request_method='POST')
def setschedule(request):
    if not is_admin(request):
        return HTTPForbidden()
    cron_oldname = request.matchdict['name']
    body = request.body
    if sys.version_info >= (3,):
        body = request.body.decode()
    cron = json.loads(body)
    cron_time = cron['slices']
    cron_banks = cron['banks']
    cron_newname = cron['comment']
    r = requests.delete(request.registry.settings['watcher_config']['web']['local_endpoint'] + '/api/cron/jobs/' + cron_oldname)
    if not r.status_code == 200:
        logging.error("Failed to contact cron service")
        return []

    cron_task = {
        'slices': cron_time,
        'banks': cron_banks,
        'comment': cron_newname
    }
    r = requests.post(request.registry.settings['watcher_config']['web']['local_endpoint'] + '/api/cron/jobs/' + cron_newname, json=cron_task)
    if not r.status_code == 200:
        logging.error("Failed to contact cron service")
        return []
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

    user = is_authenticated(request)
    if user is None:
        return False

    # settings = request.registry.settings
    if is_admin(request, user) or user['id'] == bank['properties']['owner']:
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
    user = is_authenticated(request)
    if user is None:
        return False

    # settings = request.registry.settings
    if is_admin(request, user) or user['id'] == bank['properties']['owner']:
        return True
    return False


def __api_authentification(request):
    config = request.registry.settings['watcher_config']
    auth = request.headers['Authorization'].split()
    user_id = auth[0]
    api_key = auth[1]
    r = requests.post(config['web']['local_endpoint'] + '/api/user/bind/user/' + user_id, json={'type': 'apikey', 'value': api_key})
    if not r.status_code == 200:
        return None
    user = r.json()['user']
    return user

def is_authenticated(request):
    '''
    Use session cookies or look at Authorization header with value:  USERNAME APIKEY
    '''
    config = request.registry.settings['watcher_config']
    if 'Authorization' in request.headers and request.headers['Authorization']:
        return __api_authentification(request)
    else:
        user_id = request.authenticated_userid
        if user_id:
            r = requests.get(config['web']['local_endpoint'] + '/api/user/info/user/' + user_id)
            if not r.status_code == 200:
                return None
            user = r.json()['user']
            return user
        else:
            return None


def check_user_pw(request, username, password):
    """checks for plain password vs hashed password in database"""
    config = request.registry.settings['watcher_config']
    if not password or password == '':
        return None
    r = requests.post(config['web']['local_endpoint'] + '/api/user/bind/user/' + username, json={'type': 'password', 'value': password})
    if not r.status_code == 200:
        logging.info("Wrong login for " + str(username))
        return None
    user = r.json()['user']
    return user

@view_config(route_name='api_banklocked', renderer='json', request_method='GET')
def api_bank_locked(request):
    return bank_lock(request)

@view_config(route_name='banklocked', renderer='json', request_method='GET')
def bank_locked(request):
    bank = Bank(request.matchdict['id'], no_log=True)
    if not can_read_bank(request, bank.bank):
        return HTTPForbidden('Not authorized to access this resource')

    if bank.is_locked():
        return {'status': 1}
    else:
        return {'status': 0}

@view_config(route_name='api_bankstatus', renderer='json', request_method='GET')
def api_bank_status(request):
    return bank_status(request)

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
    is_user_admin = False
    if user:
        if is_admin(request, user):
            is_user_admin = True
    return { 'user': user, 'is_admin': is_user_admin }


@view_config(route_name='auth', renderer='json', request_method='POST')
def auth_user(request):
  #load_config(request)
  settings = request.registry.settings
  user_id = request.matchdict['id']
  try:
    body = request.body
    if sys.version_info >= (3,):
        body = request.body.decode()
    form = json.loads(body, encoding=request.charset)
    password = form['password']
    user = check_user_pw(request, user_id, password)
  except Exception as e:
    logging.error('login exception: ' + str(e))
    user = is_authenticated(request)
  is_user_admin = False
  if user:
      admins = BiomajConfig.global_config.get('GENERAL', 'admin')
      if admins and user['id'] in admins.split(','):
        is_user_admin = True
      headers = remember(request, user['id'])
      request.response.headerlist.extend(headers)
  return { 'user': user, 'is_admin': is_user_admin }


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
        if block:
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
        if meta:
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

@view_config(route_name='api_bankconfig', renderer='json', request_method='GET')
def api_bank_config(request):
    return bank_config(request)

@view_config(route_name='bankconfig', renderer='json', request_method='GET')
def bank_config(request):
  if request.matchdict['id'] == 'new':
      return HTTPNotFound()
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
        if proc['files'] is None:
            proc['files'] = ''
        props[proc['name']+'.files'] =  ','.join(proc['files'])
    return proc_names


def set_metas(props, metas):
    meta_names = []
    for meta in metas:
        if meta['procs']:
            meta_names.append(meta['name'])
            proc_names = set_procs(props, meta['procs'])
            props[meta['name']] = ','.join(proc_names)
    return meta_names


def set_blocks(props, blocks):
    block_name = []
    for block in blocks:
        if block['metas']:
          block_name.append(block['name'])
          meta_names = set_metas(props, block['metas'])
          props[block['name']+".db.post.process"] = ','.join(meta_names)
    return block_name


@view_config(route_name='bankconfig', renderer='json', request_method='POST')
def update_bank_config(request):
  settings = request.registry.settings
  user = is_authenticated(request)
  if user is None:
      return HTTPForbidden('Not authenticated')

  name = request.matchdict['id']
  body = request.body
  if sys.version_info >= (3,):
    body = request.body.decode()
  props = json.loads(body)
  newprops = copy.deepcopy(props)

  if 'db.post.process' in newprops:
    del newprops['db.post.process']

  for key,value in props.iteritems():
    if key == 'no.extract':
      if props['no.extract']:
        newprops['no.extract'] = 'true'
      else:
        newprops['no.extract'] = 'false'
    elif 'depends' in props and props['depends']:
      depnames = []
      for dep in props['depends']:
        depnames.append(dep['name'])
        newprops[dep['name']+'.files.move'] = dep['files.move']
      newprops['depends'] = ','.join(depnames)
    elif 'multi' in props and props['multi']:
      count = 0
      for m in props['multi']:
        newprops['remote.file.'+str(count)+'name'] = m['name']
        newprops['remote.file.'+str(count)+'method'] = m['method']
        newprops['remote.file.'+str(count)+'protocol'] = m['protocol']
        newprops['remote.file.'+str(count)+'server'] = m['server']
        newprops['remote.file.'+str(count)+'path'] = m['path']
        newprops['remote.file.'+str(count)+'credentials'] = m['credentials']
        count += 1
      del newprops['multi']
    elif 'db.pre.process' in props and props['db.pre.process']:
        metas = set_metas(newprops, props['db.pre.process'])
        newprops['db.pre.process'] = ','.join(metas)
    elif 'db.remove.process' in props and props['db.remove.process']:
        metas = set_metas(newprops, props['db.remove.process'])
        newprops['db.remove.process'] = ','.join(metas)
    elif 'blocks' in props and props['blocks']:
        blocks = set_blocks(newprops, props['blocks'])
        newprops['blocks'] = ','.join(blocks)

  bank = None
  try:
    config = BiomajConfig(name, options)
  except Exception:
    # config does not exists, create it
    conf_dir = BiomajConfig.global_config.get('GENERAL', 'conf.dir')
    config_bank = ConfigParser.SafeConfigParser()
    config_bank.add_section('GENERAL')
    for key,value in newprops.iteritems():
      if value is None:
        value = ""
      config_bank.set('GENERAL',key,value)
    config_bank_file = open(os.path.join(conf_dir,name+".properties"),'w')
    config_bank.write(config_bank_file)
    config_bank_file.close()
  finally:
    bank = Bank(name, no_log=True)
    # Force owner to user logged in
    bank.set_owner(user['id'])
    test = bank.config.check()
    if not test:
      return {'msg': 'invalid configuration'}
  if bank is None or not can_edit_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')

  return {'msg': 'bank created/updated'}


@view_config(route_name='bankreleaseremove', renderer='json', request_method='DELETE')
def bank_release_remove(request):
    try:
        config = request.registry.settings['watcher_config']
        user = is_authenticated(request)
        if not user:
            return HTTPForbidden()
        options = {
            'proxy': config['web']['local_endpoint'],
            'bank': request.matchdict['id'],
            'release': request.matchdict['release'],
            'remove': True
        }

        headers = {}
        if user['apikey']:
            headers = {'Authorization': 'APIKEY ' + user['apikey']}
        r = requests.post(options['proxy'] + '/api/daemon', headers=headers, json={'options': options})
        if not r.status_code == 200:
            return {'msg': 'Failed to contact BioMAJ daemon'}
        result = r.json()
        status = result['status']
        msg = result['msg']

        return {'msg': str(msg), 'status': str(status)}

    except Exception as e:
        logging.error("Removal error:"+ str(e))
        return {'msg': str(e)}


@view_config(route_name='bankdetails', renderer='json', request_method='PUT')
def bank_update(request):
    try:
        config = request.registry.settings['watcher_config']

        user = is_authenticated(request)
        if not user:
            return HTTPForbidden()

        body = request.body
        if sys.version_info >= (3,):
            body = request.body.decode()
        form = json.loads(body)
        fromscratch = False
        if 'fromscratch' in form and int(form['fromscratch']) == 1:
            fromscratch = True

        options = {
            'proxy': config['web']['local_endpoint'],
            'bank': request.matchdict['id'],
            'fromscratch': fromscratch,
            'update': True
        }

        headers = {}
        if user['apikey']:
            headers = {'Authorization': 'APIKEY ' + user['apikey']}
        r = requests.post(options['proxy'] + '/api/daemon', headers=headers, json={'options': options})
        if not r.status_code == 200:
            return {'msg': 'Failed to contact BioMAJ daemon'}
        result = r.json()
        status = result['status']
        msg = result['msg']
        return {'msg': str(msg), 'status': str(status)}
    except Exception as e:
        logging.error("Update error:"+ str(e))
        return {'msg': str(e)}

@view_config(route_name='api_bankdetails', renderer='json', request_method='GET')
def api_bank_details(request):
    return bank_details(request)


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
    # load_config(request)
    bank = Bank(request.matchdict['id'], no_log=True)
    if not can_read_bank(request, bank.bank):
        return HTTPForbidden('Not authorized to access this resource')
    return bank.bank


@view_config(route_name='api_bank', renderer='json', request_method='GET')
def api_bank_list(request):
    return bank_list(request)


@view_config(route_name='bank', renderer='json', request_method='GET')
def bank_list(request):
    # load_config(request)
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

    r = requests.get(request.registry.settings['watcher_config']['web']['local_endpoint'] + '/api/user/info/user')
    if not r.status_code == 200:
        return HTTPNotFound()
    users = r.json()['users']
    return users


@view_config(route_name='user_banks', renderer='json', request_method='GET')
def user_banks(request):
    if not is_admin(request):
        return HTTPForbidden('Not authorized to access this resource')
    banks = Bank.user_banks(request.matchdict['id'])
    bank_list = []
    for bank in banks:
        bank_list.append(bank)
    return bank_list


@view_config(route_name='api_sessionlog', request_method='GET')
def api_session_log(request):
    return session_log(request)

@view_config(route_name='sessionlog', request_method='GET')
def session_log(request):
  bank = Bank(request.matchdict['id'], no_log=True)
  if not can_read_bank(request, bank.bank):
    return HTTPForbidden('Not authorized to access this resource')
  log_file = None
  last_update = bank.bank['last_update_session']
  log_file = bank.bank['status']['log_file']['status']
  if log_file is None or log_file == 'none':
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


def save_cache(use_cache, cache_file, content):
    if use_cache:
        return
    f = open(cache_file,'w')
    f.write(json.dumps(content))
    f.close()


@view_config(route_name='old_api', request_method='GET', renderer='json')
def old_api(request):
      types = []
      try:
        types = request.params.get('types')
        if types is None:
          types = []
        else:
          types = types.split('|')
      except Exception:
        types = []
      formats = []
      try:
        formats = request.params.get('formats')
        if formats is None:
          formats = []
        else:
          formats = formats.split('|')
      except Exception:
        formats= []

      requested_formats = list(formats)

      bank = None
      try:
        bank = request.params.get('banks')
      except Exception:
        bank = None

      lightmode = False
      try:
        lightmode = request.params.get('lightmode')
        if lightmode is None:
          lightmode = False
        else:
          lightmode = True
      except Exception:
        lightmode = False

      use_cache = False
      cache_dir = BiomajConfig.global_config.get('GENERAL', 'cache.dir')
      query = bank+str('_'.join(types))+str('_'.join(formats))+str(lightmode)
      if sys.version >= '3':
          query = query.encode('utf-8')
      md5query = hashlib.md5(query).hexdigest()
      if not os.path.exists(os.path.join(cache_dir,md5query)):
        # save cache
        use_cache = False
      else:
        # load from cache if not too old else save
        t = os.path.getmtime(os.path.join(cache_dir,md5query))
        cache_last_modified =  datetime.datetime.fromtimestamp(t)
        now = datetime.datetime.now()
        diff = now - cache_last_modified
        if diff.days > 1:
          # save cache
          use_cache = False
        else:
          # load from cache
          use_cache = True

      if use_cache:
        flisting = open(os.path.join(cache_dir,md5query),'r')
        data = flisting.read()
        section = json.loads(data)
        flisting.close()
        return section

      if bank is None or bank == 'all':
        # Get all banks with format/type
        _banks = Bank.search(formats, types, False)
        banks = []
        for _b in _banks:
          banks.append(Bank(_b['name'], no_log=True))
      else:
        # Get bank
        banks = [Bank(bank, no_log=True)]

      if bank is None:
        types = []
        formats = []
        for bank in banks:
          _bank = bank.bank
          if 'current' not in _bank:
            _bank['current'] = None
          if _bank['current']:
            for prod in _bank['production']:
              if prod['session'] == _bank['current']:
                for f in prod['formats']:
                  if f not in formats:
                    formats.append({"value": f})
                for t in prod['types']:
                  if t not in types:
                    types.append({"value": t})
                break
        if types:
          save_cache(use_cache, os.path.join(cache_dir,md5query), {"types": types})
          return {"types": types}
        if formats:
          save_cache(use_cache, os.path.join(cache_dir,md5query), {"formats": types})
          return {"formats": formats}


      # Else return bank(s)
      res = { "banks": []}
      for bank in banks:
        _bank = bank.bank
        if 'current' not in _bank:
          _bank['current'] = None
        bres = { "name": _bank['name'], "session_date": _bank['current'], "releases": {}, "db_type": ','.join(_bank['properties']['type'])}
        current_release = None

        # Very specific use case encountered after a migration
        if bank.config.get('dir.version') is None:
           continue

        for prod in _bank['production']:
          if _bank['current'] and prod['session'] == _bank['current']:
            current_release = prod['release']
          formats = []
          types = []
          release_dir = os.path.join(prod['data_dir'],
                            prod['dir_version'],
                            prod['prod_dir'])
          for f in prod['formats']:
            if requested_formats and f not in requested_formats:
              continue

            if lightmode:
              formats.append({"value": f})
            else:
              if os.path.exists(os.path.join(release_dir,'listingv1.'+f)):
                flisting = open(os.path.join(release_dir,'listingv1.'+f),'r')
                data = flisting.read()
                section = json.loads(data)
                section['value'] = section['name']
                flisting.close()
                formats.append(section)
              else:
                formats.append({"files": [], "name": f})
              #else:
              #  formats.append({"value": f})
          for t in prod['types']:
            types.append({"value": t})

          #if formats:
          bres['releases'][prod['release']] = { 'path': release_dir, 'formats': formats, 'db_type': types}
          #rel = { prod['release']: { 'path': release_dir, 'formats': formats, 'db_type': types}}
          #bres['releases'].append(rel)
        bres['current_release'] = current_release

        if bres['releases']:
          res['banks'].append(bres)

      save_cache(use_cache, os.path.join(cache_dir,md5query), res)
      return res
