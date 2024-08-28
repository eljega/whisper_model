from celery import Celery

def make_celery(app):
    redis_url = 'redis://junction.proxy.rlwy.net:59093/0'
    celery = Celery(
        app.import_name,
        backend=redis_url,
        broker=redis_url
    )
    celery.conf.update(app.config)
    return celery
