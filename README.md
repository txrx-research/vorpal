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
Ethereum 2.0 Coss-Shard Simulation Commands

optional arguments:
  -h, --help            show this help message and exit
  --shards SHARDS       shards to simulate
  --txs TXS             number of transactions globally per second to added to
                        mempool
  --txns TXNS           total number of transactions to simulate
  --slot SLOT           milliseconds per slot
  --time TIME           length of time for the simulation to run
                        (milliseconds). -1 means indefinite execution
  --receipts RECEIPTS   receipt limit per shard block
  --dist DIST           distribution of contracts within the shards (uniform,
                        binomial, normal)
  --collision COLLISION
                        probability a transaction will experience a mutated
                        state and cause a reversion of the transaction
```

### Data Captured
	- Mempool size
	- Receipts
	- Blocks

In this simulation we will model the execution of cross shard transactions the Ethereum 2.0 platform using varying sharding strategies.
The goal of this research is to take Eth1 transactions and execute them within the context of a cross-shard transaction.

### Factors to be considered:
	- Duration of cross shard communication
	- Network Load (Queue size)
	- Slot times
	- Probability of a reorg 

### Details collected on the transaction:
	- Execution Time
	- State Size
	- Transaction Throughput
	- Transaction Size
	- Wait time for finality  

### Simulation Notes
A problem in simulating cross-shard transactions is the cross contract calls. In Eth1 cross contract calls are synchronous, when a method is called on a deployed contract that references an external contract the transaction is processed synchronously without discontinuity. Continuity within the execution is guaranteed by the block producer having absolute control of the state. Within a sharded system the shard block producer only has control of the state within their shard. If a contract method call makes a cross contract call to mutate state on a foreign shard execution becomes discontiuous. The following structure of a traditional Eth1 transaction is unsuitable for the purposes of simulating a cross-shard transaction:

```
{
	from: 20 bytes (address),
	to: 20 bytes (address),
	value: wei,
	input: bytecode,
	gas:

}
```

The discontinuity of cross-shard transactions requires a new format to allow the simulation to orchestrate a pause and resume within a single transaction. The following structure will allow such an interaction:

`TransactionFragmentType`s are a case generalization of transaction executions that may results in a cross-shard call 
```
class TransactionFragmentType(Enum):
	PAYMENT_TO_EOA = 1
	PAYMENT_TO_SHARD = 2
	PAYMENT_TO_CONTRACT = 3
	CONTRACT_CALL = 4
	CONTRACT_DEPLOY = 5
	EE_DEPLOY = 6
```

`Transaction` list is a construction that links individual `TransactionFragment`s together to form a construction that allows for interpretting individual 
```
[
	{
		transaction_fragment_type: TransactionFragmentType
		is_foreign_shard: bool
	},
	...
]
```
Eth1 transaction will be parsed into a runtime construction that is seen above. The construction will then be passed into the simulation to extract the execution data described earlier.

### Instances of cross-shard transaction calls
By Eth1 synchronous design there several instances that could necessitate a cross-shard transaction call. In the synchronous nature of Eth1 the block producer can mutate all state within the confines of a transactions inclusion in a block construction. In Eth2 this capability will be lost in cross-shard transactions. In a single contract method there could be multiple calls to mutate state on a foreign shard.

### Simulation elements considered
1. Global slot timing
	- Transactions in mempool between slots have a coordination delay. Transactions will not execute until `(global_time % SLOT_TIME) + SLOT_TIME`
2. Mempool propagation delay
	- Transactions in mempool are delayed on a basis of propagation timing. Throughput of mempool is currently not available, mempool throughput will be approximated for research purposes
3. 
