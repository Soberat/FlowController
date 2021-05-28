import sys
import pyqtgraph
from PyQt5.QtCore import Qt, QTimer, QRegExp
from PyQt5.QtGui import QRegExpValidator, QIntValidator, QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox, QSlider, QLabel, QPushButton, QFormLayout, QComboBox, QErrorMessage
)
from pyqtgraph import PlotWidget
import numpy as np

import ControllerGUITab
from Controller import Controller
from AR6X2ConfigDialog import AR6X2ConfigDialog
from AR6X2 import AR6X2
from SensorConfigDialog import SensorConfigDialog
from Sensor import Sensor
from datetime import datetime
from numpy_ringbuffer import RingBuffer
from serial import SerialException
import re


class GlobalTab(QWidget):
    def __init__(self, controllers):
        super().__init__()

        masterLayout = QGridLayout()
        self.controller1Checkbox = None
        self.controller2Checkbox = None
        self.controller3Checkbox = None
        self.controller4Checkbox = None

        self.saveCsvButton = None
        self.dosingControlButton = None

        self.savingEnabled = False
        self.dosingEnabled = False

        self.controllers = controllers

        self.refreshTimer = QTimer()
        self.refreshTimer.setInterval(1000)
        self.refreshTimer.timeout.connect(self.update_states)
        self.refreshTimer.start()

        masterLayout.addLayout(self.create_left_column(controllers), 0, 0)

        self.controllerCheckboxes = [self.controller1Checkbox,
                                     self.controller2Checkbox,
                                     self.controller3Checkbox,
                                     self.controller4Checkbox]
        self.checkboxesStates = [box.isChecked() for box in self.controllerCheckboxes]

        self.setLayout(masterLayout)

    def update_selection(self):
        self.checkboxesStates = [box.isChecked() for box in self.controllerCheckboxes]

        if not any(self.checkboxesStates):
            self.dosingControlButton.setEnabled(False)
            self.saveCsvButton.setEnabled(False)
        else:
            self.dosingControlButton.setEnabled(True)
            self.saveCsvButton.setEnabled(True)

    def update_states(self):
        dosing = [not self.controllers[idx].dosingControlButton.isChecked() for idx, val in enumerate(self.checkboxesStates) if val]
        saving = [self.controllers[idx].csvFile is None for idx, val in enumerate(self.checkboxesStates) if val]

        if all(dosing) and not self.dosingEnabled:
            self.dosing_processes_stop()

        if all(saving) and not self.savingEnabled:
            self.saving_to_csvs_stop()

    def dosing_processes_start(self):
        self.controller1Checkbox.setEnabled(False)
        self.controller2Checkbox.setEnabled(False)
        self.controller3Checkbox.setEnabled(False)
        self.controller4Checkbox.setEnabled(False)
        self.dosingControlButton.setText("Stop dosing processes")
        self.dosingControlButton.clicked.connect(self.dosing_processes_stop)
        self.dosingEnabled = True

        for controllerTab in [controller for idx, controller in enumerate(self.controllers) if self.checkboxesStates[idx]]:
            if controllerTab is not None:
                controllerTab.dosingControlButton.setChecked(True)
                # Checking the button state via setChecked does not trigger the changedState callback, so we call it manually
                controllerTab.update_dosing_state()

    def dosing_processes_stop(self):
        self.controller1Checkbox.setEnabled(self.controllers[0] is not None and not self.savingEnabled)
        self.controller2Checkbox.setEnabled(self.controllers[1] is not None and not self.savingEnabled)
        self.controller3Checkbox.setEnabled(self.controllers[2] is not None and not self.savingEnabled)
        self.controller4Checkbox.setEnabled(self.controllers[3] is not None and not self.savingEnabled)
        self.dosingControlButton.setText("Start dosing processes")
        self.dosingControlButton.clicked.connect(self.dosing_processes_start)
        self.dosingEnabled = False

        for controllerTab in [controller for idx, controller in enumerate(self.controllers) if self.checkboxesStates[idx]]:
            if controllerTab is not None:
                controllerTab.dosingControlButton.setChecked(False)
                controllerTab.update_dosing_state()

    def saving_to_csvs_start(self):
        self.controller1Checkbox.setEnabled(False)
        self.controller2Checkbox.setEnabled(False)
        self.controller3Checkbox.setEnabled(False)
        self.controller4Checkbox.setEnabled(False)
        self.saveCsvButton.setText("Stop saving to CSVs")
        self.saveCsvButton.clicked.connect(self.saving_to_csvs_stop)
        self.savingEnabled = True

        for controllerTab in [controller for idx, controller in enumerate(self.controllers) if self.checkboxesStates[idx]]:
            if controllerTab is not None:
                controllerTab.saveCsvButton.setChecked(True)
                controllerTab.save_to_csv_start()

    def saving_to_csvs_stop(self):
        self.controller1Checkbox.setEnabled(self.controllers[0] is not None and not self.dosingEnabled)
        self.controller2Checkbox.setEnabled(self.controllers[1] is not None and not self.dosingEnabled)
        self.controller3Checkbox.setEnabled(self.controllers[2] is not None and not self.dosingEnabled)
        self.controller4Checkbox.setEnabled(self.controllers[3] is not None and not self.dosingEnabled)
        self.saveCsvButton.setText("Start saving to CSVs")
        self.saveCsvButton.clicked.connect(self.saving_to_csvs_start)
        self.savingEnabled = False

        for controllerTab in [controller for idx, controller in enumerate(self.controllers) if self.checkboxesStates[idx]]:
            if controllerTab is not None:
                controllerTab.saveCsvButton.setChecked(False)
                controllerTab.save_to_csv_stop()

    def create_left_column(self, controllerTabs):
        # Create a vertical layout for the left column
        leftColumnLayout = QVBoxLayout()

        # Valve override group
        vorGroup = QGroupBox("Simultaneous starting")
        vorLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.controller1Checkbox = QCheckBox()
        self.controller1Checkbox.setChecked(controllerTabs[0] is not None)
        self.controller1Checkbox.setEnabled(controllerTabs[0] is not None)
        self.controller1Checkbox.stateChanged.connect(self.update_selection)

        layout.addWidget(QLabel("Controller 1"))
        layout.addWidget(self.controller1Checkbox)

        self.controller2Checkbox = QCheckBox()
        self.controller2Checkbox.setChecked(controllerTabs[1] is not None)
        self.controller2Checkbox.setEnabled(controllerTabs[1] is not None)
        self.controller2Checkbox.stateChanged.connect(self.update_selection)

        layout.addWidget(QLabel("Controller 2"))
        layout.addWidget(self.controller2Checkbox)

        self.controller3Checkbox = QCheckBox()
        self.controller3Checkbox.setChecked(controllerTabs[2] is not None)
        self.controller3Checkbox.setEnabled(controllerTabs[2] is not None)
        self.controller3Checkbox.stateChanged.connect(self.update_selection)

        layout.addWidget(QLabel("Controller 3"))
        layout.addWidget(self.controller3Checkbox)

        self.controller4Checkbox = QCheckBox()
        self.controller4Checkbox.setChecked(controllerTabs[3] is not None)
        self.controller4Checkbox.setEnabled(controllerTabs[3] is not None)
        self.controller4Checkbox.stateChanged.connect(self.update_selection)

        layout.addWidget(QLabel("Controller 4"))
        layout.addWidget(self.controller4Checkbox)

        vorLayout.addLayout(layout)

        layout = QHBoxLayout()

        self.dosingControlButton = QPushButton("Start dosing processes")
        self.dosingControlButton.clicked.connect(self.dosing_processes_start)
        self.saveCsvButton = QPushButton("Start saving to CSVs")
        self.saveCsvButton.clicked.connect(self.saving_to_csvs_start)

        layout.addWidget(self.dosingControlButton)
        layout.addWidget(self.saveCsvButton)

        vorLayout.addLayout(layout)

        vorGroup.setLayout(vorLayout)
        vorGroup.setFixedWidth(400)
        vorGroup.setFixedHeight(100)

        leftColumnLayout.addWidget(vorGroup, alignment=Qt.AlignTop)

        return leftColumnLayout
