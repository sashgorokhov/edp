# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\sashgorokhov\PycharmProjects\edp\edp\gui\ui\main_window.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(300, 262)
        MainWindow.setMinimumSize(QtCore.QSize(300, 0))
        MainWindow.setMaximumSize(QtCore.QSize(300, 16777215))
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setPointSize(8)
        font.setKerning(True)
        MainWindow.setFont(font)
        MainWindow.setWindowOpacity(1.0)
        MainWindow.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        MainWindow.setAnimated(True)
        MainWindow.setDocumentMode(False)
        MainWindow.setDockNestingEnabled(False)
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 300, 21))
        self.menubar.setObjectName("menubar")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setTearOffEnabled(False)
        self.menuSettings.setObjectName("menuSettings")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setSizeGripEnabled(False)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionOverview = QtWidgets.QAction(MainWindow)
        self.actionOverview.setCheckable(True)
        self.actionOverview.setChecked(True)
        self.actionOverview.setObjectName("actionOverview")
        self.actionEvent_list = QtWidgets.QAction(MainWindow)
        self.actionEvent_list.setCheckable(True)
        self.actionEvent_list.setChecked(True)
        self.actionEvent_list.setObjectName("actionEvent_list")
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "EDP"))
        self.menuSettings.setTitle(_translate("MainWindow", "Settings"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.actionOverview.setText(_translate("MainWindow", "Overview"))
        self.actionEvent_list.setText(_translate("MainWindow", "Event list"))

