# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\sashgorokhov\PycharmProjects\edp\edp\gui\ui\overlay_window.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(732, 611)
        Form.setMinimumSize(QtCore.QSize(724, 580))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(240, 123, 5))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(240, 123, 5))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        Form.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Corbel")
        Form.setFont(font)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout_2.setContentsMargins(4, 4, 4, 4)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(Form)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.setup_button = QtWidgets.QPushButton(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.setup_button.sizePolicy().hasHeightForWidth())
        self.setup_button.setSizePolicy(sizePolicy)
        self.setup_button.setMinimumSize(QtCore.QSize(20, 20))
        self.setup_button.setMaximumSize(QtCore.QSize(199999, 20))
        self.setup_button.setStyleSheet("QPushButton {\n"
                                        "    padding: 3px;\n"
                                        "    color: rgb(232, 232, 232);\n"
                                        "    background-color: rgb(0, 179, 247);\n"
                                        "    border-style: solid;\n"
                                        "}\n"
                                        "\n"
                                        "QPushButton:hover {\n"
                                        "    background-color: rgb(10, 139, 214);\n"
                                        "}\n"
                                        "\n"
                                        "QPushButton:pressed {\n"
                                        "    color: rgb(63, 63, 63);\n"
                                        "    background-color: rgb(232, 232, 232);\n"
                                        "    border-color:  rgb(232, 232, 232);\n"
                                        "}")
        self.setup_button.setCheckable(True)
        self.setup_button.setObjectName("setup_button")
        self.horizontalLayout_2.addWidget(self.setup_button)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.vlayout_top_left = QtWidgets.QVBoxLayout()
        self.vlayout_top_left.setObjectName("vlayout_top_left")
        self.verticalLayout.addLayout(self.vlayout_top_left)
        spacerItem1 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.verticalLayout_7 = QtWidgets.QVBoxLayout()
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.vlayout_top_center = QtWidgets.QVBoxLayout()
        self.vlayout_top_center.setObjectName("vlayout_top_center")
        self.verticalLayout_7.addLayout(self.vlayout_top_center)
        spacerItem2 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_7.addItem(spacerItem2)
        self.gridLayout.addLayout(self.verticalLayout_7, 0, 2, 1, 1)
        self.verticalLayout_15 = QtWidgets.QVBoxLayout()
        self.verticalLayout_15.setObjectName("verticalLayout_15")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem3 = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem3)
        self.verticalLayout_15.addLayout(self.horizontalLayout)
        self.vlayout_top_right = QtWidgets.QVBoxLayout()
        self.vlayout_top_right.setObjectName("vlayout_top_right")
        self.verticalLayout_15.addLayout(self.vlayout_top_right)
        spacerItem4 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_15.addItem(spacerItem4)
        self.gridLayout.addLayout(self.verticalLayout_15, 0, 4, 1, 1)
        spacerItem5 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem5, 1, 2, 1, 1)
        self.verticalLayout_17 = QtWidgets.QVBoxLayout()
        self.verticalLayout_17.setObjectName("verticalLayout_17")
        spacerItem6 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_17.addItem(spacerItem6)
        self.vlayout_center_left = QtWidgets.QVBoxLayout()
        self.vlayout_center_left.setObjectName("vlayout_center_left")
        self.verticalLayout_17.addLayout(self.vlayout_center_left)
        spacerItem7 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_17.addItem(spacerItem7)
        self.gridLayout.addLayout(self.verticalLayout_17, 2, 0, 1, 1)
        spacerItem8 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.MinimumExpanding,
                                            QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem8, 2, 1, 1, 1)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        spacerItem9 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem9)
        self.vlayout_center = QtWidgets.QVBoxLayout()
        self.vlayout_center.setObjectName("vlayout_center")
        self.verticalLayout_3.addLayout(self.vlayout_center)
        spacerItem10 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem10)
        self.gridLayout.addLayout(self.verticalLayout_3, 2, 2, 1, 1)
        spacerItem11 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.MinimumExpanding,
                                             QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem11, 2, 3, 1, 1)
        self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        spacerItem12 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem12)
        self.vlayout_center_right = QtWidgets.QVBoxLayout()
        self.vlayout_center_right.setObjectName("vlayout_center_right")
        self.verticalLayout_5.addLayout(self.vlayout_center_right)
        spacerItem13 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem13)
        self.gridLayout.addLayout(self.verticalLayout_5, 2, 4, 1, 1)
        spacerItem14 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem14, 3, 2, 1, 1)
        self.verticalLayout_13 = QtWidgets.QVBoxLayout()
        self.verticalLayout_13.setObjectName("verticalLayout_13")
        spacerItem15 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_13.addItem(spacerItem15)
        self.vlayout_bottom_left = QtWidgets.QVBoxLayout()
        self.vlayout_bottom_left.setObjectName("vlayout_bottom_left")
        self.verticalLayout_13.addLayout(self.vlayout_bottom_left)
        self.gridLayout.addLayout(self.verticalLayout_13, 4, 0, 1, 1)
        self.verticalLayout_11 = QtWidgets.QVBoxLayout()
        self.verticalLayout_11.setObjectName("verticalLayout_11")
        spacerItem16 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_11.addItem(spacerItem16)
        self.vlayout_bottom_center = QtWidgets.QVBoxLayout()
        self.vlayout_bottom_center.setObjectName("vlayout_bottom_center")
        self.verticalLayout_11.addLayout(self.vlayout_bottom_center)
        self.gridLayout.addLayout(self.verticalLayout_11, 4, 2, 1, 1)
        self.verticalLayout_9 = QtWidgets.QVBoxLayout()
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        spacerItem17 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_9.addItem(spacerItem17)
        self.vlayout_bottom_right = QtWidgets.QVBoxLayout()
        self.vlayout_bottom_right.setObjectName("vlayout_bottom_right")
        self.verticalLayout_9.addLayout(self.vlayout_bottom_right)
        self.gridLayout.addLayout(self.verticalLayout_9, 4, 4, 1, 1)
        self.verticalLayout_2.addLayout(self.gridLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label.setText(_translate("Form", "EDP Overlay UI"))
        self.setup_button.setText(_translate("Form", "Setup"))

