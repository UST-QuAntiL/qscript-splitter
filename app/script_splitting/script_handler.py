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
from app.script_splitting.script_analyzer import ScriptAnalyzer
from app.script_splitting.script_splitter import ScriptSplitter
import json
import os
import zipfile
import urllib.request
import shutil
from rq import get_current_job


def do_the_split(qc_script_baron, requirements_file, knowledge_base_json):
    white_list = knowledge_base_json['white_list']
    black_list = knowledge_base_json['black_list']
    app.logger.debug('Number of white list rules: %s' % len(white_list))
    app.logger.debug('Number of black list rules: %s' % len(black_list))

    # Flatten the Script
    app.logger.info('Flatten Script')
    flattened_file = flatten(qc_script_baron)

    # Analyze the flattened script
    app.logger.info('Start analyzing script...')
    script_analyzer = ScriptAnalyzer(flattened_file, white_list, black_list)
    map_labels = script_analyzer.get_labels()

    # Split the script
    app.logger.info('Start splitting script...')
    script_splitter = ScriptSplitter(flattened_file, requirements_file, map_labels)
    script_parts = script_splitter.split_script()

    return script_parts


def split_qc_script(script_url, requirements_url, knowledge_base_url):
    app.logger.info("Script Handler: Start splitting...")

    # RedBaron object containing all information about the script to split
    with urllib.request.urlopen(script_url) as script_file:
        qc_script = RedBaron(script_file.read().decode('utf-8'))
    if qc_script is None or len(qc_script) == 0:
        app.logger.error('Could not load base script... Abort')
        return

    # Load Requirements File
    with urllib.request.urlopen(requirements_url) as req_file:
        requirements_file = req_file.read().decode('utf-8')
        app.logger.info('Loaded requirements')

    # Download knowledge base
    app.logger.info('Downloading knowledge base from: %s' % knowledge_base_url)
    with urllib.request.urlopen(knowledge_base_url) as knowledge_base_file:
        knowledge_base_json = json.load(knowledge_base_file)

    if knowledge_base_json is None:
        app.logger.error('Could not load knowledge base... Abort')
        return

    # Split into several script parts
    script_parts = do_the_split(qc_script, requirements_file, knowledge_base_json)

    # Save all script parts as files
    path = save_as_files(script_parts)
    zip_file = zipfile.ZipFile(path + '.zip', 'w', zipfile.ZIP_DEFLATED)
    zip_directory(path, zip_file)
    zip_file.close()

    return open(path + '.zip', "rb").read()


def save_as_files(script_parts):
    job_id = get_current_job().get_id()

    # Create result directory if not existing
    directory = os.path.join(app.config["RESULT_FOLDER"], job_id)
    if not os.path.exists(directory):
        app.logger.debug("Create result folder %s" % directory)
        os.makedirs(directory)

    # Write workflow to disk
    with open(os.path.join(directory, 'workflow.json'), "w") as file:
        app.logger.debug("Write workflow.json to %s" % directory)
        file.write(json.dumps(script_parts['workflow.json']))
        file.close()

    # Write iterators to disk
    iterators_directory = os.path.join(directory, 'iterators')
    if not os.path.exists(iterators_directory):
        app.logger.debug("Create 'iterators' folder %s" % iterators_directory)
        os.makedirs(iterators_directory)
    for iterator in script_parts['iterators']:
        with open(os.path.join(iterators_directory, iterator['name'] + ".js"), "w") as file:
            file.write(iterator['file'])
            file.close()

    # Save extracted parts to separate subdirectories
    for part in script_parts['extracted_parts']:
        # Create subdirectory
        part_directory = os.path.join(directory, part['name'], "service")
        if not os.path.exists(part_directory):
            app.logger.debug("Create 'part' folder %s" % part_directory)
            os.makedirs(part_directory)
        # Write app.py to disk
        with open(os.path.join(part_directory, "app.py"), "w") as file:
            app.logger.debug("Write app.py to %s" % part_directory)
            for x in part['app.py']:
                file.write(x.dumps())
            file.close()
        # Write requirements.txt to disk
        with open(os.path.join(part_directory, "requirements.txt"), "w") as file:
            app.logger.debug("Write requirements.txt to %s" % part_directory)
            file.write(part['requirements.txt'])
            file.close()

        # Add polling agent
        with open(os.path.join(part_directory, "polling_agent.py"), "w") as file:
            app.logger.debug("Write polling_agent.py to %s" % part_directory)
            file.write(part['polling_agent.py'])

        # Zip contents so far
        zip_path = os.path.join(directory, part['name'], "service.zip")
        zip_file = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        zip_directory(part_directory, zip_file)
        zip_file.close()

        # Copy Dockerfile
        source_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates", "Dockerfile")
        shutil.copyfile(source_path, os.path.join(directory, part['name'], "Dockerfile"))

    return directory


def zip_directory(directory_path, zip_file):
    app.logger.debug("Combine all files from directory %s to zip file %s" % (directory_path, zip_file.filename))
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            zip_file.write(os.path.join(root, file),
                           os.path.relpath(os.path.join(root, file),
                           os.path.join(directory_path, '..')))


if __name__ == '__main__':
    basedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "data")
    script_path = os.path.join(basedir, "files", "example.py")
    rq_path = os.path.join(basedir, "files", "requirements.txt")
    kb_path = os.path.join(basedir, "knowledge_base", "knowledge_base.json")

    result = do_the_split(RedBaron(open(script_path, "r").read()), open(rq_path, "r").read(), json.load(open(kb_path, "r")))