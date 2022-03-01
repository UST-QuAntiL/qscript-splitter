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
from app.script_splitting.Labels import Labels
import numpy as np


def split_local_function(root_baron, method_baron, white_list, black_list, label_map, quantum_objects):
    print('Splitting method with name: %s' % method_baron.name)
    print('Already labeled functions: ', label_map)
    print('Method has %d lines of code: ' % len(method_baron.value))

    # label all lines within the current function
    line_labels = []
    for line in method_baron.value:
        label, quantum_objects = label_code_line(root_baron, line, white_list, black_list, quantum_objects, label_map)
        line_labels.append(label)
    line_labels = np.array(line_labels, dtype = object)
    quantum_label_indices = np.where(line_labels == Labels.QUANTUM)[0]

    # splitting labels based on code analysis and threshold
    splitting_labels = []

    # if the complete code block is classical return with classical label
    if len(quantum_label_indices) == 0:
        label_map[method_baron.name] = Labels.CLASSICAL
        return label_map

    # check if first label has preceding classical part bigger than threshold and relabel if not
    if quantum_label_indices[0] >= app.config["SPLITTING_THRESHOLD"]:
        splitting_labels.extend(line_labels[:quantum_label_indices[0] + 1])
        previous_quantum_index = quantum_label_indices[0]
    else:
        for x in range(quantum_label_indices[0] + 1):
            splitting_labels.append(Labels.QUANTUM)
        previous_quantum_index = quantum_label_indices[0]

    # relabel if distance between previous and current quantum index is larger than threshold
    for current_quantum_index in quantum_label_indices[1:len(quantum_label_indices)]:
        print('Current quantum index: ', current_quantum_index)
        print('Previous quantum index: ', previous_quantum_index)

        # check if distance between previous and current quantum index is larger than threshold
        if current_quantum_index - previous_quantum_index <= app.config["SPLITTING_THRESHOLD"]:
            print('Relabeling to avoid split!')
            for x in range(previous_quantum_index, current_quantum_index):
                splitting_labels.append(Labels.QUANTUM)
        else:
            print('Copy existing labels!')
            splitting_labels.extend(line_labels[previous_quantum_index + 1:current_quantum_index + 1])

        # update previous quantum index
        previous_quantum_index = current_quantum_index

    # check if last label has more follow up lines than threshold and relabel if not
    if len(quantum_label_indices) > 0 and (len(line_labels) - previous_quantum_index) > app.config["SPLITTING_THRESHOLD"]:
        print('Last quantum part (index %d) has more follow up lines than threshold' %  previous_quantum_index)
        splitting_labels.extend(line_labels[previous_quantum_index + 1:len(line_labels)])
    else:
        print('Last quantum part (index %d) has less or equal follow up lines than threshold' %  quantum_label_indices[-1])
        for x in range(len(line_labels) - previous_quantum_index - 1):
            splitting_labels.append(Labels.QUANTUM)

    print('Final splitting labels for method %s: ' % method_baron.name)
    print(splitting_labels)

    # TODO: add new code parts
    label_map[method_baron.name] = 'qc'

    return label_map


def label_code_line(root_baron, line_baron, white_list, black_list, quantum_objects, method_labels):

    if line_baron.type == 'atomtrailers':

        # retrieve identifier on the left to check if it is quantum-specific
        left_most_identifier = line_baron.value[0]
        print('Object on the left side of the atomtrailer node: ', left_most_identifier)

        # check if identifier is contained in the list with assigned quantum objects
        if line_baron.value[0] in quantum_objects:
            print('Object already assigned as quantum object!')
            return Labels.QUANTUM, quantum_objects

        # check if identifier belongs to method invocation
        if line_baron.value[0] in method_labels:
            return method_labels[line_baron.value[0]], quantum_objects

        # check if the atomtrailer uses an import that is part of a quantum library defined in the knowledge base
        if is_quantum_import(line_baron.value[0], root_baron):
            return Labels.QUANTUM, quantum_objects
        else:
            return Labels.CLASSICAL, quantum_objects

    if line_baron.type == 'assignment':
        assignment_label = label_code_line(root_baron, line_baron.value, white_list, black_list, quantum_objects, method_labels)

        # if assignment assigns a quantum object, the corresponding variable is stored
        if assignment_label == Labels.QUANTUM:

            # if multiple variables are on the left side, assign all at once
            for quantum_object in line_baron.target:
                quantum_objects.extend(quantum_object.value)
        return assignment_label, quantum_objects

    # handle classical instructions
    if line_baron.type == 'if' or line_baron.type == 'while' or line_baron.type == 'comment' \
        or line_baron.type == 'endl' or line_baron.type == 'print' or line_baron.type == 'ifelseblock':
        return Labels.CLASSICAL, quantum_objects

    print('Unexpected node type received: ', line_baron.type)
    return Labels.CLASSICAL, quantum_objects


def is_quantum_import(line_value, root_baron):
    imports = root_baron.find_all('import')

    for i in imports:
        for dottedAsNameNode in i.value:
            print('Checking import: ', dottedAsNameNode.target)
            if dottedAsNameNode.target == line_value.value:
                print('Found potential import...:', line_value)
                import_parts = [value.value for value in dottedAsNameNode.value if value.type == 'name']
                # TODO: check for each sub-string if it is part of the whitelist/blacklist
                print('.'.join(import_parts))

    from_imports = root_baron.find_all('from_import')
    # TODO: handle from_imports

    print(imports)
    print(from_imports)


def split_method(method_baron, start_index, end_index):
    print('Splitting method from index %d to %d' % (start_index, end_index))
    # TODO