# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\sashgorokhov\PycharmProjects\edp\edp\gui\ui\find_nearest_station.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(205, 203)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(104, 76, 61, 100))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(104, 76, 61, 100))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(104, 76, 61, 100))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(104, 76, 61, 100))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        Form.setPalette(palette)
        Form.setAutoFillBackground(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(Form)
        self.label.setStyleSheet("color: rgb(240, 123, 5);")
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtWidgets.QLabel(Form)
        self.label_2.setStyleSheet("color: rgb(240, 123, 5);")
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.facilities_combobox = QtWidgets.QComboBox(Form)
        self.facilities_combobox.setStyleSheet("")
        self.facilities_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.facilities_combobox.setFrame(True)
        self.facilities_combobox.setObjectName("facilities_combobox")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.facilities_combobox.addItem("")
        self.horizontalLayout.addWidget(self.facilities_combobox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.search_button = QtWidgets.QPushButton(Form)
        self.search_button.setStyleSheet("QPushButton {\n"
                                         "                            padding: 3px;\n"
                                         "                            color: rgb(232, 232, 232);\n"
                                         "                            background-color: rgb(0, 179, 247);\n"
                                         "                            border-style: solid;\n"
                                         "                            }\n"
                                         "\n"
                                         "                            QPushButton:hover {\n"
                                         "                            background-color: rgb(10, 139, 214);\n"
                                         "                            }\n"
                                         "\n"
                                         "                            QPushButton:pressed {\n"
                                         "                            color: rgb(63, 63, 63);\n"
                                         "                            background-color: rgb(232, 232, 232);\n"
                                         "                            border-color: rgb(232, 232, 232);\n"
                                         "                            }\n"
                                         "                        ")
        self.search_button.setObjectName("search_button")
        self.verticalLayout.addWidget(self.search_button)
        self.result_layout = QtWidgets.QVBoxLayout()
        self.result_layout.setObjectName("result_layout")
        self.result_label_1 = QtWidgets.QLabel(Form)
        self.result_label_1.setStyleSheet("\n"
                                          "\n"
                                          "                                    QLabel {\n"
                                          "                                    color: rgb(232, 232, 232);\n"
                                          "                                    padding: 3px;\n"
                                          "                                    background-color: rgba(106, 54, 2, 180);\n"
                                          "                                    }\n"
                                          "\n"
                                          "                                    QLabel:hover {\n"
                                          "                                    color: rgb(62, 62, 62);\n"
                                          "                                    padding: 3px;\n"
                                          "                                    background-color: rgb(240, 123, 5);\n"
                                          "                                    }\n"
                                          "\n"
                                          "                                    QLabel:pressed {\n"
                                          "                                    color: rgb(63, 63, 63);\n"
                                          "                                    background-color: rgb(232, 232, 232);\n"
                                          "                                    border-color: rgb(232, 232, 232);\n"
                                          "                                    }\n"
                                          "                                ")
        self.result_label_1.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.result_label_1.setTextFormat(QtCore.Qt.PlainText)
        self.result_label_1.setWordWrap(True)
        self.result_label_1.setObjectName("result_label_1")
        self.result_layout.addWidget(self.result_label_1)
        self.result_label_2 = QtWidgets.QLabel(Form)
        self.result_label_2.setStyleSheet("\n"
                                          "\n"
                                          "                                    QLabel {\n"
                                          "                                    color: rgb(232, 232, 232);\n"
                                          "                                    padding: 3px;\n"
                                          "                                    background-color: rgba(106, 54, 2, 180);\n"
                                          "                                    }\n"
                                          "\n"
                                          "                                    QLabel:hover {\n"
                                          "                                    color: rgb(62, 62, 62);\n"
                                          "                                    padding: 3px;\n"
                                          "                                    background-color: rgb(240, 123, 5);\n"
                                          "                                    }\n"
                                          "\n"
                                          "                                    QLabel:pressed {\n"
                                          "                                    color: rgb(63, 63, 63);\n"
                                          "                                    background-color: rgb(232, 232, 232);\n"
                                          "                                    border-color: rgb(232, 232, 232);\n"
                                          "                                    }\n"
                                          "                                ")
        self.result_label_2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.result_label_2.setTextFormat(QtCore.Qt.PlainText)
        self.result_label_2.setWordWrap(True)
        self.result_label_2.setObjectName("result_label_2")
        self.result_layout.addWidget(self.result_label_2)
        self.result_label_3 = QtWidgets.QLabel(Form)
        self.result_label_3.setStyleSheet("\n"
                                          "\n"
                                          "                                    QLabel {\n"
                                          "                                    color: rgb(232, 232, 232);\n"
                                          "                                    padding: 3px;\n"
                                          "                                    background-color: rgba(106, 54, 2, 180);\n"
                                          "                                    }\n"
                                          "\n"
                                          "                                    QLabel:hover {\n"
                                          "                                    color: rgb(62, 62, 62);\n"
                                          "                                    padding: 3px;\n"
                                          "                                    background-color: rgb(240, 123, 5);\n"
                                          "                                    }\n"
                                          "\n"
                                          "                                    QLabel:pressed {\n"
                                          "                                    color: rgb(63, 63, 63);\n"
                                          "                                    background-color: rgb(232, 232, 232);\n"
                                          "                                    border-color: rgb(232, 232, 232);\n"
                                          "                                    }\n"
                                          "                                ")
        self.result_label_3.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.result_label_3.setTextFormat(QtCore.Qt.PlainText)
        self.result_label_3.setWordWrap(True)
        self.result_label_3.setObjectName("result_label_3")
        self.result_layout.addWidget(self.result_label_3)
        self.verticalLayout.addLayout(self.result_layout)
        spacerItem = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        self.label.setText(_translate("Form", "Find nearest station"))
        self.label_2.setText(_translate("Form", "Facilities"))
        self.facilities_combobox.setItemText(0, _translate("Form", "---"))
        self.facilities_combobox.setItemText(1, _translate("Form", "has_blackmarket"))
        self.facilities_combobox.setItemText(2, _translate("Form", "has_market"))
        self.facilities_combobox.setItemText(3, _translate("Form", "has_technology_broker"))
        self.facilities_combobox.setItemText(4, _translate("Form", "has_refuel"))
        self.facilities_combobox.setItemText(5, _translate("Form", "has_repair"))
        self.facilities_combobox.setItemText(6, _translate("Form", "has_rearm"))
        self.facilities_combobox.setItemText(7, _translate("Form", "has_outfitting"))
        self.facilities_combobox.setItemText(8, _translate("Form", "has_shipyard"))
        self.facilities_combobox.setItemText(9, _translate("Form", "has_material_trader"))
        self.search_button.setText(_translate("Form", "Search"))
        self.result_label_1.setText(_translate("Form", "TextLabel"))
        self.result_label_2.setText(_translate("Form", "TextLabel"))
        self.result_label_3.setText(_translate("Form", "TextLabel"))

