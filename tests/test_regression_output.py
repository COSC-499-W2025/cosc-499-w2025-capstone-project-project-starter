# tests/test_regression_output.py
from src.regression.my_module import generate_report
import os

def test_regression_output(tmp_path):
    new_output = generate_report()

    # Path relative to *this file’s* location
    here = os.path.dirname(__file__)
    ref_path = os.path.join(here, "regression_data", "reference_report.txt")

    assert os.path.exists(ref_path), f"Reference file missing at {ref_path}"

    with open(ref_path, "r") as ref:
        expected = ref.read()

    assert new_output == expected, "Regression detected! Output differs from reference."
