window.BENCHMARK_DATA = {
  "lastUpdate": 1722847908494,
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
      },
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
          "id": "d98651b8a9cd527299739963179c63617ec24591",
          "message": "feat: add ply to benchmarks",
          "timestamp": "2024-08-04T16:51:07+05:30",
          "tree_id": "241251c04835e0e4ada8e2ef6699f06d36738c0e",
          "url": "https://github.com/xonsh/peg-parser/commit/d98651b8a9cd527299739963179c63617ec24591"
        },
        "date": 1722770706722,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/test_bench.py::TestBenchSmallString::test_peg",
            "value": 1699.8403430711694,
            "unit": "iter/sec",
            "range": "stddev: 0.000042747789210107655",
            "extra": "mean: 588.2905439185306 usec\nrounds: 296"
          },
          {
            "name": "tests/test_bench.py::TestBenchSmallString::test_ply",
            "value": 4565.591520228812,
            "unit": "iter/sec",
            "range": "stddev: 0.000024358606487752092",
            "extra": "mean: 219.02966911719759 usec\nrounds: 272"
          },
          {
            "name": "tests/test_bench.py::TestBenchLargeFile::test_pegen",
            "value": 0.2807886967024433,
            "unit": "iter/sec",
            "range": "stddev: 0.037457739869209784",
            "extra": "mean: 3.561396921400001 sec\nrounds: 5"
          },
          {
            "name": "tests/test_bench.py::TestBenchLargeFile::test_ply",
            "value": 0.8259526905716784,
            "unit": "iter/sec",
            "range": "stddev: 0.003495319902386961",
            "extra": "mean: 1.2107230976000039 sec\nrounds: 5"
          }
        ]
      },
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
          "id": "c034deaa8e177818ab411b040b41168d64c1b74b",
          "message": "feat: add RSS memory benchmarks",
          "timestamp": "2024-08-05T14:18:25+05:30",
          "tree_id": "bcf0d7c2882b47eb76205849733cea46de89dc05",
          "url": "https://github.com/xonsh/peg-parser/commit/c034deaa8e177818ab411b040b41168d64c1b74b"
        },
        "date": 1722847908215,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/benchmarks.py::test_small_string[PegenParser]",
            "value": 896.2296755716459,
            "unit": "iter/sec",
            "range": "stddev: 0.00020009198876808827",
            "extra": "mean: 1.1157854144498907 msec\nrounds: 263"
          },
          {
            "name": "tests/benchmarks.py::test_small_string[PlyParser]",
            "value": 4873.27312455981,
            "unit": "iter/sec",
            "range": "stddev: 0.00003215469732798724",
            "extra": "mean: 205.20089361712667 usec\nrounds: 282"
          },
          {
            "name": "tests/benchmarks.py::test_large_file[PegenParser]",
            "value": 0.2732118723210195,
            "unit": "iter/sec",
            "range": "stddev: 0.040736558881720245",
            "extra": "mean: 3.660163050400007 sec\nrounds: 5"
          },
          {
            "name": "tests/benchmarks.py::test_large_file[PlyParser]",
            "value": 0.8221646372702258,
            "unit": "iter/sec",
            "range": "stddev: 0.010090562730284986",
            "extra": "mean: 1.2163014008000004 sec\nrounds: 5"
          }
        ]
      }
    ]
  }
}