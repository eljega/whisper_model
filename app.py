from flask import Flask, request, jsonify
import boto3
import os
from celery_config import make_celery
from botocore.exceptions import NoCredentialsError

app = Flask(__name__)
celery = make_celery(app)
model = whisper.load_model("base")

# Configura tu cliente S3
s3 = boto3.client('s3')

BUCKET_NAME = 'clipgenaieljega'

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video = request.files['video']
    temp_video_path = os.path.join('/tmp', video.filename)
    video.save(temp_video_path)

    # Subir el archivo a S3
    try:
        s3.upload_file(temp_video_path, BUCKET_NAME, video.filename)
        s3_video_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{video.filename}"
        os.remove(temp_video_path)  # Eliminar el archivo temporal localmente

        task = transcribe_video_task.delay(s3_video_url)
        return jsonify({'task_id': task.id}), 202
    except NoCredentialsError:
        return jsonify({'error': 'Credenciales de AWS no encontradas'}), 500

@celery.task
def transcribe_video_task(s3_video_url):
    # Descargar el archivo desde S3
    temp_video_path = f"/tmp/{os.path.basename(s3_video_url)}"
    s3.download_file(BUCKET_NAME, os.path.basename(s3_video_url), temp_video_path)

    if not os.path.exists(temp_video_path):
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
