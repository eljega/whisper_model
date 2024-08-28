from flask import Flask, request, jsonify
import whisper
import os

app = Flask(__name__)

model = whisper.load_model("base")

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video = request.files['video']
    temp_video_path = os.path.join('/tmp', video.filename)
    video.save(temp_video_path)
    
    result = model.transcribe(temp_video_path)
    os.remove(temp_video_path)
    
    return jsonify(result['segments'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
