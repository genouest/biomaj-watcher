from pyramid.config import Configurator
from pyramid.renderers import JSON
#from pyramid.security import authenticated_userid
from pyramid.events import BeforeRender
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

import consul
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
import os
import sys
import json
import datetime
from bson import json_util
from bson.objectid import ObjectId

from biomaj_core.config import BiomajConfig
from biomaj_core.utils import Utils


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """

    config_file = 'config.yml'
    if 'BIOMAJ_CONFIG' in os.environ:
            config_file = os.environ['BIOMAJ_CONFIG']

    config = None
    with open(config_file, 'r') as ymlfile:
        config = yaml.load(ymlfile, Loader=Loader)
        Utils.service_config_override(config)

    BiomajConfig.load_config(config['biomaj']['config'])

    settings['watcher_config'] = config

    settings['global_properties'] = config['biomaj']['config']

    if config['consul']['host']:
        consul_agent = consul.Consul(host=config['consul']['host'])
        consul_agent.agent.service.register(
            'biomaj-watcher-static',
            service_id=config['consul']['id'],
            address=config['web']['hostname'],
            port=config['web']['port'],
            tags=[
                'biomaj',
                'watcher',
                'static',
                'traefik.backend=biomaj-watcher',
                'traefik.frontends.current.rule=PathPrefix:/app',
                'traefik.frontends.old.rule=PathPrefix:/bank',
                'traefik.enable=true'
            ]
        )
        consul_agent.agent.service.register(
            'biomaj-watcher-api',
            service_id=config['consul']['id'] + '_api',
            address=config['web']['hostname'],
            port=config['web']['port'],
            tags=[
                'biomaj',
                'watcher',
                'api',
                'traefik.backend=biomaj-watcher',
                'traefik.frontend.rule=PathPrefix:/api/watcher',
                'traefik.enable=true'
            ]
        )
        check = consul.Check.http(url='http://' + config['web']['hostname'] + ':' + str(config['web']['port']) + '/api/watcher', interval=20)
        consul_agent.agent.check.register(config['consul']['id'] + '_check', check=check, service_id=config['consul']['id'])

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
    config.add_route('ping', '/api/watcher')

    config.add_route('user','/api/watcher/user')
    config.add_route('user_banks','/api/watcher/user/{id}/banks')

    config.add_route('api_user','/user')
    config.add_route('api_user_banks','/user/{id}/banks')

    config.add_route('bank', '/bank')
    config.add_route('bankdetails', '/bank/{id}')
    config.add_route('banklocked', '/bank/{id}/locked')
    config.add_route('bankstatus', '/bank/{id}/status')
    config.add_route('bankconfig', '/bank/{id}/config')
    config.add_route('bankreleaseremove', '/bank/{id}/{release}')
    config.add_route('sessionlog', '/bank/{id}/log/{session}')

    config.add_route('api_bank', '/api/watcher/bank')
    config.add_route('api_bankdetails', '/api/watcher/bank/{id}')
    config.add_route('api_bankconfig', '/api/watcher/bank/{id}/config')
    config.add_route('api_banklocked', '/api/watcher/bank/{id}/locked')
    config.add_route('api_bankstatus', '/api/watcher/bank/{id}/status')
    config.add_route('api_sessionlog', '/api/watcher/bank/{id}/log/{session}')

    config.add_route('schedulebank','/schedule')
    config.add_route('updateschedulebank','/schedule/{name}')

    config.add_route('api_schedulebank','/api/watcher/schedule')
    config.add_route('api_updateschedulebank','/api/watcher/schedule/{name}')

    config.add_route('search', '/search')
    config.add_route('search_format', '/search/format/{format}')
    config.add_route('search_format_type', '/search/format/{format}/type/{type}')
    config.add_route('search_type', '/search/type/{type}')

    config.add_route('api_search', '/api/watcher/search')
    config.add_route('api_search_format', '/api/watcher/search/format/{format}')
    config.add_route('api_search_format_type', '/api/watcher/search/format/{format}/type/{type}')
    config.add_route('api_search_type', '/api/watcher/search/type/{type}')

    config.add_route('stat', '/stat')
    config.add_route('api_stat', '/api/watcher/stat')

    config.add_route('is_auth', '/auth')
    config.add_route('auth', '/auth/{id}')
    config.add_route('logout', '/logout')

    config.add_route('api_is_auth', '/api/watcher/auth')
    config.add_route('api_auth', '/api/watcher/auth/{id}')
    config.add_route('api_logout', '/api/watcher/logout')

    config.add_route('old_api', 'BmajWatcher/GET')

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
