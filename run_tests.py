from nbdev.export import nb_export
from nbdev.clean import clean_nb
from execnb.nbio import read_nb, write_nb
import glob
import os

# Find all .ipynb files in nbs/tests recursively
notebook_files = glob.glob('test_nbs/**/*.ipynb', recursive=True)

# Clean test notebooks and export them
for notebook_file in notebook_files:
    nb = read_nb(notebook_file)
    clean_nb(nb) # Clean notebook file
    write_nb(nb, notebook_file) 
    nb_export(notebook_file, 'tests') # Export notebook file
    
# Run tests
os.system("pytest")
