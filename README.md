# Program Analysis with Chiron

A framework to teach program analysis, verification and testing in a graduate level course.

- [![Architecture Diagram](./assets/Architecture_diagram.png)](./assets/Architecture_diagram.png)

- [![Fuzzer Demo](./assets/Fuzzer_Demo.mp4)](./assets/Fuzzer_Demo.mp4)

### Installing Dependencies

```bash
pip install antlr4-python3-runtime==4.7.2
pip install networkx
pip install z3-solver numpy
sudo apt-get install python3-tk
```

### Generating the ANTLR files.

```
cd ChironCore/turtparse
java -cp ../extlib/antlr-4.7.2-complete.jar org.antlr.v4.Tool \
  -Dlanguage=Python3 -visitor -no-listener tlang.g4
```

### Running an example

The main directory for source files is `ChironCore`. We have examples of the turtle programs in `examples` folder.

```bash
$ cd ChironCore
$ ./chiron.py -r ./example/example1.tl
```

### See help for other command line options

```bash
$ ./chiron.py --help

Chiron v5.3
------------
usage: ./chiron.py [-h] [-p] [-r] [-O] [-b] [-z] [-t TIMEOUT] [-d PARAMS] [-c CONSTPARAMS] [-se] [-ai] [-dfa] [-sbfl] [-bg BUGGY] [-vars INPUTVARSLIST] [-nt NTESTS] [-pop POPSIZE] [-cp CXPB]
                 [-mp MUTPB] [-ng NGEN] [-vb VERBOSE]
                 progfl

Program Analysis Framework for Turtle.

positional arguments:
  progfl

options:
  -h, --help            show this help message and exit
  -p, --ir              pretty printing
  -r, --run             execute program
  -O, --opt             optimize
  -b, --bin             load binary IR
  -z, --fuzz            Run fuzzer on a turtle program (seed values with '-d' or '--params' flag needed.)
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout Parameter for Analysis (in secs)
  -d PARAMS, --params PARAMS
                        pass variable values to Chiron program in python dictionary format
  -c CONSTPARAMS, --constparams CONSTPARAMS
                        pass variable(for which you have to find values using circuit equivalence) values to Chiron program in python dictionary format
  -se, --symbolicExecution
                        Run Symbolic Execution on a turtle program (seed values with '-d' or '--params' flag needed) to generate test cases along all possible paths.
  -ai, --abstractInterpretation
                        Run abstract interpretation
  -dfa, --dataFlowAnalysis
                        Run data flow analysis using worklist algorithm
  -sbfl, --SBFL         Run Spectrum-basedFault localizer on turtle program
  -bg BUGGY, --buggy BUGGY
                        buggy turtle program path
  -vars INPUTVARSLIST, --inputVarsList INPUTVARSLIST
                        A list of input variables of given turtle program
  -nt NTESTS, --ntests NTESTS
                        number of tests to generate
  -pop POPSIZE, --popsize POPSIZE
                        population size for Genetic Algorithm.
  -cp CXPB, --cxpb CXPB
                        cross-over probability
  -mp MUTPB, --mutpb MUTPB
                        mutation probability
  -ng NGEN, --ngen NGEN
                        number of times Genetic Algorithm iterates
  -vb VERBOSE, --verbose VERBOSE
                        To display computation to Console

```
