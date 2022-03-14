# ******************************************************************************
#  Copyright (c) 2022 University of Stuttgart
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

from app import app
from redbaron import RedBaron
from app.script_splitting.flattener import flatten
from app.script_splitting.script_analyzer import get_labels
from app.script_splitting.script_splitter import split_script
import json
import os
import shutil
import urllib.request
from rq import get_current_job


def split_qc_script(script_url, requirements_url, knowledge_base_url):
    app.logger.info("Script Handler: Start splitting...")

    # RedBaron object containing all information about the script to split
    with urllib.request.urlopen(script_url) as script_file:
        qc_script_baron = RedBaron(script_file.read().decode('utf-8'))
    if qc_script_baron is None or len(qc_script_baron) == 0:
        app.logger.error('Could not load base script... Abort')
        return

    # Load Requirements
    with urllib.request.urlopen(requirements_url) as req_file:
        requirements_file = req_file.read().decode('utf-8')
        app.logger.info('Loaded requirements')

    # Download knowledge base
    app.logger.info('Downloading knowledge base from: %s' % knowledge_base_url)
    with urllib.request.urlopen(knowledge_base_url) as knowledge_base_file:
        knowledge_base_json = json.load(knowledge_base_file)
        white_list = knowledge_base_json['white_list']
        black_list = knowledge_base_json['black_list']
        app.logger.debug('Number of white list rules: %s' % len(white_list))
        app.logger.debug('Number of black list rules: %s' % len(black_list))

    if knowledge_base_json is None:
        app.logger.error('Could not load knowledge base... Abort')
        return

    # Flatten the Script
    app.logger.info('Flatten Script')
    flattened_file = flatten(qc_script_baron)

    # Analyze the flattened script
    app.logger.info('Start analyzing script...')
    labels = get_labels(flattened_file, white_list, black_list)

    # Split the script
    app.logger.info('Start splitting script...')
    script_parts = split_script(flattened_file, requirements_file, labels)

    # Save all script parts as files
    files = save_as_files(script_parts)

    return files


def save_as_files(script_parts):
    job_id = get_current_job().get_id()

    # Create result directory if not existing
    directory = os.path.join(app.config["RESULT_FOLDER"], job_id)
    if not os.path.exists(directory):
        app.logger.debug("Create result folder %s" % directory)
        os.makedirs(directory)

    # Save all script parts as files
    files = []
    for filename, redbaron_file in script_parts.items():
        app.logger.debug("Save %s to %s" % (filename, directory))
        with open(os.path.join(directory, filename), "w") as file:
            if filename.split("_")[0] == "requirements":
                file.write(redbaron_file)
            else:
                file.write(redbaron_file.dumps())
        files.append(file)

    return files
