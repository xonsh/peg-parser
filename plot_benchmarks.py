#!/usr/bin/env python3
import glob
import json
import sys
from datetime import datetime


def get_benchmarks(pattern, test_name):
    # Search in .benchmarks/platform-name/*.json
    files = glob.glob(pattern, recursive=True)
    results = []

    for filename in files:
        with open(filename) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

            # Prefer commit time, fallback to file datetime
            timestamp_str = data.get("commit_info", {}).get("time") or data.get("datetime")
            if not timestamp_str:
                continue

            try:
                # Handle ISO format with Z or offsets
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            for bench in data.get("benchmarks", []):
                # Match by fullname to be specific
                if test_name == bench["fullname"]:
                    results.append(
                        {
                            "time": timestamp.isoformat(),
                            "mean_ms": bench["stats"]["mean"] * 1000,
                            "ops": bench["stats"]["ops"],
                            "commit": data.get("commit_info", {}).get("id", "unknown")[:7],
                            "rounds": bench["stats"]["rounds"],
                        }
                    )
                    break

    # Sort chronologically
    results.sort(key=lambda x: x["time"])
    return results


def plot_results(results, test_name, output_file):
    if not results:
        print(f"No results found for exactly: {test_name}")
        return

    data_json = json.dumps(results, indent=2)

    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Trend: {test_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f1f5f9; margin: 40px; }}
        .container {{ max-width: 1100px; margin: auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.4); border: 1px solid #334155; }}
        h2 {{ text-align: center; color: #38bdf8; margin-bottom: 30px; font-weight: 600; }}
        .info {{ margin-top: 20px; font-size: 0.9em; color: #94a3b8; text-align: center; }}
        .controls {{ text-align: center; margin-top: 10px; }}
        button {{ background: #334155; color: #f1f5f9; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #475569; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Performance Trend: {test_name}</h2>
        <canvas id="benchmarkChart"></canvas>
        <div class="info">Wheel to Zoom, Drag to Pan. Hover for details.</div>
        <div class="controls">
            <button onclick="resetZoom()">Reset Zoom</button>
        </div>
    </div>

    <script>
        const rawData = {data_json};

        const labels = rawData.map(d => new Date(d.time));
        const means = rawData.map(d => d.mean_ms);

        const ctx = document.getElementById('benchmarkChart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Mean Execution Time (ms)',
                    data: means,
                    borderColor: '#0ea5e9',
                    backgroundColor: 'rgba(14, 165, 233, 0.1)',
                    borderWidth: 3,
                    pointRadius: 6,
                    pointHoverRadius: 10,
                    pointBackgroundColor: '#0ea5e9',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    tension: 0.3,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                interaction: {{
                    mode: 'index',
                    intersect: false,
                }},
                scales: {{
                    x: {{
                        type: 'time',
                        time: {{ unit: 'day' }},
                        title: {{ display: true, text: 'Timeline', color: '#94a3b8', font: {{ size: 14 }} }},
                        ticks: {{ color: '#94a3b8' }},
                        grid: {{ color: '#334155' }}
                    }},
                    y: {{
                        title: {{ display: true, text: 'Execution Time (ms)', color: '#94a3b8', font: {{ size: 14 }} }},
                        ticks: {{ color: '#94a3b8' }},
                        grid: {{ color: '#334155' }},
                        beginAtZero: false
                    }}
                }},
                plugins: {{
                    zoom: {{
                        zoom: {{
                            wheel: {{ enabled: true }},
                            pinch: {{ enabled: true }},
                            mode: 'x',
                        }},
                        pan: {{
                            enabled: true,
                            mode: 'x',
                        }}
                    }},
                    tooltip: {{
                        backgroundColor: '#1e293b',
                        titleColor: '#38bdf8',
                        bodyColor: '#f1f5f9',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {{
                            label: function(context) {{
                                const d = rawData[context.dataIndex];
                                return [
                                    ' Mean: ' + d.mean_ms.toFixed(3) + ' ms',
                                    ' OPS: ' + d.ops.toFixed(1),
                                    ' Commit: ' + d.commit,
                                    ' Rounds: ' + d.rounds
                                ];
                            }}
                        }}
                    }},
                    legend: {{
                        labels: {{ color: '#f1f5f9', font: {{ size: 13 }} }}
                    }}
                }}
            }}
        }});

        function resetZoom() {{
            chart.resetZoom();
        }}
    </script>
</body>
</html>
"""
    with open(output_file, "w") as f:
        f.write(html_template)
    print(f"Successfully generated JS-based interactive chart at: {output_file}")


if __name__ == "__main__":
    test_target = "tests/benchmarks.py::test_large_file[PegenParser]"
    if len(sys.argv) > 1:
        test_target = sys.argv[1]

    print(f"Generating JS-based interactive plot for: {test_target}")

    benchmark_pattern = ".benchmarks/**/*.json"
    output_name = f"benchmark_trend_{test_target.split('::')[-1].replace('[', '_').replace(']', '_')}.html"

    data = get_benchmarks(benchmark_pattern, test_target)
    plot_results(data, test_target, output_name)
