# Minimal makefile for Sphinx documentation
#
# The build directory is named ``build`` rather than the Sphinx default
# ``_build`` so that it is covered by the ``build/`` rule already present in
# the repository .gitignore.

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Sphinx's own clean target empties the output directory but leaves the
# directory itself behind, so remove it here instead.
clean:
	rm -rf $(BUILDDIR)

.PHONY: help clean Makefile

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
