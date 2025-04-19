import os
import tempfile
import random
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import time


def generate_file(file_path: str, num_lines: int) -> None:
    """Generate a test file with random data lines"""
    with open(file_path, "w") as f:
        for _ in range(num_lines):
            f.write(f"line-{random.randint(1, num_lines)}\n")


def linear_search(lines, query):
    """Linear search implementation"""
    return query in lines


def binary_search(lines, query):
    """Binary search implementation (requires sorted list)"""
    low, high = 0, len(lines) - 1
    while low <= high:
        mid = (low + high) // 2
        if lines[mid] == query:
            return True
        elif lines[mid] < query:
            low = mid + 1
        else:
            high = mid - 1
    return False


def hash_based_search(lines, query):
    """Hash table-based search implementation"""
    return query in set(lines)


def trie_search(lines, query):
    """Trie-based search implementation"""
    from collections import defaultdict
    trie = defaultdict(dict)
    for line in lines:
        current = trie
        for char in line.strip():
            current = current.setdefault(char, {})
    current = trie
    for char in query:
        if char not in current:
            return False
        current = current[char]
    return True


def regex_search(lines, query):
    """Regular expression search implementation"""
    import re
    pattern = re.compile(re.escape(query))
    return any(pattern.search(line) for line in lines)


def benchmark_search(method, lines, query):
    """Benchmark a search method's performance"""
    start_time = time.perf_counter()
    method(lines, query)
    return (time.perf_counter() - start_time) * 1000


import pandas as pd
from collections import defaultdict


def run_benchmarks():
    # ... existing code ...

    # Use a dictionary to store results
    data = defaultdict(list)
    for name, size, time_taken in results:
        data["Algorithm"].append(name)
        data["File Size"].append(size)
        data["Time (ms)"].append(time_taken)

    # Create DataFrame from dictionary
    df = pd.DataFrame(data)

    # Explicit type conversion
    df["File Size"] = df["File Size"].astype(int)
    df["Time (ms)"] = df["Time (ms)"].astype(float)

    return df


def plot_results(df):
    """Plot benchmark results and save as image"""
    plt.figure(figsize=(12, 7))

    for algo in df["Algorithm"].unique():
        subset = df[df["Algorithm"] == algo]
        plt.plot(
            subset["File Size"],
            subset["Time (ms)"],
            label=algo,
            marker="o",
            linestyle="--"
        )

    plt.title("Search Algorithm Performance Comparison", fontsize=14)
    plt.xlabel("File Size (number of lines)", fontsize=12)
    plt.ylabel("Execution Time (milliseconds)", fontsize=12)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    graph_path = os.path.join(tempfile.gettempdir(), "performance_graph.png")
    plt.savefig(graph_path, dpi=300)
    plt.close()


def generate_pdf(df):
    """Generate PDF report from benchmark results"""
    pdf = FPDF()
    pdf.add_page()

    # Report header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Speed Testing Report", 0, 1, "C")

    # Results table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 10, "Algorithm", 1, 0, "C")
    pdf.cell(40, 10, "File Size", 1, 0, "C")
    pdf.cell(40, 10, "Time (ms)", 1, 1, "C")

    pdf.set_font("Arial", "", 10)
    for _, row in df.iterrows():
        pdf.cell(60, 10, row["Algorithm"], 1)
        pdf.cell(40, 10, str(row["File Size"]), 1, 0, "C")
        pdf.cell(40, 10, f"{row['Time (ms)']:.2f}", 1, 1, "C")

    # Add performance graph
    graph_path = os.path.join(tempfile.gettempdir(), "performance_graph.png")
    pdf.ln(10)
    pdf.image(graph_path, x=10, w=180)

    output_path = os.path.join(tempfile.gettempdir(), "speed_testing_report.pdf")
    pdf.output(output_path)


def main():
    """Main function to execute benchmarking and reporting"""
    df = run_benchmarks()
    plot_results(df)
    generate_pdf(df)
    print("Report generated: speed_testing_report.pdf")


if __name__ == "__main__":
    main()
