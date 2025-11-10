def test_regression_output(tmp_path):
    new_output = generate_report()
    with open("tests/regression_data/reference_report.txt") as ref:
        expected = ref.read()
    assert new_output == expected
