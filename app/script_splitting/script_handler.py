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
import logging


logging.basicConfig(filename='logger.log', encoding='utf-8', level=logging.DEBUG)


def split_qc_script(script):
    print("start splitting")
    # load white and black lists
    knowledge_base_path = 'script_splitting/knowledge_base.json'
    logging.info('Load Knowledge Base: %s' % knowledge_base_path)
    with open(knowledge_base_path, 'r') as knowledge_base:
        knowledge_base_json = json.load(knowledge_base)
    white_list = knowledge_base_json['white_list']
    black_list = knowledge_base_json['black_list']
    logging.debug('Number of white list rules: %s' % len(white_list))
    logging.debug('Number of black list rules: %s' % len(black_list))

    # RedBaron object containing all information about the script to split
    logging.info('Load Script: %s' % script)
    with open(script, "r") as source_code:
        qc_script_baron = RedBaron(source_code.read())

    logging.info('Flatten Script')
    flattened_file = flatten(qc_script_baron)

    logging.info('Start analyzing script...')
    labels = get_labels(flattened_file, white_list, black_list)

    logging.info('Start splitting script...')
    split_script(flattened_file, labels)


