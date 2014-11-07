from pyramid.config import Configurator
from pyramid.renderers import JSON

import os
import sys
import json
import datetime
from bson import json_util
from bson.objectid import ObjectId

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    #config = Configurator(settings=settings)
    global_properties = settings.get(
               'global_properties', '/etc/biomaj/global.properties')
    if not os.path.exists(global_properties):
      print 'global.properties configuration field is not set'
      sys.exit(1)
    settings['global_properties'] = global_properties
    config = Configurator(settings=settings)
    config.include('pyramid_chameleon')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('app', 'biomajwatcher:webapp/app')
    config.add_route('home', '/')

    config.add_route('bank', '/bank')

    config.scan()

    # automatically serialize bson ObjectId and datetime to Mongo extended JSON
    json_renderer = JSON()
    def pymongo_adapter(obj, request):
        return json_util.default(obj)
    json_renderer.add_adapter(ObjectId, pymongo_adapter)
    json_renderer.add_adapter(datetime.datetime, pymongo_adapter)

    config.add_renderer('json', json_renderer)


    return config.make_wsgi_app()
