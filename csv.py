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
                if receipt != None and receipt.next_shard == None:
                    receipt_total+=1
        string = string + str(receipt_total)
        if(beacon_block != beacon_chain[len(beacon_chain) - 1]):  string = string + ","
    return string + "\n"

def probability_over_duration(probability, time, calc_crossshard_probability):
    string_probability = "\nprobability,"
    string_time = "time (seconds),"
    for interval in range(time):
        string_probability += "{0}".format(calc_crossshard_probability(probability, time, interval + 1, True))
        string_time += str(interval)
        if interval != range(time)[-1]:
            string_probability += ","
            string_time += ","
    return string_probability + "\n" + string_time + "\n"

def stats(args, time, beacon_chain, transaction_log, total_generated_transactions, collision_log):
    string = "\nexecution_time, {0}\n".format(time)

    receipt_total = 0
    for beacon_block in beacon_chain:
        for shard_block in beacon_block:
            for receipt in shard_block:
                if receipt != None and receipt.next_shard == None:
                    receipt_total+=1

    string += "collision_rate, {0}\n".format(len(collision_log) / total_generated_transactions)

    shortest_txn = -1
    longest_txn = 0
    transaction_fragment_total = 0
    for transaction in transaction_log:
        if shortest_txn == -1 or len(transaction) < shortest_txn: shortest_txn = len(transaction)
        if len(transaction) > longest_txn: longest_txn = len(transaction)
        transaction_fragment_total += len(transaction)
    avg_txn = transaction_fragment_total / (receipt_total)

    string += "shortest_txn_time (s), {0}\n".format(shortest_txn * args.slot)
    string += "longest_txn_time (s), {0}\n".format(longest_txn * args.slot)
    string += "avg_txn_time (s), {0}\n".format(avg_txn * args.slot)

    return string

def config(args):
    string = "\n"
    for arg in vars(args):
        string += "{0}, {1}\n".format(arg, getattr(args, arg))
   
    return string