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
from app.script_splitting import script_handler


def qc_script_splitting_task(qc_script_url, requirements_url, knowledge_base_url, threshold):
    app.logger.info('Start task split_qc_script...')

    script_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + qc_script_url
    rq_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + requirements_url
    kb_url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + knowledge_base_url
    if threshold is not None:
        app.config['SPLITTING_THRESHOLD'] = int(threshold)

    # Call script handler to
    script_splitting_result = script_handler.split_qc_script(script_url, rq_url, kb_url)

    # Build result using the zip file as parameter
    result = Result.query.get(get_current_job().get_id())
    result.program = script_splitting_result

    # Update database
    result.complete = True
    db.session.commit()
