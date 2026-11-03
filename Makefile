.PHONY: run test demo

run:
	sh run.sh

test:
	python3 -B -m unittest discover -s tests -t .

demo:
	sh scripts/demo.sh
