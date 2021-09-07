from pathlib import Path

from Splitter import scriptSplitter
#####################################################################
# use this script for debugging only
#####################################################################


if __name__ == '__main__':
    # windows path
    #filename = str(Path.cwd().resolve()) + '\\Test' +'\\testScript.py'
    # linux path
    filename = str(Path.cwd().resolve()) + '/Test' +'/testScript.py'
    out_file_names = scriptSplitter.split(filename)
