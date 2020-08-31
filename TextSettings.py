
def writeToFile(data, filename, priorities = []):
    message = ""
    keys = [x for x in priorities if x in data] + [x for x in data if x not in priorities]
    for key in keys:
        message += key + ":\n"
        for val in data[key]:
            message += str(val) + "\n"
        message += "\n"

    with open(filename, "w") as f:
        f.write(message)

def readFromFile(filename):
    data = dict()

    f = open(filename, "r")
    lines = f.read().splitlines()

    category = None
    for line in lines:
        line.rstrip()
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
