import ItemPool
import ItemList
import Rules
import Item
import re

shopname_to_item = {
    'Bombchu': 'Bombchus',
    'Deku Shield': 'Deku Shield',
    'Deku Nut': 'Deku Nut',
    'Deku Stick': 'Deku Stick',
    'Hylian Shield': 'Hylian Shield',
    'Blue Fire': 'Blue Fire',
    'Goron Tunic': 'Goron Tunic',
    'Zora Tunic': 'Zora Tunic',
}

# Multiple bombchu purchases are useless to track
ignore_vanilla_locs = ['Market Bombchu Shop Item {}'.format(x) for x in range(2,9)]

def baseShopName(itemname):
    a = re.sub('^Buy ', '', itemname)
    b = re.sub(' \(\d+\)$', '', a)
    return b

# If false, this item isn't worth populating, just ignore
def isProgressionShopItem(world, loc, itemname):
    item = ItemList.item_table[itemname]

    if not item[1]:
        return False
    # TODO: some of these should not be ignored
    if baseShopName(itemname) in ['Fairy\'s Spirit', 'Bottle Bug', 'Fish']:
        return False
    if world.settings.shopsanity == 'off' and loc.name in ignore_vanilla_locs:
        return False
    return True


def populateVanillaShop(world):
    locs = [x for x in world.get_locations() if x.type == 'Shop']
    progression_locs = []

    for loc in locs:
        itemname = loc.vanilla_item
        if world.settings.bombchus_in_logic and loc.name in ['KF Shop Item 8', 'Market Bazaar Item 4', 'Kak Bazaar Item 4']:
            itemname = 'Buy Bombchu (5)'

        if not isProgressionShopItem(world, loc, itemname):
            loc.shop_non_progression = True
            continue

        loc.item = Item.Item(name=itemname)
        progression_locs.append(loc)
    Rules.set_shop_rules(world)

    for loc in progression_locs:
        shopname = baseShopName(loc.item.name)
        loc.item.name = shopname_to_item[shopname]

# Populate Gold Skulltula tokens in any GS location that is not shuffled
def populateGSTokens(world):
    all_locs = world.get_locations()
    gs_locs = [x for x in all_locs if x.filter_tags and 'Skulltulas' in x.filter_tags]

    populate_these = []
    if world.settings.tokensanity in ['off', 'overworld']:
        dungeon_gs_locs = [x for x in gs_locs if x.scene < 0xA]
        populate_these.extend(dungeon_gs_locs)
    if world.settings.tokensanity in ['off', 'dungeons']:
        overworld_gs_locs = [x for x in gs_locs if x.scene >= 0xA]
        populate_these.extend(overworld_gs_locs)

    for loc in populate_these:
        loc.item = Item.Item('Gold Skulltula Token')
        loc.unshuffled_gs_token = True

# Responsible for all unshuffled population
def populateKnownUnshuffled(world):
    if world.settings.shopsanity == 'off':
        populateVanillaShop(world)

    populateGSTokens(world)

    if not world.settings.shuffle_medigoron_carpet_salesman:
        loc = world.get_location("Wasteland Bombchu Salesman")
        loc.item = Item.Item("Bombchus")
        # TODO: what to populate for Medigoron?