from flask import Flask, request, jsonify
import whisper
import os
from celery_config import make_celery

app = Flask(__name__)
celery = make_celery(app)
model = whisper.load_model("base")

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video = request.files['video']
    temp_video_path = os.path.join('/tmp', video.filename)
    video.save(temp_video_path)
    
    task = transcribe_video_task.delay(temp_video_path)
    return jsonify({'task_id': task.id}), 202

@celery.task
def transcribe_video_task(temp_video_path):
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
