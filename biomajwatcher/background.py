'''
from celery import Celery
from celery.task import task
'''
import logging
'''
from biomaj.config import BiomajConfig
from biomaj.bank import Bank

class FakeCelery(object):

  def task(self, klass):
      return klass


app = FakeCelery()

queue = None
if BiomajConfig.global_config.has_option('GENERAL', 'celery.queue'):
    queue = BiomajConfig.global_config.get('GENERAL', 'celery.queue')

broker = None
if BiomajConfig.global_config.has_option('GENERAL', 'celery.broker'):
    broker =  BiomajConfig.global_config.get('GENERAL', 'celery.broker')

if queue is not None and broker is not None:
    app = Celery(queue, broker=broker)
else:
    logging.warn('celery fields not defined in configuration')






@app.task
def update(name, options=None, global_properties='global.properties'):
  bank = Bank(name)
  if options is not None and options['fromscratch']:
    bank.options.fromscratch = options['fromscratch']
  res = bank.update()
  return res

@app.task
def remove(name, release, global_properties='global.properties'):
  bank = Bank(name)
  res = bank.remove(release)
  return 1
'''
