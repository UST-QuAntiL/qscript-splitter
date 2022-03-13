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


def qc_script_splitting_task(qc_script_url, knowledge_base_url):
    app.logger.info('Start task split_qc_script...')
    job = get_current_job()

    # get URL to the ZIP file with the required programs
    url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + qc_script_url
    kb_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + knowledge_base_url

    script_splitting_result = script_handler.split_qc_script(url, kb_url)

    zip_file = zip_files(script_splitting_result)

    # insert results into job object
    result = Result.query.get(job.get_id())
    if 'error' not in script_splitting_result:
        app.logger.info('Program generation successful!')
        result.script_parts = zip_file
    else:
        app.logger.info('Program generation failed!')
        result.error = "ERROR"

    # Update database
    result.complete = True
    db.session.commit()


def zip_files(files):
    job_id = get_current_job().get_id()

    # Create result directory if not existing
    directory = os.path.join(app.config["RESULT_FOLDER"], job_id)
    if not os.path.exists(directory):
        app.logger.debug("Create result folder %s" % directory)
        os.makedirs(directory)

    # Create new zip-file and add all files
    with zipfile.ZipFile(os.path.join(directory, 'qc-script-parts.zip'), 'w') as zip_obj:
        for file in files:
            file_path = file.name
            file_basename = os.path.basename(file_path)
            if os.path.exists(file.name):
                app.logger.debug("Add file %s to zip folder %s" % (file_basename, file_path))
                zip_obj.write(file_path, file_basename)
            else:
                app.logger.warning("File %s is not a file... skip." % file_path)

    return zip_obj
