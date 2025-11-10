from copy import deepcopy
from enum import Enum, auto
from typing import Dict, List, Optional


class Instance:
    def __init__(self, name: str, type: "Block", parent: "Block" = None):
        self.__type = type
        self.__name = name
        self.__parent = parent
        self.__interface_pins = [
            PinRef(type.interface_pins[pin_name], self)
            for pin_name in type.interface_pins
        ]

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name: str):
        self.__name = name

    @property
    def type(self) -> "Block":
        return self.__type

    @property
    def parent(self) -> "Block":
        return self.__parent

    @property
    def interface_pins(self):
        return {pin.name: pin for pin in self.__interface_pins}

    def disconnect_all_pins(self):
        for pin in self.__interface_pins:
            if pin.net is not None:
                pin.net.disconnect_pin(pin.name)

    def update_pins(self):
        pins = self.interface_pins
        block_pins = self.type.interface_pins

        for pin_name in pins:
            if pin_name not in block_pins:
                self.__interface_pins.remove(pins[pin_name])

        for pin_name in block_pins:
            if pin_name not in pins:
                self.__interface_pins.append(PinRef(block_pins[pin_name], self))


class Block:
    def __init__(
        self, name: str, is_primitive: bool = False, primitive_pins: List[str] = []
    ):
        self.__name = name
        self.__instances: dict[str, Instance] = {}
        self.__interface_pins: dict[str, Pin] = {}
        self.__interface_pins_refs: dict[str, PinRef] = {}
        self.__nets: dict[str, Net] = {}
        self.__is_primitive: bool = is_primitive

        if is_primitive:
            for pin_name in primitive_pins:
                self.__interface_pins[pin_name] = Pin(pin_name, self)
                self.__interface_pins_refs[pin_name] = PinRef(
                    self.__interface_pins[pin_name], self
                )

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def interface_pins(self):
        return self.__interface_pins_refs

    @property
    def instances(self):
        return self.__instances

    @property
    def nets(self):
        return self.__nets

    @property
    def is_primitive(self):
        return self.__is_primitive

    def __check_if_primitive(self, string: str):
        if self.__is_primitive:
            raise Exception(f"Cannot {string} in primitive block {self.name}")

    def __already_exists(self, name: str, collection: dict):
        if name in collection:
            raise Exception(f"{name} already exists in block {self.name}")

    def add_interface_pin(self, pin_name: str) -> "PinRef":
        self.__check_if_primitive("add pin")
        self.__already_exists(pin_name, self.__interface_pins)

        self.__interface_pins[pin_name] = Pin(pin_name, self)
        self.__interface_pins_refs[pin_name] = PinRef(self.__interface_pins[pin_name])
        return self.__interface_pins_refs[pin_name]

    def remove_interface_pin(self, pin_name: str):
        self.__check_if_primitive("remove pin")

        pin_net = self.__interface_pins_refs[pin_name].net
        if pin_net is not None:
            pin_net.disconnect_pin(pin_name)

        del self.__interface_pins[pin_name]
        del self.__interface_pins_refs[pin_name]

    def rename_interface_pin(self, old_name: str, new_name: str):
        self.__check_if_primitive("rename pin")
        self.__already_exists(new_name, self.__interface_pins)

        pin = self.__interface_pins[old_name]
        pin.name = new_name
        self.__interface_pins[new_name] = pin

        pin_ref = self.__interface_pins_refs[old_name]
        self.__interface_pins_refs[new_name] = pin_ref

        del self.__interface_pins[old_name]
        del self.__interface_pins_refs[old_name]

    def add_instance(self, instance_name: str, instance_type: "Block") -> Instance:
        self.__check_if_primitive("add instance")
        self.__already_exists(instance_name, self.__instances)

        self.__instances[instance_name] = Instance(instance_name, instance_type, self)
        return self.__instances[instance_name]

    def remove_instance(self, instance_name: str):
        self.__check_if_primitive("remove instance")

        instance = self.__instances[instance_name]
        instance.disconnect_all_pins()
        del self.__instances[instance_name]

    def rename_instance(self, old_name: str, new_name: str):
        self.__check_if_primitive("rename instance")
        self.__already_exists(new_name, self.__instances)

        instance = self.__instances[old_name]
        instance.name = new_name
        self.__instances[new_name] = instance
        del self.__instances[old_name]

    def add_net(self, net_name: str) -> "Net":
        self.__check_if_primitive("add net")
        self.__already_exists(net_name, self.__nets)

        self.__nets[net_name] = Net(net_name, self)
        return self.__nets[net_name]

    def remove_net(self, name: str):
        self.__check_if_primitive("remove net")

        net = self.__nets[name]
        net.disconnect_all_pins()
        del self.__nets[name]

    def rename_net(self, old_name: str, new_name: str):
        self.__check_if_primitive("rename net")
        self.__already_exists(new_name, self.__nets)

        net = self.__nets[old_name]
        net.name = new_name
        self.__nets[new_name] = net
        del self.__nets[old_name]


class Pin:
    def __init__(self, name: str, parent: Optional[object] = None):
        self.__name: str = name
        self.__owner: Optional[object] = parent

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def parent(self):
        return self.__owner


class PinRef:
    def __init__(self, pin: Pin, parent: Optional[object] = None):
        self.__pin = pin
        self.__net: Optional[Net] = None
        self.__parent = parent

    @property
    def name(self) -> str:
        return self.__pin.name

    @property
    def pin(self) -> Pin:
        return self.__pin

    @property
    def ref_parent(self):
        return self.__parent

    @property
    def net(self):
        return self.__net

    def connect_net(self, net: "Net"):
        self.__net = net

    def disconnect_net(self):
        self.__net = None


class Net:
    def __init__(self, name: str, parent: Block):
        self.__name = name
        self.__pins: list[PinRef] = []
        self.__parent = parent

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def pins(self) -> dict[str, PinRef]:
        return {pin.name: pin for pin in self.__pins}

    @property
    def parent(self) -> Block:
        return self.__parent

    def connect_pin(self, pin: PinRef):
        self.__pins.append(pin)
        pin.connect_net(self)

    def disconnect_pin(self, pin_name: str):
        pin = self.pins[pin_name]
        pin.disconnect_net()
        self.__pins.remove(pin)

    def disconnect_all_pins(self):
        for pin in self.__pins:
            pin.disconnect_net()
        self.__pins = []


class NetlistProject:
    def __init__(self, name: str, primitive_blocks: Dict[str, Block] = {}):
        self.__name: str = name
        self.__blocks: dict[str, Block] = deepcopy(primitive_blocks)
        self.__blocks_instances: dict[str, list[Instance]] = {
            block_name: [] for block_name in primitive_blocks
        }

    @property
    def name(self):
        return self.__name

    @property
    def blocks(self) -> Dict[str, Block]:
        return self.__blocks

    @property
    def blocks_instances(self) -> Dict[str, list[Instance]]:
        return self.__blocks_instances

    def add_primitive_block(self, name: str, primitive_pins: List[str]) -> Block:
        self.__already_exists(name, self.__blocks)

        self.__blocks[name] = Block(
            name, is_primitive=True, primitive_pins=primitive_pins
        )
        return self.__blocks[name]

    def remove_primitive_block(self, name: str):
        del self.__blocks[name]

    def __already_exists(self, name: str, collection: dict):
        if name in collection:
            raise Exception(f"{name} already exists in block {self.name}")

    def add_block(self, name: str) -> Block:
        self.__already_exists(name, self.__blocks)

        if name not in self.__blocks_instances:
            self.__blocks_instances[name] = []

        self.__blocks[name] = Block(name)
        return self.__blocks[name]

    def remove_block(self, name: str):
        del self.__blocks_instances[name]
        del self.__blocks[name]

    def rename_block(self, old_name: str, new_name: str):
        self.__already_exists(new_name, self.__blocks)

        block = self.__blocks[old_name]
        block.name = new_name
        self.__blocks[new_name] = block

        instances = self.__blocks_instances[old_name]
        self.__blocks_instances[new_name] = instances

        del self.__blocks_instances[old_name]
        del self.__blocks[old_name]

    def __update_block_instances(self, block_name: str):
        instances = self.__blocks_instances[block_name]
        for instance in instances:
            instance.update_pins()

    def add_pin_to_block(self, block_name: str, pin_name: str) -> PinRef:
        block = self.__blocks[block_name]
        self.__update_block_instances(block_name)
        print(block, pin_name)
        return block.add_interface_pin(pin_name)

    def remove_pin_from_block(self, block_name: str, pin_name: str):
        block = self.__blocks[block_name]
        block.remove_interface_pin(pin_name)
        self.__update_block_instances(block_name)

    def rename_pin_in_block(self, block_name: str, old_name: str, new_name: str):
        self.__blocks[block_name].rename_interface_pin(old_name, new_name)

    def add_instance_to_block(
        self, context_block_name: str, instance_name: str, instance_type_name: str
    ) -> Instance:
        block = self.__blocks[context_block_name]
        instance_type = self.__blocks[instance_type_name]
        instance = block.add_instance(instance_name, instance_type)
        self.__blocks_instances[instance_type_name].append(instance)

        return instance

    def remove_instance_from_block(self, context_block_name: str, instance_name: str):
        block = self.__blocks[context_block_name]
        instance = block.instances[instance_name]
        instance_type_name = instance.type.name

        block.remove_instance(instance_name)
        self.__blocks_instances[instance_type_name].remove(instance)

    def rename_instance_in_block(
        self, context_block_name: str, old_instance_name: str, new_instance_name: str
    ):
        self.__blocks[context_block_name].rename_instance(
            old_instance_name, new_instance_name
        )

    def add_net_to_block(self, block_name: str, net_name: str) -> Net:
        block = self.__blocks[block_name]
        return block.add_net(net_name)

    def remove_net_from_block(self, block_name: str, net_name: str):
        block = self.__blocks[block_name]
        block.remove_net(net_name)

    def rename_net_in_block(self, block_name: str, old_name: str, new_name: str):
        self.__blocks[block_name].rename_net(old_name, new_name)

    def connect_pin_to_net_in_block(
        self, block_name: str, net_name: str, pin_ref: PinRef
    ):
        block = self.__blocks[block_name]
        net = block.nets[net_name]
        net.connect_pin(pin_ref)

    def disconnect_pin_from_net_in_block(
        self, block_name: str, net_name: str, pin_name: str
    ):
        block = self.__blocks[block_name]
        net = block.nets[net_name]
        net.disconnect_pin(pin_name)


if __name__ == "__main__":
    # PRIMITIVES
    # ------------
    PRIMITIVES = {
        "transistor": Block("transistor", is_primitive=True, primitive_pins=["a", "b", "c"])
    }
    transistor = PRIMITIVES["transistor"]
    # ------------

    nl = NetlistProject("netlist", primitive_blocks=PRIMITIVES)
    main = nl.add_block("main")

    try:
        nl.add_block("main")
    except Exception as e:
        print(e)


    pin1 = nl.add_pin_to_block("main", "pin_1")
    pin2 = nl.add_pin_to_block("main", "pin_2")

    try:
        nl.add_pin_to_block("main", "pin_1")
    except Exception as e:
        print(e)

    t1 = nl.add_instance_to_block("main", "t1", "transistor")

    nl.rename_instance_in_block("main", "t1", "transistor_1")

    net1 = nl.add_net_to_block("main", "net1")

    nl.connect_pin_to_net_in_block(
        "main", "net1", nl.blocks["main"].interface_pins["pin_1"]
    )
    nl.rename_pin_in_block("main", "pin_1", "pin_3")

    nl.connect_pin_to_net_in_block("main", "net1", t1.interface_pins["a"])

    print(main.instances)

    nl.remove_instance_from_block("main", "transistor_1")

    print(main.interface_pins)
    print(net1.pins)

    nl.remove_pin_from_block("main", "pin_3")
    nl.remove_net_from_block("main", "net1")

    print(main.interface_pins)
    print(nl.blocks["main"].nets)
