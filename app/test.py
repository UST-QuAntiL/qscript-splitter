import os

from app.script_splitting.script_handler import split_qc_script

basedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
templatesDirectory = os.path.join(basedir, 'files')
script = os.path.join(templatesDirectory, 'example.py')

split_qc_script(script)

print(script)