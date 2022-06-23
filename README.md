<!-- ABOUT THE PROJECT -->

## About The Project

- One benefit of a dynamically scheduled processor is its ability to tolerate changes in latency or issue capability in out of order speculative processors.
  The purpose of this project is to evaluate this effect of different architecture parameters on a CPU design by simulating a modified (and simplified) version of the PowerPc 604 and 620 architectures. We will assume a 32-bit architecture that executes a subset of the RISC V ISA which consists of the following 9 instructions:

```sh
   fld, fsd, add, addi, fadd, fsub, fmul, fdiv, bne
```

- The simulator takes an input file as a command line input. This input file, "program.txt", will contain a RISC V assembly language program (code segment). Each line in the input file is a RISC V instruction from the aforementioned nine instructions. The simulator reads this input file, recognize the instructions, recognize the different fields of the instructions, and simulate their execution on the architecture described below. The implementation is of functional+timing simulator.

- The following 1-7 are followed while constructing this simulator.

1. The simulated architecture is a speculative, multi-issue, out of order CPU where:
   (Assuming your first instruction resides in the memory location (byte address) 0x00000hex. That
   is, the address for the first instruction is 0x00000hex. PC+4 points to next instruction).
   The fetch unit fetches up to NF=4 instructions every cycle (i.e., issue width is 4).

2. A 1-bit dynamic branch predictor (initialized to predict not taken) with 16-entry branch target
   buffer (BTB) is used. It hashes the address of a branch, L, to an entry in the BTB using bits 7-4 of
   L.

3. The decode unit decodes (in a separate cycle) the instructions fetched by the fetch unit and stores
   the decoded instructions in an instruction queue which can hold up to NI instructions. For
   simplicity, we assume that NI has unlimited entries. That is, your instruction window size is  
   unlimited and holds all the instructions fetched.

4. Up to NW=4 instructions can be issued every clock cycle to reservation stations. The  
   architecture has the following functional units with the shown latencies and number of reservation stations.

5. A circular reorder buffer (ROB) with NR=16 entries is used with NB=4 Common Data Busses
   (CDB) connecting the WB stage and the ROB to the reservation stations and the register file. You
   have to design the policy to resolve contention between the ROB and the WB stage on the CDB
   busses.

6. You need to perform register renaming to eliminate the false dependences in the decode stage.
   Assuming we have a total of 32 physical registers (p0, p1, p2, ...p31). You will need to implement
   a mapping table and a free list of the physical register as we discussed in class. Also, assuming
   that all of the physical registers can be used by either integer or floating point instructions.

7. A dedicated/separate ALU is used for the effective address calculation in the branch unit (BU)
   and simultaneously, a special hardware is used to evaluate the branch condition. Also, a  
   dedicated/separate ALU is used for the effective address calculation in the load/store unit. You
   will also need to implement forwarding in your simulation design.
   The simulator should be parameterized so that one can experiment with different values of NF,
   NW, NR and NB (either through command line arguments or reading a configuration file). To  
   simplify the simulation, we will assume that the instruction cache line contains NF instructions  
   and that the entire program fits in the instruction cache (i.e., it always takes one cycle to read a
   cache line). Also, the data cache (single ported) is very large so that writing or reading a word into
   the data cache always takes one cycle (i.e., eliminating the cache effect in memory accesses).

<p align="right">(<a href="#top">back to top</a>)</p>

### Built With

This section lists any major frameworks/libraries used to bootstrap your project.

- [Python](https://www.python.org/)

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Getting Started

These are the instructions on setting up your project locally.

### Prerequisites

Following are the prerequisites for running the project.

- Python 3.7.6
  ```sh
  https://www.python.org/downloads/release/python-376/
  ```

### Run Instructions

_For running the project please follow the following commands._

1. Download the project

2. Enter the project directory.
   ```sh
   cd Project
   ```
3. run the main.py file

   ```js
   python main.py
   ```

<p align="right">(<a href="#top">back to top</a>)</p>

Default Parameters are:

1. I_file_name: default="program.txt"
2. M_file_name: default="memory.txt"
3. NF: default= 4
4. NW: default= 4
5. NR: default= 16
6. NB: default= 4

### Run Instructions With Parameters

Please change the arguments as required:

```js
   python main.py --I_file_name "program.txt" --M_file_name "memory.txt" --NF 4 --NW 4 --NR 16 --NB 4
```
