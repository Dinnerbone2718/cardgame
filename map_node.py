import itertools


class MapNode:
    _id_counter = itertools.count()

    def __init__(self, node_type, x=0, y=0, node_id=None):
        self.id = node_id if node_id is not None else next(MapNode._id_counter)
        self.node_type = node_type
        self.x = x
        self.y = y
        self.connections = set()
        self.visited = False

        self.shop_stock = None
        self.unit_stock = None
        self.shop_entered = False
        self.upgrade_entered = False
        self.card_entered = False
        self.fight_config = None

    def connect(self, other, bidirectional=False):
        self.connections.add(other)
        if bidirectional:
            other.connections.add(self)
        return other

    def is_connected_to(self, other):
        return other in self.connections

    def switch_node_type(self, new_type):
        self.node_type = new_type

    def __repr__(self):
        return f"MapNode({self.node_type}, id={self.id})"