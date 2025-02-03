"""
Written by Group E 2024-2025

This module contains a easy to use GUI to train machine learning models using scikit-learn, and test them on a dataset.
"""

print("Launching Model Trainer... This may take a few seconds.")

####################################################################################################
# Standard library imports
from typing import Dict, Tuple, Type, List
import os, sys

# Third party imports
from sklearn.model_selection import train_test_split
import librosa
import numpy as np

# GUI imports
from PyQt6.QtWidgets import (
    # ===== LAYOUTS ===== (Used to organize widgets, not widgets themselves)
    QVBoxLayout,  # Vertical box layout
    QHBoxLayout,   # Horizontal box layout
    QGridLayout,   # Grid-based layout
    QFormLayout,   # Form layout (labels + inputs)
    
    # ===== WIDGETS ===== (Visible UI elements)
    # Core Application/Windows
    QApplication,  # Manages app flow (technically not a widget, but required)
    QWidget,       # Base container for all widgets
    QMainWindow,   # Main application window (with menu/status bars)
    QDialog,       # Dialog/popup window
    
    # Buttons
    QPushButton,   # Clickable button
    QCheckBox,     # Toggleable checkbox
    QRadioButton,  # Exclusive group selection
    
    # Inputs
    QLineEdit,     # Single-line text input
    QTextEdit,     # Rich text editor
    QComboBox,     # Dropdown list
    QSpinBox,      # Integer input spinner
    QDoubleSpinBox,# Float input spinner
    QSlider,       # Slider for values
    
    # Displays
    QLabel,        # Text/image label
    QProgressBar,  # Progress indicator
    QListWidget,   # Scrollable list of items
    QListWidgetItem,# Item for QListWidget
    QScrollArea,   # Scrollable container
    QSizePolicy,   # Size policy for layouts
    
    # Dialogs
    QFileDialog,   # File/folder selection dialog
    QMessageBox,   # Alert/confirmation dialog
    QInputDialog,  # Simple input dialog
    
    # Containers
    QTabWidget,    # Tabbed interface
    QGroupBox,     # Group with title border
    QStackedWidget,# Stack of widgets (only one visible)
    
    # Advanced
    QTableWidget,  # Table with rows/columns
    QTreeWidget,   # Hierarchical tree view
    QTreeWidgetItem,# Item for QTreeWidget
    QSplitter,     # Resizable frame splitter
    QDockWidget,   # Movable window pane
    QStatusBar,    # Status bar (in QMainWindow)
    QToolBar,      # Toolbar (in QMainWindow)
    QMenuBar,      # Menu bar (in QMainWindow)
    QStyledItemDelegate, # Custom item renderer
    QStyleOptionViewItem, # Style options for items
)

from PyQt6.QtCore import (
    Qt,           # Core Qt namespace (common enums)
    QThread,      # Worker thread for long tasks
    pyqtSignal,   # Signal for cross-thread communication
    QTimer,       # Timer for delays
    QEventLoop,   # Blocking loop for synchronous tasks
    QCoreApplication, # Core app instance (for event loop)
    QFileInfo,    # File information (path, size, etc)
    QDir,         # Directory handling
    QUrl,         # URL handling (file paths)
    QSettings,    # Persistent application settings
    QIODevice,    # Base class for I/O operations
    QFile,        # File I/O operations
    QDataStream,  # Binary stream I/O
    QByteArray,   # Raw byte array
    QBuffer,      # Memory buffer (for I/O)
    QMimeDatabase,# MIME type database
    QMimeData,    # MIME content container
    QProcess,     # External process handling
    QTemporaryFile,# Temporary file creation
    QTranslator,  # Internationalization (i18n)
    QLocale,      # Locale settings (language, etc)
    QLibraryInfo, # Qt library information
    QSysInfo,     # System information
    QModelIndex,   # Data index for model views
)

from PyQt6.QtGui import (
    QColor,       # Color value (RGB/HSV)
    QIcon,        # Window icon/image
    QPixmap,      # Image/Pixmap object
    QFont,        # Font object (family/size/etc)
    QCursor,      # Mouse cursor icon
    QPalette,     # Collection of GUI colors
    QBrush,       # Paint style for elements
    QPen,         # Line style for drawing
    QPainter,     # Low-level 2D painting
    QPaintEvent,  # Event for painting widgets
    QMouseEvent,  # Event for mouse input
    QWheelEvent,  # Event for mouse wheel
    QKeyEvent,    # Event for keyboard input
)

####################################################################################################
# Model training imports

from sklearn.linear_model import (
    LogisticRegression, 
    SGDClassifier, 
    RidgeClassifier, 
    PassiveAggressiveClassifier,
    Perceptron
)
from sklearn.svm import SVC, NuSVC, LinearSVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    AdaBoostClassifier,
    BaggingClassifier
)
from sklearn.naive_bayes import (
    GaussianNB, 
    BernoulliNB, 
    MultinomialNB, 
    ComplementNB
)
from sklearn.neighbors import (
    KNeighborsClassifier, 
    RadiusNeighborsClassifier, 
    NearestCentroid
)
from sklearn.discriminant_analysis import (
    LinearDiscriminantAnalysis, 
    QuadraticDiscriminantAnalysis
)
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.neural_network import MLPClassifier

####################################################################################################
# Models and constants

models_dict: Dict[str, Dict[str, Tuple[Type, str]]] = { # Generated by DeepSeek-R1:32B under the MIT liscence
    "Linear Models": {
        "Logistic Regression": (LogisticRegression, "Linear model for logistic regression classification"),
        "Stochastic Gradient Descent": (SGDClassifier, "Linear classifier with SGD training and regularization"),
        "Ridge Classifier": (RidgeClassifier, "Classifier using ridge regression with thresholding"),
        "Passive-Aggressive": (PassiveAggressiveClassifier, "Online learning algorithm for large-scale learning"),
        "Perceptron": (Perceptron, "Simple linear algorithm for binary classification")
    },
    
    "Support Vector Machines": {
        "Support Vector Machine (SVC)": (SVC, "C-support vector classification with kernel trick"),
        "Nu-Support Vector Machine": (NuSVC, "Nu-support vector classification with margin control"),
        "Linear Support Vector Machine": (LinearSVC, "Linear support vector classification optimized for speed")
    },
    
    "Tree-based Models": {
        "Decision Tree": (DecisionTreeClassifier, "Non-linear model using recursive partitioning"),
        "Random Forest": (RandomForestClassifier, "Ensemble of decorrelated decision trees with bagging"),
        "Extra Trees": (ExtraTreesClassifier, "Extremely randomized trees ensemble with reduced variance")
    },
    
    "Boosting Models": {
        "Gradient Boosting": (GradientBoostingClassifier, "Sequential ensemble with gradient descent optimization"),
        "Histogram Gradient Boosting": (HistGradientBoostingClassifier, "Efficient GB implementation using histograms"),
        "AdaBoost": (AdaBoostClassifier, "Adaptive boosting with emphasis on misclassified samples")
    },
    
    "Ensemble Methods": {
        "Bagging": (BaggingClassifier, "Meta-estimator for bagging-based ensemble learning")
    },
    
    "Naive Bayes Models": {
        "Gaussian Naive Bayes": (GaussianNB, "Gaussian likelihood with naive independence assumption"),
        "Bernoulli Naive Bayes": (BernoulliNB, "Bernoulli distribution for binary/boolean features"),
        "Multinomial Naive Bayes": (MultinomialNB, "Multinomial distribution for count-based features"),
        "Complement Naive Bayes": (ComplementNB, "Adaptation of MultinomialNB for imbalanced datasets")
    },
    
    "Nearest Neighbors": {
        "k-Nearest Neighbors": (KNeighborsClassifier, "Instance-based learning using k-nearest neighbors vote"),
        "Radius Neighbors": (RadiusNeighborsClassifier, "Neighbors within fixed radius for classification"),
        "Nearest Centroid": (NearestCentroid, "Simple classifier based on centroid distances")
    },
    
    "Discriminant Analysis": {
        "Linear Discriminant Analysis": (LinearDiscriminantAnalysis, "Linear decision boundaries from class statistics"),
        "Quadratic Discriminant Analysis": (QuadraticDiscriminantAnalysis, "Quadratic decision boundaries for classification")
    },
    
    "Neural Networks": {
        "Multilayer Perceptron": (MLPClassifier, "Feedforward artificial neural network classifier")
    },
    
    "Probabilistic Models": {
        "Gaussian Process": (GaussianProcessClassifier, "Probabilistic classifier based on Gaussian processes")
    }
}

# Classification classes for the dataset (Not are needed to be used, only those that are setup, will then be used and saved)
classification_classes = [
    "Unknown",
    "Birds",
    "Fire",
    "Chainsaw",
    "Handsaw",
    "Helicopter",
    "Human Voice",
    "Howling Leaves"
]

# Default model parameters for eacch model, if its not present, the default parameters will be used
model_params_per_path = {
    "Tree-based Models/Decision Tree": {
        "criterion": "gini",
        "splitter": "best",
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "min_weight_fraction_leaf": 0.0,
        "min_impurity_decrease": 0.0,
        "ccp_alpha": 0.0
    },
}

####################################################################################################
# Application logic

# Use process pools to parallelize training if needed (each job runs in a separate process)

class ModelTrainerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Model Trainer")
        self.resize(1200, 900)
        self.setDockNestingEnabled(True)  # Allow nested docks
        
        # Create the main docks
        def make_dock(name: str, widget: QWidget, features: QDockWidget.DockWidgetFeature = QDockWidget.DockWidgetFeature.NoDockWidgetFeatures) -> QDockWidget:
            dock = QDockWidget(name, self)
            dock.setWidget(widget)
            dock.setFeatures(features)

            # Style the dock (border, title bar)
            dock.setStyleSheet("QDockWidget { border: 1px solid #a0a0a0; }")
            return dock
        
        # Make the widgets
        self._base_top1 = QWidget()
        self._base_top2 = QWidget()
        self._base_top3 = QWidget()
        self._base_bottom = QWidget()

        # Create the docks
        general_features = [
            QDockWidget.DockWidgetFeature.DockWidgetMovable,
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        ]
        parsed_features = general_features[0]
        for feature in general_features[1:]:
            parsed_features |= feature
        self.dock_top1 = make_dock("Model Selection (Double click to detatch/attatch)", self._base_top1, parsed_features)
        self.dock_top2 = make_dock("Dataset Selection (Double click to detatch/attatch)", self._base_top2, parsed_features)
        self.dock_top3 = make_dock("Model Launcher (Double click to detatch/attatch)", self._base_top3, parsed_features)
        self.dock_bottom = make_dock("Training Tasks (Double click to detatch/attatch)", self._base_bottom, parsed_features)

        # Add the first top dock to the top area
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.dock_top1)
        
        # Split horizontally to add the second and third top docks
        self.splitDockWidget(self.dock_top1, self.dock_top2, Qt.Orientation.Horizontal)
        self.splitDockWidget(self.dock_top2, self.dock_top3, Qt.Orientation.Horizontal)
        
        # Add the bottom dock to the bottom area
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_bottom)

        # Set initial sizes (optional)
        self.resizeDocks( # TODO: Figure out why this is not working ??????
            [self.dock_top1, self.dock_top2, self.dock_top3], 
            [150, 200, 150],  # Widths for top docks
            Qt.Orientation.Horizontal
        )
        self.resizeDocks(
            [self.dock_bottom], 
            [10],  # Height for bottom dock
            Qt.Orientation.Vertical
        )

        # Generate the rest of the UI
        self.gen_top1()
        self.gen_top2()
        self.gen_top3()
        self.gen_bottom()

    def gen_top1(self):
        """Generate the model selection dock that uses a tree widget and buttons"""
        # Setup the layout
        self.top1_base_layout = QVBoxLayout(self._base_top1)
        self.top1_tools_group = QGroupBox("")
        self.top1_tools_layout = QVBoxLayout(self.top1_tools_group)
        self.top1_base_layout.addWidget(self.top1_tools_group)
        self.top1_tree = QTreeWidget()
        self.top1_base_layout.addWidget(self.top1_tree)

        # Add the tools
        self.top1_select_all = QPushButton("Select All")
        self.top1_deselect_all = QPushButton("Deselect All")
        self.top1_single_select = QCheckBox("Single Select")
        self.top1_tools_layout.addWidget(self.top1_select_all)
        self.top1_tools_layout.addWidget(self.top1_deselect_all)
        self.top1_tools_layout.addWidget(self.top1_single_select)

        # Format the tree (The header is blue, and the sub-items are alternating colors depending on the depth)
        self.top1_tree.setHeaderLabels(["Usable Models", "Description"])
        self.top1_tree.setAlternatingRowColors(True)

        # Add the items
        def color_line(tree_item: QTreeWidgetItem, color: QColor): [tree_item.setBackground(i, QBrush(color)) for i in range(2)]
        for model_type, model_dict in models_dict.items():
            type_item = QTreeWidgetItem([model_type, ""])
            color_line(type_item, QColor(255, 230, 255)) # Light purple
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            type_item.setFirstColumnSpanned(True)
            type_item.setToolTip(0, model_type)
            self.top1_tree.addTopLevelItem(type_item)
            for model_name, (model_class, model_description) in model_dict.items():
                model_item = QTreeWidgetItem([model_name, model_description])
                model_item.setToolTip(0, model_name)
                model_item.setToolTip(1, model_description)
                type_item.addChild(model_item)
        self.top1_tree.expandAll()

        # Make the tree connections to the tools
        def change_multi_select():
            self.top1_tree.clearSelection()
            self.top1_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection if self.top1_single_select.isChecked() else QTreeWidget.SelectionMode.MultiSelection)
        self.top1_single_select.clicked.connect(change_multi_select)
        change_multi_select()

        def select_all():
            self.top1_tree.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
            for i in range(self.top1_tree.topLevelItemCount()):
                for j in range(self.top1_tree.topLevelItem(i).childCount()):
                    self.top1_tree.topLevelItem(i).child(j).setSelected(True)
            self.top1_single_select.setChecked(False)
        def deselect_all():
            self.top1_tree.clearSelection()
        self.top1_select_all.clicked.connect(select_all)
        self.top1_deselect_all.clicked.connect(deselect_all)

    def file_tree_configure(self, tree: QTreeWidget, header_labels: List[str]):
        """Configure a tree widget with alternating colors and header labels"""
        tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        #tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        #tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        tree.setHeaderLabels(header_labels)
        tree.setAlternatingRowColors(True)
        #tree.setDragEnabled(True)
        #tree.setAcceptDrops(True)
        #tree.setDropIndicatorShown(True)

    class ClassificationColorDelegate(QStyledItemDelegate):
        hsv_classification_colors = {classification: QColor.fromHsv(360 * i // len(classification_classes), 20, 255) for i, classification in enumerate(classification_classes)}
        def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
            
            super().paint(painter, option, index)
            if index.column() == 1:
                classification = index.data()
                color = self.hsv_classification_colors.get(classification, QColor(255, 255, 255))
                color = color if index.row() % 2 else color.lighter(103)
                painter.fillRect(option.rect, QBrush(color))
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignLeft, classification)
                # BUG : I am not rendering the selection color, so the selected items are not colored, but oh well, it works for now
            
    def gen_top2(self):
        """Generate the dataset selection dock that uses a list widget and buttons"""
        # Setup the layout
        self.top2_base_layout = QVBoxLayout(self._base_top2)
        self.top2_tools_group = QGroupBox("")
        self.top2_tools_layout = QHBoxLayout(self.top2_tools_group)
        self.top2_base_layout.addWidget(self.top2_tools_group)
        self.top2_files_tabs = QTabWidget()
        self.top2_base_layout.addWidget(self.top2_files_tabs)

        # Add the 2 Trees
        self.top2_list_audio = QTreeWidget()
        self.top2_list_mel = QTreeWidget()
        self.top2_files_tabs.addTab(self.top2_list_audio, "Audio Files")
        self.top2_files_tabs.addTab(self.top2_list_mel, "MEL Files")

        # Separate the tools into two groups
        self.top2_tools_files = QWidget()
        self.top2_tools_files_layout = QVBoxLayout(self.top2_tools_files)   
        self.top2_tools_layout.addWidget(self.top2_tools_files)
        self.top2_tools_classification = QWidget()
        self.top2_tools_classification_layout = QVBoxLayout(self.top2_tools_classification)
        self.top2_tools_layout.addWidget(self.top2_tools_classification)

        # Add the tools
        self.top2_select_audio = QPushButton("Select Audio Files")
        self.top2_select_mel = QPushButton("Select MEL Files")
        self.top2_append = QCheckBox("Append Files")
        self.top2_append.setChecked(True)
        self.top2_clear = QPushButton("Clear Files")
        self.top2_tools_files_layout.addWidget(self.top2_select_audio)
        self.top2_tools_files_layout.addWidget(self.top2_select_mel)
        self.top2_tools_files_layout.addWidget(self.top2_append)

        # Add the classification tools
        self.top2_class_label = QLabel("Classification Assignments:")
        self.top2_class_assign = QComboBox()
        self.top2_class_assign.addItems(classification_classes)
        self.top2_class_apply = QPushButton("Apply")
        self.top2_tools_classification_layout.addWidget(self.top2_class_label)
        self.top2_tools_classification_layout.addWidget(self.top2_class_assign)
        self.top2_tools_classification_layout.addWidget(self.top2_class_apply)

        # Configure the tree widgets
        self.cathegories_audio = {classes: [] for classes in classification_classes}
        self.file_tree_configure(self.top2_list_audio, ["Audio File Names", "Classification", "Path"])
        self.file_tree_configure(self.top2_list_mel, ["MEL Files", "Classification", "Path"])
        self.top2_list_audio.setItemDelegateForColumn(1, self.ClassificationColorDelegate())
        self.top2_list_mel.setItemDelegateForColumn(1, self.ClassificationColorDelegate())

        # Add demo items
        for i in range(10):
            item = QTreeWidgetItem([f"Audio File {i}", "Unknown", f"Path {i}"])
            self.top2_list_audio.addTopLevelItem(item)

        # Add the connections
        def select_audio_files():
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Audio Files", "", "Audio Files (*.wav *.mp3)"
            )
            if files:
                if not self.top2_append.isChecked():
                    self.top2_list_audio.clear()
                for file in files:
                    file_name = os.path.basename(file)
                    item = QTreeWidgetItem([file_name, "Unknown", file])
                    self.top2_list_audio.setToolTip(0, file_name)
                    self.top2_list_audio.setToolTip(2, file)
                    self.top2_list_audio.addTopLevelItem(item)
        def select_mel_files():
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select MEL Files", "", "MEL Files (*.npy)"
            )
            if files:
                if not self.top2_append.isChecked():
                    self.top2_list_mel.clear()
                for file in files:
                    file_name = os.path.basename(file)
                    item = QTreeWidgetItem([file_name, "Unknown", file])
                    self.top2_list_audio.setToolTip(0, file_name)
                    self.top2_list_audio.setToolTip(2, file)
                    self.top2_list_mel.addTopLevelItem(item)
        self.top2_select_audio.clicked.connect(select_audio_files)
        self.top2_select_mel.clicked.connect(select_mel_files)

        def apply_classification():
            selected_class = self.top2_class_assign.currentText()
            for item in self.top2_list_audio.selectedItems():
                item.setText(1, selected_class)
            for item in self.top2_list_mel.selectedItems():
                item.setText(1, selected_class)
        self.top2_class_apply.clicked.connect(apply_classification)

        def clear_files():
            self.top2_list_audio.clear()
            self.top2_list_mel.clear()
        self.top2_clear.clicked.connect(clear_files)

    def gen_top3(self):
        """Generate the model training dock that uses a list widget and buttons"""
        # Setup the layout
        self.top3_main_layout = QVBoxLayout(self._base_top3)
        self.top3_base_scroll = QScrollArea()
        self.top3_base_scroll.setWidgetResizable(True)
        self.top3_main_layout.addWidget(self.top3_base_scroll)
        self.top3_scroll_layout = QVBoxLayout(self.top3_base_scroll)
        self.top3_base_widget = QWidget()
        self.top3_scroll_layout.addWidget(self.top3_base_widget)
        self.top3_base_layout = QVBoxLayout(self.top3_base_widget)
        
        # Training options must have a button to start training
        self.launch_training_button = QPushButton("Launch Training Tasks")
        self.top3_base_layout.addWidget(self.launch_training_button)
        self.launch_training_button.clicked.connect(self.train_models)

        # Training options subwidget
        self.training_options_subwidget1 = QGroupBox("Dataset Basic Settings")
        self.training_options_grid1 = QGridLayout()
        self.training_options_subwidget1.setLayout(self.training_options_grid1)
        self.top3_base_layout.addWidget(self.training_options_subwidget1)

        def make_param(label_text, widget, row, col):
            """Make a parameter entry in the grid layout"""
            label = QLabel(label_text)
            label.setFixedHeight(10)
            widget.setFixedHeight(20)
            self.training_options_grid1.addWidget(label, row, col)
            self.training_options_grid1.addWidget(widget, row, col + 1)

        self.test_split_mode = QComboBox()
        self.test_split_mode.addItems(["FUSE", "ONLY AUDIO", "ONLY MEL"])
        make_param("Dataset Split Mode:", self.test_split_mode, 0, 0)

        self.mel_size_param = QSpinBox()
        self.mel_size_param.setRange(1, 2000)
        self.mel_size_param.setValue(20)
        make_param("MEL Vector Size:", self.mel_size_param, 1, 0)

        self.mel_len_param = QSpinBox()
        self.mel_len_param.setRange(1, 2000)
        self.mel_len_param.setValue(20)
        make_param("MEL Vector Length:", self.mel_len_param, 2, 0)

        self.test_size_param = QDoubleSpinBox()
        self.test_size_param.setRange(0.0, 1.0)
        self.test_size_param.setValue(0.2)
        self.test_size_param.setSingleStep(0.01)
        make_param("Test Size:", self.test_size_param, 3, 0)

        self.random_state_param = QSpinBox()
        self.random_state_param.setRange(0, 1000)
        self.random_state_param.setValue(42)
        make_param("Random State:", self.random_state_param, 4, 0)

        # Audio to MEL Processing Parameters
        self.audio_processing_subwidget = QGroupBox("Audio Processing Parameters (To MEL)")
        self.audio_processing_grid = QGridLayout()
        self.audio_processing_subwidget.setLayout(self.audio_processing_grid)
        self.top3_base_layout.addWidget(self.audio_processing_subwidget)

        # TODO : Add the audio processing parameters here

        # MEL Processing Parameters
        self.mel_processing_subwidget = QGroupBox("MEL Processing Parameters")
        self.mel_processing_grid = QGridLayout()
        self.mel_processing_subwidget.setLayout(self.mel_processing_grid)
        self.top3_base_layout.addWidget(self.mel_processing_subwidget)

        # TODO : Add the MEL processing parameters here

        # Per Model Parameters
        self.model_parameter_load_entries = QPushButton("Load Model Parameter Widgets")
        self.model_parameter_load_entries.clicked.connect(self.load_model_parameter_entries)
        self.top3_base_layout.addWidget(self.model_parameter_load_entries)

        self.model_parameter_subwidget = QGroupBox("Model Parameters")
        self.model_parameter_grid = QVBoxLayout()
        self.model_parameter_subwidget.setLayout(self.model_parameter_grid)
        self.top3_base_layout.addWidget(self.model_parameter_subwidget)

        # List of groups with the model's parameters as a dictionary (Text entry)
        # Pre-populate with the default parameters : model_params_per_path
        self.model_parameter_entries = model_params_per_path

        # Add stretch to the bottom
        self.top3_base_layout.addStretch(999)

    def load_model_parameter_entries(self):
        """Load the model parameter entries into the widget"""
        for i in reversed(range(self.model_parameter_grid.count())):
            self.model_parameter_grid.itemAt(i).widget().deleteLater()
        for tree_item in self.top1_tree.selectedItems():
            model_name = tree_item.text(0)
            model_params = self.model_parameter_entries.get(model_name,"")
            group = QGroupBox(model_name)
            layout = QVBoxLayout()
            group.setLayout(layout)
            text_edit = QTextEdit()
            text_edit.setFixedHeight(100)
            text_edit.setText(str(model_params))
            text_edit.setPlaceholderText("Enter model parameters here as a dict, that will be applied elliptically, example : \n{\n\t\"param1\": \"value1\",\n\t\"param2\": 123,\n\t\"param3\": True\n\t\"param4\": None\n}")
            layout.addWidget(text_edit)
            self.model_parameter_grid.addWidget(group)
            text_edit.textChanged.connect(lambda: self.model_parameter_entries[model_name].update(self.parse_model_parameters(text_edit.toPlainText())))

    def gen_bottom(self):
        """Generate the training tasks dock that uses a list widget and buttons"""
        # Setup the layout
        self.bottom_base_layout = QHBoxLayout(self._base_bottom)
        self.bottom_tasks = QTreeWidget()
        self.bottom_base_layout.addWidget(self.bottom_tasks)
        self.bottom_tools_group = QGroupBox("Trained model tools")
        self.bottom_tools_layout = QVBoxLayout(self.bottom_tools_group)
        self.bottom_base_layout.addWidget(self.bottom_tools_group)

        # Configure the tree widget
        self.bottom_tasks.setHeaderLabels(["Task Model", "Progress", "Task Params", "Used Files"])
        self.bottom_tasks.setAlternatingRowColors(True)

        # Add demo items
        for i in range(10):
            item = QTreeWidgetItem([f"Task {i}", "0%", "Params", "Files"])
            self.bottom_tasks.addTopLevelItem(item)

        # Add the tools
        self.bottom_stop_all = QPushButton("Stop All Tasks")
        self.bottom_clear_all = QPushButton("Clear All Tasks")
        self.bottom_tools_layout.addWidget(self.bottom_stop_all)
        self.bottom_tools_layout.addWidget(self.bottom_clear_all)
        self.bottom_tools_layout.addWidget(QLabel("Task Tools:"))
        self.bottom_tools_stop = QPushButton("Stop Task")
        self.bottom_tools_clear = QPushButton("Clear Task")
        self.bottom_tools_analyze = QPushButton("Analyze Trained Model")
        self.bottom_tools_save = QPushButton("Save Trained Model (Pickle of dict)")
        self.bottom_tools_layout.addWidget(self.bottom_tools_stop)
        self.bottom_tools_layout.addWidget(self.bottom_tools_clear)
        self.bottom_tools_layout.addWidget(self.bottom_tools_analyze)
        self.bottom_tools_layout.addWidget(self.bottom_tools_save)

        self.bottom_tools_layout.addStretch()
        
    def train_models(self):
        """Train the selected models using the selected dataset"""
        # Get the selected models
        selected_models = []
        for tree_item in self.top1_tree.selectedItems():
            selected_models.append(tree_item.text(0))
        
        # Transform the audio datasets into MEL datasets
        audio_mel_datasets = [(self.process_audio(tree_item.text(2)), tree_item.text(1)) for tree_item in self.top2_list_audio.topLevelItems()]
        mel_datasets       = [(self.load_mel(tree_item.text(2)), tree_item.text(1)) for tree_item in self.top2_list_mel.topLevelItems()]
        mel_vec_size = self.mel_size_param.value() # 20
        mel_vec_len = self.mel_len_param.value() # 20

        # Optionaly fuse the 2 datasets
        fuse_datasets = self.test_split_mode.currentText() # FUSE, ONLY AUDIO, ONLY MEL
        if "FUSE" in fuse_datasets:
            # Fuse the datasets
            fused_datasets = [(np.concatenate([audio_data[0], mel_data[0]]), audio_data[1]) for audio_data, mel_data in zip(audio_mel_datasets, mel_datasets)]
        elif "ONLY AUDIO" in fuse_datasets:
            fused_datasets = audio_mel_datasets
        elif "ONLY MEL" in fuse_datasets:
            fused_datasets = mel_datasets

        # Transform the datasets a bit more (if needed)
        fuse_datasets = [(self.process_mel(mel_data, mel_vec_size, mel_vec_len), label) for mel_data, label in fused_datasets]

        # Split the dataset into training and testing
        test_size = self.test_size_param.value() # 0.2
        random_state = self.random_state_param.value() # 42
        X, y = zip(*fused_datasets)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

        # Train the models
        for model_name in selected_models:
            self.launch_task(model_name, X_train, X_test, y_train, y_test)

    def launch_task(self, model_name, X_train, X_test, y_train, y_test):
        """Launch a training task for a model"""
        # Create a task thread
        task_thread = QThread()
        with task_thread:
            model_to_use = self.search_model_by_name(model_name)
            if model_to_use is None:
                print(f"Model {model_name} not found")
                return
            model_instance = model_to_use()
            model_instance.fit(X_train, y_train)
            y_pred = model_instance.predict(X_test)
            accuracy = model_instance.score(X_test, y_test)
            print(f"Model {model_name} trained with accuracy {accuracy}")

    def search_model_by_name(self, model_name):
        """Search for a model by its name"""
        for model_type, model_dict in models_dict.items():
            for model_name_, (model_class, model_description) in model_dict.items():
                if model_name == model_name_:
                    return model_class
        return None

    def parse_model_parameters(self, text_dict_param: str) -> Dict:
        """
        Parse the model parameters from a text dictionary, it accepts the following format:
        {
            "param1": "value1",
            "param2": 123,
            "param3": True,
            "param4": None
        }
        """
        dict_param = {}
        for line in text_dict_param.split("\n"):
            if line:
                key, value = line.split(":")
                key = key.strip()
                value = value.strip()
                if value.isnumeric():
                    value = int(value)
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.lower() == "none":
                    value = None
                dict_param[key] = value
        return dict_param

    def process_audio(self, audio_file):
        """Process an audio file into a MEL spectrogram"""
        audio_data = librosa.load(audio_file)
        mel_data = librosa.feature.melspectrogram(audio_data[0], sr=audio_data[1])
        # TODO: Add signal processing here
        return mel_data
    
    def load_mel(self, mel_file):
        """Load a MEL spectrogram from a file"""
        mel_data = np.load(mel_file)
        return mel_data

    def process_mel(self, mel_data, mel_vec_size, mel_vec_len):
        """Process a MEL spectrogram into a fixed-size vector"""
        # TODO: Add MELVEC processing here
        return mel_data

####################################################################################################
# Entry point

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModelTrainerApp()
    window.show()
    sys.exit(app.exec())