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
import urllib.request


def qc_script_splitting_task(qc_script_url):
    app.logger.info('Start task split_qc_script...')
    job = get_current_job()

    # get URL to the ZIP file with the required programs
    url = 'http://' + os.environ.get('FLASK_RUN_HOST') + ':' + os.environ.get('FLASK_RUN_PORT') + qc_script_url

    # download the ZIP file
    app.logger.info('Downloading required programs from: %s' % url)
    with urllib.request.urlopen(url) as f:
        print(f.read().decode('utf-8'))

    result = Result.query.get(job.get_id())

    # update database
    result.complete = True
    db.session.commit()
