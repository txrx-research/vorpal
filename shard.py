import logging
import time
import constants

class ShardBlock(list):
    def __init__(self, index):
        self.index = index

class Receipt:
    def __init__(self, transactionId, shard, sequence, nextShard):
        self.transactionId = transactionId
        self.shard = shard
        self.sequence = sequence
        self.nextShard = nextShard
    
    def toString(self):
        return "*** Receipt ***\nTransaction Id: {0}\nShard: {1}\nSequence: {2}\nNextShard: {3}\n".format(self.transactionId, self.shard, self.sequence, self.nextShard)

class Shard:	
    def __init__(self, shard, strategy, onNewShardBlock, beaconChain, mempool, receiptsPerShardBlock):
        self.shard = shard
        self.strategy = strategy
        self.onNewShardBlock = onNewShardBlock
        self.beaconChain = beaconChain
        self.mempool = mempool
        self.receiptsPerShardBlock = receiptsPerShardBlock
        self.nextBlock = ShardBlock(0)
        self.hasProcessedTransaction = list()
        self.hasProcessedReceipt = list()
        self.lastProcessedBlock = 0
        self.lastBlock = 0

    def processTransactionFromForeignReceipt(self, foreignReceipt, transaction):
        for i in range(foreignReceipt.sequence, len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                self.nextBlock.append(Receipt(id(transaction), self.shard,  i, transactionFragment.shard))
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(id(transaction), self.shard,  i, None))
                return True

    def processTransaction(self, transaction):
        for i in range(len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                self.nextBlock.append(Receipt(id(transaction), self.shard, i, transactionFragment.shard))
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(id(transaction), self.shard, i, None))
                return True
    
    def processMempoolTransactions(self):
        for transaction in self.mempool:
            if transaction[0].shard == self.shard and transaction not in self.hasProcessedTransaction and len(self.nextBlock) < self.receiptsPerShardBlock:
                self.hasProcessedTransaction.append(transaction)
                if self.processTransaction(transaction):
                    self.mempool.remove(transaction)

    def processReceiptTransactions(self):
        if(len(self.beaconChain) == 0): return
        for i in range(self.lastProcessedBlock, len(self.beaconChain)):
            beaconBlock = self.beaconChain[i]
            for shardBlock in beaconBlock:
                if shardBlock != None:
                    for receipt in shardBlock:
                        if len(self.nextBlock) < self.receiptsPerShardBlock:
                            if receipt.nextShard == self.shard:
                                for transaction in self.mempool:
                                    if id(transaction) == receipt.transactionId and receipt not in self.hasProcessedReceipt:
                                        self.hasProcessedReceipt.append(receipt)
                                        if self.processTransactionFromForeignReceipt(receipt, transaction):
                                            self.mempool.remove(transaction)
                                        break
                        else: break
            self.lastProcessedBlock = i
    def commitShardBlock(self):
        self.onNewShardBlock(self.shard, self.nextBlock)
        self.nextBlock = ShardBlock(self.nextBlock.index + 1)
        self.lastBlock = self.lastBlock + 1

    def produceShardBlock(self):
        self.processReceiptTransactions()
        self.processMempoolTransactions()
        

