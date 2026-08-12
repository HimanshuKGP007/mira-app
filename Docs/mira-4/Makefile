.PHONY: test demo serve check install

install:
	pip install -e ".[serve,dev]"

test:
	python -m pytest tests -q

check:
	python -m mira_app check

demo:
	python -m mira_app demo -n 14 --out out/demo.html
	@echo "open out/demo.html"

serve:
	python -m mira_app serve --synthetic
