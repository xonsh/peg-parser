window.BENCHMARK_DATA = {
  "lastUpdate": 1722882273926,
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
          "id": "32781d0d612ed473ecddeb729db86b844db89e8e",
          "message": "refactor: show mem usage in MB",
          "timestamp": "2024-08-05T14:30:31+05:30",
          "tree_id": "bc1c9c2eee45c34e0ffed6ce492eb80391c0588b",
          "url": "https://github.com/xonsh/peg-parser/commit/32781d0d612ed473ecddeb729db86b844db89e8e"
        },
        "date": 1722848635129,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/benchmarks.py::test_small_string[PegenParser]",
            "value": 932.200179064186,
            "unit": "iter/sec",
            "range": "stddev: 0.0000909917672332255",
            "extra": "mean: 1.0727309675094425 msec\nrounds: 277"
          },
          {
            "name": "tests/benchmarks.py::test_small_string[PlyParser]",
            "value": 4865.762380838405,
            "unit": "iter/sec",
            "range": "stddev: 0.00002348851276145656",
            "extra": "mean: 205.51763973063004 usec\nrounds: 297"
          },
          {
            "name": "tests/benchmarks.py::test_large_file[PegenParser]",
            "value": 0.2764852287793625,
            "unit": "iter/sec",
            "range": "stddev: 0.019710433530694425",
            "extra": "mean: 3.6168297467999935 sec\nrounds: 5"
          },
          {
            "name": "tests/benchmarks.py::test_large_file[PlyParser]",
            "value": 0.8317638791787315,
            "unit": "iter/sec",
            "range": "stddev: 0.0070624719632339",
            "extra": "mean: 1.202264278399997 sec\nrounds: 5"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "jnoortheen@gmail.com",
            "name": "Noorhteen Raja NJ",
            "username": "jnoortheen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "13c6f5a264e16fd872bad7d5175c16b831990f08",
          "message": "Update README.md",
          "timestamp": "2024-08-05T23:50:45+05:30",
          "tree_id": "52724d1f2efcf4fa6ca1ee8fe185a226f5056c01",
          "url": "https://github.com/xonsh/peg-parser/commit/13c6f5a264e16fd872bad7d5175c16b831990f08"
        },
        "date": 1722882273522,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/benchmarks.py::test_small_string[PegenParser]",
            "value": 784.152645035499,
            "unit": "iter/sec",
            "range": "stddev: 0.00014580440965740544",
            "extra": "mean: 1.275261910204651 msec\nrounds: 245"
          },
          {
            "name": "tests/benchmarks.py::test_small_string[PlyParser]",
            "value": 4839.323072021572,
            "unit": "iter/sec",
            "range": "stddev: 0.000042377670483403984",
            "extra": "mean: 206.64047122240615 usec\nrounds: 278"
          },
          {
            "name": "tests/benchmarks.py::test_large_file[PegenParser]",
            "value": 0.2508863304127013,
            "unit": "iter/sec",
            "range": "stddev: 0.02990058949686182",
            "extra": "mean: 3.985868813000002 sec\nrounds: 5"
          },
          {
            "name": "tests/benchmarks.py::test_large_file[PlyParser]",
            "value": 0.8178733848936967,
            "unit": "iter/sec",
            "range": "stddev: 0.0032969425151600784",
            "extra": "mean: 1.2226831419999997 sec\nrounds: 5"
          }
        ]
      }
    ]
  }
}