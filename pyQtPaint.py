#!/bin/env python26

import os
import sys

from PyQt4.QtGui import *
from PyQt4.QtCore import *

try:
    from PIL import Image, ImageDraw
except ImportError:
    import Image, ImageDraw # linux


if __name__=="__main__":
    app = QApplication(sys.argv)
    app.connect(app, SIGNAL("lastWindowClosed()"),
                app, SLOT("quit()"))


class Painting(QWidget):

    numberKeys = [Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, 
            Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9]

    defaultSize = QSize(640,480)

    def __init__(self, parent, plate=None):
        super(Painting,self).__init__(parent)
        self.setFocusPolicy(Qt.WheelFocus)
        self.clear()
        if plate != None:
            self.loadPlate(plate)
        else:
            self.paintingSize = defaultSize 
        self.currentPos = QPoint(0,0)
        self.setLayers(9)

        self.clipboard = app.clipboard()

    def getPixmap(self,layer=None):
        if layer in (None, "All"):
            px = QPixmap.grabWidget(self)
        elif layer in range(self.numLayers):
            px = QPixmap(self.images[layer])
        elif layer == "Plate":
            px = QPixmap(self.plate)
        return px

    def setPixmap(self,pixmap,layer=None):
        if layer in (None, "All"):
            self.setLayers(self.numLayers)
            self.setPixmap(pixmap,"Plate")
        elif layer in range(self.numLayers):
            self.images[layer] = pixmap.toImage()
        elif layer == "Plate":
            self.plate.setPixmap(pixmap)

    #def image(self):
    #    return QImage(self.getPixmap())
    
    #def setImage(self,image):
    #    self.plate = QImage(image)
        
    def _get_width(self):  return self.paintingSize.width()
    def _set_width(self,width):   self.paintingSize.setWidth(width)
    width = property(_get_width,_set_width)

    def _get_height(self): return self.paintingSize.height()
    def _set_height(self,height): self.paintingSize.setHeight(height)
    height = property(_get_height,_set_height)

    def setLayers(self,numLayers=9):
        self.numLayers = min(9,numLayers)
        self.images = list()
        self.colors = [ QColor() for n in range(numLayers)]
        [ c.setHsv(int(255.0*float(i)/(numLayers-1)),255,255) for i,c in enumerate(self.colors)]
        for i in range(self.numLayers+1):
            self.images.append( QImage(self.defaultSize,QImage.Format_ARGB32) )
        self.currentImageIndex = 0
        icon = self._getIcon("Layer")
        self.colorIcons = []
        inset = 8
        iconSize = icon.actualSize(QSize(32,32))
        pm = icon.pixmap(iconSize)
        pi = pm.toImage()
        b = pi.bits().asstring(pi.numBytes())
    
        rect = QRect(QPoint(0,0),iconSize).adjusted (inset, inset, -inset, -inset)
        for i,clr in enumerate(self.colors):
            im = Image.frombuffer("RGBA", (pi.width(),pi.height()), b,'raw', "RGBA", 0, 1)
            draw = ImageDraw.Draw(im)
            rgb = (clr.red(),clr.green(),clr.blue())
            draw.rectangle((inset, inset, im.size[0]-inset, im.size[1]-inset), fill=rgb)
            data = im.tostring('raw', 'RGBA')
            qimage = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)
            p = QPixmap(qimage.rgbSwapped())
            ic = QIcon(p)
            self.colorIcons.append(ic)
        
        # Current paint surface:
        self.image = self.images[0]
        self.color = self.colors[0]
        self.currentImageIndex = 0
        
    def loadPlate(self,imagePath):
        self.plate = QImage(imagePath)
        self.paintingSize = self.plate.size()
        self.resize(self.width,self.height)
    
    def sizeHint(self):
        return QSize(self.width,self.height)

    def mouseMoveEvent(self, event):
        pen = QPen()
        pen.setColor(self.color)
        pen.setWidth(3)
        painter = QPainter(self.image)
        painter.setPen(pen)
        painter.drawLine(self.currentPos, event.pos())
        self.currentPos=QPoint(event.pos())
        self.update()
        self.currentPos=QPoint(event.pos())
        self.update()

    def mousePressEvent(self, event):
        if event.button() in (Qt.LeftButton,):
            self.doPaintStart(event)
        elif event.button() in (Qt.RightButton,):
            self.doContextMenu(event)
    
    def doPaintStart(self,event):
        painter = QPainter(self.image)
        pen = QPen()
        pen.setColor(QColor(Qt.black))
        pen.setWidth(8)
        painter.setPen(pen)
        painter.drawPoint(event.pos())
        self.currentPos=QPoint(event.pos())
        self.update()

    def doContextMenu(self,event):
        menu = QMenu(self)

        def addLayerMenu(m,name,icon,includeAll=True,includePlate=True):
            lm = m.addMenu(self._getIcon(icon),name)
            if includePlate:
                action = lm.addAction("Plate")
                self.connect(action, SIGNAL("triggered()"), 
                    lambda s=self,n=name: s.contextMenuCB(n,"Layer","Plate"))
            for index in range(self.numLayers):
                action = lm.addAction(self.colorIcons[index], "Layer #%d" % (index+1))
                self.connect(action, SIGNAL("triggered()"), 
                    lambda s=self,n=name,i=index: s.contextMenuCB(n,"Layer",i))
            if includeAll:
                lm.addSeparator()
                action = lm.addAction("All")
                self.connect(action, SIGNAL("triggered()"), 
                    lambda s=self,n=name: s.contextMenuCB(n,"Layer","All"))

        for i in [ 
            ("Open", "Open"), 
            ("Save", "Save"), 
            "---",
            ("Copy-Layer-Plate-All", "Page-Copy"), 
            ("Paste-Layer-Plate-All","Page-Paste"), 
            ("Clear-Layer-Plate-All","Bin"),
            "---",
            ("Paint-Layer","Palette"),
            "---",
            ("Quit","Quit"), 
            ]:
            if isinstance(i,tuple):
                name, icon = i
                if '-' in name:
                    name, subname = name.split("-",1)
                    words = subname.split("-")
                    addLayerMenu(menu,name,icon,
                        includePlate=("Plate" in words),
                        includeAll=("All" in words))
                else:
                    subname = None
                    action = menu.addAction(self._getIcon(icon),name)
                    self.connect(action, SIGNAL("triggered()"), 
                        lambda s=self,n=name: s.contextMenuCB(n))
            else:
                if isinstance(i,str) and i.startswith("-"):
                    menu.addSeparator()
        menu.exec_(event.globalPos())
        event.accept()

    def _getIcon(self,name):
        p = os.path.join("images", "icons", "%s.png" % name)
        return QIcon(str(p))

    def contextMenuCB(self,name,arg=None,param=None):

        if name == "Open":
            filePath   = QFileDialog.getOpenFileName(self, 
                "Open Image", "", "Jpeg Files (*.jpg), Png Files (*.png)")
            if not filePath:
                return
            fp = os.path.abspath(str(filePath))
            self.loadPlate(str(fp))
            self.update()
        elif name == "Save":
            filePath   = QFileDialog.getSaveFileName(self, 
                "Save Image", "", "Jpeg Files (*.jpg), Png Files (*.png)")
            if not filePath:
                return
            fp = os.path.abspath(str(filePath))
            savePixmap = self.getPixmap()
            savePixmap.save(str(fp))
        elif name == "Copy":
            self.clipboard.setPixmap(self.getPixmap(layer=param))
        elif name == "Paste":
            self.setPixmap(self.clipboard.pixmap(),layer=param)
        elif name == "Clear":
            self.clear(layer=param)
        elif name == "Paint":
            self.changedPaintLayerCB(param)
        elif name == "Quit":
            self.quitCB()

    def quitCB(self):
        self.parent().close()

    def clear(self,layer=None):
        if layer in (None,"All"):
            self.plate = QImage(self.defaultSize,QImage.Format_ARGB32)
            self.setLayers()
        elif layer in ("Plate",):
            self.plate = QImage(self.plate.size(),QImage.Format_ARGB32)
        else:
            self.images[layer] = QImage(self.plate.size(),QImage.Format_ARGB32)
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(QPoint(0,0), self.plate)
        for i in range(self.numLayers+1):
            painter.drawImage(QPoint(0,0), self.images[i])

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.AltModifier:
            if event.key() in self.numberKeys:
                i = self.numberKeys.index(event.key())
                self.changedPaintLayerCB(i)
                event.accept()

    def changedPaintLayerCB(self,layer):
        self.emit(SIGNAL("changedPaintLayer (int)"),layer)
        self.setPaintLayer(layer)

    def setPaintLayer(self,layer):  
        self.image = self.images[layer]
        self.color = self.colors[layer]
        self.currentImageIndex = layer


class MainWindow(QMainWindow):

    def __init__(self, plate=None, parent=None):
        super(MainWindow,self).__init__(parent)
        self.painting = Painting(self,plate)
        self.setCentralWidget(self.painting)

def main(args):
    resourceImageDir = os.path.dirname(__file__)
    win = MainWindow( os.path.join(resourceImageDir, "images", "bricks.bmp") )
    win.show()
    app.exec_()

if __name__=="__main__":
    main(sys.argv)