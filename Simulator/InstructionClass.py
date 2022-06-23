class Instruction:
    id = 0

    def __init__(self, op_name, d, s1, s2=None):
        self.instructionId = Instruction.id
        Instruction.id = Instruction.id + 1
        if op_name == "fsd" or op_name == "bne":
            if op_name == "fsd":
                self.d = s1
                self.s1 = d
                self.s2 = s2
            else:
                self.d = s2
                self.s1 = d
                self.s2 = s1
            self.op = op_name
            self.state = "Decode"
            self.dR = None
            self.instruction = ''
        else:
            self.op = op_name
            self.d = d
            self.s1 = s1
            self.s2 = s2
            self.state = "Decode"
            self.dR = None
            self.instruction = ''

    def __str__(self):
        return f"Id: {self.instructionId}, Inst:'[{self.instruction}]', State:'{self.state}', op:'{self.op}', d:'{self.dR if self.dR else self.d}', s1:'{self.s1}', s2:'{self.s2}'"

    def updateStage(self, state):
        self.state = state
