from nbdev.export import nb_export
from nbdev.clean import clean_nb
from execnb.nbio import read_nb, write_nb
import glob
import os

# Run nbdev_prepare
print("Running nbdev_prepare...")
os.system("nbdev_prepare")
print("")

print("Running nbdev_test on test_nbs...")
print("-----")
os.system("nbdev_test --path test_nbs")
print("-----")
print("")

print("\nRunning cleaning and exporting tests...")

# Find all .ipynb files in nbs/tests recursively
notebook_files = glob.glob('test_nbs/**/*.ipynb', recursive=True)

# Clean test notebooks and export them
for notebook_file in notebook_files:
    nb = read_nb(notebook_file)
    clean_nb(nb) # Clean notebook file
    write_nb(nb, notebook_file) 
    nb_export(notebook_file, 'tests') # Export notebook file
    
# Copy all .py files in tests_nbs as well
py_files = glob.glob('test_nbs/**/*.py', recursive=True)
for py_file in py_files:
    destination = os.path.join('tests', os.path.relpath(py_file, 'test_nbs'))
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(py_file, 'r') as src, open(destination, 'w') as dst:
        dst.write(src.read())

# Run tests
print("\nRunning pytest...")
os.system("pytest")
