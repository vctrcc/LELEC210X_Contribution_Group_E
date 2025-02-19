"""
UART reader utilities, developed by the group E, 2024-2025.
"""

# Standard Library
import datetime
import logging
import pathlib as pathl
import sys
import time
from queue import Queue
from shutil import rmtree
from threading import Lock
from typing import Optional

# Installed Libraries
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from serial import Serial, SerialException
from serial.tools import list_ports

# Local
# from mcu.src.mcu import user_classifier


###############################################################################
# Settings


class APP_Settings:
    """
    Class to store the settings of the application.

    Must be accessed using a thread lock or similar
    """

    class ChoiceBox:
        def __init__(self, default, choices):
            self.__default = default
            self.index = default
            self.choices = choices

        def reset(self):
            self.index = self.__default

        def __str__(self):
            return self.choices[self.index]

    class PathBox:
        def __init__(self, default, is_folder=False):
            self.default = default
            self.path = default
            self.is_folder = is_folder

        def reset(self):
            self.path = self.default

        def __str__(self):
            return self.path

    class DimensionElement:
        def __init__(self, tuple, editable=False):
            self.list = list(tuple)
            self.editable = editable

        def __str__(self):
            return f"{self.list[0]} x {self.list[1]}"

    def __init__(self):
        self.__lock_protection = Lock()
        self.__setting_callbacks = {}
        self.__updating = False

        # App stuff
        self.app_folder = pathl.Path(__file__).parent
        self.app_name = "UART Console App for LELEC210x"
        self.app_version = "0.2.0"
        self.app_author = "Group E, 2024-2025"
        self.app_description = "UART reader utilities."

        # Logging settings
        self.logging_level = logging.DEBUG
        self.logging_format = "[%(asctime)s] %(levelname)-9s: %(message)s"
        self.logging_date_format = "%Y-%m-%d %H:%M:%S"
        self.logging_use_file = True
        self.logging_file = self.PathBox(self.app_folder / "uart_reader.log")
        self.logging_file_max_size = 1024 * 1024  # 1 MB
        self.logging_file_backup_count = 3

        # GUI settings
        self.gui_update_rate = 60  # FPS
        self.gui_use_matplotlib_blit = True
        self.gui_min_window_size = self.DimensionElement((800, 600), editable=True)
        self.gui_default_window_size = self.DimensionElement((1280 // 2, 720))

        # Plotting settings
        self.plot_name_prefix = "plot"
        self.plot_name_postfix_timestamp = True
        self.plot_save_types = self.ChoiceBox(0, ["pdf", "png"])
        self.plot_save_all_types = True
        self.plot_save_folder_base = self.PathBox(
            self.app_folder / "plots", is_folder=True
        )

        # Serial settings
        self.serial_port = self.ChoiceBox(0, ["-- No serial port --"])
        self.serial_baud_rate = 115200  # bps
        self.serial_timeout = 1
        self.serial_allow_write = False
        self.serial_freeze = False
        self.serial_auto_select_index = 1  # Index to select when refreshing or opening

        # Nucleo board settings
        self.nucleo_config_serial_prefix = "CFG:HEX:"
        self.nucleo_sample_rate = 10240  # Hz

        # Audio settings
        self.audio_serial_prefix = "SND:HEX:"
        self.audio_folder = self.PathBox(self.app_folder / "audio", is_folder=True)
        self.audio_file_name_prefix = "audio"
        self.audio_file_types = self.ChoiceBox(0, ["wav", "ogg", "mp3", "flac"])
        self.audio_file_freq = 44100  # Hz
        self.audio_file_channels = 1
        self.audio_file_dtype = "int16"
        self.audio_file_save_numpy = False
        self.audio_file_save_plots = False
        self.audio_file_auto_save = False
        self.audio_freeze = False

        # Mel spectrogram settings
        self.mel_serial_prefix = "MEL:HEX:"
        self.mel_vector_size = 20
        self.mel_vector_num = 20
        self.mel_samples = 512
        self.mel_history_max_mem = 20  # Max in memory
        self.mel_history_max_shown = 10  # Max shown
        self.mel_autosave = False  # As numpy file (dictionary)
        self.mel_file_name_prefix = "mel"
        self.mel_autosave_folder = self.PathBox(self.app_folder / "mel", is_folder=True)
        self.mel_autosave_plots = False
        self.mel_autosave_numpy = False
        self.mel_autosave_clear = False
        self.mel_freeze = False

        # User classifier settings
        self.classifier_use = False
        self.classifier_file_pickle = self.PathBox(
            self.app_folder / "user_classifier.pkl"
        )  # If found, load
        self.classifier_file_numpy = self.PathBox(
            self.app_folder / "user_classifier.npy"
        )  # If found, load (secondary)
        self.classifier_file_auto_save = False  # As numpy file (dictionary)
        self.classifier_file_auto_save_mel = True
        self.classifier_file_auto_save_plots = False
        self.classifier_use_mel_history = False  # Requires the use of the .npy with a dictionary and "history_len" key
        self.classifier_history_max_shown = 10  # Max shown

    def register_callback(self, name: str, callback: callable):
        """
        Register a callback function to be called when settings are updated.
        """
        with self.__lock_protection:
            self.__setting_callbacks[name] = callback

    def __call_callbacks(self):
        """
        Call all the registered callbacks.

        The callback is donne as follows :
            callback(settings)
        """
        with self.__lock_protection:
            for name, callback in self.__setting_callbacks.items():
                callback(self)

    def __update_value(self, key, value):
        """
        Update a single value.
        """
        with self.__lock_protection:
            # Check if the key exists
            if hasattr(self, key):
                # Update the value depending on the type
                if isinstance(getattr(self, key), APP_Settings.ChoiceBox):
                    if type(value) == int:
                        getattr(self, key).index = value
                    elif type(value) == list:
                        getattr(self, key).choices = value
                    else:
                        index, choices = value
                        getattr(self, key).index = index
                        getattr(self, key).choices = choices
                elif isinstance(getattr(self, key), APP_Settings.PathBox):
                    getattr(self, key).path = value
                elif isinstance(getattr(self, key), APP_Settings.DimensionElement):
                    getattr(self, key).list = value
                else:
                    setattr(self, key, value)

    def update_values(self, new_settings: dict):
        """Update settings with update lock to prevent circular updates"""
        if self.__updating:  # Skip if already updating
            return

        self.__updating = True
        try:
            for key, value in new_settings.items():
                if hasattr(self, key):
                    self.__update_value(key, value)
            self.__call_callbacks()
        finally:
            self.__updating = False

    def import_settings(self, filename):
        """
        Import the settings (dictionary) from a .cfg.npy file.
        """
        with self.__lock_protection:
            try:
                new_settings = np.load(filename, allow_pickle=True).item()
                self.update_values(new_settings)
                return True
            except Exception as e:
                print(f"Failed to import settings: {e}")
                return False

    def export_settings(self, filename):
        """
        Export the settings to a .cfg.npy file.
        """
        with self.__lock_protection:
            try:
                new_dict = {}
                for key, value in self.__dict__.items():
                    if (
                        key.startswith("__")
                        or key.startswith("_")
                        or key.startswith("app_")
                    ):
                        continue
                    new_dict[key] = value

                np.save(filename, self.__dict__)
                return True
            except Exception as e:
                print(f"Failed to export settings: {e}")
                return False


###############################################################################
# Logging

# Custom levels
LOGGING_GOOD = 25


def setup_logging(settings):
    """
    Setup the logging system.
    """
    # Create the logger
    logger = logging.getLogger(settings.app_name)
    logger.setLevel(settings.logging_level)

    # Add a GOOD level for the logger
    logging.addLevelName(LOGGING_GOOD, "GOOD")

    def good(self, message, *args, **kws):
        if self.isEnabledFor(LOGGING_GOOD):
            self._log(LOGGING_GOOD, message, args, **kws)

    logging.Logger.good = good

    # Create the formatter
    formatter = logging.Formatter(settings.logging_format, settings.logging_date_format)

    # Create the console handler (CLI)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create the file handler
    if settings.logging_use_file:
        file_handler = logging.FileHandler(settings.logging_file.path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Return the logger
    return logger


class QTextEditLogger(logging.Handler):
    """
    Custom logging handler that writes to a QTextEdit widget on the GUI.
    """

    def __init__(self, text_edit: QTextEdit, settings: APP_Settings):
        super().__init__()
        self.text_edit = text_edit
        self.app_settings = settings

    STYLES = {
        logging.INFO: "color: black",
        LOGGING_GOOD: "color: green",
        logging.DEBUG: "color: blue",
        logging.WARNING: "color: orange",
        logging.ERROR: "color: red",
        logging.CRITICAL: "color: red; font-weight: bold",
    }

    HAS_RECORD_NAME = {
        logging.INFO: False,
        LOGGING_GOOD: False,
        logging.DEBUG: True,
        logging.WARNING: True,
        logging.ERROR: True,
        logging.CRITICAL: True,
    }

    def emit(self, record: logging.LogRecord):
        msg = record.getMessage()
        line = (
            f"<span style='{self.STYLES.get(record.levelno, '')}; white-space: pre'>",
            f"[{datetime.datetime.fromtimestamp(record.created).strftime(self.app_settings.logging_date_format)}] ",  # Date
            f" {record.levelname} "
            if self.HAS_RECORD_NAME.get(record.levelno, True)
            else " ",  # Level
            f">> {msg}",
            "</span>",
        )
        # Append to the text edit if its smaller than 500 lines
        if self.text_edit.document().blockCount() < 500:
            self.text_edit.append("".join(line))


def test_logging(logger: logging.Logger):
    for i in range(2):
        logger.info(f"Test log {i}")
        logger.debug(f"Test log {i}")
        logger.warning(f"Test log {i}")
        logger.error(f"Test log {i}")
        logger.critical(f"Test log {i}")
        logger.good(f"Test log {i}")


###############################################################################
# Serial


def get_available_ports(app_settings: APP_Settings):
    """Get available serial ports without triggering circular updates"""
    old_index = app_settings.serial_port.index
    old_port = app_settings.serial_port.choices[old_index]

    # Get new ports
    new_ports = ["-- No serial port --"] + [
        f"{port.device} - {port.description}" for port in list_ports.comports()
    ]

    # Update settings if changed
    if len(new_ports) == 1:
        new_index = 0
    else:
        # Try to keep the same port if possible
        # If not, select the one depending on the auto select index
        if old_port in new_ports and old_index != 0:
            new_index = new_ports.index(old_port)
        elif old_index == 0:
            new_index = app_settings.serial_auto_select_index
            if new_index > len(new_ports):
                new_index = 1
    app_settings.update_values({"serial_port": (new_index, new_ports)})


class SerialReader(QThread):
    """
    Thread-safe serial port reader with queued writing capability.

    Signals:
        data_received (str): Emitted when data is received from serial port
        connection_state (bool): Emitted when connection state changes
        error_occurred (str): Emitted when an error occurs
    """

    data_received = pyqtSignal(str)
    connection_state = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, settings, logger: logging.Logger):
        super().__init__()
        self.settings = settings
        self.logger = logger
        self._serial: Optional[Serial] = None
        self._running = False
        self._write_queue = Queue()
        self._lock = Lock()
        self._buffer_size = 1024 * 8
        self._thread_id = None

    @property
    def is_connected(self) -> bool:
        """Check if serial port is connected and operational"""
        with self._lock:
            return self._serial is not None and self._serial.is_open

    def try_start(self) -> bool:
        """Attempt to start the serial reader thread safely"""
        try:
            if self._thread_id is not None:
                self.logger.warning("Thread already running")
                return False

            if (
                self.settings.serial_port.choices[self.settings.serial_port.index]
                == "-- No serial port --"
            ):
                return False

            self._running = True
            self.start()
            return True

        except Exception as e:
            self.logger.error(f"Failed to start serial reader: {e}")
            return False

    def run(self) -> None:
        """Main thread loop"""
        try:
            self._thread_id = QThread.currentThreadId()
            self._connect()
            self._read_loop()
        except Exception as e:
            self._handle_error(f"Thread error: {e}")
        finally:
            self._thread_id = None
            self._cleanup()

    def _connect(self) -> None:
        """Connect to serial port"""
        try:
            port = self.settings.serial_port.choices[
                self.settings.serial_port.index
            ].split(" - ")[0]

            with self._lock:
                if self._serial is not None:
                    return

                self._serial = Serial(
                    port=port,
                    baudrate=self.settings.serial_baud_rate,
                    timeout=self.settings.serial_timeout,
                    write_timeout=1.0,
                )

            self.logger.good(f"Connected to {self.settings.serial_port}")
            self.connection_state.emit(True)

        except Exception as e:
            self._cleanup()
            raise RuntimeError(f"Connection failed: {e}")

    def _check_connection(self) -> bool:
        """Check if connection is still alive"""
        try:
            with self._lock:
                if not self._serial:
                    return False
                # Try to get port status - will fail if disconnected
                self._serial.in_waiting
                return True
        except (SerialException, OSError):
            return False

    def _read_loop(self) -> None:
        """Main reading loop with connection monitoring"""
        while self._running:
            try:
                # Check connection status
                if not self._check_connection():
                    self._handle_error("Serial port disconnected unexpectedly")
                    break

                # Process write queue
                if not self._write_queue.empty() and self.settings.serial_allow_write:
                    self._process_write_queue()

                # Read available data with timeout
                try:
                    if self._serial.in_waiting > 0 and not self.settings.serial_freeze:
                        data = self._serial.readline(self._buffer_size)
                        if data:
                            decoded = data.decode("ascii").strip()
                            self.data_received.emit(decoded)
                except (SerialException, OSError) as e:
                    self._handle_error(f"Serial port error: {e}")
                    break
                except UnicodeDecodeError as e:
                    self.logger.warning(f"Decode error: {e}")
                    continue

                # Small sleep to prevent CPU hogging
                time.sleep(0.001)

            except Exception as e:
                self._handle_error(f"Unexpected error in read loop: {e}")
                break

    def _process_write_queue(self) -> None:
        """Process pending write operations"""
        try:
            while not self._write_queue.empty():
                data = self._write_queue.get_nowait()
                with self._lock:
                    if self._serial and self._serial.is_open:
                        self._serial.write(data.encode("ascii"))
                self._write_queue.task_done()
        except Exception as e:
            self.logger.error(f"Write error: {e}")

    def send_data(self, data: str) -> None:
        """
        Queue data to be sent over serial port.

        Args:
            data (str): Data to send

        """
        if not data:
            return
        self.logger.debug(f"Queueing data: {data}")
        self._write_queue.put(data)

    def stop(self) -> bool:
        """Stop thread safely"""
        try:
            if self._thread_id is None:
                return True

            self.logger.debug("Stopping reader")
            self._running = False

            # Close serial port
            with self._lock:
                if self._serial:
                    try:
                        self._serial.close()
                    except:
                        pass
                    self._serial = None

            # Wait for thread to finish
            if QThread.currentThread() != self:
                if not self.wait(1000):
                    self.terminate()
                    self.wait(500)

            return True

        except Exception as e:
            self.logger.error(f"Stop error: {e}")
            return False

    def _cleanup(self) -> None:
        """Clean up resources"""
        with self._lock:
            if self._serial:
                try:
                    self._serial.close()
                except:
                    pass
                self._serial = None

            while not self._write_queue.empty():
                try:
                    self._write_queue.get_nowait()
                except:
                    pass

        self._running = False
        self.connection_state.emit(False)

    def _handle_error(self, message: str) -> None:
        """Handle errors uniformly"""
        self.logger.error(message)
        self.error_occurred.emit(message)
        self.data_received.emit("CONNECTION_TERMINATED")
        self.stop()


###############################################################################
# Plotting


def save_figure(fig, filename, plot_type, both_types, logger: logging.Logger):
    """
    Save a figure to a file.
    """
    try:
        if plot_type == 0 or both_types:
            fig.savefig(filename + ".pdf", format="pdf")
        if plot_type == 1 or both_types:
            fig.savefig(filename + ".png", format="png")
        logger.good(f"Saved plot to {filename}")
    except Exception as e:
        logger.error(f"Failed to save plot: {e}")


###############################################################################
# GUI


class GUI_ParametersWindow(QMainWindow):
    def __setting_UI_mapper(
        self, type: type, value: any, setting_key: str
    ) -> tuple[any, callable]:
        """Map settings to UI widgets with their update functions"""
        # Map the type to the correct widget
        # Bools are mapped to checkboxes
        if type == bool:
            widget = QCheckBox()
            widget.setChecked(value)
            update_func = lambda state: self.settings.update_values(
                {setting_key: bool(state)}
            )
            callback_func = lambda loc_settings: widget.setChecked(
                getattr(loc_settings, setting_key)
            )
            widget.stateChanged.connect(update_func)
            return widget, callback_func
        # Lists are mapped to multiple line edits
        elif type == list:
            widgets = []
            for i, item in enumerate(value):
                edit = QLineEdit(str(item))
                update_func = lambda text, idx=i: self.settings.update_values(
                    {
                        setting_key: [
                            x if j != idx else text for j, x in enumerate(value)
                        ]
                    }
                )
                edit.textChanged.connect(update_func)
                widgets.append(edit)
            callback_func = lambda loc_settings: [
                edit.setText(str(item))
                for edit, item in zip(widgets, getattr(loc_settings, setting_key))
            ]
            return widgets, callback_func
        # Tuples are mapped to a single label
        elif type == tuple:
            widget = QLabel("(" + " , ".join(map(str, value)) + ")")
            return widget, None  # Tuples are immutable
        # Ints are mapped to spinboxes
        elif type == int:
            widget = QSpinBox()
            widget.setMaximum(2147483647)
            widget.setMinimum(-2147483647)
            widget.setValue(value)
            update_func = lambda val: self.settings.update_values(
                {setting_key: int(val)}
            )
            callback_func = lambda loc_settings: widget.setValue(
                getattr(loc_settings, setting_key)
            )
            widget.valueChanged.connect(update_func)
            return widget, callback_func
        # Floats are mapped to spinboxes
        elif type == float:
            widget = QSpinBox()
            widget.setMaximum(1e99)
            widget.setMinimum(-1e99)
            widget.setValue(value)
            widget.setDecimals(2)
            update_func = lambda val: self.settings.update_values(
                {setting_key: float(val)}
            )
            callback_func = lambda loc_settings: widget.setValue(
                getattr(loc_settings, setting_key)
            )
            widget.valueChanged.connect(update_func)
            return widget, callback_func
        # Strings are mapped to line edits
        elif type == str:
            widget = QLineEdit(value)
            update_func = lambda text: self.settings.update_values(
                {setting_key: str(text)}
            )
            callback_func = lambda loc_settings: widget.setText(
                getattr(loc_settings, setting_key)
            )
            widget.textChanged.connect(update_func)
            return widget, callback_func
        # PathBox are mapped to line edits with a browse button
        elif type == APP_Settings.PathBox:
            widget = QLineEdit(str(value.path))
            browse = QPushButton("...")
            browse.setFixedWidth(30)
            update_func = lambda text: self.settings.update_values(
                {setting_key: APP_Settings.PathBox(text, value.is_folder)}
            )
            callback_func = lambda loc_settings: widget.setText(
                str(getattr(loc_settings, setting_key).path)
            )
            widget.textChanged.connect(update_func)
            browse.clicked.connect(
                lambda: self.__open_file_dialog(widget, value.is_folder)
            )
            return [widget, browse], callback_func
        # ChoiceBox are mapped to comboboxes
        elif type == APP_Settings.ChoiceBox:
            widget = QComboBox()
            widget.addItems(value.choices)
            widget.setCurrentIndex(value.index)
            update_func = lambda idx: self.settings.update_values({setting_key: idx})

            def callback_func(loc_settings):
                widget.clear()
                widget.addItems(getattr(loc_settings, setting_key).choices)
                widget.setCurrentIndex(getattr(loc_settings, setting_key).index)

            widget.currentIndexChanged.connect(update_func)
            return widget, callback_func
        # DimensionElement are mapped to two line edits
        elif type == APP_Settings.DimensionElement:
            if value.editable:
                w1 = QLineEdit(str(value.list[0]))
                label = QLabel("x")
                w2 = QLineEdit(str(value.list[1]))
                update_func = lambda: self.settings.update_values(
                    {
                        setting_key: APP_Settings.DimensionElement(
                            [int(w1.text()), int(w2.text())]
                        )
                    }
                )
                callback_func = lambda loc_settings: [
                    w1.setText(str(value.list[0])),
                    w2.setText(str(value.list[1])),
                ]
                w1.textChanged.connect(update_func)
                w2.textChanged.connect(update_func)
                return [w1, label, w2], callback_func
            else:
                widget = QLabel(f"{value.list[0]} x {value.list[1]}")
                callback_func = lambda loc_settings: widget.setText(
                    f"{getattr(loc_settings, setting_key).list[0]} x {getattr(loc_settings, setting_key).list[1]}"
                )
                return widget, callback_func
        # Other types are not supported
        else:
            return QLabel("Unsupported setting type"), None

    def __open_file_dialog(self, widget, is_folder: bool = False):
        if is_folder:
            path = QFileDialog.getExistingDirectory(self, "Select Folder")
        else:
            path = QFileDialog.getOpenFileName(self, "Select File")[0]
        if path:
            widget.setText(path)

    def __init__(self, settings, logger: logging.Logger):
        super().__init__()
        self.settings = settings
        self.logger = logger

        self.logger.debug("Creating the parameters window")
        self.setWindowTitle("Parameters")
        self.resize(640, 480)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.create_gui()

    def create_gui(self):
        """
        Create the GUI.
        """
        self.logger.debug("Creating the Parametter's GUI")

        # Create the settings categories
        categories = {}
        for key, value in self.settings.__dict__.items():
            if key.startswith(("__", "app", "_")):
                continue
            category = key.split("_")[0]
            if category not in categories:
                categories[category] = []
            categories[category].append((key, value))

        # Create the tab for each category
        for category, settings in categories.items():
            scroll = QScrollArea()
            container = QWidget()
            scroll.setWidget(container)
            scroll.setWidgetResizable(True)

            # Main vertical layout to hold grid and spacer
            main_layout = QVBoxLayout(container)
            main_layout.setSpacing(0)
            main_layout.setContentsMargins(5, 5, 5, 5)

            # Grid layout for widgets
            grid_layout = QGridLayout()
            grid_layout.setVerticalSpacing(2)
            grid_layout.setHorizontalSpacing(10)
            grid_layout.setContentsMargins(0, 0, 0, 0)

            # Add widgets to grid
            for i, (key, value) in enumerate(settings):
                grid_layout.addWidget(QLabel(key), i, 0)
                widgets, callback_func = self.__setting_UI_mapper(
                    type(value), value, key
                )
                if isinstance(widgets, list):
                    for j, widget in enumerate(widgets):
                        grid_layout.addWidget(widget, i, j + 1)
                else:
                    grid_layout.addWidget(widgets, i, 1)

                # Register callback
                if callback_func:
                    self.settings.register_callback(key, callback_func)

            # Add grid to main layout
            main_layout.addLayout(grid_layout)

            # Add vertical spacer to push everything up
            main_layout.addStretch(1)

            self.tab_widget.addTab(scroll, category)


class GUI_AudioWindow(QMainWindow):
    """
    Audio window of the application.
    """

    def __init__(self, settings, logger: logging.Logger):
        super().__init__()
        self.settings = settings
        self.logger = logger
        self.save_signal = pyqtSignal(str)

        # Create the audio window
        self.logger.debug("Creating the audio window")
        self.setWindowTitle("Audio")
        self.resize(
            self.settings.gui_default_window_size.list[0],
            self.settings.gui_default_window_size.list[1],
        )
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.base_layout = QVBoxLayout()
        self.central_widget.setLayout(self.base_layout)

        # Create dummy audio data
        self.audio_data = np.zeros(1024, dtype=float)

        # Create the GUI
        self.create_gui()

    def create_gui(self):
        """
        Create the GUI.
        """
        self.logger.debug("Creating the Audio's GUI")

        # Set plotting style to blit with an option, and fast
        plt.style.use("fast")
        matplotlib.use("Qt5Agg")

        # Add a FPS counter
        self.fps_counter = QLabel("FPS: 0")
        self.base_layout.addWidget(self.fps_counter)
        self.current_time = time.time()

        # Create the 2 figures for the audio signal and FFT
        self.fig_audio = Figure(figsize=(8, 6))
        self.canvas_audio = FigureCanvasQTAgg(self.fig_audio)
        self.base_layout.addWidget(self.canvas_audio)

        self.fig_fft = Figure(figsize=(8, 6))
        self.canvas_fft = FigureCanvasQTAgg(self.fig_fft)
        self.base_layout.addWidget(self.canvas_fft)

        # Setup the layouts
        self.ax_audio = self.fig_audio.add_subplot(111)
        self.ax_fft = self.fig_fft.add_subplot(111)

        self.ax_audio.set_title("Audio Signal")
        self.ax_audio.set_xlabel("Time (s)")
        self.ax_audio.set_ylabel("Amplitude (%)")
        self.ax_audio.set_xlim(0, 1)
        self.ax_audio.set_ylim(-1, 1)
        self.ax_audio.grid(True)
        self.ax_audio.autoscale(enable=False, axis="both")

        self.ax_fft.set_title("FFT")
        self.ax_fft.set_xlabel("Frequency (Hz)")
        self.ax_fft.set_ylabel("Magnitude (dB)")
        self.ax_fft.set_xlim(-10500, 10500)
        self.ax_fft.set_ylim(-1, 100)
        self.ax_fft.grid(True)
        self.ax_fft.autoscale(enable=False, axis="both")

        # Add the signal to the plots
        (self.line_audio,) = self.ax_audio.plot([], [], animated=True)
        (self.line_fft,) = self.ax_fft.plot([], [], animated=True)

        # Make the plots slightly smaller
        self.fig_audio.tight_layout()
        self.fig_audio.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.2)

        self.fig_fft.tight_layout()
        self.fig_fft.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.2)

        # Set up animation using blit
        TARGET_FPS = int(self.settings.gui_update_rate)
        self.anim_audio = FuncAnimation(
            self.fig_audio,
            self._update_audio_plot,
            init_func=self._init_audio_plot,
            interval=1 // TARGET_FPS * 1000,
            blit=self.settings.gui_use_matplotlib_blit,  # Use blit to speed up
            save_count=1,
        )
        self.anim_fft = FuncAnimation(
            self.fig_fft,
            self._update_fft_plot,
            init_func=self._init_fft_plot,
            interval=1 // TARGET_FPS * 1000,
            blit=self.settings.gui_use_matplotlib_blit,
            save_count=1,
        )

        # Create the plot settings box
        self.box_settings = QHBoxLayout()
        self.base_layout.addLayout(self.box_settings)

        # Create group boxes for plot and save settings
        self.group_plot_settings = QGroupBox("Plot Settings")
        self.group_save_settings = QGroupBox("Save Settings")
        self.group_statistic_settings = QGroupBox("Signal Statistics")

        # Create layouts for the group boxes
        self.settings_plot_box = QGridLayout()
        self.settings_save_box = QGridLayout()
        self.settings_statistic_box = QGridLayout()

        # Set layouts to the group boxes
        self.group_plot_settings.setLayout(self.settings_plot_box)
        self.group_save_settings.setLayout(self.settings_save_box)
        self.group_statistic_settings.setLayout(self.settings_statistic_box)

        # Add group boxes to the main layout
        self.box_settings.addWidget(self.group_plot_settings)
        self.box_settings.addWidget(self.group_save_settings)
        self.box_settings.addWidget(self.group_statistic_settings)

        # Add the settings for the plot
        self.label_plot_freeze = QLabel("Freeze:")
        self.settings_plot_box.addWidget(self.label_plot_freeze, 0, 0)
        self.check_plot_freeze = QCheckBox()
        self.check_plot_freeze.setChecked(self.settings.audio_freeze)
        self.check_plot_freeze.stateChanged.connect(
            lambda state: self.settings.update_values({"audio_freeze": bool(state)})
        )
        self.settings.register_callback(
            "audio_freeze",
            lambda loc_settings: self.check_plot_freeze.setChecked(
                loc_settings.audio_freeze
            ),
        )
        self.settings_plot_box.addWidget(self.check_plot_freeze, 0, 1)

        # Add the settings for the save
        self.label_save_auto = QLabel("Auto Save:")
        self.settings_save_box.addWidget(self.label_save_auto, 0, 0)
        self.check_save_auto = QCheckBox()
        self.check_save_auto.setChecked(self.settings.audio_file_auto_save)
        self.check_save_auto.stateChanged.connect(
            lambda state: self.settings.update_values(
                {"audio_file_auto_save": bool(state)}
            )
        )
        self.settings.register_callback(
            "audio_file_auto_save",
            lambda loc_settings: self.check_save_auto.setChecked(
                loc_settings.audio_file_auto_save
            ),
        )
        self.settings_save_box.addWidget(self.check_save_auto, 0, 1)

        # Add the settings for the save
        self.label_save_folder = QLabel("Save Folder:")
        self.settings_save_box.addWidget(self.label_save_folder, 4, 0)
        self.edit_save_folder = QLineEdit(str(self.settings.audio_folder.path))
        self.edit_save_folder.setReadOnly(True)
        self.settings_save_box.addWidget(self.edit_save_folder, 4, 1)
        self.button_save_folder = QPushButton("...")
        self.button_save_folder.setFixedWidth(30)
        self.button_save_folder.clicked.connect(
            lambda: self.__open_file_dialog(self.edit_save_folder, True)
        )
        self.settings_save_box.addWidget(self.button_save_folder, 4, 2)

        # Add the settings for the save
        self.label_save_name = QLabel("File Name Prefix:")
        self.settings_save_box.addWidget(self.label_save_name, 5, 0)
        self.edit_save_name = QLineEdit(self.settings.audio_file_name_prefix)
        self.settings_save_box.addWidget(self.edit_save_name, 5, 1)
        self.settings.register_callback(
            "audio_file_name_prefix",
            lambda loc_settings: self.edit_save_name.setText(
                loc_settings.audio_file_name_prefix
            ),
        )

        # Add the settings for the save
        self.label_save_numpy = QLabel("Save Numpy (.npy):")
        self.settings_save_box.addWidget(self.label_save_numpy, 2, 0)
        self.check_save_numpy = QCheckBox()
        self.check_save_numpy.setChecked(self.settings.audio_file_save_numpy)
        self.check_save_numpy.stateChanged.connect(
            lambda state: self.settings.update_values(
                {"audio_file_save_numpy": bool(state)}
            )
        )
        self.settings.register_callback(
            "audio_file_save_numpy",
            lambda loc_settings: self.check_save_numpy.setChecked(
                loc_settings.audio_file_save_numpy
            ),
        )
        self.settings_save_box.addWidget(self.check_save_numpy, 2, 1)

        # Add the settings for the save
        self.label_save_plots = QLabel("Save Plots (per settings):")
        self.settings_save_box.addWidget(self.label_save_plots, 3, 0)
        self.check_save_plots = QCheckBox()
        self.check_save_plots.setChecked(self.settings.audio_file_save_plots)
        self.check_save_plots.stateChanged.connect(
            lambda state: self.settings.update_values(
                {"audio_file_save_plots": bool(state)}
            )
        )
        self.settings.register_callback(
            "audio_file_save_plots",
            lambda loc_settings: self.check_save_plots.setChecked(
                loc_settings.audio_file_save_plots
            ),
        )
        self.settings_save_box.addWidget(self.check_save_plots, 3, 1)

        # Add the settings for the save
        self.label_save_types = QLabel("File Types:")
        self.settings_save_box.addWidget(self.label_save_types, 6, 0)
        self.edit_save_types = QComboBox()
        self.edit_save_types.addItems(self.settings.audio_file_types.choices)
        self.edit_save_types.setCurrentIndex(self.settings.audio_file_types.index)
        self.edit_save_types.currentIndexChanged.connect(
            lambda idx: self.settings.update_values({"audio_file_types": idx})
        )
        self.settings.register_callback(
            "audio_file_types",
            lambda loc_settings: self.edit_save_types.setCurrentIndex(
                loc_settings.audio_file_types.index
            ),
        )
        self.settings_save_box.addWidget(self.edit_save_types, 6, 1)

        # Add the settings for the statistic
        self.label_statistic_max = QLabel("Max:")
        self.settings_statistic_box.addWidget(self.label_statistic_max, 0, 0)
        self.label_statistic_max_value = QLabel("0")
        self.settings_statistic_box.addWidget(self.label_statistic_max_value, 0, 1)
        self.label_statistic_min = QLabel("Min:")
        self.settings_statistic_box.addWidget(self.label_statistic_min, 1, 0)
        self.label_statistic_min_value = QLabel("0")
        self.settings_statistic_box.addWidget(self.label_statistic_min_value, 1, 1)
        self.label_statistic_avg = QLabel("Avg:")
        self.settings_statistic_box.addWidget(self.label_statistic_avg, 2, 0)
        self.label_statistic_avg_value = QLabel("0")
        self.settings_statistic_box.addWidget(self.label_statistic_avg_value, 2, 1)
        self.label_statistic_std = QLabel("Std:")
        self.settings_statistic_box.addWidget(self.label_statistic_std, 3, 0)
        self.label_statistic_std_value = QLabel("0")
        self.settings_statistic_box.addWidget(self.label_statistic_std_value, 3, 1)
        self.label_statistic_entropoy = QLabel("FFT energy:")
        self.settings_statistic_box.addWidget(self.label_statistic_entropoy, 4, 0)
        self.label_statistic_entropoy_value = QLabel("0")
        self.settings_statistic_box.addWidget(self.label_statistic_entropoy_value, 4, 1)

        # Add save button
        self.button_save = QPushButton("Save")
        self.button_save.clicked.connect(self.save_audio)
        self.base_layout.addWidget(self.button_save)

        # Add a Test button
        self.button_test = QPushButton("Test")
        self.button_test.clicked.connect(self.test_audio)
        self.base_layout.addWidget(self.button_test)

    def test_audio(self):
        self.audio_data = np.random.rand(1024)

    def _init_audio_plot(self):
        """Initialize audio line for blitting."""
        self.line_audio.set_data([], [])
        return (self.line_audio,)

    def _init_fft_plot(self):
        """Initialize FFT line for blitting."""
        self.line_fft.set_data([], [])
        return (self.line_fft,)

    def _update_audio_plot(self, frame):
        """Update audio plot for animation."""
        # Update audio signal
        x = np.linspace(0, 1, len(self.audio_data))
        self.line_audio.set_data(x, self.audio_data)

        # Update statistics
        self.label_statistic_max_value.setText(f"{np.max(self.audio_data):.2f}")
        self.label_statistic_min_value.setText(f"{np.min(self.audio_data):.2f}")
        self.label_statistic_avg_value.setText(f"{np.mean(self.audio_data):.2f}")
        self.label_statistic_std_value.setText(f"{np.std(self.audio_data):.2f}")

        return (self.line_audio,)

    def _update_fft_plot(self, frame):
        """Update FFT plot for animation."""
        # Calculate FFT
        fft_data = np.abs(np.fft.fft(self.audio_data))
        fft_data = 20 * np.log10(fft_data + 1e-12)  # Avoid log(0)
        fft_data = np.fft.fftshift(fft_data)
        freqs = np.linspace(-10200, 10200, len(fft_data))
        self.line_fft.set_data(freqs, fft_data)

        # Update FPS
        current_time = time.time()
        fps = 1 / (current_time - self.current_time)
        self.current_time = current_time
        self.fps_counter.setText(f"FPS: {fps:.2f}")

        # Update energy
        fft_data_not_db = np.abs(np.fft.fft(self.audio_data))
        energy = np.sum(fft_data_not_db**2) / len(fft_data_not_db)
        self.label_statistic_entropoy_value.setText(f"{energy:.2f} units")

        return (self.line_fft,)

    def save_audio(self):
        self.logger.debug("Saving audio signal")
        file_name = (
            self.settings.audio_folder.path
            + self.settings.audio_file_name_prefix
            + time.strftime("%Y%m%d-%H%M%S")
        )
        save_figure(
            self.fig_audio,
            file_name,
            self.settings.plot_save_types.index,
            self.settings.plot_save_all_types,
            self.logger,
        )
        if self.settings.audio_file_save_numpy:
            np.save(file_name + ".npy", self.audio_data)


class GUI_MelWindow(QMainWindow):
    """
    Mel spectrogram window of the application.
    """

    def __init__(self, settings, logger: logging.Logger):
        super().__init__()
        self.settings = settings
        self.logger = logger

        # Create the mel spectrogram window
        self.logger.debug("Creating the mel spectrogram window")
        self.setWindowTitle("Mel Spectrogram")
        self.resize(640, 480)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.base_layout = QVBoxLayout()
        self.central_widget.setLayout(self.base_layout)

        # Create the GUI
        self.create_gui()

    def create_gui(self):
        """
        Create the GUI.
        """
        self.logger.debug("Creating the Mel's GUI")

        # Create the buttons
        self.button_record = QPushButton("Record")
        self.button_record.clicked.connect(self.record_mel)
        self.button_save = QPushButton("Save")
        self.button_save.clicked.connect(self.save_mel)
        self.button_clear = QPushButton("Clear")
        self.button_clear.clicked.connect(self.clear_mel)
        self.base_layout.addWidget(self.button_record)
        self.base_layout.addWidget(self.button_save)
        self.base_layout.addWidget(self.button_clear)

        # Create the mel console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.base_layout.addWidget(self.console)

    def record_mel(self):
        """
        Record mel spectrogram.
        """
        self.logger.debug("Recording mel spectrogram")

    def save_mel(self):
        """
        Save mel spectrogram.
        """
        self.logger.debug("Saving mel spectrogram")

    def clear_mel(self):
        """
        Clear mel spectrogram.
        """
        self.logger.debug("Clearing mel spectrogram")


class GUI_MainWindow(QMainWindow):
    """
    Main window of the application.
    """

    def __init__(self, settings, logger: logging.Logger):
        super().__init__()
        self.settings = settings
        self.logger = logger

        # Create the main window
        self.logger.debug("Creating the main window")
        self.setWindowTitle(f"{self.settings.app_name} - {self.settings.app_version}")
        self.resize(*self.settings.gui_default_window_size.list)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.base_layout = QVBoxLayout()
        self.central_widget.setLayout(self.base_layout)

        # Create the GUI
        self.create_gui()

        # Create the serial reader thread
        self.serial_reader = SerialReader(self.settings, self.logger)
        self.serial_reader.error_occurred.connect(self._handle_connection_error)
        self.serial_reader.connection_state.connect(self._handle_connection_state)
        self.serial_reader.data_received.connect(self._handle_data_received)

        # Add the console handler (GUI)
        handler = QTextEditLogger(self.console, self.settings)
        self.logger.addHandler(handler)

        # Test logging
        # test_logging(self.logger)

        # Adjust the windows
        self.open_audio_window()

    def create_gui(self):
        """
        Create the GUI.
        """
        self.logger.debug("Creating the GUI")

        # Create the menu
        self.create_menu_bar()

        # Create the Title
        self.title = QLabel(f"{self.settings.app_name} - v{self.settings.app_version}")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold")
        self.base_layout.addWidget(self.title)
        self.autors = QLabel(f"Developed by {self.settings.app_author}")
        self.autors.setStyleSheet("font-size: 10px")
        self.base_layout.addWidget(self.autors)

        # Create grid layout for controls
        control_grid = QGridLayout()
        control_grid.setVerticalSpacing(2)
        control_grid.setHorizontalSpacing(10)
        control_grid.setContentsMargins(5, 5, 5, 5)
        self.base_layout.addLayout(control_grid)

        # >> Add Serial Port controls <<
        row = 0
        # Label
        self.serial_port_label = QLabel("Serial Port:")
        self.serial_port_label.setMinimumWidth(130)
        control_grid.addWidget(self.serial_port_label, row, 0)

        # Combo box
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.currentIndexChanged.connect(
            self.update_serial_port_settings
        )

        def serial_port_callback(settings):
            self.serial_port_combo.clear()
            self.serial_port_combo.addItems(settings.serial_port.choices)
            self.serial_port_combo.setCurrentIndex(settings.serial_port.index)

        self.settings.register_callback("serial_port_main", serial_port_callback)
        control_grid.addWidget(self.serial_port_combo, row, 1)

        # Refresh button
        self.serial_port_refresh = QPushButton("Refresh")
        self.serial_port_refresh.setFixedWidth(100)
        self.serial_port_refresh.clicked.connect(self.update_serial_port)
        control_grid.addWidget(self.serial_port_refresh, row, 2)

        # Set column stretching
        control_grid.setColumnStretch(1, 1)

        # Initialize combo box
        self.update_serial_port()

        # >> Serial connect <<
        # Connect button
        self.serial_connect = QPushButton("Connect")
        self.serial_connect.clicked.connect(self.toggle_serial)
        self.base_layout.addWidget(self.serial_connect)
        # Status Text
        self.serial_status = QLabel("Status: Disconnected")
        self.serial_status.setStyleSheet("color: red")
        self.base_layout.addWidget(self.serial_status)

        # Add console at the bottom
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(200)
        self.base_layout.addWidget(self.console)

        # UART write text box
        self.grid_uart_write = QGridLayout()
        self.grid_uart_write.setVerticalSpacing(2)
        self.grid_uart_write.setHorizontalSpacing(10)
        self.grid_uart_write.setContentsMargins(5, 5, 5, 5)
        self.base_layout.addLayout(self.grid_uart_write)
        self.label_uart_write = QLabel("UART Write:")
        self.label_uart_write.setMinimumWidth(130)
        self.grid_uart_write.addWidget(self.label_uart_write, 0, 0)
        self.text_uart_write = QLineEdit()
        self.grid_uart_write.addWidget(self.text_uart_write, 0, 1)
        self.button_uart_write = QPushButton("Send")
        self.button_uart_write.clicked.connect(self.send_uart)
        self.grid_uart_write.addWidget(self.button_uart_write, 0, 2)

        # Add a clear button
        self.clear_button = QPushButton("Clear Console")
        self.clear_button.clicked.connect(self.console.clear)
        self.base_layout.addWidget(self.clear_button)

    def create_menu_bar(self):
        self.menu = self.menuBar()
        self.menu_file = self.menu.addMenu("&File")
        self.menu_file_import_settings = self.menu_file.addAction("&Import Settings")
        self.menu_file_import_settings.triggered.connect(self.import_settings)
        self.menu_file_export_settings = self.menu_file.addAction("&Export Settings")
        self.menu_file_export_settings.triggered.connect(self.export_settings)
        self.menu_file_exit = self.menu_file.addAction("&Exit")
        self.menu_file_exit.triggered.connect(self.close)
        self.menu_parameters = self.menu.addMenu("&Parameters")
        self.menu_parameters_edit = self.menu_parameters.addAction("&Edit Parameters")
        self.menu_parameters_edit.triggered.connect(self.open_parameters_window)
        self.menu_view = self.menu.addMenu("&View")
        self.menu_view_audio = self.menu_view.addAction("&Audio")
        self.menu_view_audio.triggered.connect(self.open_audio_window)
        self.menu_view_mel = self.menu_view.addAction("&Mel Spectrogram")
        self.menu_view_mel.triggered.connect(self.open_mel_window)
        self.menu_help = self.menu.addMenu("&Help")
        self.menu_help_about = self.menu_help.addAction("&About")
        self.menu_help_about.triggered.connect(self.open_about)
        self.menu_help_clear_audio = self.menu_help.addAction("&Clear Audio")
        self.menu_help_clear_audio.triggered.connect(self.clear_audio)
        self.menu_help_clear_mel = self.menu_help.addAction("&Clear Mel")
        self.menu_help_clear_mel.triggered.connect(self.clear_mel)
        self.menu_help_clear_plots = self.menu_help.addAction("&Clear Plots")
        self.menu_help_clear_plots.triggered.connect(self.clear_plots)

    def import_settings(self):
        """
        Import settings.
        """
        self.logger.debug("Importing settings")
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "", "Settings Files (*.cfg.npy)"
        )
        if filename:
            if self.settings.import_settings(filename):
                self.logger.good("Settings imported successfully")
            else:
                self.logger.error("Failed to import settings")

    def export_settings(self):
        """
        Export settings.
        """
        self.logger.debug("Exporting settings")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Settings", "", "Settings Files (*.cfg.npy)"
        )
        if filename:
            if self.settings.export_settings(filename):
                self.logger.good("Settings exported successfully")
            else:
                self.logger.error("Failed to export settings")

    def open_parameters_window(self):
        """
        Open the parameters window.
        """
        self.logger.debug("Opening the parameters window")
        self.parameters_window = GUI_ParametersWindow(self.settings, self.logger)
        self.parameters_window.show()

    def open_audio_window(self):
        """
        Open the audio window.
        """
        self.logger.debug("Opening the audio window")
        self.audio_window = GUI_AudioWindow(self.settings, self.logger)
        self.audio_window.show()

    def open_mel_window(self):
        """
        Open the mel spectrogram window.
        """
        self.logger.debug("Opening the mel spectrogram window")
        self.mel_window = GUI_MelWindow(self.settings, self.logger)
        self.mel_window.show()

    def open_about(self):
        """
        Show the about message.
        """
        self.logger.debug("Showing the about message")
        about_text = f"{self.settings.app_name} - {self.settings.app_version}\n\n{self.settings.app_description}\n\nDeveloped by {self.settings.app_author}"
        QMessageBox.about(self, "About", about_text)

    def _count_and_list_files(self, path: pathl.Path) -> tuple[int, list[str]]:
        """Count and list all files in directory"""
        try:
            files = list(path.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            file_list = [str(f.relative_to(path)) for f in files if f.is_file()]
            return file_count, file_list
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return 0, []

    def _safe_clear_directory(self, path: pathl.Path, dir_name: str) -> bool:
        """Safely clear directory with user confirmation"""
        try:
            # Validate path
            if not path.exists():
                self.logger.warning(f"{dir_name} folder does not exist")
                return True

            if not path.is_relative_to(self.settings.app_folder):
                self.logger.error(
                    f"Cannot delete {dir_name} folder outside app directory"
                )
                return False

            # Count and list files
            file_count, file_list = self._count_and_list_files(path)
            if file_count == 0:
                self.logger.info(f"No files to delete in {dir_name} folder")
                return True

            # Create confirmation message
            msg = f"Are you sure you want to delete {file_count} files from {dir_name}?\n\n"
            msg += "Folder: " + str(path).replace("\\", "\\ ") + "\n\n"
            msg += "Files to be deleted:\n"
            msg += "\n".join(f"- {f}" for f in file_list[:10])
            if len(file_list) > 10:
                msg += f"\n... and {len(file_list) - 10} more"
            msg += "\n\nThis action cannot be undone."

            # Ask for confirmation
            reply = QMessageBox.question(
                self,
                f"Clear {dir_name}",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                rmtree(path, ignore_errors=True)
                path.mkdir(parents=True, exist_ok=True)
                self.logger.good(f"{dir_name} cleared successfully")
                return True
            else:
                self.logger.info(f"{dir_name} clear cancelled")
                return False

        except Exception as e:
            self.logger.error(f"Failed to clear {dir_name}: {e}")
            return False

    def clear_audio(self):
        """Clear the audio folder with confirmation"""
        self.logger.debug("Clearing audio folder")
        self._safe_clear_directory(self.settings.audio_folder.path, "Audio")

    def clear_mel(self):
        """Clear the mel spectrogram folder with confirmation"""
        self.logger.debug("Clearing mel spectrogram folder")
        self._safe_clear_directory(self.settings.mel_autosave_folder.path, "Mel")

    def clear_plots(self):
        """Clear the plots folder with confirmation"""
        self.logger.debug("Clearing plots folder")
        self._safe_clear_directory(self.settings.plot_save_folder_base.path, "Plots")

    def update_serial_port_settings(self):
        """Update serial port settings with signal blocking"""
        try:
            self.serial_port_combo.blockSignals(True)
            self.settings.update_values(
                {"serial_port": self.serial_port_combo.currentIndex()}
            )
        finally:
            self.serial_port_combo.blockSignals(False)

    def update_serial_port(self):
        """
        Update the serial port.
        """
        self.logger.debug("Updating serial port list")
        get_available_ports(self.settings)

    def _handle_connection_error(self, error_message: str) -> None:
        """Handle errors without triggering port refresh"""
        self.logger.error(f"Serial connection error: {error_message}")
        self._update_ui_state(connected=False, error=True)
        QMessageBox.critical(self, "Connection Error", error_message)

    def _handle_connection_state(self, connected: bool) -> None:
        """Handle connection state changes from serial reader"""
        if not connected and self.serial_reader.is_connected:
            # Unexpected disconnect
            self.logger.warning("Unexpected serial port disconnect")
            self._update_ui_state(connected=False, error=True)
            QMessageBox.warning(
                self, "Connection Lost", "Serial port disconnected unexpectedly"
            )

    def _handle_data_received(self, data: str) -> None:
        """Handle data received from serial port"""
        if data == "CONNECTION_TERMINATED":
            self.logger.warning("Serial port connection terminated")
            self._update_ui_state(connected=False, error=True)
            QMessageBox.warning(
                self, "Connection Lost", "Serial port connection terminated"
            )
        else:
            # Main processing loop

            # TODO: Process the data
            pass

    def toggle_serial(self) -> None:
        """Toggle the serial connection state between connected and disconnected."""
        try:
            if self.serial_reader.is_connected:
                # Disconnect sequence
                self.logger.debug("Initiating serial port disconnect")
                self._update_ui_state(connecting=True)

                if not self.serial_reader.stop():
                    raise RuntimeError("Failed to stop serial reader")

                self._update_ui_state(connected=False)
                self.logger.good("Serial port disconnected successfully")

            else:
                # Connect sequence
                self.logger.debug("Initiating serial port connection")
                self._update_ui_state(connecting=True)

                if not self.serial_reader.try_start():
                    raise RuntimeError("Failed to start serial reader")

                self._update_ui_state(connected=True)
                self.logger.debug("Serial port connected successfully")

        except Exception as e:
            self.logger.error(f"Serial toggle failed: {e}")
            self._update_ui_state(connected=False, error=True)
            QMessageBox.critical(self, "Error", f"Serial connection error: {e}")

    def _update_ui_state(
        self, connected: bool = False, connecting: bool = False, error: bool = False
    ) -> None:
        """Update UI elements based on connection state."""
        try:
            # Update button state
            self.serial_connect.setEnabled(not connecting)
            self.serial_connect.setText("Disconnect" if connected else "Connect")

            # Update status indicator
            if connecting:
                status = "Status: Transitioning..."
                color = "color: orange"
            elif error:
                status = "Status: Error - Disconnected"
                color = "color: red; font-weight: bold"
            else:
                status = f"Status: {'Connected' if connected else 'Disconnected'}"
                color = f"color: {'green' if connected else 'red'}"

            self.serial_status.setText(status)
            self.serial_status.setStyleSheet(color)

            # Update other UI elements
            self.serial_port_combo.setEnabled(not connected)
            self.serial_port_refresh.setEnabled(not connected)

            # Update write UI elements
            self.text_uart_write.setEnabled(connected)
            self.button_uart_write.setEnabled(connected)

        except Exception as e:
            self.logger.error(f"Failed to update UI state: {e}")

    def send_uart(self):
        """
        Send UART data.
        """
        data = self.text_uart_write.text()
        self.logger.info(f"Sending UART data: {data}")
        self.text_uart_write.clear()

    def closeEvent(self, event):
        """
        Close the application.
        """
        self.logger.debug("Closing the application")
        # Stop the serial reader
        self.serial_reader.stop()
        # Close the logger
        for handler in self.logger.handlers:
            handler.close()
        # Close all windows
        for window in QApplication.topLevelWidgets():
            window.close()
        event.accept()


###############################################################################
# Main

if __name__ == "__main__":
    # Settings
    settings = APP_Settings()

    # Update settings
    get_available_ports(settings)

    # Logging
    logger = setup_logging(settings)

    # GUI
    app = QApplication(sys.argv)
    main_window = GUI_MainWindow(settings, logger)
    main_window.show()

    sys.exit(app.exec())
