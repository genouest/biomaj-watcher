from pyramid.config import Configurator
from pyramid.renderers import JSON
#from pyramid.security import authenticated_userid
from pyramid.events import BeforeRender
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy



import os
import sys
import json
import datetime
from bson import json_util
from bson.objectid import ObjectId

from biomaj.config import BiomajConfig


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    #config = Configurator(settings=settings)
    global_properties = settings.get(
               'global_properties', '/etc/biomaj/global.properties')
    if not os.path.exists(global_properties):
      print 'global.properties configuration field is not set'
      sys.exit(1)

    BiomajConfig.load_config(global_properties)

    settings['global_properties'] = global_properties

    config = Configurator(settings=settings)
    config.include('pyramid_chameleon')

    config.add_subscriber(before_render, BeforeRender)

    authentication_policy = AuthTktAuthenticationPolicy('seekrit',
        callback=None, hashalg='sha512')
    authorization_policy = ACLAuthorizationPolicy()

    config.set_authentication_policy(authentication_policy)
    config.set_authorization_policy(authorization_policy)




    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('app', 'biomajwatcher:webapp/app')
    config.add_route('home', '/')

    config.add_route('user','/user')
    config.add_route('user_banks','/user/{id}/banks')

    config.add_route('bank', '/bank')
    config.add_route('bankdetails', '/bank/{id}')
    config.add_route('bankstatus', '/bank/{id}/status')
    config.add_route('sessionlog', '/bank/{id}/log/{session}')

    config.add_route('search', '/search')

    config.add_route('search_format', '/search/format/{format}')
    config.add_route('search_format_type', '/search/format/{format}/type/{type}')
    config.add_route('search_type', '/search/type/{type}')

    config.add_route('stat', '/stat')

    config.add_route('is_auth', '/auth')
    config.add_route('auth', '/auth/{id}')
    config.add_route('logout', '/logout')

    config.scan()

    # automatically serialize bson ObjectId and datetime to Mongo extended JSON
    json_renderer = JSON()
    def pymongo_adapter(obj, request):
        return json_util.default(obj)
    json_renderer.add_adapter(ObjectId, pymongo_adapter)
    json_renderer.add_adapter(datetime.datetime, pymongo_adapter)

    config.add_renderer('json', json_renderer)


    return config.make_wsgi_app()

def before_render(event):
    event["username"] = event['request'].authenticated_userid
