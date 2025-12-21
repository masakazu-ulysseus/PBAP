#!/bin/bash
cd /home/masakazu/develop/claude-code/PBAP/poc
source /home/masakazu/develop/claude-code/PBAP/apps/admin-tool/.venv/bin/activate

mkdir -p output/assembly_numbers_v2/batch_validation_test

for f in input/AssemblyImage/sample/*.png; do
    name=$(basename "$f" .png)
    echo "=== $name ==="
    python extract_assembly_numbers_v2.py "$f" --debug -o "output/assembly_numbers_v2/batch_validation_test/$name" 2>&1 | grep -E "(Valid:|DONE|VALIDATION REJECT)"
done
