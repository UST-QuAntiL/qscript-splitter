import os
from shutil import copyfile
from rope.base.project import Project
from rope.base import libutils
from rope.refactor.extract import ExtractMethod
from rope.base.change import ChangeSet
from redbaron import RedBaron


def analyze(filename):
    """
    uses an FST to analyze the given source code
    the returned information can be used to generate candidate objects

    :param filename: python source file to analyze
    :return: tuple of parts (pre,quantum,post,[imports])
    """

    # read in code
    with open(filename, "r") as source:
        code_file = source.read()
        red = RedBaron(code_file)
    # test for read
    # print(red.dumps())

    imports = {}
    import_nodes = []
    qc_nodes = []

    # find all used libs and group them
    tmp_nodes = red.find_all("FromImportNode")
    for i in tmp_nodes:
        import_nodes.append(i)
        for j in i.targets:
            # brackets are misleading here and must be skipped
            if not ('(' in j.value or (')') in j.value):
                try:
                    imports[i.name.value].append(j.value)
                except KeyError:
                    imports[i.name.value] = [j.value]
    # find full imports
    tmp_nodes = red.find_all("ImportNode")
    for i in tmp_nodes:
        import_nodes.append(i)

    # find qc nodes in calls (those are stored in AtomtrailersNodes)
    tmp_nodes = red.find_all("AtomtrailersNode")
    for node in tmp_nodes:
        for v in node.value:
            if any(lib in str(v) for lib in imports["qiskit"]):
                qc_nodes.append(node)

    first_qc_node = qc_nodes[0]
    last_qc_node = qc_nodes[-1]
    last_import_index = get_last_index(red, import_nodes)
    first_qc_index, last_qc_index, condition = handle_for_loops(red, first_qc_node, last_qc_node)

    # debugging
    print("first node:", first_qc_node, first_qc_index)
    print("last node:", last_qc_node, last_qc_index)

    # define parts as redBaron instances
    qc_part_code = RedBaron("def quantum(): return 0")
    pre_part_code = RedBaron("def pre(): return 0")
    post_part_code = RedBaron("def post(): return 0")

    # prepare code of quantum part
    qc_part_code[0].value = ""
    for i in range(first_qc_index, last_qc_index+1):
        # +1 is mandatory to include the last node due to indexing reasons
        qc_part_code[0].value.append(red[i].copy())
    post_req = get_prov_vars(qc_part_code)
    qc_part_code[0].value.append("return "+str(post_req))

    # prepare code of pre part
    pre_part_code[0].value = ""
    for i in range(last_import_index+1, first_qc_index):
        pre_part_code[0].value.append(red[i].copy())
    quantum_req = get_prov_vars(pre_part_code)
    pre_part_code[0].value.append("return "+str(quantum_req))

    # prepare code of post part
    post_part_code[0].value = ""
    for i in red[last_qc_index+1:]:
        post_part_code[0].value.append(red[red.index(i)])
    post_part_code[0].value.append("return "+str(get_prov_vars(post_part_code)))

    """
    for i in range(last_qc_index + 1, 100000):
        try:
            post_part_code.insert(i, red[i].copy())
        except IndexError:
            break
    """
    # fix for imports. This will put all imports to the new code
    for im in import_nodes:
        qc_part_code.insert(0, im.copy())
        pre_part_code.insert(0, im.copy())
        post_part_code.insert(0, im.copy())



    # the following works but is commented out for run time reasons
    # create parts
    qc_part = Part(start_line=first_qc_index, offset=(0, 0), nodes=[], code_as_string=qc_part_code.dumps())
    pre_part = Part(start_line=0, offset=(0, 0), nodes=[], code_as_string=pre_part_code.dumps())
    post_part = Part(start_line=last_qc_index + 1, offset=(0, 0), nodes=[], code_as_string=post_part_code.dumps())

    my_candidate = Candidate(filename)
    my_candidate.loop_condition = condition
    my_candidate.init_quantum(qc_part)
    my_candidate.init_pre(pre_part)
    my_candidate.init_post(post_part)

    return "Splitting successful"

def handle_for_loops(red, first, last):
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

    # TODO adjust loop.iterator and loop.target and set meta data to generate bpmn loop

    # check the beginning of the quantum part
    try:
        first_qc_index = red.index(first.parent)
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
                break
    return_condition = store_loop_condition(conditions)
    return first_qc_index, last_qc_index, return_condition


def store_loop_condition(conditions):
    """
    save the loop conditions

    :param conditions: list of conditions (iterator,value-space)
    :return: tuple of human-readable condition
    """
    if not conditions:
        return ()
    return conditions[0]


def get_req_vars(code):
    """
    compute all variable that a given code-snippet may need

    :param code: code-snippet to analyse
    :return: list of all required variables
    """
    # TODO optional
    vars = []

    return vars


def get_prov_vars(code):
    """
    helper function
    compute all variable that a given code-snippet may provide for other parts

    :param code: code-snippet to analyse
    :return: list of all provided variables
    """
    vars = []
    # TODO implement
    return vars

def get_last_index(red, nodes):
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
        # project needs the directory
        self.project = Project(filename[:filename.rfind("\\")])
        self.resource_original_name = filename
        self.resource_pre_name, self.resource_quantum_name, self.resource_post_name, self.output_file_name = self.init_files(
            filename)

        self.resource_original = libutils.path_to_resource(self.project, self.resource_original_name)
        self.output_file = libutils.path_to_resource(self.project, self.output_file_name)
        self.imports = []
        self.dst_pre, self.dst_quantum, self.dst_post, self.dst_out = self.init_files(filename)

    def init_files(self, filename):
        """
        Initialize (create) dummy-files that may be used as output as well
        :param filename: the original filename
        :return: names (str,str,str,str) of the new files
        """
        src = filename
        dst_pre = filename[:filename.rfind(".py")] + "_pre_file.py"
        dst_quantum = filename[:filename.rfind(".py")] + "_quantum_file.py"
        dst_post = filename[:filename.rfind(".py")] + "_post_file.py"
        dst_out = filename[:filename.rfind(".py")] + "_out.py"
        # clear the files if they exist; otherwise surprising things will happen...
        if os.path.exists(dst_out):
            os.remove(dst_out)
        # create files and copy content to output-file
        empty_pre = open(dst_pre, "w")
        empty_pre.close()
        empty_quantum = open(dst_quantum, "w")
        empty_quantum.close()
        empty_post = open(dst_post, "w")
        empty_post.close()
        copyfile(src, dst_out)
        return dst_pre, dst_quantum, dst_post, dst_out

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
        """
        # old
        if (part.offset[0] > part.offset[1]):
            # there is no pre part
            return
        extractor = ExtractMethod(self.project, self.output_file, part.offset[0], part.offset[1])
        changes = extractor.get_changes('pre_part')
        self.pre_part.changes = changes
        self.project.validate()
        self.project.do(changes)
        """

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
        """
        #old:
        extractor = ExtractMethod(self.project, self.output_file, part.offset[0], part.offset[1])
        changes = extractor.get_changes('quantum_part')
        self.quantum_part.changes = changes
        
        # self.project.validate()
        # self.project.do(changes)
        """

    def init_post(self, part):
        """
        Initialize postprocessing-part.
        Especially computes the changes to the source file.
        Additional information will be stored in the part object.
        :param part
        """
        self.pre_part = part
        # write quantum part to dst-file
        with open(self.dst_post, "w") as out:
            out.writelines(part.code_as_string)
        """
        # old
        extractor = ExtractMethod(self.project, self.output_file, part.offset[0], part.offset[1])
        changes = extractor.get_changes('post_part')
        self.post_part.changes = changes
        self.project.validate()
        self.project.do(changes)
        """

    def __do_backup(self):
        """
        Copy the source-file before refactoring.
        File will be saved under <source-path><source-name>_backup
        """
        src = self.filename
        dst = self.filename[:self.filename.rfind(".py")] + "_backup.py"
        copyfile(src, dst)

    def get_file_names(self):
        return self.resource_pre_name, self.resource_quantum_name, self.resource_post_name, self.output_file_name

    def set_imports(self, imports):
        self.imports = imports
