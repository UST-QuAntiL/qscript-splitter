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
import shutil


@app.route('/qc-script-splitter/api/v1.0/split-qc-script', methods=['POST'])
def split_qc_script():
    """Put QC script split job in queue. Return location of the later result."""

    # Clear working directories
    if app.config['CLEAR_FILES_ON_NEW_REQUEST']:
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            app.logger.debug('Delete upload folder %s' % app.config['UPLOAD_FOLDER'])
            shutil.rmtree(app.config['UPLOAD_FOLDER'])
        if os.path.exists(app.config['RESULT_FOLDER']):
            app.logger.debug('Delete result folder %s' % app.config['RESULT_FOLDER'])
            shutil.rmtree(app.config['RESULT_FOLDER'])

    # Extract required input data
    script = request.files['script']
    app.logger.info('Received request for splitting script...')

    # Store file with required script in local file and forward path to the workers
    upload_folder = app.config["UPLOAD_FOLDER"]
    app.logger.info('Storing uploaded script at folder: ' + str(upload_folder))
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    file_name = 'qc-script-' + random_string + '.py'
    script.save(os.path.join(upload_folder, file_name))

    script_url = url_for('download_uploaded_file', name=os.path.basename(file_name))
    app.logger.info('File available via URL: ' + str(script_url))

    kb_url = url_for('download_knowledge_base')
    app.logger.info('Knowledge base available via URL: ' + str(kb_url))

    # Execute job asynchronously
    job = app.queue.enqueue('app.tasks.qc_script_splitting_task', qc_script_url=script_url, knowledge_base_url=kb_url, job_timeout=18000)
    app.logger.info('Added job for qc script splitting to the queue...')
    result = Result(id=job.get_id())
    db.session.add(result)
    db.session.commit()

    # Return location of task object to retrieve final result
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
    """Return file from upload folder."""
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)


@app.route('/qc-script-splitter/api/v1.0/qc-script-parts/<result_id>')
def download_generated_file(result_id):
    """Return file from result folder."""
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
    """Return knowledge base."""
    return send_from_directory(app.config["KNOWLEDGE_BASE_FOLDER"], 'knowledge_base.json')
