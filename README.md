# Cross Shard Simulation for Ethereum 2.0

In this simulation we will model the execution of cross shard transactions the Ethereum 2.0 platform using varying sharding strategies.

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
	from: 20 byte address,
	to: 20 byte address,
	value: wei,
	input: bytecode,
	gas:

}
```

The discontinuity of cross-shard transactions requires a new format to allow the simulation to orchestrate a pause and resume within a single transaction. The following structure will allow such an interaction:

```
{

}
```