# ******************************************************************************
#  Copyright (c) 2021 University of Stuttgart
#
#  See the NOTICE file(s) distributed with this work for additional
#  information regarding copyright ownership.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************

from app import app, db
from app.result_model import Result
from flask import jsonify, abort, request, send_from_directory, url_for
import logging
import os
import string
import random


@app.route('/qc-script-splitter/api/v1.0/split-qc-script', methods=['POST'])
def split_qc_script():
    """Put qc srcipt split job in queue. Return location of the later result."""

    # extract required input data
    script = request.files['script']
    app.logger.info('Received request for splitting script...')

    # store file with required programs in local file and forward path to the workers
    directory = app.config["UPLOAD_FOLDER"]
    app.logger.info('Storing file comprising required programs at folder: ' + str(directory))
    if not os.path.exists(directory):
        os.makedirs(directory)
    randomString = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    fileName = 'qc-script-' + randomString + '.py'
    script.save(os.path.join(directory, fileName))
    url = url_for('download_uploaded_file', name=os.path.basename(fileName))
    app.logger.info('File available via URL: ' + str(url))

    kb_url = url_for('download_knowledge_base')

    # execute job asynchronously
    job = app.queue.enqueue('app.tasks.qc_script_splitting_task', qc_script_url=url, knowledge_base_url=kb_url, job_timeout=18000)
    app.logger.info('Added job for qc script splitting to the queue...')
    result = Result(id=job.get_id())
    db.session.add(result)
    db.session.commit()

    # return location of task object to retrieve final result
    logging.info('Returning HTTP response to client...')
    content_location = '/qc-script-splitter/api/v1.0/results/' + result.id
    response = jsonify({'Location': content_location})
    response.status_code = 202
    response.headers['Location'] = content_location
    return response


@app.route('/qc-script-splitter/api/v1.0/results/<result_id>', methods=['GET'])
def get_result(result_id):
    """Return result when it is available."""
    result = Result.query.get(result_id)
    if result.complete:
        if result.error:
            return jsonify({'id': result.id, 'complete': result.complete, 'error': result.error}), 200
        else:
            return jsonify({'id': result.id, 'complete': result.complete,
                            'script_parts_url': url_for('download_generated_file', result_id=str(result_id))}), 200
    else:
        return jsonify({'id': result.id, 'complete': result.complete}), 200


@app.route('/qc-script-splitter/api/v1.0/uploads/<name>')
def download_uploaded_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)


@app.route('/qc-script-splitter/api/v1.0/qc-script-parts/<result_id>')
def download_generated_file(result_id):
    directory = os.path.join(app.config["RESULT_FOLDER"], result_id)
    file_name = 'qc-script-parts.zip'
    return send_from_directory(directory, file_name)


@app.route('/qc-script-splitter/api/v1.0/version', methods=['GET'])
def version():
    return jsonify({'version': '1.0'})


@app.route('/qc-script-splitter/api/v1.0/knowledge-base', methods=['DELETE'])
def delete_knowledge_base():
    # TODO
    pass


@app.route('/qc-script-splitter/api/v1.0/knowledge-base', methods=['POST', 'PUT'])
def upload_knowledge_base():
    # TODO
    pass


@app.route('/qc-script-splitter/api/v1.0/knowledge-base', methods=['GET'])
def download_knowledge_base():
    return send_from_directory(app.config["KNOWLEDGE_BASE_FOLDER"], 'knowledge_base.json')
