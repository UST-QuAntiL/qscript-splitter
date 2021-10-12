from pathlib import Path

from Splitter import scriptParser
#####################################################################
# use this script for debugging only
#####################################################################


if __name__ == '__main__':
    # take care with the file-path
    filename = str(Path.cwd().resolve()) + '/Example' + '/exampleScript.py'
    result = scriptParser.analyze(filename)
