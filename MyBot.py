import hlt
from collections import namedtuple
from itertools import combinations
import logging
import random

from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square

LOG_FILENAME = 'randomerror.log'
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

myId, game_map = hlt.get_init()
hlt.send_init('randomerror')
moves = []

CaptureMove = namedtuple('CaptureMove', 'move time')


def find_borders():
    colony = [tile for tile in game_map if tile.owner == myId]

    border = set()

    for tile in colony:
        others = [neighbor for neighbor in game_map.neighbors(tile) if neighbor.owner != myId]
        border.update(others)

    return border


def production_next_tick(tile):
    return min(255 - tile.strength, tile.production)


def get_capture_moves(capturee):
    assert capturee.owner != myId, "can't get capture moves to own tile"

    adjacent = [tile for tile in game_map.neighbors(capturee) if tile.owner == myId]

    distance = {}  # wasted_energy: [[tiles_to_move]]

    for i in range(len(adjacent)):
        subsets = combinations(adjacent, i + 1)
        for subset in subsets:
            total_strength = sum([tile.strength for tile in subset])
            if total_strength > capturee.strength:
                wasted_energy = sum([production_next_tick(tile) for tile in subset])
                if wasted_energy not in distance:
                    distance[wasted_energy] = []
                distance[wasted_energy].append(subset)

    if not distance:
        return []  # needs more recursion

    less_waste = sorted(distance.items())[0][1]
    if len(less_waste) > 1:
        logging.debug("it could actually make a difference")
    less_waste = less_waste[0]

    return [CaptureMove(Move(tile, game_map.get_direction(tile, capturee)), 0) for tile in less_waste]


def tick():
    game_map.get_frame()
    moves.clear()

    border = find_borders()

    tile_capture_moves = {tile: get_capture_moves(tile) for tile in border}
    tile_capture_moves = {k: v for k, v in tile_capture_moves.items() if v}

    if len(tile_capture_moves) != 0:
        sorted_capture_moves_dict = sorted(tile_capture_moves.items(), key=lambda item: item[0].production)
        sorted_capture_moves_dict.reverse()
        all_capture_moves = [capture_move.move for capture_moves_dict_entry in sorted_capture_moves_dict for capture_move in capture_moves_dict_entry[1]]

        moves.extend(all_capture_moves)

    unmoved_colony = [tile for tile in game_map if tile.owner == myId and tile.strength >= 200]
    for tile in unmoved_colony:
        moves.append(Move(tile, random.choice((NORTH, WEST))))

    hlt.send_frame(moves)


while True:
    tick()
