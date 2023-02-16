run:
  python3 sunspec_json.py
profile:
  python3 -m cProfile -o profile.log sunspec_json.py
results:
  python3 traceout.py | bat
