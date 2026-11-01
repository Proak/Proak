.PHONY: blockout audit
blockout:
	python production/scripts/build_scene01_blockout.py

audit:
	python production/scripts/quality_gate.py
