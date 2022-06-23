import argparse
from Simulator import Processor as CPU


class InstructionFileReader:
    def __init__(self, instructionCount):
        self.reference = {}
        self.instructions = [None] * (instructionCount * 4)

    def decode(self, lines):
        for i in range(len(lines)):
            line = lines[i]
            if ":" in line:
                refer, line = line.split(":")
                self.reference[refer] = i * 4
            if "bne" in line:
                for key in self.reference.keys():
                    if key in line:
                        line = line.replace(key, str(self.reference[key]))
            self.instructions[i * 4] = line.replace("\n", "").strip()
        return self.instructions


def readConfigurationFile(configFile):
    parameters = configFile
    return parameters


def readProgramFile(programFile):
    file = open(programFile, "r")
    lines = file.readlines()
    file.close()
    instruct = InstructionFileReader(len(lines))
    program = instruct.decode(lines)
    return program


def readMemoryFile(memoryFile):
    file = open(memoryFile, "r")
    lines = file.readlines()
    file.close()
    length = int(lines[-1].split(",")[0].strip()) + 1
    RAM = [0] * length
    for i in range(len(lines)):
        line = lines[i]
        address, value = line.split(",")
        address, value = int(address.strip()), int(value.strip())
        RAM[address] = value
    return RAM


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Enter the program file name")
    parser.add_argument('--I_file_name', help="Program File", default="program.txt")
    parser.add_argument('--M_file_name', help="Memory Program File", default="memory.txt")
    parser.add_argument('--NF', help="NF", default=4)
    parser.add_argument('--NW', help="NW", default=4)
    parser.add_argument('--NR', help="NR", default=16)
    parser.add_argument('--NB', help="NB", default=4)
    args = parser.parse_args()
    programFile = args.I_file_name
    memoryFile = args.M_file_name
    config = readConfigurationFile({"NF": int(args.NF), "NW": int(args.NW), "NR": int(args.NR), "NB": int(args.NB)})
    instructionFile = readProgramFile(programFile)
    MainMemory = readMemoryFile(memoryFile)
    print("Running Simulation....")
    simulation = CPU.Processor(config, MainMemory, instructionFile)
    simulation.begin()
    print("Simulation Complete, please check logs/simulationLogs for results")
