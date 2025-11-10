import sys
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView,
    QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsSimpleTextItem, QInputDialog, QMessageBox, QPushButton, QComboBox
)
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QPainter
from PyQt6.QtCore import Qt, QPointF, QObject, QRectF

try:
    from PyQt6.QtGui import QPainterPathStroker

    STROKER_AVAILABLE = True
except Exception:
    STROKER_AVAILABLE = False


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class ObjModelItem:
    id: int


@dataclass
class PortModel:
    name: str
    x: float
    y: float

    def copy(self) -> "PortModel":
        """Create a copy of this port."""
        return PortModel(name=self.name, x=self.x, y=self.y)


@dataclass
class InstanceModel:
    id: str = field(default_factory=new_id)
    name: str = "Instance"
    block_name: str = ""
    x: float = 0.0
    y: float = 0.0
    w: float = 120.0
    h: float = 60.0
    ports: List[PortModel] = field(default_factory=list)

    obj_mod_el_id: int = None

    def to_dict(self):
        return {"id": self.id, "name": self.name, "block_name": self.block_name,
                "x": self.x, "y": self.y, "w": self.w, "h": self.h,
                "ports": [asdict(p) for p in self.ports]}

    @staticmethod
    def from_dict(d):
        ports = [PortModel(p["name"], p["x"], p["y"]) for p in
                 d.get("ports", [])]
        return InstanceModel(id=d.get("id", new_id()),
                             name=d.get("name", "Instance"),
                             block_name=d.get("block_name", ""), x=d.get("x", 0.0),
                             y=d.get("y", 0.0),
                             w=d.get("w", 120.0), h=d.get("h", 60.0),
                             ports=ports)

    def update_obj_mod():
        pass

    def copy(self) -> "InstanceModel":
        """Create a deep copy of this instance with new ID."""
        from copy import deepcopy
        new_inst = deepcopy(self)
        new_inst.id = new_id()
        new_inst.ports = [p.copy() for p in self.ports]
        return new_inst


@dataclass
class WireModel:
    id: str = field(default_factory=new_id)
    name: str = ""
    start: Tuple[str, str] = field(default_factory=tuple)  # (owner_id, port_name) or ("j:<id>", "")
    end: Tuple[str, str] = field(default_factory=tuple)

    obj_mod_el_id: int = None

    def to_dict(self):
        return {"id": self.id, "name": self.name, "start": list(self.start), "end": list(self.end)}

    @staticmethod
    def from_dict(d):
        return WireModel(
            id=d.get("id", new_id()),
            name=d.get("name", ""),
            start=tuple(d.get("start", [])),
            end=tuple(d.get("end", [])),
        )

    def copy(self, instance_id_map: Dict[str, str] = None, block_id_map: Dict[str, str] = None) -> "WireModel":
        """Create a copy of this wire with new ID and updated references.
        
        Args:
            instance_id_map: Dictionary mapping old instance IDs to new instance IDs.
            block_id_map: Dictionary mapping old block IDs to new block IDs.
        """
        new_start = self.start
        new_end = self.end
        
        # Update references if mapping is provided
        if instance_id_map:
            if self.start and self.start[0] in instance_id_map:
                new_start = (instance_id_map[self.start[0]], self.start[1])
            if self.end and self.end[0] in instance_id_map:
                new_end = (instance_id_map[self.end[0]], self.end[1])
        
        # Update block-level pin references
        if block_id_map:
            if self.start and self.start[0].startswith("block:"):
                old_block_id = self.start[0].split(":", 1)[1]
                if old_block_id in block_id_map:
                    new_start = (f"block:{block_id_map[old_block_id]}", self.start[1])
            if self.end and self.end[0].startswith("block:"):
                old_block_id = self.end[0].split(":", 1)[1]
                if old_block_id in block_id_map:
                    new_end = (f"block:{block_id_map[old_block_id]}", self.end[1])
        
        new_wire = WireModel(
            id=new_id(),
            name=self.name,
            start=new_start,
            end=new_end
        )
        return new_wire


@dataclass
class JunctionModel:
    id: str = field(default_factory=new_id)
    x: float = 0.0
    y: float = 0.0
    wire_id: Optional[str] = None  # host wire where junction was created

    obj_mod_el_id: int = None

    def to_dict(self):
        return {"id": self.id, "x": self.x, "y": self.y,
                "wire_id": self.wire_id}

    @staticmethod
    def from_dict(d):
        return JunctionModel(id=d.get("id", new_id()), x=d.get("x", 0.0),
                             y=d.get("y", 0.0), wire_id=d.get("wire_id"))

    def update_obj_mod():
        pass

    def copy(self, wire_id_map: Dict[str, str] = None) -> "JunctionModel":
        """Create a copy of this junction with new ID and updated wire reference.
        
        Args:
            wire_id_map: Dictionary mapping old wire IDs to new wire IDs.
                        If provided, updates the junction's wire_id reference.
        """
        new_wire_id = self.wire_id
        
        # Update wire reference if mapping is provided
        if wire_id_map and self.wire_id in wire_id_map:
            new_wire_id = wire_id_map[self.wire_id]
        
        new_junc = JunctionModel(
            id=new_id(),
            x=self.x,
            y=self.y,
            wire_id=new_wire_id
        )
        return new_junc


@dataclass
class BlockModel:
    id: str = field(default_factory=new_id)
    name: str = "Block"
    x: float = 0.0
    y: float = 0.0
    w: float = 360.0
    h: float = 220.0
    ports: List[PortModel] = field(default_factory=list)
    instances: List[InstanceModel] = field(default_factory=list)
    wires: List[WireModel] = field(default_factory=list)
    junctions: List[JunctionModel] = field(default_factory=list)

    obj_mod_el_id: int = None

    def to_dict(self):
        return {"id": self.id, "name": self.name, "x": self.x, "y": self.y,
                "w": self.w, "h": self.h,
                "ports": [asdict(p) for p in self.ports],
                "instances": [inst.to_dict() for inst in self.instances],
                "wires": [w.to_dict() for w in self.wires],
                "junctions": [j.to_dict() for j in self.junctions]}

    @staticmethod
    def from_dict(d):
        ports = [PortModel(p["name"], p["x"], p["y"]) for p in
                 d.get("ports", [])]
        instances = [InstanceModel.from_dict(i) for i in
                     d.get("instances", [])]
        wires = [WireModel.from_dict(w) for w in d.get("wires", [])]
        junctions = [JunctionModel.from_dict(j) for j in
                     d.get("junctions", [])]
        return BlockModel(id=d.get("id", new_id()),
                          name=d.get("name", "Block"),
                          x=d.get("x", 0.0), y=d.get("y", 0.0),
                          w=d.get("w", 360.0), h=d.get("h", 220.0),
                          ports=ports, instances=instances, wires=wires,
                          junctions=junctions)

    def update_obj_mod():
        pass

    def copy(self, offset_x: float = 50, offset_y: float = 50, block_id_map: Dict[str, str] = None) -> "BlockModel":
        """Create a deep copy of this block with new IDs for all contents.
        
        All instances, wires, and junctions get new IDs, and references are updated.
        
        Args:
            offset_x: X offset for the new block position
            offset_y: Y offset for the new block position
            block_id_map: Optional dictionary to track block ID mappings for external references
        """
        # Create mapping from old IDs to new IDs for instances
        instance_id_map = {}
        new_instances = []
        for inst in self.instances:
            new_inst = inst.copy()
            instance_id_map[inst.id] = new_inst.id
            new_instances.append(new_inst)
        
        # Create mapping from old IDs to new IDs for wires
        wire_id_map = {}
        new_wires = []
        
        # If block_id_map provided, add this block's mapping
        local_block_id_map = block_id_map.copy() if block_id_map else {}
        local_block_id_map[self.id] = new_id()
        
        for wire in self.wires:
            new_wire = wire.copy(instance_id_map, local_block_id_map)
            wire_id_map[wire.id] = new_wire.id
            new_wires.append(new_wire)
        
        # Copy junctions with updated wire references
        new_junctions = []
        for junc in self.junctions:
            new_junc = junc.copy(wire_id_map)
            new_junctions.append(new_junc)
        
        new_block = BlockModel(
            id=local_block_id_map[self.id],
            name=self.name,
            x=self.x + offset_x,
            y=self.y + offset_y,
            w=self.w,
            h=self.h,
            ports=[p.copy() for p in self.ports],
            instances=new_instances,
            wires=new_wires,
            junctions=new_junctions
        )
        return new_block


def project_point_to_segment(p: QPointF, a: QPointF, b: QPointF) -> QPointF:
    ax, ay = a.x(), a.y()
    bx, by = b.x(), b.y()
    px, py = p.x(), p.y()
    vx = bx - ax;
    vy = by - ay
    wx = px - ax;
    wy = py - ay
    vlen2 = vx * vx + vy * vy
    if vlen2 == 0:
        return a
    t = (wx * vx + wy * vy) / vlen2
    t = max(0.0, min(1.0, t))
    return QPointF(ax + t * vx, ay + t * vy)


class PortItem(QGraphicsEllipseItem):
    R = 6

    def __init__(self, parent_item, model: PortModel, controller=None,
                 owner_id: Optional[str] = None,
                 color: QColor = QColor("orange")):
        super().__init__(-self.R, -self.R, 2 * self.R, 2 * self.R,
                         parent=parent_item)
        self.model = model
        self.parent_item = parent_item
        self.controller = controller
        self.owner_id = owner_id
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(2)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.label = QGraphicsSimpleTextItem(model.name, self)
        self.label.setBrush(QBrush(Qt.GlobalColor.white))
        self.label.setScale(0.8)
        self.update_from_model()

    def update_from_model(self):
        rect = self.parent_item.rect()
        self.setPos(self.model.x * rect.width(), self.model.y * rect.height())
        self.label.setPos(8, -8)

    def mousePressEvent(self, event):
        if self.controller and self.controller.add_wire_mode:
            if self.controller.temp_wire_start is not None:
                self.controller.finish_wire(self)
            else:
                self.controller.start_wire(self)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        parent = self.parent_item
        rect = parent.rect()
        last_local = parent.mapFromScene(event.lastScenePos())
        cur_local = parent.mapFromScene(event.scenePos())
        delta_local = cur_local - last_local
        new_local = self.pos() + delta_local
        nx = min(max(new_local.x(), 0.0), rect.width())
        ny = min(max(new_local.y(), 0.0), rect.height())
        left = nx;
        right = rect.width() - nx;
        top = ny;
        bottom = rect.height() - ny
        m = min(left, right, top, bottom)
        if m == left:
            nx = 0.0
        elif m == right:
            nx = rect.width()
        elif m == top:
            ny = 0.0
        else:
            ny = rect.height()
        self.setPos(nx, ny)
        self.model.x = nx / rect.width() if rect.width() else 0.0
        self.model.y = ny / rect.height() if rect.height() else 0.0
        if self.controller:
            self.controller.update_wires_for_pin(self)
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()


class InstanceItem(QGraphicsRectItem):
    def __init__(self, model: InstanceModel, controller):
        super().__init__(0.0, 0.0, model.w, model.h)
        self.model = model
        self.controller = controller
        self.setBrush(QBrush(QColor("#2E86C1")))
        self.setPen(QPen(QColor("white"), 2))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setPos(model.x, model.y)
        self.title = QGraphicsSimpleTextItem(model.name, self)
        self.title.setBrush(QBrush(Qt.GlobalColor.white))
        self.title.setPos(5, 4)
        self.port_items: Dict[str, PortItem] = {}
        for p in model.ports:
            if p.name not in self.port_items:
                self.port_items[p.name] = PortItem(self, p,
                                                   controller=controller,
                                                   owner_id=model.id,
                                                   color=QColor("orange"))

    def mouseMoveEvent(self, event):
        parent = self.parentItem()
        if isinstance(parent, BlockFrame):
            last_local = parent.mapFromScene(event.lastScenePos())
            cur_local = parent.mapFromScene(event.scenePos())
            delta_local = cur_local - last_local
            new_local = self.pos() + delta_local
            pr = parent.rect()
            max_x = pr.width() - self.rect().width()
            max_y = pr.height() - self.rect().height()
            nx = min(max(new_local.x(), 0.0), max_x if max_x > 0 else 0.0)
            ny = min(max(new_local.y(), 0.0), max_y if max_y > 0 else 0.0)
            self.setPos(nx, ny)
            self.model.x = nx;
            self.model.y = ny
            self.controller.update_wires_for_instance(self)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.model.x, self.model.y = self.pos().x(), self.pos().y()


class WireItem(QGraphicsPathItem):
    def __init__(self, start_obj: Any, end_obj: Any, model: WireModel):
        super().__init__()
        self.start_obj = start_obj
        self.end_obj = end_obj
        self.model = model
        self.setPen(QPen(QColor("#FFD700"), 2))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        self.label = QGraphicsSimpleTextItem("", self)
        self.label.setBrush(QBrush(Qt.GlobalColor.white))
        self.label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.label.setZValue(2)
        self.update_label(getattr(self.model, "name", "") or "")
        self.update_path()

    def update_path(self):
        s = self.start_obj.scenePos()
        e = self.end_obj.scenePos()
        path = QPainterPath(s)
        mid = (s + e) / 2
        path.cubicTo(mid, mid, e)
        self.setPath(path)
        self._update_label_position()

    def update_label(self, text: Optional[str] = None):
        if text is None:
            text = getattr(self.model, "name", "") or ""
        elif hasattr(self.model, "name"):
            self.model.name = text
        self.label.setText(text)
        self._update_label_position()

    def _update_label_position(self):
        if self.label.text() == "":
            return
        path = self.path()
        if path.isEmpty():
            return
        mid = path.pointAtPercent(0.5)
        rect = self.label.boundingRect()
        self.label.setPos(mid.x() - rect.width() / 2, mid.y() - rect.height() / 2)

    def shape(self):
        p = self.path()
        if STROKER_AVAILABLE:
            stroker = QPainterPathStroker()
            stroker.setWidth(6.0)
            return stroker.createStroke(p)
        return p

    def hoverEnterEvent(self, event):
        self.setPen(QPen(QColor("#FFA500"), 3))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(QPen(QColor("#FFD700"), 2))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if hasattr(self,
                   'controller') and self.controller and self.controller.add_junction_mode:
            event.ignore()
            return
        super().mousePressEvent(event)


class JunctionItem(QGraphicsEllipseItem):
    R = 6

    def __init__(self, model: JunctionModel, controller,
                 attached_wire_id: Optional[str] = None):
        super().__init__(-self.R, -self.R, 2 * self.R, 2 * self.R)
        self.model = model
        self.controller = controller
        self.attached_wire_id = attached_wire_id
        self.setBrush(QBrush(QColor("#FF69B4")))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        # ensure interactivity
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(100)
        self.setAcceptHoverEvents(True)
        self.setPos(model.x, model.y)
        # flag to indicate user dragging: used to avoid automatic reprojection during user drag
        self._dragging = False

    def mousePressEvent(self, event):
        if self.controller and self.controller.add_wire_mode:
            if self.controller.temp_wire_start is not None:
                self.controller.finish_wire(self)
            else:
                self.controller.start_wire(self)
            event.accept()
            return
        # Start dragging
        self._dragging = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # If attached to a wire, move along the wire (projection)
        if self.attached_wire_id and self.attached_wire_id in self.controller.current_wire_items:
            wire_item: WireItem = self.controller.current_wire_items[
                self.attached_wire_id]
            a = wire_item.start_obj.scenePos()
            b = wire_item.end_obj.scenePos()
            cur = event.scenePos()
            proj = project_point_to_segment(cur, a, b)
            self.setPos(proj)
            self.model.x, self.model.y = proj.x(), proj.y()
            # update wire visuals and reproject other junctions on that wire
            self.controller.update_wires_for_junction(self)
            event.accept()
        else:
            # free move fallback
            last = event.lastScenePos()
            cur = event.scenePos()
            delta = cur - last
            self.setPos(self.pos() + delta)
            self.model.x, self.model.y = self.pos().x(), self.pos().y()
            self.controller.update_wires_for_junction(self)
            event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # stop dragging
        self._dragging = False
        self.controller.update_wires_for_junction(self)


class Controller:
    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.blocks: Dict[str, BlockFrame] = {}
        # Visual items for wires and junctions for the currently visible block:
        self.current_wire_items: Dict[str, WireItem] = {}
        self.current_junction_items: Dict[str, JunctionItem] = {}
        self.temp_wire_start: Optional[Any] = None
        self.add_wire_mode = False
        self.add_junction_mode = False
        self._visible_block_id: Optional[str] = None

    def add_block(self, name: str = "Block") -> 'BlockFrame':
        bm = BlockModel(name=name, x=40.0 + len(self.blocks) * 420.0, y=60.0)
        bf = BlockFrame(bm, self)
        self.scene.addItem(bf)
        self.blocks[bm.id] = bf
        bf.setVisible(False)
        return bf

    def propagate_new_pin_to_instances(self, source_block_id: str,
                                       port_model: PortModel):
        for bf in self.blocks.values():
            for inst in bf.model.instances:
                if inst.block_name == self.blocks[source_block_id].model.name:
                    if port_model.name not in {p.name for p in inst.ports}:
                        inst.ports.append(
                            PortModel(port_model.name, port_model.x,
                                      port_model.y))
                    inst_item = bf.instance_items.get(inst.id)
                    if inst_item:
                        if port_model.name not in inst_item.port_items:
                            pm = next((p for p in inst.ports if
                                       p.name == port_model.name), None)
                            if pm:
                                inst_item.port_items[pm.name] = PortItem(
                                    inst_item, pm, controller=self,
                                    owner_id=inst.id, color=QColor("orange"))
                        else:
                            pin_vis = inst_item.port_items[port_model.name]
                            pin_vis.model.x = port_model.x;
                            pin_vis.model.y = port_model.y
                            pin_vis.update_from_model()

    def _collect_wires_connected_to_obj(self, obj: Any) -> List[str]:
        ids = []
        for wid, wv in list(self.current_wire_items.items()):
            if wv.start_obj == obj or wv.end_obj == obj:
                ids.append(wid)
        return ids

    def delete_wire(self, wire_item: WireItem):
        wid = wire_item.model.id
        if wid in self.current_wire_items:
            try:
                self.scene.removeItem(self.current_wire_items[wid])
            except Exception:
                pass
            del self.current_wire_items[wid]
        for bm in self.blocks.values():
            bm.model.wires = [w for w in bm.model.wires if w.id != wid]
        for bm in self.blocks.values():
            for jm in list(bm.model.junctions):
                if jm.wire_id == wid:
                    bm.model.junctions.remove(jm)
                    if jm.id in self.current_junction_items:
                        try:
                            self.scene.removeItem(
                                self.current_junction_items[jm.id])
                        except Exception:
                            pass
                        del self.current_junction_items[jm.id]
        self._cleanup_orphan_junctions()

    def delete_junction(self, junction_item: JunctionItem):
        jid = junction_item.model.id
        if jid in self.current_junction_items:
            try:
                self.scene.removeItem(self.current_junction_items[jid])
            except Exception:
                pass
            del self.current_junction_items[jid]
        for bm in self.blocks.values():
            bm.model.junctions = [j for j in bm.model.junctions if j.id != jid]
        wires_to_delete = set()
        for bm in self.blocks.values():
            for w in bm.model.wires:
                if (isinstance(w.start, (list, tuple)) and len(w.start) and
                    w.start[0] == f"j:{jid}") \
                        or (isinstance(w.end, (list, tuple)) and len(w.end) and
                            w.end[0] == f"j:{jid}"):
                    wires_to_delete.add(w.id)
        for wid in list(wires_to_delete):
            if wid in self.current_wire_items:
                try:
                    self.scene.removeItem(self.current_wire_items[wid])
                except Exception:
                    pass
                del self.current_wire_items[wid]
            for bm in self.blocks.values():
                bm.model.wires = [w for w in bm.model.wires if w.id != wid]
        self._cleanup_orphan_junctions()

    def delete_instance(self, inst_item: 'InstanceItem'):
        wires_to_delete = set()
        for p in inst_item.port_items.values():
            wires_to_delete.update(self._collect_wires_connected_to_obj(p))
        for wid in list(wires_to_delete):
            wi = self.current_wire_items.get(wid)
            if wi:
                try:
                    self.scene.removeItem(wi)
                except Exception:
                    pass
                if wid in self.current_wire_items:
                    del self.current_wire_items[wid]
            for bm in self.blocks.values():
                bm.model.wires = [w for w in bm.model.wires if w.id != wid]
        parent = inst_item.parentItem()
        if isinstance(parent, BlockFrame):
            inst_id = inst_item.model.id
            parent.model.instances = [i for i in parent.model.instances if
                                      i.id != inst_id]
            if inst_id in parent.instance_items:
                del parent.instance_items[inst_id]
        self.scene.removeItem(inst_item)
        self._cleanup_orphan_junctions()

    def delete_block_pin(self, pin_item: PortItem):
        if not pin_item.owner_id or not pin_item.owner_id.startswith("block:"):
            return
        block_id = pin_item.owner_id.split(":", 1)[1]
        pin_name = pin_item.model.name
        visuals = []
        bf = self.blocks.get(block_id)
        if bf:
            if pin_name in bf.port_items:
                visuals.append(bf.port_items[pin_name])
            for other_bf in self.blocks.values():
                for inst in other_bf.model.instances:
                    if inst.block_id == block_id:
                        inst_item = other_bf.instance_items.get(inst.id)
                        if inst_item and pin_name in inst_item.port_items:
                            visuals.append(inst_item.port_items[pin_name])
        wires_to_delete = set()
        for v in visuals:
            wires_to_delete.update(self._collect_wires_connected_to_obj(v))
        for wid in list(wires_to_delete):
            wi = self.current_wire_items.get(wid)
            if wi:
                try:
                    self.scene.removeItem(wi);
                    del self.current_wire_items[wid]
                except Exception:
                    pass
            for bm in self.blocks.values():
                bm.model.wires = [w for w in bm.model.wires if w.id != wid]
        if bf:
            bf.model.ports = [p for p in bf.model.ports if p.name != pin_name]
            if pin_name in bf.port_items:
                pvis = bf.port_items.pop(pin_name);
                self.scene.removeItem(pvis)
            for other_bf in self.blocks.values():
                for inst in list(other_bf.model.instances):
                    if inst.block_id == block_id:
                        inst.ports = [p for p in inst.ports if
                                      p.name != pin_name]
                        inst_item = other_bf.instance_items.get(inst.id)
                        if inst_item and pin_name in inst_item.port_items:
                            pvis = inst_item.port_items.pop(pin_name);
                            self.scene.removeItem(pvis)
        self._cleanup_orphan_junctions()

    def delete_block(self, block_frame: 'BlockFrame'):
        block_id = block_frame.model.id
        ans = QMessageBox.question(None, "Delete block",
                                   f"Delete block '{block_frame.model.name}' and all its instances and wires?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        all_pin_visuals = []
        bf = self.blocks.get(block_id)
        if bf:
            all_pin_visuals.extend(list(bf.port_items.values()))
        for other_bf in self.blocks.values():
            for inst in list(other_bf.model.instances):
                if inst.block_id == block_id:
                    inst_item = other_bf.instance_items.get(inst.id)
                    if inst_item:
                        all_pin_visuals.extend(
                            list(inst_item.port_items.values()))
        wires_to_delete = set()
        for pv in all_pin_visuals:
            wires_to_delete.update(self._collect_wires_connected_to_obj(pv))
        for wid in list(wires_to_delete):
            wi = self.current_wire_items.get(wid)
            if wi:
                try:
                    self.scene.removeItem(wi);
                    del self.current_wire_items[wid]
                except Exception:
                    pass
            for bm in self.blocks.values():
                bm.model.wires = [w for w in bm.model.wires if w.id != wid]
        for other_bf in list(self.blocks.values()):
            inst_ids = [inst.id for inst in other_bf.model.instances if
                        inst.block_id == block_id]
            for iid in inst_ids:
                inst_item = other_bf.instance_items.get(iid)
                if inst_item:
                    self.delete_instance(inst_item)
            other_bf.model.instances = [inst for inst in
                                        other_bf.model.instances if
                                        inst.block_id != block_id]
        if block_id in self.blocks:
            if bf:
                for pv in list(bf.port_items.values()):
                    try:
                        self.scene.removeItem(pv)
                    except Exception:
                        pass
                try:
                    self.scene.removeItem(bf)
                except Exception:
                    pass
            del self.blocks[block_id]
        self._cleanup_orphan_junctions()

    def _cleanup_orphan_junctions(self):
        to_remove_model = []
        for bm in self.blocks.values():
            existing_wire_ids = {w.id for w in bm.model.wires}
            for jm in list(bm.model.junctions):
                if jm.wire_id is None or jm.wire_id not in existing_wire_ids:
                    to_remove_model.append((bm, jm.id))
        for bm, jid in to_remove_model:
            bm.model.junctions = [j for j in bm.model.junctions if j.id != jid]
            if jid in self.current_junction_items:
                try:
                    self.scene.removeItem(self.current_junction_items[jid])
                except Exception:
                    pass
                del self.current_junction_items[jid]
        for jid in list(self.current_junction_items.keys()):
            found = False
            for bm in self.blocks.values():
                if any(j.id == jid for j in bm.model.junctions):
                    found = True;
                    break
            if not found:
                try:
                    self.scene.removeItem(self.current_junction_items[jid])
                except Exception:
                    pass
                del self.current_junction_items[jid]

    def set_add_wire_mode(self, enabled: bool):
        self.add_wire_mode = enabled
        if not enabled and self.temp_wire_start is not None:
            self._restore_pin_color(self.temp_wire_start)
            self.temp_wire_start = None

    def set_add_junction_mode(self, enabled: bool):
        self.add_junction_mode = enabled

    def start_wire(self, obj: Any):
        if not self.add_wire_mode:
            return
        self.temp_wire_start = obj
        if isinstance(obj, (PortItem, JunctionItem)):
            obj.setBrush(QBrush(QColor("red")))

    def _restore_pin_color(self, item):
        if isinstance(item, PortItem):
            if item.owner_id and item.owner_id.startswith("block:"):
                item.setBrush(QBrush(QColor("lime")))
            else:
                item.setBrush(QBrush(QColor("orange")))
        elif isinstance(item, JunctionItem):
            item.setBrush(QBrush(QColor("#FF69B4")))

    def finish_wire(self, obj: Any):
        """Finish creating a wire between two pins or junctions."""
        if self.temp_wire_start is None:
            return

        start = self.temp_wire_start
        end = obj

        if start is end:
            self._restore_pin_color(start)
            self.temp_wire_start = None
            return

        def block_of_endpoint(o: Any) -> Optional[str]:
            if isinstance(o, PortItem):
                return self.owner_block_of_port(o)
            if isinstance(o, JunctionItem):
                for bid, bf in self.blocks.items():
                    local_pos = bf.mapFromScene(QPointF(o.model.x, o.model.y))
                    if bf.rect().contains(local_pos):
                        return bid
                return None
            return None

        s_block = block_of_endpoint(start)
        e_block = block_of_endpoint(end)

        if s_block is not None and e_block is not None and s_block != e_block:
            QMessageBox.warning(None, "Invalid connection",
                                "Cannot connect pins/junctions from different blocks.")
            self._restore_pin_color(start)
            self.temp_wire_start = None
            return

        def id_for(o):
            if isinstance(o, PortItem):
                return (o.owner_id or "unknown", o.model.name)
            if isinstance(o, JunctionItem):
                return (f"j:{o.model.id}", "")
            return ("unknown", "")

        wm = WireModel(start=id_for(start), end=id_for(end))

        target_block_id = s_block or e_block or self._visible_block_id
        if target_block_id is None:
            QMessageBox.warning(None, "Invalid",
                                "Could not determine block for this wire.")
            self._restore_pin_color(start)
            self.temp_wire_start = None
            return

        bm = self.blocks[target_block_id].model
        bm.wires.append(wm)

        wi = WireItem(start, end, wm)
        wi.controller = self
        self.scene.addItem(wi)
        self.current_wire_items[wm.id] = wi

        # IMPORTANT FIX:
        # Do NOT override an existing junction.model.wire_id (host) when connecting a new wire to an existing junction.
        # Only set junction.model.wire_id if it is currently None (i.e. junction had no host).
        for ep in (start, end):
            if isinstance(ep, JunctionItem):
                if ep.model.wire_id is None:
                    ep.model.wire_id = wm.id
                    ep.attached_wire_id = wm.id
                # else: keep existing host wire_id — do NOT overwrite

        wi.update_path()

        # restore interactivity
        for obj in (start, end):
            if isinstance(obj, (PortItem, JunctionItem)):
                obj.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
                obj.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                            True)
                obj.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        # disable add-wire mode after creating one wire
        self.set_add_wire_mode(False)

        self._restore_pin_color(start)
        self._restore_pin_color(end)
        self.temp_wire_start = None
        return wi

    def create_junction_at(self, scene_pos: QPointF,
                           attached_wire: WireItem) -> JunctionItem:
        if attached_wire is None:
            return None
        wire_model = attached_wire.model
        owner_block = None
        for bid, bf in self.blocks.items():
            if any(w.id == wire_model.id for w in bf.model.wires):
                owner_block = bf
                break
        if owner_block is None:
            return None
        jm = JunctionModel(x=scene_pos.x(), y=scene_pos.y(),
                           wire_id=wire_model.id)
        owner_block.model.junctions.append(jm)
        ji = JunctionItem(jm, self, attached_wire_id=wire_model.id)
        # ensure interactivity
        ji.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        ji.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        ji.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.scene.addItem(ji)
        ji.setZValue(100)
        a = attached_wire.start_obj.scenePos()
        b = attached_wire.end_obj.scenePos()
        proj = project_point_to_segment(scene_pos, a, b)
        ji.setPos(proj)
        ji.model.x, ji.model.y = proj.x(), proj.y()
        self.current_junction_items[jm.id] = ji
        return ji

    def _reproject_junctions_for_wire(self, wire_id: str):
        """Reproject junctions on the given wire and refresh all connected wires."""
        w_item = self.current_wire_items.get(wire_id)
        if not w_item:
            return

        a = w_item.start_obj.scenePos()
        b = w_item.end_obj.scenePos()

        # найти блок, которому принадлежит провод
        block = None
        for bid, bf in self.blocks.items():
            if any(w.id == wire_id for w in bf.model.wires):
                block = bf
                break
        if not block:
            return

        moved_junctions = []

        for jm in block.model.junctions:
            if jm.wire_id != wire_id:
                continue
            ji = self.current_junction_items.get(jm.id)
            if not ji:
                continue

            proj, t = project_point_to_segment_local(QPointF(jm.x, jm.y), a, b)
            jm.t = t
            jm.x, jm.y = proj.x(), proj.y()
            ji.setPos(proj)
            moved_junctions.append(jm.id)

        # теперь обновляем все провода, которые подключены к этим junctions
        if not moved_junctions:
            return

        for wm in block.model.wires:
            # если провод не из этого блока — пропускаем
            if wm.id not in self.current_wire_items:
                continue
            wi2 = self.current_wire_items[wm.id]
            # если этот провод начинается или заканчивается на один из moved_junctions
            start_key = wm.start[0] if wm.start else ""
            end_key = wm.end[0] if wm.end else ""
            for jid in moved_junctions:
                if start_key == f"j:{jid}" or end_key == f"j:{jid}":
                    wi2.update_path()
                    break

        # и наконец, обновляем host-wire тоже
        if wire_id in self.current_wire_items:
            self.current_wire_items[wire_id].update_path()

    def update_wires_for_pin(self, pin_item: PortItem):
        for wid, wv in list(self.current_wire_items.items()):
            if wv.start_obj == pin_item or wv.end_obj == pin_item:
                wv.update_path()
                # reproject junctions only for wires where those junctions are host (jm.wire_id == wid)
                self._reproject_junctions_for_wire(wid)

    def update_wires_for_junction(self, junction_item: JunctionItem):
        for wid, wv in list(self.current_wire_items.items()):
            if wv.start_obj == junction_item or wv.end_obj == junction_item:
                wv.update_path()
                self._reproject_junctions_for_wire(wid)

    def update_wires_for_instance(self, inst_item: InstanceItem):
        for p in inst_item.port_items.values():
            self.update_wires_for_pin(p)

    def update_wires_for_block_move(self, block_frame: 'BlockFrame', dx: float,
                                    dy: float):
        """Move junctions (models and visuals) by dx,dy and update wire visuals.
           Do NOT reproject junctions that belong to this block — they moved rigidly."""
        # move junction models & visuals
        for jm in block_frame.model.junctions:
            jm.x += dx
            jm.y += dy
            if jm.id in self.current_junction_items:
                ji = self.current_junction_items[jm.id]
                ji.setPos(QPointF(jm.x, jm.y))
                ji.model.x, ji.model.y = jm.x, jm.y

        # update wire visuals for this block
        for wm in block_frame.model.wires:
            wid = wm.id
            wi = self.current_wire_items.get(wid)
            if wi:
                wi.update_path()
                # do not reproject junctions inside this block (they already moved)
        # nevertheless reproject junctions for any other wires whose geometry changed
        for wid in list(self.current_wire_items.keys()):
            self._reproject_junctions_for_wire(wid)

    def show_only_block(self, block_id: str):
        self._visible_block_id = block_id
        for bid, bf in self.blocks.items():
            visible = (bid == block_id)
            bf.setVisible(visible)
        for wid, wi in list(self.current_wire_items.items()):
            try:
                self.scene.removeItem(wi)
            except Exception:
                pass
        self.current_wire_items.clear()
        for jid, ji in list(self.current_junction_items.items()):
            try:
                self.scene.removeItem(ji)
            except Exception:
                pass
        self.current_junction_items.clear()
        bf = self.blocks.get(block_id)
        if not bf:
            return
        for jm in bf.model.junctions:
            ji = JunctionItem(jm, self, attached_wire_id=jm.wire_id)
            ji.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            ji.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            ji.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
            self.scene.addItem(ji)
            ji.setPos(QPointF(jm.x, jm.y))
            self.current_junction_items[jm.id] = ji
        for wm in bf.model.wires:
            start_obj = self.find_object_by_id_tuple(wm.start, for_block=bf)
            end_obj = self.find_object_by_id_tuple(wm.end, for_block=bf)
            if start_obj and end_obj:
                wi = WireItem(start_obj, end_obj, wm)
                wi.controller = self
                self.scene.addItem(wi)
                self.current_wire_items[wm.id] = wi
        for jm in bf.model.junctions:
            if jm.wire_id and jm.wire_id in self.current_wire_items:
                ji = self.current_junction_items.get(jm.id)
                if ji:
                    ji.attached_wire_id = jm.wire_id
                    wi = self.current_wire_items[jm.wire_id]
                    a = wi.start_obj.scenePos()
                    b = wi.end_obj.scenePos()
                    proj = project_point_to_segment(QPointF(jm.x, jm.y), a, b)
                    ji.setPos(proj)
                    ji.model.x, ji.model.y = proj.x(), proj.y()

    def save_scene(self, filename: str):
        data = {"blocks": []}
        for bf in self.blocks.values():
            data["blocks"].append(bf.model.to_dict())
        with open(filename, "w", encoding="utf8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # QMessageBox.information(None, "Saved", f"Saved to {filename}")

    def load_scene(self, filename: str):
        try:
            with open(filename, "r", encoding="utf8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load: {e}")
            return
        self.scene.clear()
        self.blocks.clear()
        self.current_wire_items.clear()
        self.current_junction_items.clear()
        for bd in data.get("blocks", []):
            bm = BlockModel.from_dict(bd)
            bf = BlockFrame(bm, self)
            self.scene.addItem(bf)
            bf.setVisible(False)
            self.blocks[bm.id] = bf
        if self.blocks:
            first_id = next(iter(self.blocks.keys()))
            self.show_only_block(first_id)

    def find_object_by_id_tuple(self, info: Tuple[str, str],
                                for_block: Optional['BlockFrame'] = None) -> \
    Optional[Any]:
        key, pname = info
        if key.startswith("j:"):
            jid = key.split(":", 1)[1];
            return self.current_junction_items.get(jid)
        if key.startswith("block:"):
            _, bid = key.split(":", 1)
            bf = self.blocks.get(bid)
            if bf and pname in bf.port_items:
                return bf.port_items[pname]
            return None
        if for_block:
            inst = for_block.instance_items.get(key)
            if inst and pname in inst.port_items:
                return inst.port_items[pname]
        for bf in self.blocks.values():
            inst_item = bf.instance_items.get(key)
            if inst_item and pname in inst_item.port_items:
                return inst_item.port_items[pname]
        return None

    def owner_block_of_port(self, port_item: PortItem) -> Optional[str]:
        if not port_item.owner_id:
            return None
        if port_item.owner_id.startswith("block:"):
            return port_item.owner_id.split(":", 1)[1]
        for bid, bf in self.blocks.items():
            if port_item.owner_id in bf.instance_items:
                return bid
        return None

    def copy_block(self, block_frame: 'BlockFrame') -> 'BlockFrame':
        """Create a deep copy of the block with all its contents."""
        # Use model's copy method
        new_model = block_frame.model.copy()
        
        # Create new BlockFrame
        new_bf = BlockFrame(new_model, self)
        self.scene.addItem(new_bf)
        self.blocks[new_model.id] = new_bf
        new_bf.setVisible(False)

        return new_bf

    def copy_instance(self, inst_item: 'InstanceItem', parent_frame: 'BlockFrame') -> 'InstanceItem':
        """Create a deep copy of the instance within the same parent block."""
        # Use model's copy method - generates new ID
        new_inst_model = inst_item.model.copy()
        
        # Offset position
        new_inst_model.x += 20
        new_inst_model.y += 20

        # Add to parent block model
        parent_frame.model.instances.append(new_inst_model)

        # Create new visual instance
        new_inst_item = parent_frame._create_instance_visual(new_inst_model)

        return new_inst_item
    
    def get_block_by_id(self, block_id: str) -> Optional[BlockModel]:
        return self.blocks.get(block_id, None).model
    
    def get_instance_by_id(self, instance_id: str) -> Optional[InstanceModel]:
        for bf in self.blocks.values():
            if instance_id in bf.instance_items:
                return bf.instance_items[instance_id].model
        return None

    def get_port_by_name(self, block_id: str, port_name: str) -> Optional[PortModel]:
        bf = self.get_block_by_id(block_id)
        if not bf:
            return None
        for pm in bf.ports:
            if pm.name == port_name:
                return pm
        return None


# ---------------- BlockFrame ----------------
class BlockFrame(QGraphicsRectItem):
    RESIZE_MARGIN = 12.0
    MIN_W = 120.0
    MIN_H = 80.0

    def __init__(self, model: BlockModel, controller: Controller):
        super().__init__(0.0, 0.0, model.w, model.h)
        self.model = model
        self.controller = controller
        self.is_moving = False

        self.port_items: Dict[str, PortItem] = {}
        self.instance_items: Dict[str, InstanceItem] = {}

        self.setPen(QPen(QColor("#888888"), 2))
        self.setBrush(QBrush(QColor("#0b0b0b")))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        self.setPos(model.x, model.y)

        self.title = QGraphicsSimpleTextItem(model.name, self)
        self.title.setBrush(QBrush(QColor("#00FF88")))
        self.title.setPos(5, -20)

        self._resizing = False
        self._resize_dirs = {"left": False, "right": False, "top": False,
                             "bottom": False}
        self._resize_start_scene = QPointF()
        self._orig_rect = QRectF(self.rect())
        self._orig_pos = QPointF(self.pos())
        self._inst_scene_positions: Dict[str, QPointF] = {}

        for pm in self.model.ports:
            self._create_block_port(pm)
        for inst in self.model.instances:
            self._create_instance_visual(inst)

    def _create_block_port(self, pm: PortModel) -> PortItem:
        if pm.name in self.port_items:
            existing = self.port_items[pm.name]
            existing.model.x, existing.model.y = pm.x, pm.y
            existing.update_from_model()
            return existing
        p = PortItem(self, pm, controller=self.controller,
                     owner_id=f"block:{self.model.id}", color=QColor("lime"))
        self.port_items[pm.name] = p
        return p

    def _create_instance_visual(self,
                                inst_model: InstanceModel) -> InstanceItem:
        item = InstanceItem(inst_model, self.controller)
        item.setParentItem(self)
        item.setPos(inst_model.x, inst_model.y)
        # for bp in self.model.ports:
        #     if bp.name not in [p.name for p in inst_model.ports]:
        #         inst_model.ports.append(PortModel(bp.name, bp.x, bp.y))
        for pm in inst_model.ports:
            if pm.name not in item.port_items:
                item.port_items[pm.name] = PortItem(item, pm,
                                                    controller=self.controller,
                                                    owner_id=inst_model.id,
                                                    color=QColor("orange"))
        self.instance_items[inst_model.id] = item
        return item

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # compute dx,dy based on model stored old pos
            old_x, old_y = self.model.x, self.model.y
            new_x, new_y = self.pos().x(), self.pos().y()
            dx, dy = new_x - old_x, new_y - old_y
            # update model pos
            self.model.x, self.model.y = new_x, new_y
            if dx != 0.0 or dy != 0.0:
                # notify controller with exact delta
                self.controller.update_wires_for_block_move(self, dx, dy)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self.is_moving = True

        pos_local = event.pos()
        dirs = self._detect_resize_zone(pos_local)
        if any(dirs.values()):
            self._resizing = True
            self._resize_dirs = dirs
            self._resize_start_scene = event.scenePos()
            self._orig_rect = QRectF(self.rect())
            self._orig_pos = QPointF(self.pos())
            self._inst_scene_positions = {}
            for iid, inst_item in self.instance_items.items():
                self._inst_scene_positions[iid] = inst_item.scenePos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            cur_scene = event.scenePos()
            delta = cur_scene - self._resize_start_scene
            orig = self._orig_rect
            new_w = orig.width()
            new_h = orig.height()
            dx = delta.x()
            dy = delta.y()

            moved_x = 0.0
            moved_y = 0.0
            if self._resize_dirs["left"]:
                new_w = max(self.MIN_W, orig.width() - dx)
                moved_x = orig.width() - new_w
            if self._resize_dirs["right"]:
                new_w = max(self.MIN_W, orig.width() + dx)
            if self._resize_dirs["top"]:
                new_h = max(self.MIN_H, orig.height() - dy)
                moved_y = orig.height() - new_h
            if self._resize_dirs["bottom"]:
                new_h = max(self.MIN_H, orig.height() + dy)

            if self._resize_dirs["left"] or self._resize_dirs["top"]:
                new_scene_x = self._orig_pos.x() + moved_x
                new_scene_y = self._orig_pos.y() + moved_y
                self.setPos(new_scene_x, new_scene_y)

            self.setRect(0.0, 0.0, new_w, new_h)
            self.model.w = new_w;
            self.model.h = new_h
            self.model.x = self.pos().x();
            self.model.y = self.pos().y()

            for pvis in self.port_items.values():
                pvis.update_from_model()

            for iid, inst_item in self.instance_items.items():
                old_scene_pos = self._inst_scene_positions.get(iid,
                                                               inst_item.scenePos())
                new_local = self.mapFromScene(old_scene_pos)
                max_x = max(0.0, new_w - inst_item.rect().width())
                max_y = max(0.0, new_h - inst_item.rect().height())
                nx = min(max(new_local.x(), 0.0), max_x)
                ny = min(max(new_local.y(), 0.0), max_y)
                inst_item.setPos(nx, ny)
                inst_item.model.x = nx;
                inst_item.model.y = ny

            for pvis in self.port_items.values():
                self.controller.update_wires_for_pin(pvis)
            for inst_item in self.instance_items.values():
                self.controller.update_wires_for_instance(inst_item)

            self.controller.update_wires_for_block_move(self, 0.0,
                                                        0.0)  # resizing - no positional delta
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.is_moving = False

        if self._resizing:
            self._resizing = False
            self._resize_dirs = {"left": False, "right": False, "top": False,
                                 "bottom": False}
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._inst_scene_positions.clear()
            self.model.x = self.pos().x();
            self.model.y = self.pos().y()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _detect_resize_zone(self, pos_local: QPointF):
        r = self.rect()
        x, y = pos_local.x(), pos_local.y()
        left_zone = (0 <= x <= self.RESIZE_MARGIN)
        right_zone = (r.width() - self.RESIZE_MARGIN <= x <= r.width())
        top_zone = (0 <= y <= self.RESIZE_MARGIN)
        bottom_zone = (r.height() - self.RESIZE_MARGIN <= y <= r.height())
        dirs = {"left": left_zone, "right": right_zone, "top": top_zone,
                "bottom": bottom_zone}
        return dirs

    def hoverMoveEvent(self, event):
        pos_local = event.pos()
        dirs = self._detect_resize_zone(pos_local)
        cursor = Qt.CursorShape.ArrowCursor
        if (dirs["left"] and dirs["top"]) or (
                dirs["right"] and dirs["bottom"]):
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif (dirs["right"] and dirs["top"]) or (
                dirs["left"] and dirs["bottom"]):
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif dirs["left"] or dirs["right"]:
            cursor = Qt.CursorShape.SizeHorCursor
        elif dirs["top"] or dirs["bottom"]:
            cursor = Qt.CursorShape.SizeVerCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def add_instance(self, child_frame: 'BlockFrame',
                     local_pos: QPointF) -> InstanceItem:
        child_block = child_frame.model
        idx = len(self.model.instances) + 1
        inst_model = InstanceModel(name=f"{child_block.name}_inst{idx}",
                                   block_name=child_block.name,
                                   x=local_pos.x(), y=local_pos.y(), w=120.0,
                                   h=60.0,
                                   ports=[PortModel(p.name, p.x, p.y) for p in
                                          child_block.ports])
        self.model.instances.append(inst_model)
        return self._create_instance_visual(inst_model)

    def add_block_pin(self, name: Optional[str] = None, relx: float = 0.0,
                      rely: float = 0.5) -> PortModel:
        if not name:
            base = "P"
            idx = len(self.model.ports) + 1
            '''existing_names = {p.name for p in self.model.ports}
            while f"{base}{idx}" in existing_names:
                idx += 1'''
            name = f"{base}{idx}"
        pm = PortModel(name, relx, rely)
        self.model.ports.append(pm)
        self._create_block_port(pm)
        self.controller.propagate_new_pin_to_instances(self.model.id, pm)
        return pm


class BlockEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Block Editor — final (PyQt6)")
        self.resize(1100, 750)
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("#000000")))

        self.view = QGraphicsView(self.scene)
        try:
            self.view.setRenderHints(QPainter.RenderHint.Antialiasing)
        except Exception:
            pass

        self.controller = Controller(self.scene)

        top_layout = QHBoxLayout()
        btn_add_block = QPushButton("Add Block")
        btn_add_inst = QPushButton("Add Instance")
        btn_add_pin = QPushButton("Add Block Pin")
        btn_add_wire = QPushButton("Add Wire")
        btn_add_junction = QPushButton("Add Junction")
        btn_delete = QPushButton("Delete Selected")
        btn_save = QPushButton("Save")
        btn_load = QPushButton("Load")
        self.combo_blocks = QComboBox()

        top_layout.addWidget(btn_add_block)
        top_layout.addWidget(self.combo_blocks)
        top_layout.addWidget(btn_add_inst)
        top_layout.addWidget(btn_add_pin)
        top_layout.addWidget(btn_add_wire)
        top_layout.addWidget(btn_add_junction)
        top_layout.addWidget(btn_delete)
        top_layout.addWidget(btn_save)
        top_layout.addWidget(btn_load)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.view)

        btn_add_block.clicked.connect(self._on_add_block)
        btn_add_inst.clicked.connect(self._on_add_instance)
        btn_add_pin.clicked.connect(self._on_add_pin)
        btn_add_wire.clicked.connect(self._on_add_wire)
        btn_add_junction.clicked.connect(self._on_add_junction)
        btn_delete.clicked.connect(self._on_delete_selected)
        btn_save.clicked.connect(
            lambda: self.controller.save_scene("scene_blocks.json"))
        btn_load.clicked.connect(lambda: self._on_load_scene())

        self.combo_blocks.currentIndexChanged.connect(self._on_combo_changed)
        self._current_block_id: Optional[str] = None

        self.active_mode = None
        self.current_filter = None

        b1 = self.controller.add_block("BlockA")
        b2 = self.controller.add_block("BlockB")

        self._refresh_combo()
        if self.combo_blocks.count() > 0:
            self.combo_blocks.setCurrentIndex(0)
            self._show_block_by_index(0)

    def _refresh_combo(self):
        cur = self.combo_blocks.currentText()
        self.combo_blocks.blockSignals(True)
        self.combo_blocks.clear()
        for bf in self.controller.blocks.values():
            self.combo_blocks.addItem(bf.model.name, bf.model.id)
        idx = self.combo_blocks.findText(cur)
        if idx >= 0:
            self.combo_blocks.setCurrentIndex(idx)
        self.combo_blocks.blockSignals(False)

    def _get_block_id_by_index(self, idx: int) -> Optional[str]:
        if idx < 0:
            return None
        return self.combo_blocks.itemData(idx)

    def _show_block_by_index(self, idx: int):
        bid = self._get_block_id_by_index(idx)
        if bid is None:
            return
        self.controller.show_only_block(bid)
        self._current_block_id = bid

    def _on_combo_changed(self, idx: int):
        self._deactivate_mode()
        new_bid = self._get_block_id_by_index(idx)
        if new_bid is None:
            return
        if self._current_block_id is None:
            self._show_block_by_index(idx);
            return
        if new_bid == self._current_block_id: return
        ans = QMessageBox.question(self, "Save changes",
                                   f"Save changes to current block '{self.controller.blocks[self._current_block_id].model.name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if ans == QMessageBox.StandardButton.Cancel:
            cur_idx = self.combo_blocks.findData(self._current_block_id)
            if cur_idx >= 0:
                self.combo_blocks.blockSignals(True)
                self.combo_blocks.setCurrentIndex(cur_idx)
                self.combo_blocks.blockSignals(False)
            return
        if ans == QMessageBox.StandardButton.Yes:
            self.controller.save_scene("scene_blocks.json")
        self._show_block_by_index(idx)

    def _deactivate_mode(self):
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

    def _on_add_block(self):
        self._deactivate_mode()
        name, ok = QInputDialog.getText(self, "New block", "Block name:",
                                        text=f"Block{len(self.controller.blocks) + 1}")
        if not ok or not name:
            return
        bf = self.controller.add_block(name)
        self._refresh_combo()
        idx = self.combo_blocks.findData(bf.model.id)
        if idx >= 0:
            self.combo_blocks.setCurrentIndex(idx)
            self._show_block_by_index(idx)

    def _on_add_instance(self):
        self._deactivate_mode()
        if len(self.controller.blocks) < 2:
            QMessageBox.information(self, "Info", "Need at least two blocks.")
            return
        names = [bf.model.name for bf in self.controller.blocks.values()]
        child_name, ok = QInputDialog.getItem(self, "Choose block to insert",
                                              "Block:", names, 0, False)
        if not ok: return
        parent_name, ok = QInputDialog.getItem(self, "Choose parent block",
                                               "Parent:", names, 0, False)
        if not ok: return
        if child_name == parent_name:
            QMessageBox.warning(self, "Error",
                                "Cannot insert block into itself.");
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
                parent_frame.add_instance(child_frame.model, local)
                self._refresh_combo()
                self.view.viewport().removeEventFilter(filter_obj)
                return True
            return False

        class OneShot(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == 2: return handler(ev)
                return False

        filter_obj = OneShot();
        self.view.viewport().installEventFilter(filter_obj)

    def _on_add_pin(self):
        self._deactivate_mode()
        QMessageBox.information(self, "Add Pin",
                                "Click inside the visible block to add a pin (copied into its instances).")

        def handler(ev):
            pos = self.view.mapToScene(ev.position().toPoint())
            for bf in self.controller.blocks.values():
                if bf.isVisible() and bf.mapRectToScene(bf.rect()).contains(
                        pos):
                    self._controller_add_block_pin_at_point(bf, pos)
                    self.view.viewport().removeEventFilter(filter_obj)
                    return True
            return False

        class OneShot(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == 2: return handler(ev)
                return False

        filter_obj = OneShot();
        self.view.viewport().installEventFilter(filter_obj)

    def _controller_add_block_pin_at_point(self, block_frame: BlockFrame,
                                           scene_pos: QPointF):
        local = block_frame.mapFromScene(scene_pos)
        rect = block_frame.rect()
        lx = min(max(local.x(), 0.0), rect.width());
        ly = min(max(local.y(), 0.0), rect.height())
        left = lx;
        right = rect.width() - lx;
        top = ly;
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
        block_frame.add_block_pin(name=None, relx=relx, rely=rely)
        self.controller.show_only_block(self._current_block_id)

    def _on_add_wire(self):
        if self.active_mode == 'wire':
            self._deactivate_mode()
            return

        self._deactivate_mode()
        self.active_mode = 'wire'
        self.controller.set_add_wire_mode(True)

        QMessageBox.information(self, "Add Wire",
                                "Click a pin/junction to start, then click another pin/junction to complete the wire. Click 'Add Wire' again to cancel.")

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
                self.controller.start_wire(item)
                return True
            else:
                self.controller.finish_wire(item)
                # after finish we want to exit the mode automatically:
                self._deactivate_mode()
                return True

        class WireModeFilter(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == 2:
                    return handler(ev)
                return False

        self.current_filter = WireModeFilter()
        self.view.viewport().installEventFilter(self.current_filter)

    def _on_add_junction(self):
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

    def _on_delete_selected(self):
        self._deactivate_mode()
        selected = list(self.scene.selectedItems())
        if not selected:
            QMessageBox.information(self, "Delete", "No selection.")
            return
        blocks = [it for it in selected if isinstance(it, BlockFrame)]
        instances = [it for it in selected if isinstance(it, InstanceItem)]
        ports = [it for it in selected if isinstance(it, PortItem)]
        wires = [it for it in selected if isinstance(it, WireItem)]
        junctions = [it for it in selected if isinstance(it, JunctionItem)]
        for b in blocks: self.controller.delete_block(b)
        for inst in instances: self.controller.delete_instance(inst)
        for p in ports:
            if p.owner_id and p.owner_id.startswith("block:"):
                self.controller.delete_block_pin(p)
            else:
                QMessageBox.information(self, "Delete pin",
                                        "Only deletion of block-level pins is supported via toolbar.")
        for w in wires: self.controller.delete_wire(w)
        for j in junctions: self.controller.delete_junction(j)
        QMessageBox.information(self, "Delete", "Selected items processed.")
        self._refresh_combo()
        if self._current_block_id:
            self.controller.show_only_block(self._current_block_id)

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key.Key_Escape:
            self._deactivate_mode()
        elif ev.key() == Qt.Key.Key_Delete:
            self._on_delete_selected()
        else:
            super().keyPressEvent(ev)

    def _on_load_scene(self):
        self._deactivate_mode()
        self.controller.load_scene("scene_blocks.json")
        self._refresh_combo()
        if self.combo_blocks.count() > 0:
            self.combo_blocks.setCurrentIndex(0)
            self._show_block_by_index(0)


def project_point_to_segment_local(p: QPointF, a: QPointF, b: QPointF) -> \
Tuple[QPointF, float]:
    """Project point p onto segment a-b (all in same coordinate space).
       Returns (projected_point, t), where t in [0..1]"""
    ax, ay = a.x(), a.y()
    bx, by = b.x(), b.y()
    px, py = p.x(), p.y()
    vx = bx - ax;
    vy = by - ay
    wx = px - ax;
    wy = py - ay
    vlen2 = vx * vx + vy * vy
    if vlen2 == 0:
        return QPointF(ax, ay), 0.0
    t = (wx * vx + wy * vy) / vlen2
    t = max(0.0, min(1.0, t))
    proj = QPointF(ax + t * vx, ay + t * vy)
    return proj, t


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = BlockEditor()
    editor.show()
    sys.exit(app.exec())
