import os
import tempfile
from benchmark_file_search import (
    generate_file,
    linear_search,
    binary_search,
    hash_based_search,
    benchmark_search,
)


def test_generate_file():
    # Test that the file is generated with the correct number of lines.
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test_file.txt")
        num_lines = 100
        generate_file(file_path, num_lines)

        with open(file_path, "r") as f:
            lines = f.readlines()

        assert len(lines) == num_lines


def test_linear_search():
    # Test that linear search correctly finds or doesn't find elements.
    lines = ["line-1", "line-2", "line-3"]
    assert linear_search(lines, "line-2") is True
    assert linear_search(lines, "line-4") is False


def test_binary_search():
    # Test that binary search works on sorted data.
    lines = ["line-1", "line-2", "line-3"]
    lines.sort()
    assert binary_search(lines, "line-2") is True
    assert binary_search(lines, "line-4") is False


def test_hash_based_search():
    # Test that hash-based search correctly finds or doesn't find elements.
    lines = ["line-1", "line-2", "line-3"]
    assert hash_based_search(lines, "line-2") is True
    assert hash_based_search(lines, "line-4") is False


def test_benchmark_search():
    # Test if benchmark search runs without errors
    # and returns a non-negative time.
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test_file.txt")
        num_lines = 100
        generate_file(file_path, num_lines)

        query = "line-1"
        time_taken = benchmark_search(linear_search, file_path, query)

        assert time_taken >= 0
