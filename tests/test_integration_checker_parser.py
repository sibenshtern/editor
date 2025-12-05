import os
import pytest
from checker.src.checker import FileChecker
from checker.src.report import Report
from netlist_model import NetlistProject

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), '..', 'test_files')

def test_checker_parser_integration_valid_file():
    """
    Test that FileChecker can successfully load a valid netlist file using the Parser
    and run checks on it.
    """
    file_path = os.path.join(TEST_FILES_DIR, 'test_file_1.net')
    
    # Ensure file exists
    assert os.path.exists(file_path), f"Test file not found: {file_path}"
    
    # Initialize FileChecker
    # This triggers loading the file via Parser
    checker = FileChecker(file_path)
    
    # Check if object model is loaded correctly
    netlist = checker.get_object_model()
    assert netlist is not None
    assert isinstance(netlist, NetlistProject)
    
    # Run checks
    report = checker.check()
    assert report is not None
    assert isinstance(report, Report)
    
    # Verify that we got some result (either success or failure, but a valid report)
    # We don't strictly assert success because test_file_1.net might have logical errors
    # that the checker is supposed to find.
    report_dict = report.to_dict()
    print(f"Report status: {report_dict['status']}")
    print(f"Report entries: {len(report_dict['errors'])}")

def test_checker_parser_integration_nonexistent_file():
    """
    Test that FileChecker raises an error when trying to load a nonexistent file.
    """
    file_path = os.path.join(TEST_FILES_DIR, 'nonexistent_file.net')
    
    # Expecting an error when loading a non-existent file
    # FileStream in parser likely raises FileNotFoundError or IOError
    with pytest.raises((FileNotFoundError, IOError)):
        FileChecker(file_path)
