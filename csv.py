def transaction_segments_per_block(beacon_chain):
    string = "slots,"
    for column in range(len(beacon_chain)):
        string = string + str(column)
        if column + 1 != len(beacon_chain): string = string + ","
    string = string + "\n" + "transaction_segments,"
    for beacon_block in beacon_chain:
        receipt_total = 0
        for shard_block in beacon_block:
            for receipt in shard_block:
                if receipt != None:
                    receipt_total+=1
        string = string + str(receipt_total)
        if(beacon_block != beacon_chain[len(beacon_chain) - 1]):  string = string + ","
    return string + "\n"

def transactions_per_block(beacon_chain):
    string = "transactions,"
    for beacon_block in beacon_chain:
        receipt_total = 0
        for shard_block in beacon_block:
            for receipt in shard_block:
                if receipt != None and receipt.nextShard == None:
                    receipt_total+=1
        string = string + str(receipt_total)
        if(beacon_block != beacon_chain[len(beacon_chain) - 1]):  string = string + ","
    return string + "\n"

def stats(args, time, beacon_chain, transactionsLog, total_generated_transactions):
    string = "execution_time, {0}\n".format(time)

    receipt_total = 0
    for beacon_block in beacon_chain:
        for shard_block in beacon_block:
            for receipt in shard_block:
                if receipt != None and receipt.nextShard == None:
                    receipt_total+=1

    string += "collision_rate, {0}\n".format(100 - (receipt_total/total_generated_transactions)*100)

    shortest_txn = -1
    longest_txn = 0
    transaction_fragment_total = 0
    for transaction in transactionsLog:
        if shortest_txn == -1 or len(transaction) < shortest_txn: shortest_txn = len(transaction)
        if len(transaction) > longest_txn: longest_txn = len(transaction)
        transaction_fragment_total += len(transaction)
    avg_txn = transaction_fragment_total / (receipt_total)

    string += "shortest_txn_time (s), {0}\n".format(shortest_txn * args.slot)
    string += "longest_txn_time (s), {0}\n".format(longest_txn * args.slot)
    string += "avg_txn_time (s), {0}\n".format(avg_txn * args.slot)

    return string

def config(args):
   string = "shards, {0}\n".format(args.shards)
   string += "tps, {0}\n".format(args.tps)
   string += "slot, {0}\n".format(args.slot)
   string += "duration, {0}\n".format(args.duration)
   string += "blocklimit, {0}\n".format(args.blocklimit)
   string += "dist, {0}\n".format(args.dist)
   string += "crossshard, {0}\n".format(args.crossshard)
   string += "collision, {0}\n".format(args.collision)
   string += "sweep, {0}\n".format(args.sweep)
   string += "output, {0}\n".format(args.output.name)
   
   return string