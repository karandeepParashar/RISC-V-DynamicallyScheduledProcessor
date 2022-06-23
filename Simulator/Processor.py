import logging, re
from Simulator.InstructionClass import Instruction
from Simulator.RegisterHandler import FreeRegisterTable, RegisterMappingTable, RegisterFile
from Simulator.ReservationStationAndROB import ReservationStation, ReorderBuffer, ReservationStationUnity


def decodeHelper(instruction):
    op, inst = instruction.split(" ", 1)
    if op in ["add", "addi", "fadd", "fsub", "fmul", "fdiv"]:
        d, s1, s2 = inst.split(",")
    elif op in ["fld", "fsd"]:
        d, inst = inst.split(",")
        s1, s2 = inst.split("(")
        s2 = s2.replace(")", "")
    elif op in ["bne"]:
        d, s1, s2 = inst.split(",")
    op, d, s1, s2 = op.strip(), d.strip(), s1.strip(), s2.strip()
    return Instruction(op, d, s1, s2)


def checkForRegister(s):
    if s is None:
        return False
    if s[0] in ['-', '+']:
        return not s[1:].isdigit()
    return not s.isdigit()


class Processor:
    def __init__(self, config, MainMemory, instructionFile):
        self.instructionFile = instructionFile
        self.PC = 0
        self.cycle = 0
        self.finished = False

        # Setting Configuration Values
        self.NF, self.NW, self.NR, self.NB = config['NF'], config['NW'], config['NR'], config['NB']
        self.MainMemory = MainMemory

        # Building Register File
        self.registers = RegisterFile(32)
        self.freeRegisters = FreeRegisterTable(list(self.registers.registers.keys()))
        self.registerMappingTable = RegisterMappingTable()

        # Building Reservation Stations
        self.ReservationStation = ReservationStationUnity()

        # Building ReorderBuffer Table
        self.ROB = ReorderBuffer(self.NR)

        # Building Common Data Bus
        self.CommonDataBus = []

        # Instruction Queue
        self.DecodeQueue = []
        self.InstructionQueue = []

        self.stalls = {"RS": 0, "ROB": 0, "CDB": 0}

        # Branch Prediction BTB
        self.BTB = {}
        self.BranchPrediction = False

    # fetch instructions as NF size, push them to Decode Queue
    def fetch(self, instructionFile):
        logging.info(f"[{self.cycle}]: STATE: FETCH")
        windowSize = self.NF
        for i in range(windowSize):
            if self.PC >= len(instructionFile):
                return self.DecodeQueue
            instruction = instructionFile[self.PC]
            logging.info(f"[{self.cycle}]::Fetch:[{self.PC}]:: {instruction}")
            self.DecodeQueue.append(instruction)
            self.PC = self.PC + 4
        logging.info("")
        return self.DecodeQueue

    # Register Renaming and Mapping for each register
    def registerRenaming(self, register, isDestination=False):
        renamedRegister = self.registerMappingTable.isAlreadyMapped(register)
        if renamedRegister is None or isDestination is True:
            renamedRegister = self.freeRegisters.isAvailable()
            if renamedRegister is not None:
                self.registerMappingTable.registerRenaming(register, renamedRegister)
            else:
                raise Exception("No register free!")
        return renamedRegister

    def registerMappingHelper(self, s1=None, s2=None, d=None):
        try:
            if s1 is not None:
                s1 = self.registerRenaming(s1)
            if s2 is not None:
                s2 = self.registerRenaming(s2)
            if d is not None:
                d = self.registerRenaming(d, True)
            return s1, s2, d
        except Exception:
            raise Exception("No register free!")

    # Parsing Instructions and Register Renaming being Called as per Instruction Type
    def registerMapping(self, instruction):
        try:
            op = instruction.op
            if op in ["addi"]:
                # d, s1
                instruction.s1, _, instruction.dR = self.registerMappingHelper(instruction.s1, None, instruction.d)
            elif op in ["add", "fmul", "fdiv", "fadd", "fsub"]:
                # d, s1, s2
                instruction.s1, instruction.s2, instruction.dR = self.registerMappingHelper(instruction.s1,
                                                                                            instruction.s2,
                                                                                            instruction.d)
            elif op in ["fld"]:
                # d, s2
                _, instruction.s2, instruction.dR = self.registerMappingHelper(None, instruction.s2, instruction.d)
            elif op in ["fsd"]:
                instruction.s1, instruction.s2 = self.registerRenaming(instruction.s1), self.registerRenaming(
                    instruction.s2)
            elif op in ["bne"]:
                # d, s1
                instruction.s1, instruction.s2 = self.registerRenaming(instruction.s1), self.registerRenaming(
                    instruction.s2)
        except Exception:
            raise Exception("No register free!")

    # Create an ROB Entry for the Instruction
    def createROBEntry(self, instruction):
        robEntry = self.ROB.getROB()
        robEntry.state = "Decode"
        robEntry.busy = True
        robEntry.inst_id = instruction.instructionId
        # Setup the Reservation Stations Entry
        robEntry.inst = instruction.instruction
        robEntry.dest = instruction.d
        if not instruction.op in ["fsd", "bne"]:
            robEntry.RR = instruction.dR
            # Now we need to map the ROB with RR register
            robRegister = self.registers.registers[instruction.dR]
            if robRegister:
                robRegister.rename = robEntry.name
                robRegister.busy = True
        return robEntry

    # Create Reservation Station and ROB Entry
    def createROBAndRSEntryHelper(self, instruction):
        # Fetch a RS
        rs = self.ReservationStation.getStation(instruction.op)
        rs.instId = instruction.instructionId
        rs.busy = True
        # Create a ROB Entry
        robEntry = self.createROBEntry(instruction)
        rs.op = instruction.op
        rs.dest = robEntry.name
        rs.instruction = instruction.instruction
        # Update RS Entry for Vj, Vk or Qj, Qk
        if checkForRegister(instruction.s1):
            s1 = self.registers.registers[instruction.s1]
            if not s1.busy:
                rs.vj = s1.name
            else:
                rs.qj = s1.rename
        else:
            rs.vj = instruction.s1
        if checkForRegister(instruction.s2):
            s2 = self.registers.registers[instruction.s2]
            if not s2.busy:
                rs.vk = s2.name
            else:
                rs.qk = s2.rename
        else:
            rs.vk = instruction.s2

    # Checking for available ROB free and Reservation Station free and implementing accordingly
    def createROBAndRSEntry(self):
        # Loop over Instruction Queue for creating an ROB and RS Entry
        for i in range(self.NW):
            if not self.InstructionQueue:
                return
            instruction = self.InstructionQueue.pop(0)
            # returns True if free rob entry else False
            rob = self.ROB.isAvailable()
            if rob:
                # returns True if free RS else False
                rs = self.ReservationStation.isAvailable(instruction.op)
                if rs:
                    self.createROBAndRSEntryHelper(instruction)
                else:
                    # stalls for one instruction if RS not available
                    self.stalls["RS"] += 1
                    self.InstructionQueue.insert(0, instruction)
                    return
            else:
                # Stalls for all if no ROB available
                self.stalls["ROB"] += 1
                self.InstructionQueue.insert(0, instruction)
                return

    # Branch Prediction
    def predictBranch(self, instruction):
        if not self.BranchPrediction:
            return self.PC
        address = self.instructionFile.index(instruction.instruction)
        address = format(address, "b")
        value = self.BTB.get(address)
        if value is None:
            self.BTB[address] = int(instruction.d)
        return self.BTB[address]

    # Instruction Decode, Register Mapping, Register Renaming, Reservation Station and ROB Entry
    def decode(self):
        logging.info(f"[{self.cycle}]: STATE: DECODE")
        # Instruction Decode Step into Instruction Object
        while len(self.DecodeQueue) > 0:
            instruction = self.DecodeQueue.pop(0)
            try:
                instructionObj = decodeHelper(instruction)
                # Register Renaming
                self.registerMapping(instructionObj)
                instructionObj.instruction = instruction
                logging.info(f"[{self.cycle}]: {str(instructionObj)}")
                self.InstructionQueue.append(instructionObj)
                if instructionObj.op == "bne":
                    self.PC = self.predictBranch(instructionObj)
            except Exception:
                self.DecodeQueue.insert(0, instruction)
                logging.info(f"[{self.cycle}]:: Exiting Decoding as no register in free list.")
                break
        # Creating and ROB and RS Entry
        self.createROBAndRSEntry()
        # Log ALl Tables and Mappings
        logging.info(f"\nRegister Mapping: {self.registerMappingTable.mappingTable}\n")
        logging.info(f"Free Registers: {self.freeRegisters.freeRegisters}\n")
        logging.info(f"Register Values: {str(self.registers)}\n")
        logging.info(str(self.ROB))
        logging.info(str(self.ReservationStation))

    # Execute All Reservation Station's Functional Units
    def execute(self):
        logging.info(f"[{self.cycle}]: STATE: EXECUTE")
        # Execute All Reservation Stations
        self.ReservationStation.execute(self.CommonDataBus, self.ROB, self.registers, self.MainMemory,
                                        self.registerMappingTable.mappingTable)
        # Log ALl Tables and Mappings
        logging.info(f"\nRegister Mapping: {self.registerMappingTable.mappingTable}\n")
        logging.info(f"Free Registers: {self.freeRegisters.freeRegisters}\n")
        logging.info(f"Register Values: {str(self.registers)}\n")
        logging.info(str(self.ROB))
        logging.info(str(self.ReservationStation))
        self.CommonDataBus = []

    # Write Back stage for entries that have completed execution
    def writeBack(self):
        robEntries = self.ROB.entries
        for robEntry in robEntries:
            if robEntry.state == "Execution Complete":
                robEntry.state = "Ready For WriteBack"
            elif robEntry.state == "Ready For WriteBack":
                if len(self.CommonDataBus) < self.NB:
                    self.CommonDataBus.append([robEntry.name, robEntry.RR])
                    robEntry.state = "WriteBack"
                else:
                    self.stalls["CDB"] += 1
                    logging.info(f"Common Data Bus: {str(self.CommonDataBus)}\n")
                    return
        logging.info(f"Common Data Bus: {str(self.CommonDataBus)}\n")

    # Updating the register file, freeing registers and updating values
    def updateRegisterFile(self, rob, robRegister):
        if robRegister is None:
            return
        register = self.registers.registers[robRegister]
        originalRegister = rob.dest
        if register.name == self.registerMappingTable.mappingTable[originalRegister][0]:
            register.busy = False
            register.rename = None
        else:
            if register.name in self.registerMappingTable.mappingTable[originalRegister]:
                self.registerMappingTable.mappingTable[originalRegister].remove(register.name)
            register.busy = False
            self.registers.registers[self.registerMappingTable.mappingTable[originalRegister][0]].value = register.value
            self.freeRegisters.addRegister(register.name)

    # Flushing the instructions in case of mis-prediction
    def branchFlush(self):
        logging.info(f"[{self.cycle}]: BRANCH FLUSH")
        self.ROB.tail = self.ROB.tail - 1 if self.ROB.tail > 0 else len(self.ROB.entries) - 1
        while self.ROB.head != self.ROB.tail:
            if self.ROB.head == self.ROB.tail:
                continue
            robEntry = self.ROB.entries[self.ROB.tail]
            robEntry.busy = False
            robRegister = robEntry.RR
            if robRegister is not None:
                register = self.registers.registers[robRegister]
                originalRegister = robEntry.dest
                if checkForRegister(originalRegister) and register.name in self.registerMappingTable.mappingTable[
                    originalRegister]:
                    self.registerMappingTable.mappingTable[originalRegister].remove(register.name)
                register.busy = False
                self.freeRegisters.addRegister(register.name)
            self.ROB.tail = self.ROB.tail - 1 if self.ROB.tail > 0 else len(self.ROB.entries) - 1
        self.ROB.tail = self.ROB.head + 1
        if self.ROB.tail >= len(self.ROB.entries):
            self.ROB.tail = 0
        self.ReservationStation.flush()
        self.CommonDataBus = []
        self.DecodeQueue = []
        for instruction in self.InstructionQueue:
            if checkForRegister(instruction.dR):
                originalRegister = instruction.d
                self.registerMappingTable.mappingTable[originalRegister].remove(instruction.dR)
                self.registers.registers[instruction.dR].busy = False
                self.freeRegisters.addRegister(instruction.dR)
        self.InstructionQueue = []

    # Commit for ROB Head if WriteBack is done
    def commit(self):
        # Commit the head of ROB
        robHead = self.ROB.commitHead()
        if robHead and robHead.state == "WriteBack" and len(self.CommonDataBus) < self.NB:
            if robHead.inst.find("bne") != -1:
                branchTaken = True if robHead.value is not None else False
                # Compare with prediction: if same move on with commit
                if branchTaken != self.BranchPrediction:
                    logging.info(f"[{self.cycle}]: True Value:{branchTaken}, Predicted Value:{self.BranchPrediction}")
                    self.BranchPrediction = True if not self.BranchPrediction else False
                    self.branchFlush()
                    self.PC = int(robHead.value) if robHead.value is not None else self.instructionFile.index(
                        robHead.inst) + 4
            self.ROB.updateHead()
            if "fsd" in robHead.inst:
                self.MainMemory[robHead.dest] = robHead.value
            robHead.state = "Commit"
            robHead.busy = False
            if robHead.RR is not None and checkForRegister(robHead.RR):
                self.CommonDataBus.append([robHead.name, robHead.RR])
            if "fsd" not in robHead.inst and "bne" not in robHead.inst:
                self.updateRegisterFile(robHead, robHead.RR)
            self.commit()
        else:
            return

    # Pipelining the stages
    def pipelining(self, instructionFile):
        self.fetch(instructionFile)
        if len(self.DecodeQueue) == 0 and self.ROB.isEmpty():
            return True
        # Decode is done starting from 1st Cycle
        if self.cycle > 0:
            self.decode()
        # Execute starts from 1 cycle as well
        if self.cycle > 0:
            self.execute()
        if self.cycle > 1:
            self.writeBack()
        self.commit()
        return False

    # Begin the Pipeline process till finished
    def begin(self):
        # Initiate Server Logs
        logFile = "logs/simulationLogs"
        with open(logFile, 'r+') as f:
            f.truncate(0)
        logging.basicConfig(filename=logFile, format='%(message)s', level=logging.INFO)
        while not self.finished:
            logging.info(
                f"**********************************************CYCLE: {self.cycle}**********************************************")
            self.finished = self.pipelining(self.instructionFile)
            self.cycle += 1
        # Log ALl Tables and Mappings
        logging.info(f"\nRegister Mapping: {self.registerMappingTable.mappingTable}\n")
        logging.info(f"Free Registers: {self.freeRegisters.freeRegisters}\n")
        logging.info(f"Register Values: {str(self.registers)}\n")
        register = self.getVirtualMappingValueTable()
        logging.info(f"Architected Register Values: {str(register)}\n")
        mainMemory = []
        for i in range(0, len(self.MainMemory), 8):
            mainMemory.append(f"[{i} : {self.MainMemory[i]}]")
        logging.info(f"Main Memory: {str(mainMemory)}\n")
        logging.info(str(self.ROB))
        logging.info(str(self.ReservationStation))
        logging.info(self.stalls)

    # Display final mapped values of used registers
    def getVirtualMappingValueTable(self):
        register = {}
        for key, value in self.registerMappingTable.mappingTable.items():
            register[key] = self.registers.registers[value[0]].value
        return register
