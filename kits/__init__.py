"""Domain shell kits. All bmesh / bpy.data — no bpy.ops."""

from .beach import build_shell as beach
from .city import build_shell as city
from .forest import build_shell as forest
from .generic import build_shell as generic
from .interior import build_shell as interior
from .park import build_shell as park
from .space import build_shell as space
from .zoo import build_shell as zoo

KITS = {
    "interior": interior,
    "park": park,
    "forest": forest,
    "city": city,
    "zoo": zoo,
    "space": space,
    "beach": beach,
    "generic": generic,
}
