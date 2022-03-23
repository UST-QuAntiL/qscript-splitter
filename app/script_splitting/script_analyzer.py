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
#

from app import app
from app.script_splitting.Labels import Labels


def get_labels(script, white_list, black_list):
    # Get Initial labels
    labels = get_initial_labels(script, white_list, black_list)
    app.logger.debug("Initial Labels: %s" % labels)

    # If code blocks (ifs, whiles, etc.) are not hybrid, their explicit label is changed to QUANTUM/CLASSICAL
    relabel_code_blocks_if_not_hybrid(script, labels)
    app.logger.debug("Labels after relabeling: %s" % labels)

    # Apply threshold to labels
    apply_threshold(script, labels)
    app.logger.debug("Labels after applying threshold: %s" % labels)

    return labels


def get_initial_labels(script, white_list, black_list, quantum_objects=None):
    if quantum_objects is None:
        quantum_objects = []
    labels = {}

    for baron_node in script:
        app.logger.debug('Label code line: %s...' % repr(baron_node.dumps()))

        # Handle imports
        if baron_node.type in ['import', 'from_import']:
            app.logger.debug('Found import --> IMPORT')
            labels[baron_node] = Labels.IMPORTS

        # Handle splitting markers
        elif baron_node.type == 'comment':
            if baron_node.value == '# ---start prevent split---':
                labels[baron_node] = Labels.START_PREVENT_SPLIT
            elif baron_node.value == '# ---end prevent split---':
                labels[baron_node] = Labels.START_PREVENT_SPLIT
            elif baron_node.value == '# ---force split---':
                labels[baron_node] = Labels.FORCE_SPLIT
            else:
                labels[baron_node] = Labels.NO_CODE

        # Handle empty lines and comments
        elif baron_node.type in ['endl']:
            app.logger.debug('Empty Line or Comment --> NO_CODE')
            labels[baron_node] = Labels.NO_CODE

        # Handle if-else-blocks
        elif baron_node.type in ['ifelseblock']:
            app.logger.info('Found ifelse code block --> Handle recursively')
            labels[baron_node] = Labels.IF_ELSE_BLOCK
            for if_else_node in baron_node.value:
                code_block = if_else_node.value
                sub_labels = get_initial_labels(code_block, white_list, black_list, quantum_objects)
                labels.update(sub_labels)

        # Handle while-/for-loops
        elif baron_node.type in ['while', 'for']:
            app.logger.info('Found while/for code block --> Handle recursively')
            labels[baron_node] = Labels.LOOP
            code_block = baron_node.value
            sub_labels = get_initial_labels(code_block, white_list, black_list, quantum_objects)
            labels.update(sub_labels)

        # Handle basic classical instructions
        elif baron_node.type in ['print', 'tuple', 'int', 'list']:
            app.logger.info('Basic Type. --> CLASSICAL!')
            labels[baron_node] = Labels.CLASSICAL

        # Handle assignments
        elif baron_node.type == 'assignment':
            if baron_node.value.type != 'atomtrailers':
                app.logger.error('Unexpected node type received: %s' % baron_node.value.type)
            label = handle_atomic_trailer_nodes(baron_node.value, script, white_list, black_list, quantum_objects)
            labels[baron_node] = label
            if label == Labels.QUANTUM:
                app.logger.debug(
                    '"%s" is QUANTUM, thus, "%s" is QUANTUM as well.' % (baron_node.value, baron_node.target.value))
                quantum_objects.append(baron_node.target.value)

        # Handle atomtrailers
        elif baron_node.type == 'atomtrailers':
            label = handle_atomic_trailer_nodes(baron_node, script, white_list, black_list, quantum_objects)
            labels[baron_node] = label

        else:
            app.logger.error('Unexpected node type received: %s' % baron_node.type)
            labels[baron_node] = Labels.NO_CODE

    return labels


def handle_atomic_trailer_nodes(atom_trailers_node, script, white_list, black_list, quantum_objects):
    # Retrieve identifier on the left to check if it is quantum-specific
    left_most_identifier = atom_trailers_node.value[0]
    app.logger.debug('Object on the left side of the atomtrailer node: %s' % left_most_identifier)

    # Check if identifier is contained in the list with assigned quantum objects
    app.logger.debug('Check if %s is contained in %s: %s' % (
        str(atom_trailers_node.value[0]), quantum_objects, str(atom_trailers_node.value[0]) in quantum_objects))
    if str(atom_trailers_node.value[0]) in quantum_objects:
        app.logger.debug('Object already assigned as QUANTUM object!')
        return Labels.QUANTUM
    else:
        app.logger.debug('Object is NOT yet assigned as quantum!')

    # Check if the atomtrailer uses an import that is part of a quantum library defined in the knowledge base
    if uses_quantum_import(atom_trailers_node.value[0], script, white_list, black_list):
        return Labels.QUANTUM
    else:
        return Labels.CLASSICAL


def uses_quantum_import(line_value, script, white_list, black_list):
    import_statement = get_import_statement(line_value, script)
    app.logger.info('Related module for line "%s" is: "%s"' % (line_value, import_statement))

    # Check white and black list of knowledge bases separately
    found_in_whitelist = is_in_knowledge_base(import_statement, white_list)
    found_in_blacklist = is_in_knowledge_base(import_statement, black_list)
    if found_in_whitelist:
        if found_in_blacklist:
            app.logger.info('Found module in whitelist but in blacklist, too. --> Classical!')
        else:
            app.logger.info('Found module in whitelist but not in blacklist. --> Quantum!')
    else:
        app.logger.info('Did not find module in whitelist. --> Classical!')

    # Element must be in white list but not in blacklist
    return found_in_whitelist and not found_in_blacklist


def get_import_statement(line_value, script):
    app.logger.info('Get module for %s...' % line_value)

    # Search through all 'from' imports and return matching modules
    # E.g.: from qiskit.visualization import plot_histogram --> return qiskit.visualization.plot_histogram
    as_imports = script.find_all('import')
    for as_import in as_imports:
        for dottedAsNameNode in as_import.value:
            if hasattr(line_value, 'value') and dottedAsNameNode.target == line_value.value:
                return [value.value for value in dottedAsNameNode.value if value.type == 'name']

    # Search through all 'as' imports and return matching modules
    # E.g.: import qiskit as qs --> return qiskit
    from_imports = script.find_all('from_import')
    for from_import in from_imports:
        for target in from_import.targets:
            if str(target.value) == str(line_value):
                import_parts = [value.value for value in from_import.value if value.type == 'name']
                import_parts.append(target.value)
                return import_parts

    # Return empty list since statement is not from any imported module
    return []


def is_in_knowledge_base(package_orig, knowledge_base):
    # if any parameter is not defined, log warning and return False
    if package_orig is None or knowledge_base is None:
        app.logger.warning("Search for %s in %s is invalid since one of both is None." % (package_orig, knowledge_base))
        return False

    # If search term is empty, return False
    if not package_orig:
        app.logger.debug("Search for empty list in knowledge base --> return False")
        return False

    # Copy array to work on a copy instead of the original
    package_copy = package_orig[:]

    # Search in KB iteratively adding elements from package_orig to search term.
    # E.g.: packages_copy =  ['first','second','third']
    # Start to search for 'first' in KB. Continue with 'first.second', and finally search for 'first.second.third' in KB
    search_list = []
    while len(package_copy) > 0:
        search_list.append(package_copy.pop(0))
        if ".".join(search_list) in knowledge_base:
            return True

    return False


def relabel_code_blocks_if_not_hybrid(script, splitting_labels):
    for node in script:
        if node.type in ["ifelseblock", "for", "while"]:
            found_quantum = contains_any(node, splitting_labels, Labels.QUANTUM)
            found_classical = contains_any(node, splitting_labels, Labels.CLASSICAL)
            if found_quantum and not found_classical:
                splitting_labels[node] = Labels.QUANTUM
            elif found_classical and not found_quantum:
                splitting_labels[node] = Labels.CLASSICAL


def contains_any(node, splitting_labels, label):
    if node.type == 'ifelseblock':
        for block in node.value:
            for n in block.value:
                if contains_any(n, splitting_labels, label):
                    return True
    elif node.type in ['while', 'for']:
        for n in node.value:
            if contains_any(n, splitting_labels, label):
                return True

    return node in splitting_labels and splitting_labels[node] == label


def apply_threshold(script, splitting_labels):
    app.logger.debug("Start relabeling with threshold=%s..." % app.config["SPLITTING_THRESHOLD"])

    # Calculate number of classical lines before each quantum block and relabel if it is smaller than threshold
    classical_nodes = []
    any_quantum = False
    for node in script:
        # Handle if-else-blocks recursively. Do not relabel preceding classical.
        if splitting_labels[node] == Labels.IF_ELSE_BLOCK:
            for block in node.value:
                apply_threshold(block.value, splitting_labels)
            classical_nodes = []

        # Handle while-/for-blocks recursively. Do not relabel preceding classical.
        if splitting_labels[node] == Labels.LOOP:
            apply_threshold(node.value, splitting_labels)
            classical_nodes = []

        # If a quantum label if found, relabel preceding classical nodes (when threshold is missed)
        if splitting_labels[node] == Labels.QUANTUM:
            relabel_if_threshold_not_reached(classical_nodes, splitting_labels)
            classical_nodes = []
            any_quantum = True

        # Add classical labels to list of 'preceding' classical_nodes
        if splitting_labels[node] == Labels.CLASSICAL:
            classical_nodes.append(node)

    # Calculate number of trailing classical lines and relabel if it is smaller than threshold.
    # For code blocks only containing classical elements, any_quantum is False.
    if any_quantum:
        relabel_if_threshold_not_reached(classical_nodes, splitting_labels)


def relabel_if_threshold_not_reached(classical_nodes, splitting_labels):
    # Code blocks (ifs, whiles, etc.) also have additional code lines counted for threshold
    weight = 0
    for node in classical_nodes:
        weight += calc_weight(node)

    # Relabel classical nodes if threshold is not reached
    if 0 < weight < app.config["SPLITTING_THRESHOLD"]:
        for node in classical_nodes:
            relabel(node, splitting_labels)


def relabel(node, splitting_labels):
    splitting_labels[node] = Labels.QUANTUM
    # Relabel if-else-blocks recursively
    if node.type == 'ifelseblock':
        for block in node.value:
            for x in block.value:
                if x in splitting_labels:
                    relabel(x)
    # Relabel while-/for-blocks recursively
    if node.type in ['while', 'for']:
        for block in node.value:
            if block in splitting_labels:
                relabel(block)


def calc_weight(node):
    weight = 1
    if node.type == 'ifelseblock':
        for block in node.value:
            weight -= 1
            for x in block.value:
                weight += calc_weight(x)
    if node.type in ['while', 'for']:
        weight -= 1
        for block in node.value:
            weight += calc_weight(block)
    return weight
