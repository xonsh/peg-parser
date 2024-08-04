window.BENCHMARK_DATA = {
  "lastUpdate": 1722737162359,
  "repoUrl": "https://github.com/xonsh/peg-parser",
  "entries": {
    "Python Benchmark": [
      {
        "commit": {
          "author": {
            "email": "jnoortheen@gmail.com",
            "name": "Noortheen Raja",
            "username": "jnoortheen"
          },
          "committer": {
            "email": "jnoortheen@gmail.com",
            "name": "Noortheen Raja",
            "username": "jnoortheen"
          },
          "distinct": true,
          "id": "1832aa3f7158931c7288c0230707085e4b29e71b",
          "message": "chore(ci): check permissions to push to gh-pages",
          "timestamp": "2024-08-04T07:33:52+05:30",
          "tree_id": "e2ef16d569fae93c75953915236943ebf51de9f6",
          "url": "https://github.com/xonsh/peg-parser/commit/1832aa3f7158931c7288c0230707085e4b29e71b"
        },
        "date": 1722737162126,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/test_bench.py::TestBenchSmallString::test_peg",
            "value": 1715.768488421814,
            "unit": "iter/sec",
            "range": "stddev: 0.00001809392848078461",
            "extra": "mean: 582.829214283923 usec\nrounds: 14"
          },
          {
            "name": "tests/test_bench.py::TestBenchLargeFile::test_pegen",
            "value": 0.28298407356437033,
            "unit": "iter/sec",
            "range": "stddev: 0.041867817101583986",
            "extra": "mean: 3.5337677749999954 sec\nrounds: 5"
          }
        ]
      }
    ]
  }
}