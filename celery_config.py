from celery import Celery

def make_celery(app):
    redis_url = 'redis://redis.railway.internal:6379/0'
    celery = Celery(
        app.import_name,
        backend=redis_url,
        broker=redis_url
    )
    celery.conf.update(app.config)
    celery.conf.task_soft_time_limit = 1800  # 30 minutos
    celery.conf.task_time_limit = 3600  # 60 minutos
    return celery
