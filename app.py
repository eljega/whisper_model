import os
import boto3
import whisper
from flask import Flask, request, jsonify
from celery_config import make_celery

app = Flask(__name__)
celery = make_celery(app)
model = whisper.load_model("base")

# Ruta del bucket en S3
BUCKET_NAME = "clipgenaieljega"

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video = request.files['video']
    s3_key = f"uploads/{video.filename}"
    
    try:
        # Subir el archivo a S3
        s3 = boto3.client('s3')
        s3.upload_fileobj(video, BUCKET_NAME, s3_key)
        print(f"Archivo subido a S3: {s3_key}")
    except Exception as e:
        return jsonify({'error': f'Error uploading to S3: {str(e)}'}), 500
    
    # Crear la tarea de transcripción
    task = transcribe_video_task.delay(s3_key)
    return jsonify({'task_id': task.id}), 202

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_video_task(self, s3_key):
    s3 = boto3.client('s3')
    local_path = f"/tmp/{os.path.basename(s3_key)}"
    
    try:
        # Descargar desde S3
        s3.download_file(BUCKET_NAME, s3_key, local_path)
        print(f"Archivo descargado desde S3: {local_path}")
        
        # Verificar que el archivo ha sido descargado correctamente
        if not os.path.exists(local_path):
            raise RuntimeError(f"El archivo no existe: {local_path}")
        
        if os.path.getsize(local_path) == 0:
            raise RuntimeError(f"El archivo está vacío: {local_path}")
        
        # Transcribir
        print(f"Comenzando la transcripción del archivo: {local_path}")
        result = model.transcribe(local_path)
        
    except Exception as exc:
        # Reintentar en caso de error
        print(f"Error durante la transcripción o descarga: {str(exc)}")
        raise self.retry(exc=exc)
    
    finally:
        # Eliminar el archivo temporal después de la transcripción
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Archivo temporal eliminado: {local_path}")
    
    return result['segments']

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    task = transcribe_video_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {'state': task.state}
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result}
    elif task.state == 'FAILURE':
        response = {'state': task.state, 'error': str(task.info)}
    else:
        response = {'state': task.state, 'error': 'Unknown state'}
    
    print(f"Estado de la tarea {task_id}: {response}")
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
