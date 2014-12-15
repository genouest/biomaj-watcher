from celery import Celery
from celery.task import task

from biomaj.config import BiomajConfig
from biomaj.bank import Bank

queue = BiomajConfig.global_config.get('GENERAL', 'celery.queue')
broker =  BiomajConfig.global_config.get('GENERAL', 'celery.broker')

app = Celery(queue, broker=broker)

@app.task
def update(name):
  bank = Bank(name, no_log=True)
  res = bank.update()
  return res

@app.task
def remove(name, release):
  return 1
