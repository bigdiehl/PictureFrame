
from flask import Flask, render_template, request

app = Flask(__name__, static_url_path='', static_folder='')

@app.route('/')
def index():
	return app.send_static_file('index.html')



if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')

