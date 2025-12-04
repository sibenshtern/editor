import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QInputDialog, QMessageBox, QVBoxLayout,
                             QFileDialog, QGraphicsScene, QGraphicsView)
from PyQt6.QtCore import Qt, QPointF, QObject
from PyQt6.QtGui import QColor, QPainter, QBrush

from ui.editor_ui import EditorWindowUI
from graphical import (Controller, BlockFrame, PortItem, InstanceItem, WireItem, 
                       JunctionItem)
from netlist_model import NetlistProject
from version_manager import VersionManager
from parser.parser import Parser


class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file_path = None
        
        # Initialize circuit object model
        self.netlist_project = NetlistProject("circuit_project")
        self.parser = Parser()
                
        self.ui = EditorWindowUI()
        self.ui.show()
        
        # Initialize graphical components
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("#000000")))
        
        self.view = QGraphicsView(self.scene)
        try:
            self.view.setRenderHints(QPainter.RenderHint.Antialiasing)
        except Exception:
            pass
        
        self.controller = Controller(self.scene)
        
        # Add the graphics view to the UI layout
        graphics_widget = self.ui.graphics_frame
        layout = graphics_widget.layout()
        if layout is None:
            layout = QVBoxLayout(graphics_widget)
        layout.addWidget(self.view)
        
        # Mode management
        self.active_mode = None
        self.current_filter = None
        self._current_block_id = None
        
        # Initialize version manager (None means unsaved file - will create UUID repository)
        self.version_manager = VersionManager(None, self.controller)

        self.setup_menu_bar()
        self.setup_connections()
        self.refresh_objects_list()
        
        if self.ui.objects_list.count() > 0:
            self.ui.objects_list.setCurrentRow(0)
            self._show_block_by_index(0)

        # Save initial state
        self._save_version("Initial state")

    def _save_version(self, action_name: str):
        """Save current state to version manager."""
        try:
            # Save to external file if we have one, otherwise just to repository
            self.version_manager.save_state(action_name, save_to_file=self.current_file_path)
        except Exception as e:
            print(f"Failed to save version: {e}")

    def _restore_from_version(self):
        """Restore both graphical and object models after undo/redo."""
        # Refresh graphical model (already done by version_manager.undo/redo)
        self.refresh_objects_list()
        
        # Rebuild object model from graphical model
        self._rebuild_object_model_from_graphical()
        
        # Update display
        if self._current_block_id and self._current_block_id in self.controller.blocks:
            self.controller.show_only_block(self._current_block_id)
        elif self.controller.blocks:
            first_id = next(iter(self.controller.blocks.keys()))
            self.controller.show_only_block(first_id)
            self._current_block_id = first_id

    def _rebuild_object_model_from_graphical(self, file_path: str):
        """Rebuild the entire object model from the graphical model."""
        # Clear object model
        self.netlist_project, _ = self.parser.load_netlist_from_file(file_path)

        self._log_object_model()

    def _get_pin_ref(self, block_name: str, owner_id: str, pin_name: str):
        """Get PinRef from owner_id and pin_name."""
        if owner_id.startswith("block:"):
            block_id = owner_id.split(":", 1)[1]
            block_frame = self.controller.blocks.get(block_id)
            if block_frame and block_frame.model.name == block_name:
                return self.netlist_project.blocks[block_name].interface_pins.get(pin_name)
        else:
            # Instance pin
            for inst_model in self.controller.blocks[self._current_block_id].model.instances:
                if inst_model.id == owner_id:
                    data_inst = self.netlist_project.blocks[block_name].instances.get(inst_model.name)
                    if data_inst:
                        return data_inst.interface_pins.get(pin_name)
        return None

    def setup_menu_bar(self):
        """Create the menu bar with File menu."""
        self.ui.menu_actions['open'].triggered.connect(self.open_file)
        self.ui.menu_actions['save'].triggered.connect(self.save_file)
        self.ui.menu_actions['save_as'].triggered.connect(self.save_file_as)

    def open_file(self):
        """Open a file dialog to select a scene file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Scene File",
            "",
            "JSON Files (*.json);;Netlist File (*.net);;All Files (*)"
        )
        if file_path:
            self.current_file_path = file_path

            file_name = file_path.split('.')[0]
            graphical_file = f"{file_name}.json"
            netlist_file = f"{file_name}.net"

            try:
                # Create new version manager for this file (will load existing repository if available)
                self.version_manager = VersionManager(file_path, self.controller)
                
                # Load the file
                self.controller.load_scene(graphical_file)
                self.refresh_objects_list()
                self.ui.setWindowTitle(f"Editor - {netlist_file}")
                
                # Rebuild object model after loading
                self._rebuild_object_model_from_graphical(netlist_file)
                
                if self.ui.objects_list.count() > 0:
                    self.ui.objects_list.setCurrentRow(0)
                    self._show_block_by_index(0)
                
                QMessageBox.information(self, "Success", f"Loaded: {netlist_file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def save_file(self):
        """Save the current scene to the current file path."""
        if self.current_file_path is None:
            self.save_file_as()
        else:
            try:
                # Associate repository with file if not already associated
                if self.version_manager.file_path != self.current_file_path:
                    self.version_manager.associate_with_file(self.current_file_path)
                
                self.controller.save_scene(self.current_file_path)
                # Save version after saving file
                self._save_version(f"Save file {os.path.basename(self.current_file_path)}")
                self.parser.save_netlist_to_file(f"{self.current_file_path.split('.')[0]}.net", self.netlist_project)
                QMessageBox.information(self, "Success", f"Saved: {self.current_file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def save_file_as(self):
        """Save the current scene to a new file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Scene File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.current_file_path = file_path
            try:
                # Associate current repository with the new file
                self.version_manager.associate_with_file(file_path)
                
                self.controller.save_scene(file_path)
                self.ui.setWindowTitle(f"Editor - {file_path}")
                
                # Save version after saving file
                self._save_version(f"Save file as {os.path.basename(file_path)}")
                self.parser.save_netlist_to_file(f"{self.current_file_path.split('.')[0]}.net", self.netlist_project)
                QMessageBox.information(self, "Success", f"Saved: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def setup_connections(self):
        """Connect all buttons to their handler functions."""
        # Block operations
        self.ui.add_block.clicked.connect(self.add_block)
        self.ui.del_block.clicked.connect(self.delete_block)
        self.ui.copy_block.clicked.connect(self.copy_block)
        self.ui.rename_block.clicked.connect(self.rename_block)

        # Instance operations
        self.ui.add_instance.clicked.connect(self.add_instance)
        self.ui.del_instance.clicked.connect(self.delete_instance)
        self.ui.copy_instance.clicked.connect(self.copy_instance)
        self.ui.rename_instance.clicked.connect(self.rename_instance)

        # Pin operations
        self.ui.add_pin.clicked.connect(self.add_pin)
        self.ui.del_pin.clicked.connect(self.delete_pin)
        self.ui.rename_pin.clicked.connect(self.rename_pin)

        # Net operations
        self.ui.add_net.clicked.connect(self.add_net)
        self.ui.del_net.clicked.connect(self.delete_net)
        self.ui.rename_net.clicked.connect(self.rename_net)

        # Junction operations
        self.ui.add_junction.clicked.connect(self.add_junction)
        self.ui.del_junction.clicked.connect(self.delete_junction)

        # Undo/Redo operations
        self.ui.btn_undo.clicked.connect(self.undo)
        self.ui.btn_redo.clicked.connect(self.redo)

        # Objects list selection
        self.ui.objects_list.itemClicked.connect(self.on_object_selected)

    def _get_block_id_by_index(self, idx: int):
        """Get block ID from block name at index in objects_list."""
        if idx < 0 or idx >= self.ui.objects_list.count():
            return None
        item = self.ui.objects_list.item(idx)
        block_name = item.text()
        for block_id, block_frame in self.controller.blocks.items():
            if block_frame.model.name == block_name:
                return block_id
        return None

    def _show_block_by_index(self, idx: int):
        """Show block by index."""
        bid = self._get_block_id_by_index(idx)
        if bid is None:
            return
        self.controller.show_only_block(bid)
        self._current_block_id = bid

    def _deactivate_mode(self):
        """Deactivate current mode."""
        if self.current_filter:
            try:
                self.view.viewport().removeEventFilter(self.current_filter)
            except Exception:
                pass
            self.current_filter = None

        if self.active_mode == 'wire':
            self.controller.set_add_wire_mode(False)
        elif self.active_mode == 'junction':
            self.controller.set_add_junction_mode(False)

        self.active_mode = None

    def refresh_objects_list(self):
        """Refresh the list of objects (blocks) in the objects_list widget."""
        current_selection = self.ui.objects_list.currentItem()
        current_name = current_selection.text() if current_selection else None
        
        self.ui.objects_list.clear()
        for block_frame in self.controller.blocks.values():
            self.ui.objects_list.addItem(block_frame.model.name)
        
        # Restore selection if possible
        if current_name:
            for i in range(self.ui.objects_list.count()):
                if self.ui.objects_list.item(i).text() == current_name:
                    self.ui.objects_list.setCurrentRow(i)
                    break

    def on_object_selected(self, item):
        """Handle selection of an object in the objects list."""
        block_name = item.text()
        for block_id, block_frame in self.controller.blocks.items():
            if block_frame.model.name == block_name:
                self.controller.show_only_block(block_id)
                self._current_block_id = block_id
                break

    def add_block(self):
        """Add a new block to both graphical and object model."""
        self._deactivate_mode()
        name = self.__get_new_name("New block", "Block name:", f"Block{len(self.controller.blocks) + 1}")
        if not name:
            return
        
        if self._block_name_exists(name):
            QMessageBox.warning(self, "Error", f"Block name '{name}' already exists.")
            return
        
        bf = self.controller.add_block(name)
        if not self._sync_block_added(name):
            self.controller.delete_block(bf)
            return
        for bf_item in self.controller.blocks.values():
            if bf_item.model.name not in self.netlist_project.blocks:
                try:
                    self.netlist_project.add_block(bf_item.model.name)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to add block to model: {e}")
        self.refresh_objects_list()
        for i in range(self.ui.objects_list.count()):
            if self.ui.objects_list.item(i).text() == bf.model.name:
                self.ui.objects_list.setCurrentRow(i)
                self._show_block_by_index(i)
                break
        
        self._save_version(f"Add block '{name}'")

    def delete_block(self):
        """Delete the selected block from both models."""
        selected = list(self.scene.selectedItems())
        blocks = [it for it in selected if isinstance(it, BlockFrame)]
        if not blocks:
            QMessageBox.information(self, "Delete Block", "Select a block to delete.")
            return
        for b in blocks:
            block_name = b.model.name
            if not self._sync_block_removed(block_name):
                continue
            self.controller.delete_block(b)
            self._save_version(f"Delete block '{block_name}'")
        self.refresh_objects_list()

    def copy_block(self):
        """Copy the selected block with a new name."""
        selected = list(self.scene.selectedItems())
        blocks = [it for it in selected if isinstance(it, BlockFrame)]
        if not blocks:
            QMessageBox.information(self, "Copy Block", "Select a block to copy.")
            return
        
        block = blocks[0]
        new_name = self.__get_new_name(
            "Copy Block", "New block name:",
            f"{block.model.name}_copy"
        )
        if not new_name:
            return
        
        # Check for unique name
        if self._block_name_exists(new_name):
            QMessageBox.warning(self, "Error", f"Block name '{new_name}' already exists.")
            return
        
        try:
            # Use controller's copy method which uses model.copy() for deep copy with new IDs
            new_bf = self.controller.copy_block(block)
            new_bf.model.name = new_name
            new_bf.title.setText(new_name)

            if not self._sync_block_added(new_name):
                self.controller.delete_block(new_bf)
                return
            # Sync with object model
            for bf_item in self.controller.blocks.values():
                if bf_item.model.name not in self.netlist_project.blocks:
                    try:
                        self.netlist_project.add_block(bf_item.model.name)
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to add block to model: {e}")
            
            self.refresh_objects_list()
            for i in range(self.ui.objects_list.count()):
                if self.ui.objects_list.item(i).text() == new_name:
                    self.ui.objects_list.setCurrentRow(i)
                    self._show_block_by_index(i)
                    break
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to copy block: {e}")
        self._save_version(f"Copy block '{block.model.name}' to '{new_name}'")

    def rename_block(self):
        """Rename the selected block in both models."""
        selected = list(self.scene.selectedItems())
        blocks = [it for it in selected if isinstance(it, BlockFrame)]
        if not blocks:
            QMessageBox.information(self, "Rename Block", "Select a block to rename.")
            return
        block = blocks[0]
        new_name = self.__get_new_name(
            "Rename Block", "New name:", block.model.name
        )
        if new_name:
            # Check for unique name (excluding current block)
            if self._block_name_exists(new_name, exclude_id=block.model.id):
                QMessageBox.warning(self, "Error", f"Block name '{new_name}' already exists.")
                return
            
            try:
                old_name = block.model.name
                if not self._sync_block_renamed(old_name, new_name):
                    return
                block.model.name = new_name
                block.title.setText(new_name)
                self.refresh_objects_list()
                self._save_version(f"Rename block '{old_name}' to '{new_name}'")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to rename block: {e}")

    def add_instance(self):
        """Add a new instance to the current block."""
        self._deactivate_mode()
        if len(self.controller.blocks) < 2:
            QMessageBox.information(self, "Info", "Need at least two blocks.")
            return
        names = [bf.model.name for bf in self.controller.blocks.values()]
        child_name, ok = QInputDialog.getItem(self, "Choose block to insert",
                                              "Block:", names, 0, False)
        if not ok:
            return
        parent_name, ok = QInputDialog.getItem(self, "Choose parent block",
                                               "Parent:", names, 0, False)
        if not ok:
            return
        if child_name == parent_name:
            QMessageBox.warning(self, "Error", "Cannot insert block into itself.")
            return
        child_frame = next(bf for bf in self.controller.blocks.values() if
                           bf.model.name == child_name)
        parent_frame = next(bf for bf in self.controller.blocks.values() if
                            bf.model.name == parent_name)
        QMessageBox.information(self, "Place",
                                "Click inside parent block to place instance.")

        def handler(ev):
            pos = self.view.mapToScene(ev.position().toPoint())
            if parent_frame.mapRectToScene(parent_frame.rect()).contains(pos):
                local = parent_frame.mapFromScene(pos)
                try:
                    inst_item = parent_frame.add_instance(child_frame, local)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to add instance: {e}")
                    self.view.viewport().removeEventFilter(filter_obj)
                    return True
                if not self._sync_instance_added(parent_name, inst_item.model.name, child_frame.model.name):
                    self.controller.delete_instance(inst_item)
                    self.view.viewport().removeEventFilter(filter_obj)
                    return True
                self._save_version(f"Add instance '{inst_item.model.name}' to '{parent_name}'")
                self.refresh_objects_list()
                self.view.viewport().removeEventFilter(filter_obj)
                return True
            return False

        class OneShot(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == 2:
                    return handler(ev)
                return False

        filter_obj = OneShot()
        self.view.viewport().installEventFilter(filter_obj)

    def delete_instance(self):
        """Delete the selected instance."""
        selected = list(self.scene.selectedItems())
        instances = [it for it in selected if isinstance(it, InstanceItem)]
        if not instances:
            QMessageBox.information(
                self, "Delete Instance", "Select an instance to delete."
            )
            return
        for inst in instances:
            parent_block = inst.parentItem()
            if isinstance(parent_block, BlockFrame):
                block_name = parent_block.model.name
                if not self._sync_instance_removed(block_name, inst.model.name):
                    continue
            self._save_version(f"Delete instance '{inst.model.name}'")
            self.controller.delete_instance(inst)

    def copy_instance(self):
        """Copy the selected instance with a new name."""
        selected = list(self.scene.selectedItems())
        instances = [it for it in selected if isinstance(it, InstanceItem)]
        if not instances:
            QMessageBox.information(self, "Copy Instance", "Select an instance to copy.")
            return
        
        inst = instances[0]
        parent_block = inst.parentItem()
        
        if not isinstance(parent_block, BlockFrame):
            QMessageBox.warning(self, "Error", "Instance parent is not a BlockFrame.")
            return
        
        new_name = self.__get_new_name(
            "Copy Instance", "New instance name:",
            f"{inst.model.name}_copy"
        )
        if not new_name:
            return
        
        # Check for unique name within parent block
        if self._instance_name_exists_in_block(parent_block, new_name):
            QMessageBox.warning(self, "Error", f"Instance name '{new_name}' already exists in this block.")
            return
        
        try:
            # Use controller's copy method which uses model.copy() for deep copy with new IDs
            new_inst_item = self.controller.copy_instance(inst, parent_block)
            new_inst_item.model.name = new_name
            new_inst_item.title.setText(new_name)
            if not self._sync_instance_added(parent_block.model.name, new_name, inst.model.block_name):
                self.controller.delete_instance(new_inst_item)
                return
            self._save_version(f"Copy instance '{inst.model.name}' to '{new_name}'")
            self.refresh_objects_list()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to copy instance: {e}")

    def rename_instance(self):
        """Rename the selected instance in both models."""
        selected = list(self.scene.selectedItems())
        instances = [it for it in selected if isinstance(it, InstanceItem)]
        if not instances:
            QMessageBox.information(
                self, "Rename Instance", "Select an instance to rename."
            )
            return
        inst = instances[0]
        new_name = self.__get_new_name(
            "Rename Instance", "New name:", inst.model.name
        )
        if new_name:
            # Get parent block
            parent_block = inst.parentItem()
            if not isinstance(parent_block, BlockFrame):
                QMessageBox.warning(self, "Error", "Instance parent is not a BlockFrame.")
                return
            
            # Check for unique name within parent block (excluding current instance)
            if self._instance_name_exists_in_block(parent_block, new_name, exclude_id=inst.model.id):
                QMessageBox.warning(self, "Error", f"Instance name '{new_name}' already exists in this block.")
                return
            
            try:
                # Update object model
                block_name = parent_block.model.name
                old_name = inst.model.name
                if not self._sync_instance_renamed(block_name, old_name, new_name):
                    return
                self._save_version(f"Rename instance '{old_name}' to '{new_name}'")
                inst.model.name = new_name
                inst.title.setText(new_name)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to rename instance: {e}")

    def add_pin(self):
        """Add a new pin to the selected object."""
        self._deactivate_mode()
        QMessageBox.information(self, "Add Pin",
                                "Click inside the visible block to add a pin (copied into its instances).")

        def handler(ev):
            pos = self.view.mapToScene(ev.position().toPoint())
            for bf in self.controller.blocks.values():
                if bf.isVisible() and bf.mapRectToScene(bf.rect()).contains(pos):
                    self._controller_add_block_pin_at_point(bf, pos)
                    self.view.viewport().removeEventFilter(filter_obj)
                    return True
            return False

        class OneShot(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == 2:
                    return handler(ev)
                return False

        filter_obj = OneShot()
        self.view.viewport().installEventFilter(filter_obj)

    def _controller_add_block_pin_at_point(self, block_frame: BlockFrame, scene_pos: QPointF):
        """Add block pin at specific point."""
        local = block_frame.mapFromScene(scene_pos)
        rect = block_frame.rect()
        lx = min(max(local.x(), 0.0), rect.width())
        ly = min(max(local.y(), 0.0), rect.height())
        left = lx
        right = rect.width() - lx
        top = ly
        bottom = rect.height() - ly
        m = min(left, right, top, bottom)
        if m == left:
            nx, ny = 0.0, ly
        elif m == right:
            nx, ny = rect.width(), ly
        elif m == top:
            nx, ny = lx, 0.0
        else:
            nx, ny = lx, rect.height()
        relx = nx / rect.width() if rect.width() else 0.0
        rely = ny / rect.height() if rect.height() else 0.0
        pm = block_frame.add_block_pin(name=None, relx=relx, rely=rely)
        block_name = block_frame.model.name
        if not self._sync_pin_added(block_name, pm.name):
            try:
                self.controller.delete_block_pin(pm)
            except Exception:
                pass
            return
        self._save_version(f"Add pin '{pm.name}' to block '{block_name}'")
        self.controller.show_only_block(self._current_block_id)

    def delete_pin(self):
        """Delete the selected pin from both models."""
        selected = list(self.scene.selectedItems())
        ports = [it for it in selected if isinstance(it, PortItem)]
        if not ports:
            QMessageBox.information(self, "Delete Pin", "Select a pin to delete.")
            return
        for p in ports:
            if p.owner_id and p.owner_id.startswith("block:"):
                block_id = p.owner_id.split(":", 1)[1]
                block_frame = self.controller.blocks.get(block_id)
                if block_frame:
                    block_name = block_frame.model.name
                    pin_name = p.model.name
                    # Remove from object model
                    if block_name in self.netlist_project.blocks:
                        if not self._sync_pin_removed(block_name, pin_name):
                            continue
                self._save_version(f"Delete pin '{pin_name}' from block '{block_name}'")
                self.controller.delete_block_pin(p)
            else:
                QMessageBox.information(
                    self, "Delete Pin", "Only block-level pins can be deleted."
                )

    def __get_new_name(self, title: str, label: str, current_name: str):
        """Helper to get a new name via input dialog."""
        new_name, ok = QInputDialog.getText(
            self, title, label, text=current_name
        )
        if ok and new_name:
            return new_name
        return None
    
    def rename_pin(self):
        selected = self.scene.selectedItems()
        pins = [element for element in selected if isinstance(element, PortItem)]
        
        if not pins:
            QMessageBox.information(self, "Rename Pin", "Select a pin to rename.")
            return
        
        pin = pins[0]
        
        if not pin.owner_id.startswith("block:"):
            QMessageBox.information(self, "Rename Pin", "Only block-level pins can be renamed.")
            return
        
        new_name = self.__get_new_name("Rename Pin", "New name:", pin.model.name)
        
        if new_name is None:
            return

        if not pin.owner_id or not pin.owner_id.startswith("block:"):
            return

        block_id = pin.owner_id.split(":", 1)[1]
        block_frame = self.controller.blocks.get(block_id)

        if not block_frame:
            return

        block_name = block_frame.model.name
        old_name = pin.model.name

        if not self._sync_pin_renamed(block_name, old_name, new_name):
            return

        pin.model.name = new_name
        pin.label.setText(new_name)

        for instance in self.controller.get_instances(block_name):
            pin = instance.port_items[old_name]
            pin.model.name = new_name
            pin.label.setText(new_name)

        self._save_version(f"Rename pin '{old_name}' to '{new_name}'")

    def add_net(self):
        """Add a new net connection (wire)."""
        if self.active_mode == 'wire':
            self._deactivate_mode()
            return

        self._deactivate_mode()
        self.active_mode = 'wire'
        self.controller.set_add_wire_mode(True)

        def handler(ev):
            if ev.button() != Qt.MouseButton.LeftButton:
                return False

            pos = self.view.mapToScene(ev.position().toPoint())
            items = self.scene.items(pos)

            item = None
            for it in items:
                if isinstance(it, (PortItem, JunctionItem)):
                    item = it
                    break

            if item is None:
                return False

            if self.controller.temp_wire_start is None:
                # Проверка: нельзя начинать wire с уже подключенного пина
                block_frame = self.controller.blocks.get(self._current_block_id)
                if block_frame and isinstance(item, PortItem):
                    if self._is_pin_already_connected(item, block_frame):
                        QMessageBox.warning(None, "Error", "Cannot connect to a pin that is already connected to a net.")
                        self._deactivate_mode()
                        return True
                self.controller.start_wire(item)
                return True
            else:
                # Проверка: нельзя завершать wire на уже подключенном пине
                block_frame = self.controller.blocks.get(self._current_block_id)
                if block_frame and isinstance(item, PortItem):
                    if self._is_pin_already_connected(item, block_frame):
                        QMessageBox.warning(None, "Error", "Cannot connect to a pin that is already connected to a net.")
                        self.controller._restore_pin_color(self.controller.temp_wire_start)
                        self.controller.temp_wire_start = None
                        self._deactivate_mode()
                        return True
                
                new_wire = self.controller.finish_wire(item)
                block_frame = self.controller.blocks.get(self._current_block_id)
                if isinstance(new_wire, WireItem) and block_frame:
                    block_name = block_frame.model.name
                    wire_model = getattr(new_wire, "model", None)
                    net_name = getattr(wire_model, "name", None) or self._generate_net_name(block_frame)

                    def get_type_and_id_and_name(connection):
                        # lambda connection: (*(lambda x: ('inst' if ':' not in x else x.split(':')[0], x[0] if ':' not in x else x.split(':')[1]))(connection[0]), connection[1])
                        _type = None
                        _id = None
                        if ':' not in connection[0]:
                            _type = 'inst'
                            _id = connection[0]
                        else:
                            splitted = connection[0].split(':')
                            _type = splitted[0]
                            _id = splitted[1]
                        name = connection[1]
                        return _type, _id, name

                    start_type, start_id, start_name = get_type_and_id_and_name(wire_model.start)
                    end_type, end_id, end_name = get_type_and_id_and_name(wire_model.end)

                    functions = {
                        'inst': self.controller.get_instance_by_id,
                        'block': self.controller.get_block_by_id
                    }

                    if start_type == 'j' and end_type in ('block', 'inst'):
                        wire_id = self.controller.current_junction_items[
                            start_id].model.wire_id
                        wire_name = self.controller.current_wire_items[
                            wire_id].model.name

                        pin_block_name = functions[end_type](end_id).name

                        if end_type == 'block':
                            pin = self.netlist_project.blocks[pin_block_name].interface_pins[end_name]
                        else:
                            name = functions[end_type](end_id).block_name
                            for instance in self.netlist_project.blocks_instances[name]:
                                if instance.name == pin_block_name:
                                    pin = instance.interface_pins[end_name]

                        self.netlist_project.blocks[block_name].nets[wire_name].connect_pin(pin)

                        new_wire.model.name = None
                    elif start_type in ('block', 'inst') and end_type == 'j':
                        wire_id = self.controller.current_junction_items[
                            end_id].model.wire_id
                        wire_name = self.controller.current_wire_items[
                            wire_id].model.name

                        pin_block_name = functions[start_type](start_id).name

                        if end_type == 'block':
                            pin = self.netlist_project.blocks[pin_block_name].interface_pins[start_name]
                        else:
                            name = functions[start_type](start_id).block_name
                            for instance in self.netlist_project.blocks_instances[name]:
                                if instance.name == pin_block_name:
                                    pin = instance.interface_pins[start_name]

                        self.netlist_project.blocks[block_name].nets[
                            wire_name].connect_pin(pin)

                        new_wire.model.name = None
                    elif start_type == 'j' and end_type == 'j':
                        start_wire = self.netlist_project.blocks[block_name].nets[
                            self.controller.current_wire_items[
                                self.controller.current_junction_items[
                                    start_id
                                ].model.wire_id
                            ].model.name
                        ]

                        end_wire_item = self.controller.current_wire_items[
                                self.controller.current_junction_items[
                                    end_id
                                ].model.wire_id
                            ]

                        end_wire = self.netlist_project.blocks[block_name].nets[
                            end_wire_item.model.name
                        ]

                        end_wire_pins = end_wire.pins
                        for pin in end_wire_pins:
                            start_wire.connect_pin(end_wire_pins[pin])
                        self.netlist_project.remove_net_from_block(block_name, end_wire.name)

                        end_wire_item.label.setText('')
                        end_wire_item.model.name = None

                        new_wire.model.name = None
                    elif start_type in ('block', 'inst') and end_type in ('block', 'inst'):
                        start_func = functions[start_type]
                        start_block_name = start_func(start_id).name

                        end_func = functions[end_type]
                        end_block_name = end_func(end_id).name

                        if start_type == 'block':
                            start_pin = self.netlist_project.blocks[
                                start_block_name].interface_pins[start_name]
                        else:
                            model_name = start_func(start_id).block_name
                            for instance in \
                            self.netlist_project.blocks_instances[model_name]:
                                if instance.name == start_block_name:
                                    start_pin = instance.interface_pins[start_name]

                        if end_type == 'block':
                            end_pin = self.netlist_project.blocks[
                                end_block_name].interface_pins[end_name]
                        else:
                            model_name = end_func(end_id).block_name
                            for instance in \
                                    self.netlist_project.blocks_instances[
                                        model_name]:
                                if instance.name == end_block_name:
                                    end_pin = instance.interface_pins[
                                        end_name]

                        if wire_model and not getattr(wire_model, "name", None):
                            wire_model.name = net_name
                        if hasattr(new_wire, "update_label"):
                            new_wire.update_label(net_name)
                        if not self._sync_net_added(block_name, net_name, [start_pin, end_pin]):
                            self.controller.delete_wire(new_wire)
                            self._deactivate_mode()
                            return True
                        self._save_version(f"Add net '{net_name}' in block '{block_name}'")
                self._deactivate_mode()
                return True

        class WireModeFilter(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == 2:
                    return handler(ev)
                return False

        self.current_filter = WireModeFilter()
        self.view.viewport().installEventFilter(self.current_filter)
    
    def _is_pin_already_connected(self, port_item: PortItem, block_frame: BlockFrame) -> bool:
        """Проверить, подключен ли пин уже к какому-либо wire."""
        # Проверяем все wires в текущем блоке
        for wire_model in block_frame.model.wires:
            # Проверяем start
            if wire_model.start and len(wire_model.start) >= 2:
                start_owner = wire_model.start[0]
                start_pin = wire_model.start[1]
                if start_owner == port_item.owner_id and start_pin == port_item.model.name:
                    return True
            
            # Проверяем end
            if wire_model.end and len(wire_model.end) >= 2:
                end_owner = wire_model.end[0]
                end_pin = wire_model.end[1]
                if end_owner == port_item.owner_id and end_pin == port_item.model.name:
                    return True
        
        return False

    def delete_net(self):
        """Delete the selected net (wire)."""
        selected = list(self.scene.selectedItems())
        wires = [it for it in selected if isinstance(it, WireItem)]
        if not wires:
            QMessageBox.information(self, "Delete Wire", "Select a wire to delete.")
            return

        wire = wires[0]
        block_frame = self.controller.blocks.get(self._current_block_id)

        connected_wires = [
            self.controller.current_wire_items[wire_id]
            for wire_id in self._find_connected_wires(wire.model.id, block_frame)
        ]
        connected_wires.append(wire)

        wire_with_name = None
        for _wire in connected_wires:
            if _wire.model.name is not None:
                wire_with_name = _wire

        net_name = wire_with_name.model.name
        self._sync_net_removed(block_frame.model.name, net_name)

        for wire in connected_wires:
            self.controller.delete_wire(wire)
        
        self._save_version(f"Delete net '{net_name}'")

    def rename_net(self):
        """Rename the selected net."""
        selected = list(self.scene.selectedItems())
        wires = [it for it in selected if isinstance(it, WireItem)]
        if not wires:
            QMessageBox.information(self, "Rename Net", "Select a wire to rename.")
            return
        wire = wires[0]
        block_frame = self.controller.blocks.get(self._current_block_id)
        if not block_frame:
            QMessageBox.warning(self, "Error", "No block context for selected wire.")
            return

        connected_wires = [
            self.controller.current_wire_items[wire_id]
            for wire_id in self._find_connected_wires(wire.model.id, block_frame)
        ]
        connected_wires.append(wire)

        wire_with_name = None
        for _wire in connected_wires:
            if _wire.model.name is not None:
                wire_with_name = _wire

        old_name = wire_with_name.model.name

        junctions = [
            junction.model.wire_id == wire_with_name.model.id
            for junction in self.controller.current_junction_items.values()
        ]

        if not old_name and len(junctions) == 0:
            QMessageBox.warning(self, "Error", "Selected wire has no name to rename.")
            return

        new_name = self.__get_new_name("Rename Net", "New name:", old_name)
        if not new_name or new_name == old_name:
            return
        
        if self._net_name_exists(block_frame, new_name, exclude=old_name):
            QMessageBox.warning(self, "Error", f"Net name '{new_name}' already exists in this block.")
            return

        block_name = block_frame.model.name

        # Переименовать в объектной модели
        if not self._sync_net_renamed(block_name, old_name, new_name):
            return

        wire_with_name.model.name = new_name
        wire_with_name.update_label(new_name)
    
    def _find_connected_wires(self, wire_id: str, block_frame: BlockFrame) -> set:
        """Найти все wire, связанные с данным через junctions (рекурсивно).
        
        Проходит по графу: wire -> junction -> wire -> junction -> ...
        и собирает все достижимые wire.
        """
        visited_wires = set()
        visited_junctions = set()
        to_visit_wires = {wire_id}
        
        while to_visit_wires:
            current_wire_id = to_visit_wires.pop()
            if current_wire_id in visited_wires:
                continue
            visited_wires.add(current_wire_id)
            
            # Найти все junctions, связанные с текущим wire:
            # 1. Junction, на котором этот wire является host (jm.wire_id == current_wire_id)
            # 2. Junctions, к которым подключен этот wire (start/end ссылаются на junction)
            
            connected_junctions = set()
            
            # Host junctions (где wire является host-проводом)
            for jm in block_frame.model.junctions:
                if jm.wire_id == current_wire_id and jm.id not in visited_junctions:
                    connected_junctions.add(jm.id)
            
            # Junctions, к которым подключен wire (по start/end)
            for wm in block_frame.model.wires:
                if wm.id == current_wire_id:
                    # Проверяем start
                    if wm.start and len(wm.start) > 0 and wm.start[0].startswith("j:"):
                        jid = wm.start[0].split(":", 1)[1]
                        if jid not in visited_junctions:
                            connected_junctions.add(jid)
                    # Проверяем end
                    if wm.end and len(wm.end) > 0 and wm.end[0].startswith("j:"):
                        jid = wm.end[0].split(":", 1)[1]
                        if jid not in visited_junctions:
                            connected_junctions.add(jid)
                    break
            
            # Для каждого найденного junction ищем все подключенные к нему wires
            for junction_id in connected_junctions:
                if junction_id in visited_junctions:
                    continue
                visited_junctions.add(junction_id)
                
                # Найти все wires, подключенные к этому junction
                for wm in block_frame.model.wires:
                    if wm.id in visited_wires:
                        continue
                    
                    # Wire подключен к junction, если:
                    # - его start или end ссылаются на junction
                    is_connected = False
                    if wm.start and len(wm.start) > 0 and wm.start[0] == f"j:{junction_id}":
                        is_connected = True
                    if wm.end and len(wm.end) > 0 and wm.end[0] == f"j:{junction_id}":
                        is_connected = True
                    
                    if is_connected:
                        to_visit_wires.add(wm.id)
                
                # Также добавляем host wire этого junction
                for jm in block_frame.model.junctions:
                    if jm.id == junction_id and jm.wire_id and jm.wire_id not in visited_wires:
                        to_visit_wires.add(jm.wire_id)
        
        # Убираем исходный wire из результата (т.к. он уже был обработан)
        visited_wires.discard(wire_id)
        return visited_wires

    def add_junction(self):
        """Add a new junction on an existing wire."""
        if self.active_mode == 'junction':
            self._deactivate_mode()
            return

        self._deactivate_mode()
        self.active_mode = 'junction'
        self.controller.set_add_junction_mode(True)

        QMessageBox.information(self, "Add Junction",
                                "Click on an existing wire to add a junction. Click 'Add Junction' again to cancel.")

        def handler(ev):
            if ev.button() != Qt.MouseButton.LeftButton:
                return False

            pos = self.view.mapToScene(ev.position().toPoint())
            items = self.scene.items(pos)

            for it in items:
                if isinstance(it, JunctionItem):
                    return False

            wire_item = None
            for it in items:
                if isinstance(it, WireItem):
                    wire_item = it
                    break

            if wire_item is not None:
                self.controller.create_junction_at(pos, wire_item)
                self._save_version("Add junction")
                self._deactivate_mode()
                return True

            return False

        class JunctionModeFilter(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == 2:
                    result = handler(ev)
                    if result:
                        ev.accept()
                        return True
                    return False
                return False

        self.current_filter = JunctionModeFilter()
        self.view.viewport().installEventFilter(self.current_filter)

    def delete_junction(self):
        """Delete the selected junction."""
        selected = list(self.scene.selectedItems())
        junctions = [it for it in selected if isinstance(it, JunctionItem)]
        if not junctions:
            QMessageBox.information(
                self, "Delete Junction", "Select a junction to delete."
            )
            return
        for j in junctions:
            self.controller.delete_junction(j)
            self._save_version("Delete junction")

    def undo(self):
        """Undo the last action."""
        if self.version_manager.undo():
            self._restore_from_version()
            QMessageBox.information(self, "Undo", "Action undone successfully.")
        else:
            QMessageBox.information(self, "Undo", "Nothing to undo.")

    def redo(self):
        """Redo the last undone action."""
        if self.version_manager.redo():
            self._restore_from_version()
            QMessageBox.information(self, "Redo", "Action redone successfully.")
        else:
            QMessageBox.information(self, "Redo", "Nothing to redo.")

    def _block_name_exists(self, name: str, exclude_id: str = None) -> bool:
        """Check if a block name already exists."""
        for block_id, block_frame in self.controller.blocks.items():
            if exclude_id and block_id == exclude_id:
                continue
            if block_frame.model.name == name:
                return True
        return False

    def _instance_name_exists_in_block(self, block_frame: BlockFrame, name: str, exclude_id: str = None) -> bool:
        """Check if an instance name already exists in a given block."""
        for inst in block_frame.model.instances:
            if exclude_id and inst.id == exclude_id:
                continue
            if inst.name == name:
                return True
        return False

    def _sync_block_added(self, block_name: str) -> bool:
        if block_name in self.netlist_project.blocks:
            return True
        try:
            self.netlist_project.add_block(block_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add block to model: {e}")
            return False

    def _sync_block_removed(self, block_name: str) -> bool:
        if block_name not in self.netlist_project.blocks:
            return True
        try:
            self.netlist_project.remove_block(block_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete block from model: {e}")
            return False

    def _sync_block_renamed(self, old_name: str, new_name: str) -> bool:
        if old_name == new_name:
            return True
        try:
            self.netlist_project.rename_block(old_name, new_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to rename block: {e}")
            return False

    def _sync_instance_added(self, parent_block: str, instance_name: str, source_block: str) -> bool:
        if parent_block not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Parent block '{parent_block}' not found in model.")
            return False
        try:
            self.netlist_project.add_instance_to_block(parent_block, instance_name, source_block)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add instance to model: {e}")
            return False

    def _sync_instance_removed(self, parent_block: str, instance_name: str) -> bool:
        if parent_block not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Parent block '{parent_block}' not found in model.")
            return False
        try:
            self.netlist_project.remove_instance_from_block(parent_block, instance_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete instance: {e}")
            return False

    def _sync_instance_renamed(self, parent_block: str, old_name: str, new_name: str) -> bool:
        if parent_block not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Parent block '{parent_block}' not found in model.")
            return False
        try:
            self.netlist_project.rename_instance_in_block(parent_block, old_name, new_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to rename instance: {e}")
            return False

    def _sync_pin_added(self, block_name: str, pin_name: str) -> bool:
        if block_name not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Block '{block_name}' not found in model.")
            return False
        try:
            self.netlist_project.add_pin_to_block(block_name, pin_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add pin to model: {e}")
            return False

    def _sync_pin_removed(self, block_name: str, pin_name: str) -> bool:
        if block_name not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Block '{block_name}' not found in model.")
            return False
        try:
            self.netlist_project.remove_pin_from_block(block_name, pin_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete pin: {e}")
            return False

    def _sync_pin_renamed(self, block_name: str, old_name: str, new_name: str) -> bool:
        if block_name not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Block '{block_name}' not found in model.")
            return False
        try:
            self.netlist_project.rename_pin_in_block(block_name, old_name, new_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to rename pin: {e}")
            return False

    def _sync_net_added(self, block_name: str, net_name: str, pins: list) -> bool:
        if block_name not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Block '{block_name}' not found in model.")
            return False
        try:
            net = self.netlist_project.add_net_to_block(block_name, net_name)
            for pin in pins:
                net.connect_pin(pin)
                
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add net to model: {e}")
            return False

    def _sync_net_removed(self, block_name: str, net_name: str) -> bool:
        if block_name not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Block '{block_name}' not found in model.")
            return False
        try:
            self.netlist_project.remove_net_from_block(block_name, net_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete net: {e}")
            return False

    def _sync_net_renamed(self, block_name: str, old_name: str, new_name: str) -> bool:
        if block_name not in self.netlist_project.blocks:
            QMessageBox.warning(self, "Error", f"Block '{block_name}' not found in model.")
            return False
        try:
            self.netlist_project.rename_net_in_block(block_name, old_name, new_name)
            self._log_object_model()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to rename net: {e}")
            return False
        
        
    def _generate_net_name(self, block_frame: BlockFrame) -> str:
        block_model = getattr(block_frame, "model", None)
        block_name = getattr(block_model, "name", None)
        used = set()
        if block_name and block_name in self.netlist_project.blocks:
            used.update(self.netlist_project.blocks[block_name].nets.keys())
        model_nets = getattr(block_model, "nets", None)
        if isinstance(model_nets, dict):
            used.update(model_nets.keys())
        idx = 1
        while True:
            candidate = f"net_{idx}"
            if candidate not in used:
                return candidate
            idx += 1

    def _net_name_exists(self, block_frame: BlockFrame, name: str, exclude: str = None) -> bool:
        block_model = getattr(block_frame, "model", None)
        block_name = getattr(block_model, "name", None)
        if not block_name or block_name not in self.netlist_project.blocks:
            return False
        nets = self.netlist_project.blocks[block_name].nets.keys()
        return any(net == name and net != exclude for net in nets)
    
    def _log_object_model(self):
        blocks_snapshot = []
        for name, block in self.netlist_project.blocks.items():
            instance_names = list(block.instances.keys())
            pin_names = list(block.interface_pins.keys())
            net_infos = []
            for net_name, net in block.nets.items():
                pin_details = []
                for pin_name, pin_ref in net.pins.items():
                    owner = getattr(pin_ref.ref_parent, "name", None)
                    pin_details.append(f"{pin_name}@{owner or 'block'}")
                net_infos.append(f"{net_name}({pin_details})")
            blocks_snapshot.append(
                f"{name}: instances={instance_names}, pins={pin_names}, nets={net_infos}"
            )
        if not blocks_snapshot:
            print("Object model:\n<empty>")
        else:
            print("Object model:\n" + "\n".join(blocks_snapshot))

