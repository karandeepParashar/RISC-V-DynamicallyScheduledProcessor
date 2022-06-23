class FunctionalUnit:
    def __init__(self, name, latency):
        self.name = name
        self.executionEntry = None
        self.latency = latency
        self.isBusy = False
        self.coolDown = 0

    def executeNewEntry(self, entry, reorderBuffer, registerFile, mainMemory):
        self.coolDown = 0
        self.executionEntry = entry
        self.isBusy = True
        return self.execute(reorderBuffer, registerFile, mainMemory)

    def executeAlreadyExistingEntry(self, reorderBuffer, registerFile, mainMemory):
        return self.execute(reorderBuffer, registerFile, mainMemory)

    def execute(self, reorderBuffer, registerFile, mainMemory):
        self.coolDown += 1
        if self.coolDown == self.latency:
            # Updating the destination Register
            entry = self.executionEntry
            dest = entry.dest
            destinationRegister = registerFile.getROBRegister(dest)
            result = None
            if entry.op == "add":
                result = int(registerFile.registers[entry.vj].value) + int(registerFile.registers[entry.vk].value)
            elif entry.op == "addi":
                result = int(registerFile.registers[entry.vj].value) + int(entry.vk)
            elif entry.op == "fld":
                address = int(entry.vj) + int(registerFile.registers[entry.vk].value)
                result = mainMemory[address]
            elif entry.op == "fsd":
                robEntry = reorderBuffer.getROBWithName(dest)
                offset = robEntry.dest
                address = int(registerFile.registers[entry.vk].value) + int(offset)
                robEntry.dest = address
                result = registerFile.registers[entry.vj].value
            elif entry.op == "fadd":
                result = float(registerFile.registers[entry.vj].value) + float(registerFile.registers[entry.vk].value)
            elif entry.op == "fsub":
                result = float(registerFile.registers[entry.vj].value) - float(registerFile.registers[entry.vk].value)
            elif entry.op == "fmul":
                result = float(registerFile.registers[entry.vj].value) * float(registerFile.registers[entry.vk].value)
            elif entry.op == "fdiv":
                result = float(registerFile.registers[entry.vj].value) / float(registerFile.registers[entry.vk].value)
            elif entry.op == "bne":
                robEntry = reorderBuffer.getROBWithName(dest)
                value1 = float(registerFile.registers[entry.vj].value)
                value2 = float(registerFile.registers[entry.vk].value)
                if value1 != value2:
                    result = robEntry.dest
                else:
                    result = None
            if entry.op not in ["bne", "fsd"]:
                destinationRegister.value = result
            # Update ROB Table for being ready to commit and also for value
            robEntry = reorderBuffer.getROBWithName(dest)
            robEntry.ready = True
            robEntry.value = result
            robEntry.state = "Execution Complete"
            self.executionEntry = None
            self.isBusy = False
            return True, entry
        else:
            entry = self.executionEntry
            dest = entry.dest
            robEntry = reorderBuffer.getROBWithName(dest)
            robEntry.ready = False
            robEntry.state = "Executing"
            return False, None


class ReservationStationEntry:
    def __init__(self, latency):
        self.instId = None
        self.instruction = None
        self.op = None
        self.vj = None
        self.vk = None
        self.qj = None
        self.qk = None
        self.dest = None
        self.busy = False
        self.coolDown = latency
        self.ready = False

    def __str__(self):
        return f"|{self.busy}|instr_id={self.instId}|instr=[{self.instruction}]|op={self.op}|vj={self.vj} |vk={self.vk} |qj={self.qj} |qk={self.qk} |dest={self.dest}|"

    def execute(self):
        self.coolDown -= 1
        return self.coolDown


class ReservationStation:
    def __init__(self, name, count, instructions, latency, functionalUnit):
        self.id = [i for i in range(count)]
        self.Name = name
        self.instructions = instructions
        self.latency = latency
        self.entries = [ReservationStationEntry(latency) for i in range(count)]
        self.executeFlag = False
        self.executingEntry = None
        self.functionalUnit = functionalUnit
        self.ready = False

    def __str__(self):
        string = ""
        for i in range(len(self.entries)):
            string += f"|{self.Name}{self.id[i]}" + str(self.entries[i]) + "\n"
        return string

    def isAvailable(self):
        for i in range(len(self.entries)):
            if not self.entries[i].busy:
                return True
        return False

    def removeEntry(self, entry):
        self.entries.remove(entry)
        self.entries.append(ReservationStationEntry(self.latency))

    def getReadyEntry(self):
        for entry in self.entries:
            if entry.busy and entry.ready:
                return entry
        return None

    def updateEntriesWithCommonDataBus(self, commonDataBus, reorderBuffer, registerFile, registerMappingTable):
        for entry in self.entries:
            for data in commonDataBus:
                if entry.qj is not None:
                    if data[0] == entry.qj:
                        entry.qj = None
                        entry.vj = data[1]
                if entry.qk is not None:
                    if data[0] == entry.qk:
                        entry.qk = None
                        entry.vk = data[1]
            if entry.busy and entry.qj is None and entry.qk is None:
                entry.ready = True
            if entry.busy and entry.qj is not None and entry.qk is not None:
                rob = reorderBuffer.getROBWithName(entry.qj)
                if entry.qj is not None:
                    if rob.state == "Commit":
                        entry.vj = registerMappingTable[rob.dest][0]
                rob = reorderBuffer.getROBWithName(entry.qk)
                if entry.qk is not None:
                    if rob.state == "Commit":
                        entry.vk = registerMappingTable[rob.dest][0]

    def execute(self, commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable):
        # Update Reservation Station Entries With Common Data Bus Data
        self.updateEntriesWithCommonDataBus(commonDataBus, reorderBuffer, registerFile, registerMappingTable)
        fUnit = self.functionalUnit
        # Check if fUnit is busy: If Yes Execute Already Existing Instruction
        if fUnit.isBusy:
            finished, entry = fUnit.executeAlreadyExistingEntry(reorderBuffer, registerFile, mainMemory)
            if finished:
                self.removeEntry(entry)
        # If No Pick an Entry and Start Execution
        else:
            entry = self.getReadyEntry()
            if entry is not None:
                finished, entry = fUnit.executeNewEntry(entry, reorderBuffer, registerFile, mainMemory)
                if finished:
                    self.removeEntry(entry)


class ReservationStationUnity:
    def __init__(self):
        self.intRS = ReservationStation("INT", 4, ["add", "addi"], 1, FunctionalUnit("INT", 1))
        loadStoreUnit = FunctionalUnit("LoadStore", 1)
        self.loadBuffer = ReservationStation("Load", 2, ["fld"], 1, loadStoreUnit)
        self.storeBuffer = ReservationStation("Store", 2, ["fsd"], 3, loadStoreUnit)
        self.fpAddRS = ReservationStation("FPadd", 3, ["fadd", "fsub"], 4, FunctionalUnit("FPadd", 3))
        self.fpMultRS = ReservationStation("FPmult", 4, ["fmul"], 8, FunctionalUnit("FPmult", 4))
        self.fpDivRS = ReservationStation("FPdiv", 2, ["fdiv"], 8, FunctionalUnit("FPdiv", 8))
        self.BU = ReservationStation("BU", 1, ["bne"], 1, FunctionalUnit("BU", 1))
        self.Stations = {
            "add": self.intRS,
            "addi": self.intRS,
            "fld": self.loadBuffer,
            "fsd": self.storeBuffer,
            "fadd": self.fpAddRS,
            "fsub": self.fpAddRS,
            "fmul": self.fpMultRS,
            "fdiv": self.fpDivRS,
            "bne": self.BU
        }

    def __str__(self):
        string = "              RESERVATION STATUS TABLE\n"
        for unit in ["add", "fld", "fsd", "fadd", "fmul", "fdiv", "bne"]:
            string += f"{str(self.Stations[unit])}"
        return string

    def isAvailable(self, op):
        rsUnit = self.Stations[op]
        rsAvailable = rsUnit.isAvailable()
        if rsAvailable:
            return True
        return False

    def getStation(self, op):
        unit = self.Stations[op]
        for entry in unit.entries:
            if not entry.busy:
                return entry
        return None

    def loadStoreExecute(self, commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable):
        self.storeBuffer.updateEntriesWithCommonDataBus(commonDataBus, reorderBuffer, registerFile,
                                                        registerMappingTable)
        self.loadBuffer.updateEntriesWithCommonDataBus(commonDataBus, reorderBuffer, registerFile, registerMappingTable)
        store1, store2, load1, load2 = self.storeBuffer.entries[0], self.storeBuffer.entries[1], \
                                       self.loadBuffer.entries[0], self.loadBuffer.entries[1]
        if store1.ready and load1.ready:
            if int(store1.dest[-1]) > int(load1.dest[-1]):
                self.loadBuffer.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
            else:
                self.storeBuffer.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
        elif not store1.ready and not load1.ready:
            if store2.ready and load2.ready:
                if int(store2.dest[-1]) > int(load2.dest[-1]):
                    self.loadBuffer.execute(commonDataBus, reorderBuffer, registerFile, mainMemory,
                                            registerMappingTable)
                else:
                    self.storeBuffer.execute(commonDataBus, reorderBuffer, registerFile, mainMemory,
                                             registerMappingTable)
            else:
                return
        elif not store1.ready:
            self.loadBuffer.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
        else:
            self.storeBuffer.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)

    def execute(self, commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable):
        self.intRS.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
        self.loadStoreExecute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
        self.fpAddRS.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
        self.fpMultRS.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
        self.fpDivRS.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)
        self.BU.execute(commonDataBus, reorderBuffer, registerFile, mainMemory, registerMappingTable)

    def flush(self):
        self.intRS = ReservationStation("INT", 4, ["add", "addi"], 1, FunctionalUnit("INT", 1))
        loadStoreUnit = FunctionalUnit("LoadStore", 1)
        self.loadBuffer = ReservationStation("Load", 2, ["fld"], 1, loadStoreUnit)
        self.storeBuffer = ReservationStation("Store", 2, ["fsd"], 3, loadStoreUnit)
        self.fpAddRS = ReservationStation("FPadd", 3, ["fadd", "fsub"], 4, FunctionalUnit("FPadd", 3))
        self.fpMultRS = ReservationStation("FPmult", 4, ["fmul"], 8, FunctionalUnit("FPmult", 4))
        self.fpDivRS = ReservationStation("FPdiv", 2, ["fdiv"], 8, FunctionalUnit("FPdiv", 8))
        self.BU = ReservationStation("BU", 1, ["bne"], 1, FunctionalUnit("BU", 1))
        self.Stations = {
            "add": self.intRS,
            "addi": self.intRS,
            "fld": self.loadBuffer,
            "fsd": self.storeBuffer,
            "fadd": self.fpAddRS,
            "fsub": self.fpAddRS,
            "fmul": self.fpMultRS,
            "fdiv": self.fpDivRS,
            "bne": self.BU
        }


class ReorderBufferEntry:
    def __init__(self, name):
        self.name = name
        self.inst_id = None
        self.state = None
        self.dest = None
        self.value = None
        self.RR = None
        self.busy = False
        self.inst = None
        self.ready = False

    def __str__(self):
        return f"inst_id:{self.inst_id}|name={self.name}|busy={self.busy}|inst='{self.inst}'|dest={self.dest}|rr={self.RR}|state={self.state}|\n"


class ReorderBuffer:
    def __init__(self, count):
        self.head = 0
        self.tail = 0
        self.entries = [ReorderBufferEntry("ROB" + str(i)) for i in range(count)]
        self.size = count

    def __str__(self):
        string = f"         Head: {self.head} || Tail: {self.tail}\n"
        for entry in self.entries:
            string += str(entry)
        return string

    def isAvailable(self):
        if self.tail + 1 == self.head:
            return False
        else:
            if self.tail + 1 >= len(self.entries):
                if self.head == 0:
                    return False
            return True

    def getROB(self):
        tail = self.tail
        self.tail = 0 if self.tail + 1 >= len(self.entries) else self.tail + 1
        return self.entries[tail] if not self.entries[tail].busy else False

    def getROBWithName(self, name):
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def commitHead(self):
        robHead = self.entries[self.head]
        if robHead.state == "WriteBack":
            return robHead
        else:
            return None

    def updateHead(self):
        self.head = 0 if self.head + 1 == len(self.entries) else self.head + 1

    def isEmpty(self):
        for entry in self.entries:
            if entry.busy:
                return False
        return True
