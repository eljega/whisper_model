from celery import Celery

def make_celery(app):
    redis_url = 'redis://default:MTjiwpXRHbzKWTTbncmjutMjgLBOILrm@autorack.proxy.rlwy.net:16420/0'
    celery = Celery(
        app.import_name,
        backend=redis_url,
        broker=redis_url
    )
    celery.conf.update(app.config)
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_time_limit=7200,  # 2 horas
        task_soft_time_limit=7140,  # Un poco menos de 2 horas
    )
    return celery
