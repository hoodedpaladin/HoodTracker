import EntranceShuffle
import re

def allGrottoRegionsWithTypes(types):
    grottos = filter(lambda x: x[0] == 'Grotto', EntranceShuffle.entrance_shuffle_table)

    results = []
    for x in filter(lambda x: x[1][1]['entrance'] in types, grottos):
        match = re.fullmatch("(.*) -> (.*)", x[1][0])
        assert match
        results.append(match.group(2))
    return results

def allGreatFairyFountains():
    interiors = filter(lambda x: x[0] == 'Interior', EntranceShuffle.entrance_shuffle_table)

    results = []
    for x in filter(lambda x: "Great Fairy Fountain" in x[1][0], interiors):
        match = re.fullmatch("(.*) -> (.*)", x[1][0])
        assert match
        results.append(match.group(2))
    return results

class AutoGrotto:
    def __init__(self):
        self._regions = {}
        self._regions['auto_generic_grotto'] = allGrottoRegionsWithTypes([0x3f])
        self._regions['auto_scrub_grotto'] = allGrottoRegionsWithTypes([0x5a4, 0x5bc, 0x5b0])
        self._regions['auto_fairy_fountain'] = allGrottoRegionsWithTypes([0x036D])
        self._regions['auto_great_fairy_fountain'] = allGreatFairyFountains()
        self._all = []
        for x in self._regions.values():
            self._all.extend(x)
        #print(self._all)

    # Does a replacement with auto_* types
    def serveRegion(self, type):
        if type in self._regions:
            return self._regions[type].pop()
        raise Exception("Unknown auto type "+type)

    def getAllRegions(self):
        return self._all

    # Call this with regions that are taken already so that they do not get automatically served
    def removeRegions(self, regions):
        for key in self._regions:
            for region in regions:
                if region in self._regions[key]:
                    self._regions[key].remove(region)
