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

from redbaron import RedBaron
import logging
import random
import string


def split_script(file, labels):
    pass


def get_all_external_variables_of_code_block(code_block):
    initialized_variables = []
    external_variables = []
    for line in code_block:
        created_variables, referenced_variables = get_all_variables_of_line(line)
        # check if referenced variables of line have been initialized before
        # add to external_variables if not
        for referenced_variable in referenced_variables:
            if referenced_variable not in initialized_variables:
                external_variables.append(referenced_variable)
        initialized_variables.extend(referenced_variables)

    return external_variables


def get_all_variables_of_line(line):
    created_variables = []
    referenced_variables = []

    if line.type == "assignment":
        if line.target.type == 'tuple':
            for variable in line.target.value:
                created_variables.append(variable.value)
        else:
            created_variables.append(line.target.value)

    # TODO: Get used variables
    # TODO: What should we do with method invocations?

    return created_variables, referenced_variables


def extract_method(code_block):
    logging.info("Extract code block to separate function...")

    # create method name
    letters = string.ascii_lowercase
    method_name = ''.join(random.choice(letters) for i in range(10))

    # create parameters list
    variables = get_all_external_variables_of_code_block(code_block)
    parameters = ",".join(variables)

    # create new def node
    create_str = "def extracted_method_" + method_name + "(" + parameters + "):"

    # add lines to def node
    for line in code_block:
        create_str += "\n    " + str(line.dumps())

    return RedBaron(create_str)


def split_code_block(root_baron, method_baron, splitting_labels):
    logging.info('Break up code block into several parts based on final labels:')
    for i in range(len(method_baron.value)):
        if method_baron.value[i].type != "endl":
            logging.debug("[%i] %s [%s]" % (i, method_baron.value[i], splitting_labels[i]))

    to_extract = []
    result_definitions = []
    for i in range(len(splitting_labels)):
        if len(to_extract) == 0:
            logging.debug("Start new block")
        if method_baron.value[i].type == "endl":
            continue
        logging.debug('Add %s to current block' % method_baron.value[i].dumps())
        to_extract.append(method_baron.value[i])
        # for very last element or when next elements label is different
        if i == len(splitting_labels)-1 or splitting_labels[i+1] != splitting_labels[i]:
            new_method = extract_method(to_extract)
            logging.debug("Created method: %s" % repr(new_method.dumps()))
            result_definitions.append(new_method)
            to_extract = []