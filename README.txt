# biomaj-watcher

Web interface for biomaj

License: AGPL

in development with biomaj

# Development - build web app

in biomajwatcher/webapp:

    npm install -g grunt
    npm install -g bower
    grunt install
    bower install
    grunt

# Running

Dev: pserve development.ini

Prod: to be documented, should use gunicorn

 gunicorn -p /var/run/gunicorn_bmaj.pid --log-config=production.ini --paste production.ini &


## Admin user creation

python db/seed.py --config production.ini --user yyy --pwd xxxx


# Credits

Signin from http://bootsnipp.com/snippets/featured/google-style-login
