# biomaj-watcher

Web interface for biomaj (https://github.com/genouest/biomaj) 

# License

AGPL

# Requirements

biomaj3

Javascript dependencies are downloaded help with bower (see next).
Dependencies are listed in biomajwatcher/webapp/bower.json.

# Build web app

Install npm (apt-get install npm/ yum install npm)

in biomajwatcher/webapp

    npm install -g bower
    bower install

# Configuration

Configuration is done in development.ini or production.ini

    global_properties = PATH_TO_BIOMAJ_global.properties
    
    # List of user ids with admin priviledges.
    # Users need to be create or be ldap users if ldap
    # is configured in global.properties
    admin = admin, jdoe
    
    # Celery configuration over mongodb, mongodb url
    BROKER_URL = mongodb://localhost/biomaj_celery


# Running

## Development

    pserve development.ini

## Production

    gunicorn -p /var/run/gunicorn_bmaj.pid --log-config=production.ini --paste production.ini &


Web server will start to listen on port 6543 by default. Update ini files to
customize web configuration.


# Background processing (Optional)

To allow banks update/removal by authenticated user, Celery is needed. Celery can run on same node, or multiple distant ones to execute bank updates.

    pceleryd development.ini/production.ini

One can use flower to monitor celery.

# User creation

python db/seed.py --config production.ini --user yyy --pwd xxxx

# API / REST interface

The old API interface (/BmajWatcher/GET) is still available. A new REST
interface is available but we kept the old one for compatibility for other
tools. The old interface does not take advantage of the new features however.

# Don't like the color? Need your logo?

You can easily customize the look of the watcher. Theme is pure CSS and CSS giles are available in directroy biomajwatcher/webapp/app/styles. CSS are based on Bootstrap 3. You may also need to override some directives from *app.css* according to your theme (font color...)

If you want to customize the theme, create a new theme CSS file (with an other name), and update the <link> reference to "_path_to_styles_/theme.css" to your new file in biomajwatcher/webapp/app/index.html.

In index.html you can also add your logol, chnage header etc...

# REST API

    /bank  : list of banks
    /bank/:id : details of bank
    /bank/:id/status: current status of the bank
    /bank/:id/config: properties of the bank
    /bank/:id/log/:sessionid : log file of the session
    /search: search in banks with GET parameter "q=query", query follows Lucene syntax
    /search/format/:format: get banks having format
    /search/type/:type: get banks having type
    /search/format/:format/type/:type : get banks having format and type
    /stat : get banks disk usage

# Credits

Signin image from http://bootsnipp.com/snippets/featured/google-style-login
