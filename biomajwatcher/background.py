from celery import Celery
from celery.task import task

from biomaj.config import BiomajConfig
from biomaj.bank import Bank

queue = BiomajConfig.global_config.get('GENERAL', 'celery.queue')
broker =  BiomajConfig.global_config.get('GENERAL', 'celery.broker')

app = Celery(queue, broker=broker)






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
