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

from os import listdir
from tempfile import mkdtemp

from app import db, app
from rq import get_current_job

from app.result_model import Result
import os
import zipfile
from app.script_splitting import script_handler


def qc_script_splitting_task(qc_script_url, requirements_url, knowledge_base_url):
    app.logger.info('Start task split_qc_script...')

    script_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + qc_script_url
    rq_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + requirements_url
    kb_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + knowledge_base_url

    # Call script handler to
    script_splitting_result = script_handler.split_qc_script(script_url, rq_url, kb_url)

    # Pack all resulting files in one zip
    zip_file = zip_files(script_splitting_result)

    # Build result using the zip file as parameter
    result = Result.query.get(get_current_job().get_id())
    if 'error' not in script_splitting_result:
        app.logger.info('Script splitting successful!')
        result.program = zip_file
    else:
        app.logger.info('Script splitting failed!')
        result.error = "ERROR"
        # TODO: Error handling

    # Update database
    result.complete = True
    db.session.commit()


def zip_files(files):
    app.logger.info('Start zipping files...')

    # Create result directory if not existing
    directory = os.path.join(app.config["RESULT_FOLDER"], get_current_job().get_id())
    if not os.path.exists(directory):
        app.logger.debug("Create result folder %s" % directory)
        os.makedirs(directory)

    # Create new zip-file and add all files
    with zipfile.ZipFile(os.path.join(directory, 'qc-script-parts.zip'), 'w') as result_zip_file:
        for file in files:
            file_path = file.name
            file_basename = os.path.basename(file_path)
            if os.path.exists(file.name):
                app.logger.debug("Add file %s to zip folder %s" % (file_basename, os.path.join(directory, 'qc-script-parts.zip')))
                result_zip_file.write(file_path, file_basename)
            else:
                app.logger.warning("File %s is not a file... skip." % file_path)
    result_zip_file.close()

    result_zip_file = open(os.path.join(directory, 'qc-script-parts.zip'), "rb")
    return result_zip_file.read()
