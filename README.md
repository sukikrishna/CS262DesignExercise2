# Scale Models and Logical Clocks 

This project implements a distributed system where multiple virtual machines (VMs) are running simultaneously and communicate with each other by exchanging messages. Each VM operates with a unique clock rate, processes incoming messages, maintains its own logical clock (using Lamport’s algorithm), and logs events (sent, received, or internal) along with system time and logical clock values.

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

Tests can be run with `pytest`. The reported tests coverage by `pytest` is `91%`:
```bash
python -m pytest tests
```

Running the program will output the logs in `logs` directory for each virtual machine to separate files in the format sim[x]_vm[i]_log.txt, where x is the simulation number and i is the virtual machine number.
