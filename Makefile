PY=.venv/bin/python

.PHONY: setup build build-offline preview test check all
setup:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

check:          ## verify markup follows the TRMNL X structure
	$(PY) tests/check_structure.py

build:          ## fetch live openfootball data -> output/trmnl_data.json
	$(PY) src/build_data.py

build-offline:  ## use cached data/ files
	$(PY) src/build_data.py --matches data/worldcup.json --teams data/worldcup.teams.json

preview:        ## render the 4 layouts to preview/*.html
	$(PY) src/render_preview.py

test:
	$(PY) tests/test_standings.py

all: check test build preview
