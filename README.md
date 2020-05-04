# Cross Shard Simulation for Ethereum 2.0

## Install Instructions

```
cd cross-shard-txn-sim 
python3 -m venv
pip install -r requirements.txt
```

## Run Instructions
```
python3 script.py
```

## Running CLI with parameters
```
usage: script.py [-h] [-sh SHARDS] [-s SLOT] [-b BLOCKSIZE] [-ws WITNESSSIZE]
                 [-css TRANSACTIONSIZE] [-t TPS] [-d DURATION]
                 [-cs CROSSSHARD] [-c COLLISION] [-sw] [-g] [-o OUTPUT]
                 [-ot OUTPUTTRANSACTIONS] [-i INPUT]

Ethereum 2.0 Coss-Shard Simulation Commands

optional arguments:
  -h, --help            show this help message and exit
  -sh SHARDS, --shards SHARDS
                        shards to simulate
  -s SLOT, --slot SLOT  seconds per slot (decimal)
  -b BLOCKSIZE, --blocksize BLOCKSIZE
                        size of shard blocks (kb)
  -ws WITNESSSIZE, --witnesssize WITNESSSIZE
                        size of Eth1 stateless witness (kb)
  -css TRANSACTIONSIZE, --transactionsize TRANSACTIONSIZE
                        size of a cross-shard transaction receipt (bytes)
  -t TPS, --tps TPS     number of transactions globally per second to added to
                        mempool
  -d DURATION, --duration DURATION
                        duration of time to simulate (seconds)
  -cs CROSSSHARD, --crossshard CROSSSHARD
                        probability a cross-shard call will occur within a
                        transaction
  -c COLLISION, --collision COLLISION
                        probability a transaction will experience a mutated
                        state and cause a reversion of the transaction
  -sw, --sweep          sweeps the probability for the test duration (eg:
                        0.25, 0 -> 0.25)
  -g, --generate        application will only generate and stores transactions
                        without simulation
  -o OUTPUT, --output OUTPUT
                        path to file for saving output
  -ot OUTPUTTRANSACTIONS, --outputtransactions OUTPUTTRANSACTIONS
                        path to file for saving output
  -i INPUT, --input INPUT
                        path to file to transaction inputs
```