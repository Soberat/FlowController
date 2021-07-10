from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QPushButton, QComboBox, QFormLayout
)
from Brooks025X import Brooks025X
import resources


# TODO: Add options a group for global device options
# TODO: Large plot of all measurements

class GlobalTab(QWidget):
    def __init__(self, brooksObject: Brooks025X, controllerTabs):
        super().__init__()

        self.brooks = brooksObject
        self.tabs = controllerTabs

        self.saving1Checkbox = QCheckBox()
        self.saving2Checkbox = QCheckBox()
        self.saving3Checkbox = QCheckBox()
        self.saving4Checkbox = QCheckBox()
        self.savingCheckboxes = [self.saving1Checkbox, self.saving2Checkbox, self.saving3Checkbox, self.saving4Checkbox]

        self.dosing1Checkbox = QCheckBox()
        self.dosing2Checkbox = QCheckBox()
        self.dosing3Checkbox = QCheckBox()
        self.dosing4Checkbox = QCheckBox()
        self.dosingCheckboxes = [self.dosing1Checkbox, self.dosing2Checkbox, self.dosing3Checkbox, self.dosing4Checkbox]

        self.saving1Enabled = False
        self.saving2Enabled = False
        self.saving3Enabled = False
        self.saving4Enabled = False

        self.dosing1Enabled = False
        self.dosing2Enabled = False
        self.dosing3Enabled = False
        self.dosing4Enabled = False

        self.saveCsvButton = None
        self.dosingControlButton = None

        errorImage = QPixmap(":/error.png")

        self.savingErrorLabel = QLabel()
        self.savingErrorLabel.setPixmap(errorImage)
        self.savingErrorLabel.setMask(errorImage.mask())

        self.dosingErrorLabel = QLabel()
        self.dosingErrorLabel.setPixmap(errorImage)
        self.dosingErrorLabel.setMask(errorImage.mask())

        self.savingInfoLabel = QLabel()
        self.dosingInfoLabel = QLabel()

        self.audioBeepCheckbox = QCheckBox()
        self.zeroSuppressCheckbox = QCheckBox()
        self.powerSpClearCheckbox = QCheckBox()

        # Connect to all existing tabs' signals
        if self.tabs[0] is not None:
            self.tabs[0].dosingSignal.connect(self.update_dosing1)
            self.tabs[0].savingSignal.connect(self.update_saving1)

        if self.tabs[1] is not None:
            self.tabs[1].dosingSignal.connect(self.update_dosing2)
            self.tabs[1].savingSignal.connect(self.update_saving2)

        if self.tabs[2] is not None:
            self.tabs[2].dosingSignal.connect(self.update_dosing3)
            self.tabs[2].savingSignal.connect(self.update_saving3)

        if self.tabs[3] is not None:
            self.tabs[3].dosingSignal.connect(self.update_dosing4)
            self.tabs[3].savingSignal.connect(self.update_saving4)

        masterLayout = QGridLayout()
        masterLayout.addLayout(self.create_left_column(self.tabs), 0, 0)

        self.setLayout(masterLayout)

    # Callbacks to updating functions
    def update_dosing1(self, enabled: bool):
        self.dosing1Enabled = enabled
        self.update_checkboxes_dosing()

    def update_dosing2(self, enabled: bool):
        self.dosing2Enabled = enabled
        self.update_checkboxes_dosing()

    def update_dosing3(self, enabled: bool):
        self.dosing3Enabled = enabled
        self.update_checkboxes_dosing()

    def update_dosing4(self, enabled: bool):
        self.dosing4Enabled = enabled
        self.update_checkboxes_dosing()

    def update_saving1(self, enabled: bool):
        self.saving1Enabled = enabled
        self.saving_signal_update()

    def update_saving2(self, enabled: bool):
        self.saving2Enabled = enabled
        self.saving_signal_update()

    def update_saving3(self, enabled: bool):
        self.saving3Enabled = enabled
        self.saving_signal_update()

    def update_saving4(self, enabled: bool):
        self.saving4Enabled = enabled
        self.saving_signal_update()

    # If user turned off all ongoing saving processes, this function will revert the button back to the proper state
    def saving_signal_update(self):
        if not any([self.saving1Enabled, self.saving2Enabled, self.saving3Enabled, self.saving4Enabled]):
            self.saveCsvButton.setText("Start saving to CSVs")
            self.saveCsvButton.clicked.connect(self.start_saving_to_csv)

    # Callbacks for changed selection of controllers
    # Saving can be enabled even if it was already enabled, it will just be restarted
    def update_checkboxes_saving(self):
        enabled = any([box.isChecked() for box in self.savingCheckboxes])
        self.saveCsvButton.setEnabled(enabled)
        self.savingInfoLabel.setVisible(not enabled)
        self.savingErrorLabel.setVisible(not enabled)

    # Dosing requires valid vectors for all controllers in the program
    def update_checkboxes_dosing(self):
        enabled = any([box.isChecked() for box in self.dosingCheckboxes]) and not any([self.dosing1Enabled,
                                                                                       self.dosing2Enabled,
                                                                                       self.dosing3Enabled,
                                                                                       self.dosing4Enabled])
        self.dosingControlButton.setEnabled(enabled)
        self.dosingInfoLabel.setVisible(not enabled)
        self.dosingErrorLabel.setVisible(not enabled)

        # Set an error message depending on the error
        if not any([box.isChecked() for box in self.dosingCheckboxes]):
            self.dosingInfoLabel.setText("No controller was selected!")
        else:
            self.dosingInfoLabel.setText("One of dosing vectors is wrong or dosing is already enabled for a controller")

    def start_saving_to_csv(self):
        for box in self.savingCheckboxes:
            box.setEnabled(False)
        self.saveCsvButton.setText("Stop saving to CSVs")
        self.saveCsvButton.clicked.connect(self.stop_saving_to_csv)

        if self.saving1Checkbox.isChecked():
            self.tabs[0].save_to_csv_start()
        if self.saving2Checkbox.isChecked():
            self.tabs[1].save_to_csv_start()
        if self.saving3Checkbox.isChecked():
            self.tabs[2].save_to_csv_start()
        if self.saving4Checkbox.isChecked():
            self.tabs[3].save_to_csv_start()

    # Stop the saving which is in progress
    def stop_saving_to_csv(self):
        self.saving1Checkbox.setEnabled(self.tabs[0] is not None)
        self.saving2Checkbox.setEnabled(self.tabs[1] is not None)
        self.saving3Checkbox.setEnabled(self.tabs[2] is not None)
        self.saving4Checkbox.setEnabled(self.tabs[3] is not None)
        self.saveCsvButton.setText("Start saving to CSVs")
        self.saveCsvButton.clicked.connect(self.start_saving_to_csv)

        if self.saving1Checkbox.isChecked():
            self.tabs[0].save_to_csv_stop()
        if self.saving2Checkbox.isChecked():
            self.tabs[1].save_to_csv_stop()
        if self.saving3Checkbox.isChecked():
            self.tabs[2].save_to_csv_stop()
        if self.saving4Checkbox.isChecked():
            self.tabs[3].save_to_csv_stop()

    def start_dosing(self):
        for box in self.dosingCheckboxes:
            box.setEnabled(False)
        self.dosingControlButton.setText("Stop dosing processes")
        self.dosingControlButton.clicked.connect(self.stop_dosing)

        if self.dosing1Checkbox.isChecked():
            self.tabs[0].dosingControlButton.setChecked(True)
            self.tabs[0].update_dosing_state()
        if self.dosing2Checkbox.isChecked():
            self.tabs[1].dosingControlButton.setChecked(True)
            self.tabs[1].update_dosing_state()
        if self.dosing3Checkbox.isChecked():
            self.tabs[2].dosingControlButton.setChecked(True)
            self.tabs[2].update_dosing_state()
        if self.dosing4Checkbox.isChecked():
            self.tabs[3].dosingControlButton.setChecked(True)
            self.tabs[3].update_dosing_state()

    def stop_dosing(self):
        self.dosing1Checkbox.setEnabled(self.tabs[0] is not None)
        self.dosing2Checkbox.setEnabled(self.tabs[1] is not None)
        self.dosing3Checkbox.setEnabled(self.tabs[2] is not None)
        self.dosing4Checkbox.setEnabled(self.tabs[3] is not None)

        self.dosingControlButton.setText("Start dosing processes")
        self.dosingControlButton.clicked.connect(self.start_dosing)

        if self.dosing1Checkbox.isChecked():
            self.tabs[0].dosingControlButton.setChecked(False)
            self.tabs[0].update_dosing_state()
        if self.dosing2Checkbox.isChecked():
            self.tabs[1].dosingControlButton.setChecked(False)
            self.tabs[1].update_dosing_state()
        if self.dosing3Checkbox.isChecked():
            self.tabs[2].dosingControlButton.setChecked(False)
            self.tabs[2].update_dosing_state()
        if self.dosing4Checkbox.isChecked():
            self.tabs[3].dosingControlButton.setChecked(False)
            self.tabs[3].update_dosing_state()

    # Checkbox handlers
    def update_audio_beep(self):
        self.brooks.set_audio_beep(self.audioBeepCheckbox.isChecked())

    def update_zero_suppress(self):
        self.brooks.set_zero_suppress(self.zeroSuppressCheckbox.isChecked())

    def update_power_sp_clear(self):
        self.brooks.set_power_sp_clear(self.powerSpClearCheckbox.isChecked())

    # Function to create the layout
    def create_left_column(self, controllerTabs):
        # Create a vertical layout for the left column
        leftColumnLayout = QVBoxLayout()

        # Saving group
        savingGroup = QGroupBox("Simultaneous saving start")
        savingLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.saving1Checkbox.setChecked(controllerTabs[0] is not None)
        self.saving1Checkbox.setEnabled(controllerTabs[0] is not None)
        self.saving1Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving1Checkbox, alignment=Qt.AlignTop)

        self.saving2Checkbox.setChecked(controllerTabs[1] is not None)
        self.saving2Checkbox.setEnabled(controllerTabs[1] is not None)
        self.saving2Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving2Checkbox, alignment=Qt.AlignTop)

        self.saving3Checkbox.setChecked(controllerTabs[2] is not None)
        self.saving3Checkbox.setEnabled(controllerTabs[2] is not None)
        self.saving3Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving3Checkbox, alignment=Qt.AlignTop)

        self.saving4Checkbox.setChecked(controllerTabs[3] is not None)
        self.saving4Checkbox.setEnabled(controllerTabs[3] is not None)
        self.saving4Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving4Checkbox, alignment=Qt.AlignTop)

        savingLayout.addLayout(layout)

        layout = QHBoxLayout()
        self.saveCsvButton = QPushButton("Start saving to CSVs")
        self.saveCsvButton.clicked.connect(self.start_saving_to_csv)
        layout.addWidget(self.saveCsvButton, alignment=Qt.AlignTop)
        savingLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(self.savingErrorLabel, alignment=Qt.AlignBottom)
        self.savingInfoLabel.setText("No controller was selected!")
        layout.addWidget(self.savingInfoLabel, alignment=Qt.AlignBottom)
        layout.setStretch(1, 10)
        self.savingInfoLabel.setVisible(False)
        self.savingErrorLabel.setVisible(False)

        savingLayout.setStretch(1, 10)
        savingLayout.addLayout(layout)

        savingGroup.setLayout(savingLayout)
        savingGroup.setFixedWidth(405)
        savingGroup.setFixedHeight(103)

        leftColumnLayout.addWidget(savingGroup, alignment=Qt.AlignTop)

        # Dosing group
        dosingGroup = QGroupBox("Simultaneous dosing start")
        dosingLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.dosing1Checkbox.setChecked(controllerTabs[0] is not None)
        self.dosing1Checkbox.setEnabled(controllerTabs[0] is not None)
        self.dosing1Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing1Checkbox, alignment=Qt.AlignTop)

        self.dosing2Checkbox.setChecked(controllerTabs[1] is not None)
        self.dosing2Checkbox.setEnabled(controllerTabs[1] is not None)
        self.dosing2Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing2Checkbox, alignment=Qt.AlignTop)

        self.dosing3Checkbox.setChecked(controllerTabs[2] is not None)
        self.dosing3Checkbox.setEnabled(controllerTabs[2] is not None)
        self.dosing3Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing3Checkbox, alignment=Qt.AlignTop)

        self.dosing4Checkbox.setChecked(controllerTabs[3] is not None)
        self.dosing4Checkbox.setEnabled(controllerTabs[3] is not None)
        self.dosing4Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing4Checkbox, alignment=Qt.AlignTop)

        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        self.dosingControlButton = QPushButton("Start dosing processes")
        self.dosingControlButton.clicked.connect(self.dosing_processes_start)
        layout.addWidget(self.dosingControlButton, alignment=Qt.AlignTop)
        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(self.dosingErrorLabel, alignment=Qt.AlignBottom)
        layout.addWidget(self.dosingInfoLabel, alignment=Qt.AlignBottom)
        self.dosingInfoLabel.setVisible(False)
        self.dosingErrorLabel.setVisible(False)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)
        dosingLayout.setStretch(1, 10)

        dosingGroup.setLayout(dosingLayout)
        dosingGroup.setFixedSize(405, 103)

        leftColumnLayout.addWidget(dosingGroup, alignment=Qt.AlignTop)

        # Global device configuration group
        deviceGroup = QGroupBox("Device configuration")
        deviceLayout = QFormLayout()

        self.audioBeepCheckbox.stateChanged.connect(self.update_audio_beep)
        self.zeroSuppressCheckbox.stateChanged.connect(self.update_zero_suppress)
        self.powerSpClearCheckbox.stateChanged.connect(self.update_power_sp_clear)
        networkAddressLabel = QLabel(self.brooks.get_network_address())

        deviceLayout.addRow(QLabel("Audio beep"), self.audioBeepCheckbox)
        deviceLayout.addRow(QLabel("Zero suppress"), self.zeroSuppressCheckbox)
        deviceLayout.addRow(QLabel("Power SP Clear"), self.powerSpClearCheckbox)
        deviceLayout.addRow(QLabel("Network address"), networkAddressLabel)

        deviceGroup.setLayout(deviceLayout)
        deviceGroup.setFixedWidth(405)
        leftColumnLayout.addWidget(deviceGroup, alignment=Qt.AlignTop)

        leftColumnLayout.setStretch(2, 10)
        return leftColumnLayout
