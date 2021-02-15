
=============
 PYAML-TESTS
=============
----------------------------------------------------------
 pytest wrapper for using yaml files for tests declaration
----------------------------------------------------------

Installation
============

1. Install poetry
2. poetry build
3. pip install the pacakge .whl file (or poetry add in your project)


Tests dir structure in your project
===================================

project's root/
    tests/
        operations/
        specs/

operations - holds the test functions written in python
specs - holds the parameteres for the test functions


Examples
========

See examples dir


Run
===

1. export MY_WORKSPACE=<workspace>
2. RUN: dunk --project <your project_name(root) [options]


Help
====

dunk --help
