from celery import Celery

def make_celery(app):
    redis_url = 'redis://default:MTjiwpXRHbzKWTTbncmjutMjgLBOILrm@autorack.proxy.rlwy.net:16420/0'
    celery = Celery(
        app.import_name,
        backend=redis_url,
        broker=redis_url
    )
    celery.conf.update(app.config)
    return celery
