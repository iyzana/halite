import hlt

from operator import itemgetter
from collections import namedtuple
from itertools import combinations
import logging
import random

from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square

myId, game_map = hlt.get_init()
hlt.send_init('randomerror')
moves = []

LOG_FILENAME = 'randomerror.log'
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

CaptureMove = namedtuple('CaptureMove', 'move time')


def find_borders():
    colony = [tile for tile in game_map if tile.owner == myId]

    border = set()

    for tile in colony:
        others = [neighbor for neighbor in game_map.neighbors(tile) if neighbor.owner != myId]
        border.update(others)

    return border


def total_strength(obj):
    if isinstance(obj, Square):
        return obj.strength
    elif isinstance(obj, (list, set, tuple)):
        return sum([o.strength for o in obj])
    else:
        raise TypeError("can't get strength for {}".format(type(obj)))


def production_next_tick(tile):
    return min(255 - tile.strength, tile.production)


def get_capture_moves(capturee):
    adjacents = [tile for tile in game_map.neighbors(capturee) if ((tile.owner == myId) and (tile.strength > 0))]

    if not adjacents:
        return []

    return get_capture_moves_internal(adjacents, capturee, 0)


def get_capture_moves_internal(adjacents, capturee, t=0):
    min_wasted = None
    least_waste = None

    adjacent_combinations = [combination for combination_length in range(len(adjacents)) for combination in
                             combinations(adjacents, combination_length + 1)]

    strong_combinations = [c for c in adjacent_combinations if (total_strength(c) > capturee.strength)]

    if not strong_combinations:
        # if t == 0:
        #     for adjacent in adjacents:
        #         adjacent.strength += adjacent.production
        #
        #     capture_moves = get_capture_moves_internal(adjacents, capturee, 1)
        #
        #     if not capture_moves:
        #         pass
        #
        #     for adjacent in adjacents:
        #         adjacent.strength -= adjacent.production
        #
        #     if capture_moves:
        #         return capture_moves
        # else:
        return []  # needs more recursion

    for subset in strong_combinations:
        wasted_energy = sum(map(production_next_tick, subset))
        if least_waste is None or wasted_energy < min_wasted:
            least_waste = [subset]
            min_wasted = wasted_energy
        elif wasted_energy == min_wasted:
            least_waste.append(subset)
        else:
            continue

    if len(least_waste) > 1:
        least_waste = sorted(least_waste, key=total_strength, reverse=True)
        logging.debug("it could actually make a difference {}".format(least_waste))
        logging.debug("took {}".format(least_waste[0]))
    least_waste = least_waste[0]

    return [CaptureMove(Move(tile, game_map.get_direction(tile, capturee)), t) for tile in least_waste]


StrengthCombination = namedtuple('StrengthCombination', 'x y strength production')


def calc_path_strength(current, path, depth):
    path_sum = sum([combi[0].strength for combi in path])

    if depth != 0:
        return current.strength + path_sum + current.production
    else:
        return path_sum


def calc_previous_loss(path):
    path_sum = sum([combi[0].production for combi in path])

    return path_sum


def strength_combination_for_tile(tile):
    return [(StrengthCombination(tile.x, tile.y, tile.strength, production_next_tick(tile)), None)]


def get_strength_from_adjacent(current, needed_strength, visited, depth=0):
    # logging.debug(needed_strength)
    if (depth > 1) or (needed_strength < 0):
        return strength_combination_for_tile(current)

    neighbors = [neighbor for neighbor in game_map.neighbors(current) if neighbor.owner == myId and neighbor not in visited]

    next_visited = visited.union(neighbors)
    next_visited.add(current)
    neighbor_strengths = map(lambda n: get_strength_from_adjacent(n, needed_strength - ((current.strength + current.production) if depth != 0 else 0), next_visited, depth + 1), neighbors)
    neighbor_strengths = [x for y in neighbor_strengths for x in y if x[0].strength != 0]

    strength_combinations = [list(combination) for combination_length in range(len(neighbor_strengths)) for combination in
                             combinations(neighbor_strengths, combination_length + 1)]

    distinct_strength_combinations = []

    for strength_combination in strength_combinations:
        if len(strength_combination) == len(set(map(lambda x: (x[0].x, x[0].y), strength_combination))):
            distinct_strength_combinations.append(strength_combination)

    def construct_sc(strength, previous_loss):
        return StrengthCombination(current.x, current.y, min(255, strength), max(0, strength - 255) + production_next_tick(current) + previous_loss)

    strength_combinations_for_current_neighbors = [(construct_sc(((current.strength + current.production) if depth != 0 else 0) + n.strength, n.production), strength_combination_for_tile(n)) for n in neighbors if n.strength != 0]

    def construct_tuple(strength_combination):
        path = [(combi[0].strength, combi[0].production) for combi in strength_combination]
        strength_sum = sum(map(itemgetter(0), path))
        production_sum = sum(map(itemgetter(1), path))

        if depth != 0:
            strength_sum = current.strength + strength_sum + current.production

        return construct_sc(strength_sum, production_sum), strength_combination

    strength_combinations_for_rest = [construct_tuple(strength_combination) for strength_combination in distinct_strength_combinations if len(strength_combination) > 1]

    return strength_combinations_for_current_neighbors + strength_combinations_for_rest


# [(s1, [(s2, [...]), (s3, None)]), ...]

def tick():
    game_map.get_frame()
    moves.clear()

    borders = list(find_borders())

    if current_tick == 100:
        logging.debug("examined border {}".format(borders[0]))
        logging.debug(get_strength_from_adjacent(borders[0], borders[0].strength, set()))

    tile_capture_moves = {tile: get_capture_moves(tile) for tile in borders}
    tile_capture_moves = dict(filter(lambda t: len(t[1]) > 0, tile_capture_moves.items()))

    tile_capture_moves = [(tile.production, capture_moves) for tile, capture_moves in tile_capture_moves.items()]
    capture_moves_dict = sorted(tile_capture_moves, reverse=True)
    capture_moves_list = map(itemgetter(1), capture_moves_dict)
    all_capture_moves = [capture_move.move for capture_moves in capture_moves_list
                         for capture_move in capture_moves]

    distinct_moves = {}
    for capture_move in all_capture_moves:
        if not any(capture_move.square.x == sq.x and capture_move.square.y == sq.y for sq in distinct_moves.keys()):
            distinct_moves[capture_move.square] = capture_move

    moves.extend(distinct_moves.values())

    unmoved_colony = [tile for tile in game_map if (is_inner(tile)) and (should_get_out(tile))]
    for tile in unmoved_colony:
        moves.append(Move(tile, random.choice((NORTH, WEST))))

    hlt.send_frame(moves)


def friendly_neighbors(tile):
    return len([n for n in game_map.neighbors(tile) if n.owner == myId])


def is_inner(tile):
    return tile.owner == myId and friendly_neighbors(tile) == 4


def should_get_out(tile):
    return tile.strength > 5 * tile.production


current_tick = 0

while True:
    logging.debug("tick {}".format(current_tick))
    current_tick += 1
    tick()
