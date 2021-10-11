import os
from pathlib import Path
from shutil import copyfile
from redbaron import RedBaron, CodeBlockNode


def analyze(filename):
    """
    uses an FST to analyze the given source code
    the returned information can be used to generate candidate objects

    :param filename: python source file to analyze
    :return: Candidate object including all parts and additional information
    """

    # experts can use append to add new libraries to the quantum_set
    quantum_set = ["qiskit"]

    # read in code
    with open(filename, "r") as source:
        code_file = source.read()
        red = RedBaron(code_file)

    imports = {}
    import_nodes = []
    qc_nodes = []

    # find all used libs and group them
    tmp_nodes = red.find_all("FromImportNode")
    for i in tmp_nodes:
        import_nodes.append(i)
        for j in i.targets:
            # brackets are misleading here and must be skipped
            if not ('(' in j.value or ')' in j.value):
                try:
                    imports[i.name.value].append(j.value)
                except KeyError:
                    imports[i.name.value] = [j.value]
    # find full imports
    tmp_nodes = red.find_all("ImportNode")
    for i in tmp_nodes:
        import_nodes.append(i)
        if not ('(' in i.value or ')' in i.value):
            # add the top-level lib itself or add some sub-lib to the top-level lib
            try:
                imports[i.name.value].append(str(i.value[0].value[-1]))
            except KeyError:
                imports[i.name.value] = [str(i.value[0].value[-1])]

    # remove possible dangerous character-entries
    for qc_lib_name in quantum_set:
        # this may be refined in the future
        while "*" in imports[qc_lib_name] :
            imports[qc_lib_name].remove("*")

    # find qc nodes in calls (those are stored in AtomtrailersNodes)
    tmp_nodes = red.find_all("AtomtrailersNode")
    for node in tmp_nodes:
        for v in node.value:
            if any(lib in str(v) for qc_lib_name in quantum_set for lib in imports[qc_lib_name]):
                qc_nodes.append(node)
    # the analysis must not use internal nodes
    first_qc_node = qc_nodes[0]
    last_qc_node = qc_nodes[-1]
    last_import_index = __get_last_index(red, import_nodes)
    first_qc_index, last_qc_index, condition = __handle_for_loops(red, first_qc_node, last_qc_node)

    # debugging
    # print("first node:", first_qc_node, first_qc_index)
    # print("last node:", last_qc_node, last_qc_index)

    # define parts as redBaron instances
    qc_part_code = RedBaron("def quantum(): return 0")
    pre_part_code = RedBaron("def pre(): return 0")
    post_part_code = RedBaron("def post(): return 0")
    # redBaron can only deal with inserting/appending str and converts them to nodes internally

    # prepare code of pre part
    pre_part_code[0].value = ""
    for i in range(last_import_index + 1, first_qc_index):
        pre_part_code[0].value.append(str(red[i].copy()))
    quantum_req = __get_prov_vars(pre_part_code)
    # add return statement with matching arguments
    pre_part_code[0].value.append("return")
    pre_part_code[0].value[-1].value = str(quantum_req).replace("'", "")

    # prepare code of quantum part
    qc_part_code[0].value = ""
    for i in range(first_qc_index, last_qc_index + 1):
        # +1 is mandatory to include the last node due to indexing reasons
        qc_part_code[0].value.append(str(red[i].copy()))
    post_req = __get_prov_vars(qc_part_code)
    post_req.extend(__get_prov_vars(pre_part_code))
    # add return statement with matching arguments
    qc_part_code[0].value.append("return ")
    qc_part_code[0].value[-1].value = str(post_req).replace("'", "")
    # add arguments to dummy function, especially the loop-condition
    quantum_req.append(condition[0])
    for arg in quantum_req:
        qc_part_code[0].arguments.append(arg)

    # prepare code of post part
    post_part_code[0].value = ""
    for i in red[last_qc_index + 1:]:
        post_part_code[0].value.append(str(red[red.index(i)]))
    post_prov = __get_prov_vars(post_part_code)
    # add return statement with matching arguments
    post_part_code[0].value.append("return ")
    post_part_code[0].value[-1].value = str(post_prov).replace("'", "")
    # add arguments to dummy function
    for arg in post_req:
        post_part_code[0].arguments.append(arg)

    # fix for imports. This will put all imports to the new code
    for im in import_nodes:
        qc_part_code.insert(0, im.copy())
        pre_part_code.insert(0, im.copy())
        post_part_code.insert(0, im.copy())

    # the following works but may get commented out for run time reasons
    # create parts
    qc_part = Part(start_line=first_qc_index, offset=(0, 0), nodes=[], code_as_string=qc_part_code.dumps())
    pre_part = Part(start_line=0, offset=(0, 0), nodes=[], code_as_string=pre_part_code.dumps())
    post_part = Part(start_line=last_qc_index + 1, offset=(0, 0), nodes=[], code_as_string=post_part_code.dumps())

    my_candidate = Candidate(filename)
    my_candidate.loop_condition = condition
    my_candidate.init_quantum(qc_part)
    my_candidate.init_pre(pre_part)
    my_candidate.init_post(post_part)

    return my_candidate


def __find_topLevel_node(node):
    """
    Find the top-level node which holds the given node.
    This will use the parent relationship between nodes in the RedBaron tree.
    If the node is a top-level node itself, the node is returned.

    :param node: node to check
    :return: the highest possible parent of the given node
    """
    if isinstance(node.parent, RedBaron) or isinstance(node.parent, CodeBlockNode):
        return node
    else:
        return __find_topLevel_node(node.parent)


def __handle_for_loops(red, first, last):
    """
    find all loops that make use of quantum nodes

    :param red: redBaron instance to work with
    :param first: first qc node
    :param last: last qc node
    :return: index of first and last qc node and the condition of possibly intersected loops
    """
    loop_nodes = red.find_all("ForNode")
    complete_loop = False
    intersecting_loops = []
    conditions = []
    # if there is no loop, this operation has to return immediately
    if not loop_nodes:
        conditions.append("NoLoopFound")
        conditions.append("False")
        return red.index(__find_topLevel_node(first)), red.index(__find_topLevel_node(last)), conditions

    # check the beginning of the quantum part
    try:
        first_qc_index = red.index(first.parent)
        print(first)
    except ValueError:
        # loop begins before the quantum part
        # use loop-node as first node
        first_qc_index = red.index(first.parent.parent)

    # check the end of the quantum part
    try:
        last_qc_index = red.index(last.parent)
    except ValueError:
        # last node is still contained in loop -> loop around whole part
        # use first node also as last node since all nodes are included in the loop-node
        last_qc_index = first_qc_index
        complete_loop = True

    if complete_loop:
        # loop around whole part must be adjusted
        for loop in loop_nodes:
            if last.parent.parent == loop:
                conditions.append((str(loop.iterator.value), str(loop.target.value[-1])))
                loop.target = "range(1)"
                loop.iterator = "_loop_dummy"
                break
    return_condition = __store_loop_condition(conditions)
    return first_qc_index, last_qc_index, return_condition


def __store_loop_condition(conditions):
    """
    save the loop conditions

    :param conditions: list of conditions (iterator,value-space)
    :return: tuple of human-readable condition
    """
    if not conditions:
        return ()

    return conditions[0]


def __get_req_vars(code):
    """
    compute all variable that a given code-snippet may need

    :param code: code-snippet to analyse
    :return: list of all required variables
    """
    # TODO optional
    vars = []

    return vars


def __get_prov_vars(code):
    """
    helper function
    compute all variable that a given code-snippet may provide for other parts

    :param code:  redBaron instance representing the code-snippet to analyse
    :return: list of all provided variables
    """
    vars = []

    assignments = code.findAll("AssignmentNode")
    for a in assignments:
        if isinstance(a.target.value, str):
            vars.append(a.target.value)
        else:
            # combined assignment e.g. x,y = f()
            split_target = str(a.target).split(",")
            for s in split_target:
                vars.append(s)
    # filter duplicates before returning
    return list(dict.fromkeys(vars))


def __get_last_index(red, nodes):
    """
    compute the highest (last) index from a given node-list

    :param: red redBaron instance
    :param: nodes list of nodes
    :return: index of last node
    """
    index = 0
    for i in nodes:
        index = max(index, red.index(i))
    return index


class Part():
    """
    Class to represent a single part of the script
    This will be either a pre- post- or quantum-processing part
    """

    def __init__(self, start_line=0, offset=(0, 0), nodes=None, code_as_string="", req_vars=None, prov_vars=None):
        # self.changes = ChangeSet("my changes")
        if nodes is None:
            nodes = []
        self.start_line = start_line
        self.offset = offset
        self.nodes = nodes
        self.code_as_string = code_as_string
        self.req_vars = req_vars
        self.prov_vars = prov_vars


class Candidate:
    """
    Class to represent the possible splitting result
    In particular, objects of this class will have a pre-/quantum-/post-part
    """

    def __init__(self, filename):
        self.pre_part = Part()
        self.quantum_part = Part()
        self.post_part = Part()
        self.loop_condition = ()
        self.filename = filename
        self.dst_pre, self.dst_quantum, self.dst_post = self.init_files()

    def init_files(self):
        """
        Initialize (create) dummy-files that may be used as output as well

        :param filename: the original filename
        :return: names (str,str,str,str) of the new files
        """

        dst_pre = str(Path.cwd().resolve()) + '/Example' + '/prePart.py'
        dst_quantum = str(Path.cwd().resolve()) + '/Example' + '/quantumPart.py'
        dst_post = str(Path.cwd().resolve()) + '/Example' + '/postPart.py'
        # clear the files if they exist; otherwise surprising things will happen...
        # create files and copy content to output-file
        empty_pre = open(dst_pre, "w")
        empty_pre.close()
        empty_quantum = open(dst_quantum, "w")
        empty_quantum.close()
        empty_post = open(dst_post, "w")
        empty_post.close()
        return dst_pre, dst_quantum, dst_post

    def init_pre(self, part):
        """
        Initialize preprocessing-part.
        Especially computes the changes to the source file.
        Additional information will be stored in the part object.
        :param part
        """
        self.pre_part = part
        # write quantum part to dst-file
        with open(self.dst_pre, "w") as out:
            out.writelines(part.code_as_string)

    def init_quantum(self, part):
        """
        Initialize quantum-part.
        Especially computes the changes to the source file.
        Additional information will be stored in the part object.
        :param part
        """
        self.quantum_part = part
        # write quantum part to dst-file
        with open(self.dst_quantum, "w") as out:
            out.writelines(part.code_as_string)

    def init_post(self, part):
        """
        Initialize postprocessing-part.
        Especially computes the changes to the source file.
        Additional information will be stored in the part object.
        :param part
        """
        self.post_part = part
        # write quantum part to dst-file
        with open(self.dst_post, "w") as out:
            out.writelines(part.code_as_string)

    def __do_backup(self):
        """
        Copy the source-file before refactoring.
        File will be saved under <source-path><source-name>_backup
        """
        src = self.filename
        dst = self.filename[:self.filename.rfind(".py")] + "_backup.py"
        copyfile(src, dst)

    def get_file_names(self):
        return self.dst_pre, self.dst_quantum, self.dst_post, self.dst_out

    def get_loop_condition(self):
        target = self.loop_condition[0]
        value = self.loop_condition[1]
        # currently only this simple case works fine
        simple_case = True
        condition = ""
        if simple_case:
            condition = target + " < " + value
        # needs to be extended
        return condition
