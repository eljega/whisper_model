from flask import Flask, request, jsonify
import whisper
import os
import logging
from celery import Celery

# Configuración de la aplicación Flask
app = Flask(__name__)

# Configuración de Redis para Celery
redis_url = 'redis://default:MTjiwpXRHbzKWTTbncmjutMjgLBOILrm@autorack.proxy.rlwy.net:16420/0'
celery = Celery(app.name, broker=redis_url, backend=redis_url)

# Cargar el modelo Whisper
model = whisper.load_model("base")

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video = request.files['video']
    temp_video_path = os.path.join('/tmp', video.filename)  # Directorio temporal

    logging.info(f"Guardando el archivo en: {temp_video_path}")
    video.save(temp_video_path)
    
    # Verificar si el archivo fue guardado correctamente
    if not os.path.exists(temp_video_path):
        logging.error(f"El archivo no se guardó correctamente en: {temp_video_path}")
        return jsonify({'error': 'Failed to save video file'}), 500
    
    task = transcribe_video_task.delay(temp_video_path)
    return jsonify({'task_id': task.id}), 202

@celery.task
def transcribe_video_task(temp_video_path):
    logging.info(f"Transcribiendo el archivo: {temp_video_path}")
    
    # Verificar si el archivo aún existe antes de intentar procesarlo
    if not os.path.exists(temp_video_path):
        logging.error(f"El archivo no existe: {temp_video_path}")
        raise RuntimeError(f"El archivo no existe: {temp_video_path}")
    
    result = model.transcribe(temp_video_path)
    os.remove(temp_video_path)
    return result['segments']

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    task = transcribe_video_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state}
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result}
    else:
        response = {'state': task.state, 'error': str(task.info)}
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
