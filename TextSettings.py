import logging

def writeToFile(data, filename, priorities = []):
    message = ""
    keys = [x for x in priorities if x in data] + [x for x in data if x not in priorities]
    for key in keys:
        message += key + ":\n"
        for val in data[key]:
            message += str(val) + "\n"
        message += "\n"

    logging.info("Writing to file {}...".format(filename))
    with open(filename, "w") as f:
        f.write(message)
    logging.info("Done writing to {}.".format(filename))

def readFromFile(filename):
    data = dict()

    f = open(filename, "r")
    lines = f.read().splitlines()

    logging.info("Getting input from {}".format(filename))

    category = None
    for line in lines:
        line.rstrip()
        logging.info(line)
        if line == "":
            category = None
            continue
        if line.endswith(":"):
            category = line[:-1]
            assert category not in data
            data[category] = []
        else:
            assert category != None
            data[category].append(line)
    return data
