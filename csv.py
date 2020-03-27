def beacon_chain_to_receipt_per_beacon_block(beacon_chain):
    string = ""
    for column in range(len(beacon_chain)):
        string = string + str(column)
        if column + 1 != len(beacon_chain): string = string + ","
    string = string + "\n"
    for beacon_block in beacon_chain:
        receipt_total = 0
        for shard_block in beacon_block:
            for receipt in shard_block:
                if receipt != None:
                    receipt_total+=1
        string = string + str(receipt_total)
        if(beacon_block != beacon_chain[len(beacon_chain) - 1]):  string = string + ","
    return string

