import os
import whisper
import ffmpeg
import boto3
from flask import Flask, request, jsonify
from celery_config import make_celery

# Configuración de S3
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
s3_client = boto3.client('s3')

# Configuración de la aplicación Flask
app = Flask(__name__)
celery = make_celery(app)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'video' not in request.files:
        return jsonify({'error': 'No se proporcionó ningún archivo de video'}), 400
    
    video = request.files['video']
    video_filename = video.filename
    temp_video_path = os.path.join('/tmp', video_filename)
    video.save(temp_video_path)
    
    # Subir el video a S3
    s3_client.upload_file(temp_video_path, BUCKET_NAME, video_filename)
    
    # Eliminar archivo temporal
    os.remove(temp_video_path)
    
    # Iniciar tarea de transcripción en segundo plano
    task = transcribe_video_task.delay(video_filename)
    return jsonify({'task_id': task.id}), 202

@celery.task
def transcribe_video_task(video_filename):
    # Descargar video desde S3
    temp_video_path = f'/tmp/{video_filename}'
    s3_client.download_file(BUCKET_NAME, video_filename, temp_video_path)
    
    # Cargar el modelo Whisper
    model = whisper.load_model("base")  # Cambia a "base" o "small" si es necesario
    result = model.transcribe(temp_video_path)
    
    # Crear archivo de subtítulos ASS
    ass_file_path = f'/tmp/{os.path.splitext(video_filename)[0]}.ass'
    create_ass_subtitle_file(result['segments'], ass_file_path)
    
    # Añadir subtítulos al video
    output_video_path = f'/tmp/video_con_subtitulos_{video_filename}'
    add_stylized_subtitles(temp_video_path, ass_file_path, output_video_path)
    
    # Subir video con subtítulos de vuelta a S3
    s3_output_key = f'video_con_subtitulos_{video_filename}'
    s3_client.upload_file(output_video_path, BUCKET_NAME, s3_output_key)
    
    # Eliminar archivos temporales
    os.remove(temp_video_path)
    os.remove(ass_file_path)
    os.remove(output_video_path)
    
    return {'video_url': f'https://{BUCKET_NAME}.s3.amazonaws.com/{s3_output_key}'}

def create_ass_subtitle_file(transcription, subtitle_file):
    ass_content = """
[Script Info]
Title: Subtítulos
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFF00,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0.00,0.00,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """
    
    for segment in transcription:
        start = format_time(segment['start'])
        end = format_time(segment['end'])
        text = segment['text'].strip()
        animated_text = (
            f"{{\\t(0,200,\\fscx50\\fscy50)\\t(200,300,\\fscx100\\fscy100)}}{text}"
            f"{{\\t({int((float(end.split(':')[-1]) - float(start.split(':')[-1])) * 1000) - 200},{int((float(end.split(':')[-1]) - float(start.split(':')[-1])) * 1000)},\\fscx50\\fscy50)}}"
        )
        ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{animated_text}\n"

    with open(subtitle_file, 'w') as f:
        f.write(ass_content)

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours}:{minutes:02}:{seconds:05.2f}"

def add_stylized_subtitles(video_file, subtitle_file, output_file):
    (
        ffmpeg
        .input(video_file)
        .output(output_file, vf=f'ass={subtitle_file}')
        .run(overwrite_output=True)
    )


@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    task = celery.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pendiente...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', ''),
            'result': task.info.get('result', '') if task.state == 'SUCCESS' else None
        }
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
