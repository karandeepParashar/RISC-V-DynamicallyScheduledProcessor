class Register:
    def __init__(self, name):
        self.name = name
        self.value = 0
        self.rename = None
        self.busy = False

    def __str__(self):
        return f"{self.busy}, {self.value}, {self.rename}"


class RegisterFile:
    def __init__(self, NR):
        self.registers = {}
        for i in range(NR):
            rName = "p" + str(i)
            self.registers[rName] = Register(rName)

    def __str__(self):
        string = ""
        for key, value in self.registers.items():
            string += f"'{key}': [{str(value)}], "
        return "{"+string+"}"

    def getROBRegister(self, rob):
        for key, value in self.registers.items():
            if value.rename == rob:
                return value
        return None


class FreeRegisterTable:
    def __init__(self, registers):
        self.freeRegisters = registers if registers else []

    def isAvailable(self):
        if len(self.freeRegisters) == 0:
            return None
        else:
            return self.freeRegisters.pop(0)

    def addRegister(self, register):
        if register not in self.freeRegisters:
            self.freeRegisters.append(register)


class RegisterMappingTable:
    def __init__(self):
        self.mappingTable = {}

    def registerRenaming(self, instructionRegister, physicalRegister):
        if instructionRegister in self.mappingTable:
            self.mappingTable[instructionRegister].append(physicalRegister)
        else:
            self.mappingTable[instructionRegister] = [physicalRegister]

    def isAlreadyMapped(self, register):
        mappedRegisters = self.mappingTable.get(register)
        return mappedRegisters[-1] if mappedRegisters is not None else mappedRegisters
