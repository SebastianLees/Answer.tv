#Imports
from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from atv.security import groupfinder
import os
from .models import (
                     DBSession,
                     Base,
                     )

#All views must be stated here in order for view decorators to function
def main(global_config, **settings):
    """This function returns a Pyramid WSGI application."""
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    authn_policy = AuthTktAuthenticationPolicy('sosecret', callback=groupfinder,
                                                hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()
    memcache_server = os.environ.get('MEMCACHE_SERVERS')
    settings['beaker.cache.url'] = memcache_server
    config = Configurator(settings=settings,
                          root_factory='atv.models.RootFactory')
    config.include('pyramid_chameleon')
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.add_static_view('URL',
                           'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('panda', '/panda/authorize_upload')
    config.add_route('search', '/search')
    config.add_route('searchb', '/search/')
    config.add_route('answer', '/answer')
    config.add_route('delete', '/delete')
    config.add_route('denied', '/denied')
    config.add_route('explore', '/explore')
    config.add_route('exploreb', '/explore/')
    config.add_route('exploretrending', '/explore/trending')
    config.add_route('exploretrendingb', '/explore/trending/')
    config.add_route('explorelatest', '/explore/latest')
    config.add_route('explorelatestb', '/explore/latest/')
    config.add_route('exploreourpicks', '/explore/ourpicks')
    config.add_route('exploreourpicksb', '/explore/ourpicks/')
    config.add_route('vote', '/vote')
    config.add_route('deleteanswer', '/deleteanswer')
    config.add_route('stream', '/i/stream')
    config.add_route('streamb', '/i/stream/')
    config.add_route('streamlatest', '/i/stream/latest')
    config.add_route('streamlatestb', '/i/stream/latest/')
    config.add_route('streamtop', '/i/stream/top')
    config.add_route('streamtopb', '/i/stream/top/')
    config.add_route('edit', '/i/edit')
    config.add_route('editb', '/i/edit/')
    config.add_route('followunfollow', '/2x4b32cp')
    config.add_route('deletenotification', '/2x4b32qp')
    config.add_route('chanlatest', '/{channel}/latest')
    config.add_route('chanlatestb', '/{channel}/latest/')
    config.add_route('chanrising', '/{channel}/top')
    config.add_route('chanrisingb', '/{channel}/top/')
    config.add_route('ask', '/ask')
    config.add_route('signup', '/signup')
    config.add_route('signupb', '/signup/')
    config.add_route('login', '/login')
    config.add_route('loginb', '/login/')
    config.add_route('logout', '/logout')
    config.add_route('logoutb', '/logout/')
    config.add_route('privacy', '/privacy')
    config.add_route('privacyb', '/privacy/')
    config.add_route('terms', '/terms')
    config.add_route('termsb', '/terms/')
    config.add_route('blog', '/blog')
    config.add_route('blogb', '/blog/')
    config.add_route('admin', '/admin')
    config.add_route('adminb', '/admin/')
    config.add_route('copyright', '/copyright')
    config.add_route('copyrightb', '/copyright/')
    config.add_route('contact', '/contact')
    config.add_route('contactb', '/contact/')
    config.add_route('verify', '/verify')
    config.add_route('verifyb', '/verify/')
    config.add_route('reset', '/reset')
    config.add_route('resetb', '/reset/')
    config.add_route('ereset', '/ereset')
    config.add_route('eresetb', '/ereset/')
    config.add_route('verifyereset', '/ereset/{code}')
    config.add_route('verifyreset', '/reset/{code}')
    config.add_route('verifyemail', '/verify/{code}')
    config.add_route('following', '/{channel}/following')
    config.add_route('followingb', '/{channel}/following/')
    config.add_route('a_history', '/{channel}/history/a')
    config.add_route('a_historyb', '/{channel}/history/a/')
    config.add_route('history', '/{channel}/history/q')
    config.add_route('historyb', '/{channel}/history/q/')
    config.add_route('question', '/{channel}/{question}')
    config.add_route('questionb', '/{channel}/{question}/')
    config.add_route('channel', '/{channel}')
    config.add_route('channelb', '/{channel}/')
    
    #Create WSGI app
    config.scan()
    return config.make_wsgi_app()
