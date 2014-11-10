from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
import json
from bson import json_util
from bson.objectid import ObjectId
from bson.errors import InvalidId

from biomaj.bank import Bank
from biomaj.config import BiomajConfig

def load_config(request):
  if BiomajConfig.global_config is None:
    settings = request.registry.settings
    global_properties = settings['global_properties']
    print global_properties
    BiomajConfig.load_config(global_properties)

@view_config(route_name='home')
def my_view(request):
  #return {'project': 'biomaj-watcher'}
  return HTTPFound(request.static_url('biomajwatcher:webapp/app/'))


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
  load_config(request)
  bank = Bank(request.matchdict['id'])
  return bank.bank

@view_config(route_name='bank', renderer='json', request_method='GET')
def bank_list(request):
  load_config(request)
  banks = Bank.list()
  bank_list = []
  for bank in banks:
    bank_list.append(bank)
  return bank_list
