from z3 import *
import argparse
import json
import sys

sys.path.insert(0, "../ChironCore/")

from interfaces.sExecutionInterface import *
import z3solver as zs
from irhandler import *
from interpreter import *
import ast


def example(s):
    # To add symbolic variable x to solver
    s.addSymbVar("x")
    s.addSymbVar("y")
    # To add constraint in form of string
    s.addConstraint("x==5+y")
    s.addConstraint("And(x==y,x>5)")
    # s.addConstraint('Implies(x==4,y==x+8')
    # To access solvers directly use s.s.<function of z3>()
    print("constraints added till now", s.s.assertions())
    # To assign z=x+y
    s.addAssignment("z", "x+y")
    # To get any variable assigned
    print("variable assignment of z =", s.getVar("z"))


def checkEq(args, ir):
    file1 = open("../Submission/testData.json", "r+")
    testData = json.loads(file1.read())
    file1.close()
    s = zs.z3Solver()
    testData = convertTestData(testData)
    print(testData)
    # output = args.output
    # example(s)
    # TODO: write code to check equivalence


if __name__ == "__main__":
    cmdparser = argparse.ArgumentParser(
        description="symbSubmission for assignment Program Synthesis using Symbolic Execution"
    )
    cmdparser.add_argument("progfl")
    cmdparser.add_argument("-b", "--bin", action="store_true", help="load binary IR")
    cmdparser.add_argument(
        "-e",
        "--output",
        default=list(),
        type=ast.literal_eval,
        help="pass variables to Chiron program in python dictionary format",
    )
    args = cmdparser.parse_args()
    ir = loadIR(args.progfl)
    checkEq(args, ir)
    exit()
