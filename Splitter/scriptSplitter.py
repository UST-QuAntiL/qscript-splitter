from Splitter import scriptParser
from flask import Flask

app = Flask(__name__)


@app.route('/')
def split(file_name):
    x = scriptParser.analyze(file_name)
    return x