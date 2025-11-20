"""
Тесты для editor.graphical.Controller (остальное требует взаимодействия с пользователем)
"""

import sys
import os
import pytest

# ensure project root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QGraphicsScene, QMessageBox
from PyQt6.QtCore import QPointF

from editor.graphical import Controller, project_point_to_segment, project_point_to_segment_local

# Добавление двух блоков и показ одного
def test_add_block_and_show():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    bf1 = ctrl.add_block("A")
    bf2 = ctrl.add_block("B")
    assert len(ctrl.blocks) == 2
    ctrl.show_only_block(bf1.model.id)
    assert ctrl._visible_block_id == bf1.model.id
    assert bf1.isVisible() is True
    assert bf2.isVisible() is False

# Добавление pin в блок и проверка, что инстансы получают этот pin
def test_add_block_pin_propagates_to_instances():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    child = ctrl.add_block("Child")
    parent = ctrl.add_block("Parent")
    parent.add_instance(child, QPointF(10, 10))
    child.add_block_pin(name="PIN1", relx=0.0, rely=0.5)
    inst_model = parent.model.instances[0]
    assert any(p.name == "PIN1" for p in inst_model.ports)
    inst_vis = parent.instance_items.get(inst_model.id)
    assert inst_vis is not None
    assert "PIN1" in inst_vis.port_items

# Создание цепи между пинами двух инстансов внутри одного блока
def test_create_simple_wire_between_instances():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5)
    c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10, 10)); i2 = parent.add_instance(c2, QPointF(150, 10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    assert pi1 is not None and pi2 is not None
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    assert any(w.id == wi.model.id for w in parent.model.wires)
    assert wi.model.id in ctrl.current_wire_items

# Удаление цепи
def test_delete_wire_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5); c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10, 10)); i2 = parent.add_instance(c2, QPointF(150, 10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    wid = wi.model.id
    ctrl.delete_wire(wi)
    assert not any(w.id == wid for w in parent.model.wires)
    assert wid not in ctrl.current_wire_items

# Добавление и удаление пина
def test_delete_block_pin_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    bf = ctrl.add_block("BlockX")
    bf.add_block_pin(name="PX", relx=0.0, rely=0.5)
    assert any(p.name == "PX" for p in bf.model.ports)
    assert "PX" in bf.port_items
    pin_vis = bf.port_items["PX"]
    ctrl.delete_block_pin(pin_vis)
    assert not any(p.name == "PX" for p in bf.model.ports)
    assert "PX" not in bf.port_items

# Создание и удаление пересечения в цепе
def test_create_and_delete_junction_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5); c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10,10)); i2 = parent.add_instance(c2, QPointF(150,10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    a = wi.start_obj.scenePos(); b = wi.end_obj.scenePos()
    mid = QPointF((a.x()+b.x())/2, (a.y()+b.y())/2)
    ji = ctrl.create_junction_at(mid, wi)
    assert ji is not None
    assert any(j.id == ji.model.id for j in parent.model.junctions)
    assert ji.model.id in ctrl.current_junction_items
    ctrl.delete_junction(ji)
    assert not any(j.id == ji.model.id for j in parent.model.junctions)
    assert ji.model.id not in ctrl.current_junction_items

# Копирование блока
def test_copy_block_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    child = ctrl.add_block("Child")
    child.add_block_pin(name="pv", relx=0.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    parent.add_instance(child, QPointF(10, 10))
    copied = ctrl.copy_block(parent)
    assert copied is not None
    assert copied.model.id != parent.model.id
    assert len(copied.model.instances) == len(parent.model.instances)

# Копирование инстанса
def test_copy_instance_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    child = ctrl.add_block("Child")
    child.add_block_pin(name="pv", relx=0.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    inst_vis = parent.add_instance(child, QPointF(10, 10))
    before = len(parent.model.instances)
    new_vis = ctrl.copy_instance(inst_vis, parent)
    assert new_vis is not None
    assert len(parent.model.instances) == before + 1
    assert new_vis.model.id != inst_vis.model.id

# Проверка геттеров
def test_getters_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    b = ctrl.add_block("B")
    b.add_block_pin(name="pv", relx=0.0, rely=0.5)
    inst = ctrl.add_block("Parent").add_instance(b, QPointF(5, 5))
    bm = ctrl.get_block_by_id(b.model.id)
    assert bm.name == b.model.name
    im = ctrl.get_instance_by_id(inst.model.id)
    assert im is not None and im.id == inst.model.id
    pm = ctrl.get_port_by_name(b.model.id, "pv")
    assert pm is not None and pm.name == "pv"

# Простой тест: удаление блока с подтверждением
def test_delete_block_confirmation_simple(monkeypatch):
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    bf = ctrl.add_block("ToDelete")
    bid = bf.model.id
    assert bid in ctrl.blocks
    monkeypatch.setattr("editor.graphical.QMessageBox.question",
                        lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    ctrl.delete_block(bf)
    assert bid not in ctrl.blocks

# Копирование инстанса
def test_copy_instance_creates_new_visual_and_model():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    child = ctrl.add_block("Child")
    child.add_block_pin(name="pv", relx=0.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    inst_vis = parent.add_instance(child, QPointF(10,10))
    before_count = len(parent.model.instances)
    new_inst_vis = ctrl.copy_instance(inst_vis, parent)
    assert new_inst_vis is not None
    assert len(parent.model.instances) == before_count + 1
    assert new_inst_vis.model.id != inst_vis.model.id
    assert new_inst_vis.model.id in parent.instance_items

# Создание и удаление цепей
def test_delete_wire_removes_model_and_visual():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1")
    c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5)
    c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10,10))
    i2 = parent.add_instance(c2, QPointF(150,10))
    ctrl.show_only_block(parent.model.id)
    p1 = i1.port_items.get("p")
    p2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True)
    ctrl.start_wire(p1)
    wi = ctrl.finish_wire(p2)
    assert wi is not None
    wid = wi.model.id
    assert any(w.id == wid for w in parent.model.wires)
    assert wid in ctrl.current_wire_items

    ctrl.delete_wire(wi)
    assert not any(w.id == wid for w in parent.model.wires)
    assert wid not in ctrl.current_wire_items

# Добавление и удаление пина
def test_delete_block_pin_removes_pin_and_visual():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    bf = ctrl.add_block("BlockX")
    pm = bf.add_block_pin(name="PX", relx=0.0, rely=0.5)
    assert any(p.name == "PX" for p in bf.model.ports)
    assert "PX" in bf.port_items

    pin_vis = bf.port_items["PX"]
    ctrl.delete_block_pin(pin_vis)
    assert not any(p.name == "PX" for p in bf.model.ports)
    assert "PX" not in bf.port_items

# Удаление блока
def test_delete_block_removes_block_after_confirmation(monkeypatch):
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    bf = ctrl.add_block("ToDelete")
    bid = bf.model.id
    assert bid in ctrl.blocks

    monkeypatch.setattr("editor.graphical.QMessageBox.question",
                        lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    ctrl.delete_block(bf)
    assert bid not in ctrl.blocks
    assert not any(p.name == "PX" for p in bf.model.ports)
    assert "PX" not in bf.port_items

# Включение/выключение режима добавления пересечения
def test_set_add_junction_mode_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    assert ctrl.add_junction_mode is False
    ctrl.set_add_junction_mode(True)
    assert ctrl.add_junction_mode is True
    ctrl.set_add_junction_mode(False)
    assert ctrl.add_junction_mode is False

# Удаление инстанса
def test_delete_instance_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5); c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10,10)); i2 = parent.add_instance(c2, QPointF(150,10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    wid = wi.model.id
    ctrl.delete_instance(i1)
    assert i1.model.id not in parent.instance_items
    assert not any(w.id == wid for w in parent.model.wires)
    assert wid not in ctrl.current_wire_items

# Перемещение пина
def test_update_wires_for_pin_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5); c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10,10)); i2 = parent.add_instance(c2, QPointF(150,10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    before_mid = wi.path().pointAtPercent(0.5)
    pi1.model.x = 0.5
    pi1.update_from_model()
    ctrl.update_wires_for_pin(pi1)
    after_mid = wi.path().pointAtPercent(0.5)
    assert not (abs(before_mid.x() - after_mid.x()) < 1e-6 and abs(before_mid.y() - after_mid.y()) < 1e-6)

# Создание цепи и пересечения, проверка обновления координат
def test_update_wires_for_junction_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5); c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10,10)); i2 = parent.add_instance(c2, QPointF(150,10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    a = wi.start_obj.scenePos(); b = wi.end_obj.scenePos()
    mid = QPointF((a.x()+b.x())/2, (a.y()+b.y())/2)
    ji = ctrl.create_junction_at(mid, wi)
    assert ji is not None
    before_mid = wi.path().pointAtPercent(0.5)
    ji.model.x += 10.0; ji.model.y += 5.0
    ji.setPos(QPointF(ji.model.x, ji.model.y))
    ctrl._reproject_junctions_for_wire(wi.model.id)
    after_mid = wi.path().pointAtPercent(0.5)
    assert (abs(before_mid.x() - after_mid.x()) < 1e-6 or abs(before_mid.y() - after_mid.y()) < 1e-6)

# Обновление цепей при перемещении инстанса
def test_update_wires_for_instance_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5); c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10,10)); i2 = parent.add_instance(c2, QPointF(150,10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    before_mid = wi.path().pointAtPercent(0.5)
    i1.setPos(QPointF(i1.pos().x() + 20, i1.pos().y()))
    i1.model.x = i1.pos().x(); i1.model.y = i1.pos().y()
    ctrl.update_wires_for_instance(i1)
    after_mid = wi.path().pointAtPercent(0.5)
    assert not (abs(before_mid.x() - after_mid.x()) < 1e-6 and abs(before_mid.y() - after_mid.y()) < 1e-6)

# Обновление цепей при перемещении блока
def test_update_wires_for_block_move_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    c1 = ctrl.add_block("C1"); c2 = ctrl.add_block("C2")
    c1.add_block_pin(name="p", relx=0.0, rely=0.5); c2.add_block_pin(name="p", relx=1.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    i1 = parent.add_instance(c1, QPointF(10,10)); i2 = parent.add_instance(c2, QPointF(150,10))
    ctrl.show_only_block(parent.model.id)
    pi1 = i1.port_items.get("p"); pi2 = i2.port_items.get("p")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    assert wi is not None
    before_mid = wi.path().pointAtPercent(0.5)
    ctrl.update_wires_for_block_move(parent, 10.0, 0.0)
    after_mid = wi.path().pointAtPercent(0.5)
    assert not (abs(before_mid.x() - after_mid.x()) > 1e-6 and abs(before_mid.y() - after_mid.y()) > 1e-6)

# Сохранение графического представления в файл
def test_save_and_load_scene_simple(tmp_path):
    scene1 = QGraphicsScene()
    ctrl1 = Controller(scene1)
    b1 = ctrl1.add_block("SaveBlock1")
    b1.add_block_pin(name="p1", relx=0.0, rely=0.5)
    b2 = ctrl1.add_block("SaveBlock2")
    fname = tmp_path / "scene_test.json"
    ctrl1.save_scene(str(fname))
    scene2 = QGraphicsScene()
    ctrl2 = Controller(scene2)
    ctrl2.load_scene(str(fname))
    assert len(ctrl2.blocks) == len(ctrl1.blocks)
    names1 = {bf.model.name for bf in ctrl1.blocks.values()}
    names2 = {bf.model.name for bf in ctrl2.blocks.values()}
    assert names1 == names2

# Проверка корректности поиска объектов по ID
def test_find_object_by_id_tuple_simple():
    scene = QGraphicsScene()
    ctrl = Controller(scene)
    child = ctrl.add_block("Child")
    child.add_block_pin(name="pv", relx=0.0, rely=0.5)
    parent = ctrl.add_block("Parent")
    inst_vis = parent.add_instance(child, QPointF(10,10))
    key = (f"block:{child.model.id}", "pv")
    found = ctrl.find_object_by_id_tuple(key)
    assert found is not None
    key2 = (inst_vis.model.id, "pv")
    found2 = ctrl.find_object_by_id_tuple(key2, for_block=parent)
    assert found2 is not None
    ctrl.show_only_block(parent.model.id)
    pi1 = inst_vis.port_items.get("pv")
    inst2 = parent.add_instance(child, QPointF(100,10))
    pi2 = inst2.port_items.get("pv")
    ctrl.set_add_wire_mode(True); ctrl.start_wire(pi1)
    wi = ctrl.finish_wire(pi2)
    a = wi.start_obj.scenePos(); b = wi.end_obj.scenePos()
    ji = ctrl.create_junction_at((a + b) / 2, wi)
    jid = ji.model.id
    found_j = ctrl.find_object_by_id_tuple((f"j:{jid}", ""))
    assert found_j is not None

