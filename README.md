# CSDesignExercise2

This project implements a distributed system where multiple virtual machines (VMs) are running simultaneously and communicate with each other by exchanging messages.

## Setup and Installation

### Installation

Clone the repository:
```bash
git https://github.com/sukikrishna/CS262DesignExercise2
cd CS262DesignExercise2
```

### Usage

```bash
python src/virtual_machines.py
```

### Tests

Tests can be run with `pytest`:
```bash
python -m pytest tests
```

Running the program will output the logs for each virtual machine to separate files in the format sim[x]_vm[i]_log.txt, where x is the simulation number and i is the virtual machine number.