from PySide2.QtWidgets import *
from PySide2 import QtGui
from PySide2.QtCore import *
import os
import logging

imageNamesDict = {
    'Ocarina': 'OoT_Ocarina_of_Time_Icon.png',
    'Small Key (Bottom of the Well)': 'OoT_Small_Key_Icon.png',
    'Small Key (Fire Temple)': 'OoT_Small_Key_Icon.png',
    'Small Key (Forest Temple)': 'OoT_Small_Key_Icon.png',
    'Small Key (Ganons Castle)': 'OoT_Small_Key_Icon.png',
    'Small Key (Gerudo Training Grounds)': 'OoT_Small_Key_Icon.png',
    'Small Key (Shadow Temple)': 'OoT_Small_Key_Icon.png',
    'Small Key (Spirit Temple)': 'OoT_Small_Key_Icon.png',
    'Small Key (Water Temple)': 'OoT_Small_Key_Icon.png',
    'Small Key (Gerudo Fortress)': 'OoT_Small_Key_Icon.png',
    'Kokiri Sword': 'OoT_Kokiri_Sword_Icon.png',
    'Progressive Hookshot': ['OoT_Hookshot_Icon.png', 'OoT_Longshot_Icon.png'],
    'Boss Key (Fire Temple)': 'OoT_Boss_Key_Icon.png',
    'Boss Key (Shadow Temple)': 'OoT_Boss_Key_Icon.png',
    'Boss Key (Spirit Temple)': 'OoT_Boss_Key_Icon.png',
    'Boss Key (Water Temple)': 'OoT_Boss_Key_Icon.png',
    'Boss Key (Forest Temple)': 'OoT_Boss_Key_Icon.png',
    'Boss Key (Ganons Castle)': 'OoT_Boss_Key_Icon.png',
    'Bombchus (10)': 'OoT_Bombchu_Icon.png',
    'Boomerang': 'OoT_Boomerang_Icon.png',
    'Lens of Truth': 'OoT_Lens_of_Truth_Icon.png',
    'Megaton Hammer': 'OoT_Megaton_Hammer_Icon.png',
    'Cojiro': 'OoT_Cojiro_Icon.png',
    'Bottle': 'OoT_Bottle_Icon.png',
    'Rutos Letter': 'OoT_Letter_Icon.png',
    'Sell Big Poe': 'OoT_Big_Poe_Soul_Icon.png',
    'Magic Bean': 'OoT_Magic_Bean_Icon.png',
    'Pocket Egg': 'OoT_Weird_Egg_Icon.png',
    'Pocket Cucco': 'OoT_Cucco_Icon.png',
    'Odd Mushroom': 'OoT_Odd_Mushroom_Icon.png',
    'Odd Potion': 'OoT_Odd_Potion_Icon.png',
    'Poachers Saw': 'OoT_Poachers_Saw_Icon.png',
    'Broken Sword': 'OoT_Broken_Giants_Knife_Icon.png',
    'Prescription': 'OoT_Prescription_Icon.png',
    'Eyeball Frog': 'OoT_Eyeball_Frog_Icon.png',
    'Claim Check': 'OoT_Claim_Check_Icon.png',
    'Mirror Shield': 'OoT_Mirror_Shield_Icon.png',
    'Goron Tunic': 'OoT_Goron_Tunic_Icon.png',
    'Zora Tunic': 'OoT_Zora_Tunic_Icon.png',
    'Iron Boots': 'OoT_Iron_Boots_Icon.png',
    'Hover Boots': 'OoT_Hover_Boots_Icon.png',
    'Stone of Agony': 'OoT_Stone_of_Agony_Icon.png',
    'Gerudo Membership Card': 'OoT_Gerudo_Token_Icon.png',
    'Weird Egg': 'OoT_Weird_Egg_Icon.png',
    'Biggoron Sword': 'OoT_Giants_Knife_Icon.png',
    'Fire Arrows': 'OoT_Fire_Arrow_Icon.png',
    'Light Arrows': 'OoT_Light_Arrow_Icon.png',
    'Dins Fire': 'OoT_Dins_Fire_Icon.png',
    'Nayrus Love': 'OoT_Nayrus_Love_Icon.png',
    'Farores Wind': 'OoT_Farores_Wind_Icon.png',
    'Progressive Strength Upgrade': ['OoT_Gorons_Bracelet_Icon.png', 'OoT_Silver_Gauntlets_Icon.png', 'OoT_Golden_Gauntlets_Icon.png'],
    'Bomb Bag': 'OoT_Big_Bomb_Bag_Icon.png',
    'Bow': 'OoT_Fairy_Bow_Icon.png',
    'Slingshot': 'OoT_Fairy_Slingshot_Icon.png',
    'Progressive Wallet': 'OoT_Adults_Wallet_Icon.png',
    'Progressive Scale': ['OoT_Silver_Scale_Icon.png', 'OoT_Golden_Scale_Icon.png'],
    'Bombchus': 'OoT_Bombchu_Icon.png',
    'Magic Meter': 'OoT3D_Magic_Jar_Icon.png',
    'Bottle with Big Poe': 'OoT_Big_Poe_Soul_Icon.png',
    'Magic Bean Pack': 'OoT_Magic_Bean_Icon.png',
    'Zeldas Letter': 'OoT_Zeldas_Letter_Icon.png',
    'Zeldas Lullaby': 'white_note.png',
    'Eponas Song': 'white_note.png',
    'Suns Song': 'white_note.png',
    'Sarias Song': 'white_note.png',
    'Song of Time': 'white_note.png',
    'Song of Storms': 'white_note.png',
    'Minuet of Forest': 'green_note.png',
    'Prelude of Light': 'yellow_note.png',
    'Bolero of Fire': 'red_note.png',
    'Serenade of Water': 'blue_note.png',
    'Nocturne of Shadow': 'purple_note.png',
    'Requiem of Spirit': 'orange_note.png',
    'Kokiri Emerald': 'OoT_Spiritual_Stone_of_the_Forest_Icon.png',
    'Goron Ruby': 'OoT_Spiritual_Stone_of_Fire_Icon.png',
    'Zora Sapphire': 'OoT_Spiritual_Stone_of_Water_Icon.png',
    'Forest Medallion': 'OoT_Forest_Medallion_Icon.png',
    'Fire Medallion': 'OoT_Fire_Medallion_Icon.png',
    'Water Medallion': 'OoT_Water_Medallion_Icon.png',
    'Shadow Medallion': 'OoT_Shadow_Medallion_Icon.png',
    'Spirit Medallion': 'OoT_Spirit_Medallion_Icon.png',
    'Light Medallion': 'OoT_Light_Medallion_Icon.png',
    'Bombchu Drop': 'OoT_Bombchu_Icon.png',
    'Deku Stick Capacity': 'OoT_Deku_Stick_Icon.png',
    'Deku Shield': 'OoT_Deku_Shield_Icon.png',
    'Hylian Shield': 'OoT_Hylian_Shield_Icon.png',
    'Blue Fire': 'OoT_Blue_Fire_Icon.png',
    'Gold Skulltula Token': 'OoT_Token_Icon.png',
    'Deku Nut': 'OoT_Deku_Nut_Icon.png',
}

helperTextDict = {
    'Small Key (Bottom of the Well)': 'BOTW',
    'Small Key (Fire Temple)': 'Fire',
    'Small Key (Forest Temple)': 'Forest',
    'Small Key (Ganons Castle)': 'GC',
    'Small Key (Gerudo Training Grounds)': 'GTG',
    'Small Key (Shadow Temple)': 'Shadow',
    'Small Key (Spirit Temple)': 'Spirit',
    'Small Key (Water Temple)': 'Water',
    'Small Key (Gerudo Fortress)': 'GF',
    'Boss Key (Fire Temple)': 'Fire',
    'Boss Key (Shadow Temple)': 'Shadow',
    'Boss Key (Spirit Temple)': 'Spirit',
    'Boss Key (Water Temple)': 'Water',
    'Boss Key (Forest Temple)': 'Forest',
    'Boss Key (Ganons Castle)': 'GC',
    'Zeldas Lullaby': 'ZL',
    'Eponas Song': 'Epona',
    'Suns Song': 'Sun',
    'Sarias Song': 'Saria',
    'Song of Time': 'Time',
    'Song of Storms': 'Storms',
}

class ImageInvButton(QAbstractButton):
    def __init__(self,  name, max, current, parent):
        super(ImageInvButton, self).__init__()

        self.parent = parent
        self.name = name
        self.current = current
        self.max = max

        # Load one or more images for this button
        image_names = imageNamesDict.get(name, "fix.png")
        if isinstance(image_names, str):
            image_names = [image_names]
        paths = [os.path.join("images", image_name) for image_name in image_names]
        self.pixmaps = [QtGui.QPixmap(path) for path in paths]

        if name in helperTextDict:
            self.helperText = helperTextDict[name]
        else:
            self.helperText = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.plusEvent()
        if event.button() == Qt.RightButton:
            self.minusEvent()

    def plusEvent(self):
        if (self.current >= self.max):
            return
        self.current = self.current + 1
        logging.info("User has increased {} to {}".format(self.name, self.current))
        self.update()
        self.parent.update(self)

    def minusEvent(self):
        if (self.current < 1):
            return
        self.current = self.current - 1
        logging.info("User has decreased {} to {}".format(self.name, self.current))
        self.update()
        self.parent.update(self)

    def paintEvent(self, event):
        # Decide the extent of our rect (maintain a square button)
        rect = self.rect()
        assert rect.left() == 0
        assert rect.top() == 0
        if rect.width() > rect.height():
            rect = QRect(0, 0, rect.height(), rect.height())
        if rect.width() < rect.height():
            rect = QRect(0, 0, rect.width(), rect.width())

        # Black background, plus item, shaded if current == 0
        painter = QtGui.QPainter(self)
        painter.fillRect(rect, QtGui.QColor(0,0,0))

        if len(self.pixmaps) > 1 and self.current > 1:
            pixmap = self.pixmaps[self.current - 1]
        else:
            pixmap = self.pixmaps[0]
        painter.drawPixmap(rect, pixmap)
        if self.current == 0:
            painter.fillRect(rect, QtGui.QColor(0,0,0,180))

        # White text in center
        if self.current > 0 and self.max > 1 and len(self.pixmaps) == 1:
            font = QtGui.QFont('Open Sans', 14)
            painter.setPen(QtGui.QColor(0, 0, 0))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            path = QtGui.QPainterPath()
            path.addText(0, 0, font, str(self.current))
            textcenter = path.boundingRect().center()
            boxcenter = QPointF(rect.center())
            difference = boxcenter - textcenter
            path.translate(difference)
            painter.drawPath(path)

        # Helper text
        if self.helperText:
            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.setFont(QtGui.QFont('Open Sans', 9))
            painter.drawText(rect, self.helperText)

    def sizeHint(self):
        return QSize(80, 80)
