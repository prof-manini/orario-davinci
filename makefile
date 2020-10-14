all:
	echo "No default target"

pdf: README.pdf

%.pdf: %.tex
	pdflatex --shell-escape $<
	pdflatex --shell-escape $<

clean:
	rm -f *~
	rm -rf __pycache__/
	rm -f *.toc *.log *.out *.aux

cleaner: clean
	rm -f *.tex *.pdf
