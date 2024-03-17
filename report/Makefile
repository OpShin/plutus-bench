# Makefile for compiling LaTeX documents

# Variables
DOC=main
PDF=$(DOC).pdf
TEX=$(wildcard *.tex)
BIB=$(wildcard *.bib)

# Main target
all: $(PDF)

# Compile PDF
$(PDF): $(TEX) $(BIB)
	pdflatex $(DOC)
	biber $(DOC)
	pdflatex $(DOC)
	pdflatex $(DOC)


# Clean auxiliary files
clean:
	rm -f $(DOC).aux $(DOC).bbl $(DOC).blg $(DOC).log $(DOC).out $(DOC).toc $(DOC).bcf $(DOC).run.xml

# Clean all files including PDF
distclean: clean
	rm -f $(PDF)

# Phony targets
.PHONY: all clean distclean
