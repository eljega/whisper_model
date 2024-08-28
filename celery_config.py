from celery import Celery

def make_celery(app):
    redis_url = 'redis://autorack.proxy.rlwy.net:16420/0'  # Actualiza con la URL correcta
    celery = Celery(
        app.import_name,
        backend=redis_url,
        broker=redis_url
    )
    celery.conf.update(app.config)

    # Configuración de tiempos de espera
    celery.conf.update({
        'task_soft_time_limit': 3600,  # 1 hora para tareas largas
        'task_time_limit': 7200,  # 2 horas como límite máximo
    })

    return celery
