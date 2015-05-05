import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'pyramid==1.5.1',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'waitress',
    'pymongo',
    'py-bcrypt',
    'ldap3',
    'gunicorn',
    'gevent',
    'Celery==3.0.23',
    'celery-with-mongodb',
    'pyramid_celery==1.3',
    'python-crontab==1.9.2',
    'future'
    ]

setup(name='biomajwatcher',
      version='3.0.4',
      description='biomaj-watcher',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Olivier Sallou',
      author_email='olivier.sallou@irisa.fr',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="biomajwatcher",
      entry_points="""\
      [paste.app_factory]
      main = biomajwatcher:main
      """,
      )
