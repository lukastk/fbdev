from nbdev.export import nb_export
import glob
import os

# Find all .ipynb files in nbs/tests recursively
notebook_files = glob.glob('test_nbs/**/*.ipynb', recursive=True)

# Export each notebook file
for notebook_file in notebook_files:
    nb_export(notebook_file, 'tests')