import json
from flask import Flask, request
import sys

from Splitter import scriptParser

app = Flask(__name__)


@app.route('/')
def hello():
    # this is only used to check if the api is reachable at all
    return "Hello world!"


@app.route('/scriptSplitter', methods=['POST'])
def call_script_splitting_algorithm():
    #filename = str(Path.cwd().resolve()) + '/Example' +'/testScriptQHED.py'
    filename = request.json.get('sourceFile')
    print("-----------------------------------------------------", file=sys.stdout)
    print(request.json, file=sys.stdout)

    result = scriptParser.analyze(filename)

    meta_data = createMetaFromCandidate(result)
    return meta_data


def createMetaFromCandidate(candidate):
    """
    Extract the meta data contained in the given Candidate Object.

    :param candidate: the data to convert, usually this is a Candidate Object
    :return: json file
    """
    # use get_loop_condition() to abstract from internal extraction
    extracted = {"PreStart": candidate.pre_part.start_line, "QuantumStart": candidate.quantum_part.start_line, "PostStart": candidate.post_part.start_line,
                 "LoopConditions": candidate.get_loop_condition()}
    return json.dumps(extracted)