.PHONY: all layout layout-check rules reachability audio-check static blockout audit

all: layout-check rules reachability audio-check static

layout:        ## regenerate the L0_B01 layout JSON from its source
	python3 tools/levelgen/l0_b01_layout_src.py

layout-check:
	python3 tools/levelgen/l0_b01_layout_src.py --check

rules:         ## build + run the engine-independent gameplay rules tests
	cmake -S tests/core -B build/core >/dev/null && cmake --build build/core && ./build/core/confession_rules_tests

reachability:  ## offline capsule/route/LOS/soft-lock check of the layout (not an engine test)
	python3 tools/layout_reachability.py

audio-check:   ## WAV format contract + loudness (needs numpy, scipy)
	python3 tools/audio/analyze_sfx.py

static:
	python3 tools/handoff_preflight.py && python3 tools/studio_static_audit.py && python3 -m unittest discover -s tests -v

blockout:
	python production/scripts/build_scene01_blockout.py

audit:
	python production/scripts/quality_gate.py
