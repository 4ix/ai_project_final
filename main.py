from flask import Flask, render_template, jsonify, request, send_file

import genYoutube

app = Flask(__name__)

@app.route('/')

def index():
    return render_template('index.html')

@app.route('/update', methods=['POST'])
def update():
    return jsonify({
        'logs': genYoutube.logs
    })

@app.route('/result')
def result():
    value = request.args.get('subject')
    result = genYoutube.setName(value)
    if result:
        return render_template('result.html', value=value, korean=genYoutube.korean)
    
@app.route('/download')
def Download_File():
    PATH = genYoutube.final_video_path
    return send_file(PATH, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)