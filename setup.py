import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(name='biomajwatcher',
      version='3.1.5',
      description='biomaj-watcher',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Programming Language :: Python :: 3",
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
      install_requires=requirements,
      tests_require=requirements,
      test_suite="biomajwatcher",
      entry_points="""\
      [paste.app_factory]
      main = biomajwatcher:main
      """,
      )
