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


StrengthCombination = namedtuple('StrengthCombination', 'x y strength production time')


def strength_combination_for_tile(tile, strength=tile.strength, production=production_next_tick(tile), time=0):
    wasted_strength = max(0, 255 - strength)
    return [(StrengthCombination(tile.x, tile.y, min(255, strength), production + wasted_strength, time), None)]


# def get_strength_from_adjacent(current, needed_strength, visited, depth=0):
#     if (depth > 1) or (needed_strength < 0):
#         return strength_combination_for_tile(current)
#
#     neighbors = [neighbor for neighbor in game_map.neighbors(current) if neighbor.owner == myId and neighbor not in visited]
#
#     next_visited = visited.union(neighbors)
#     next_visited.add(current)
#     neighbor_strengths = map(lambda n: get_strength_from_adjacent(n, needed_strength - n.strength, next_visited, depth + 1), neighbors)
#     neighbor_strengths = [x for y in neighbor_strengths for x in y if x[0].strength != 0]
#
#     strength_combinations = [list(combination) for combination_length in range(len(neighbor_strengths)) for combination in
#                              combinations(neighbor_strengths, combination_length + 1)]
#
#     distinct_strength_combinations = []
#
#     for strength_combination in strength_combinations:
#         if len(strength_combination) == len(set(map(lambda t: (t[0].x, t[0].y), strength_combination))):
#             distinct_strength_combinations.append(strength_combination)
#
#     def construct_sc(strength, previous_loss, time):
#         return StrengthCombination(current.x, current.y, min(255, strength), max(0, strength - 255) + (production_next_tick(current) if depth != 0 else 0) + previous_loss, time)
#
#    # strength_combinations_for_current_neighbors = [(construct_sc(((current.strength + current.production) if depth != 0 else 0) + n.strength, n.production, 1), strength_combination_for_tile(n)) for n in neighbors if n.strength != 0]
#
#     def construct_tuple(strength_combination):
#         path = [combo[0] for combo in strength_combination]
#         strength_sum = sum(map(itemgetter(2), path))
#         production_sum = sum(map(itemgetter(3), path))
#         max_time = max(map(itemgetter(4), path))
#
#         # if max_time == 0:
#         #     return None
#
#         if depth != 0:
#             strength_sum = current.strength + strength_sum + current.production
#
#         return construct_sc(strength_sum, production_sum, max_time + 1), strength_combination
#
#     strength_combinations_data = [construct_tuple(strength_combination) for strength_combination in distinct_strength_combinations]
#
#     if depth != 0:
#         if current.strength >= needed_strength:
#             strength_combinations_data.extend(strength_combination_for_tile(current))
#         elif (current.strength + current.production) > needed_strength:
#             logging.debug("next tick stuff")
#             strength_combinations_data.append((StrengthCombination(current.x, current.y, current.strength + current.production, production_next_tick(current), 1), None))
#
#     return strength_combinations_data
#
#
# def get_energy_source_paths(tile):
#     possible_energy_sources = get_strength_from_adjacent(tile, tile.strength, set())
#     # logging.debug("all paths {}".format(possible_energy_sources))
#     strong_energy_sources = [source for source in possible_energy_sources if source[0].strength >= tile.strength]
#     strong_energy_sources = sorted(strong_energy_sources, key=lambda item: (item[0].time, item[0].production))
#     return strong_energy_sources

# [(s1, [(s2, [...]), (s3, None)]), ...]

def get_energy_source_paths(tile):
    max_strength = sum([t.strength for t in game_map.neighbors(tile, n=2)])
    max_production = sum([t.production for t in game_map.neighbors(tile)])

    if max_strength + max_production < tile.strength:
        return []

    possible_energy_sources = [source for neighbor in game_map.neighbors(tile) if neighbor.owner == myId for source in
                               get_strength_from(neighbor, tile.strength, set())]

    possible_energy_sources = merge_substrengths(possible_energy_sources)

    # logging.debug("all paths {}".format(possible_energy_sources))
    strong_energy_sources = [source for source in possible_energy_sources if source[0].strength >= tile.strength]
    strong_energy_sources = sorted(strong_energy_sources, key=lambda item: (item[0].time, item[0].production))
    return strong_energy_sources


def get_strength_from(tile, needed_strength, visited, depth=0):
    if tile.strength + tile.production >= needed_strength:
        if tile.strength >= needed_strength:
            return [strength_combination_for_tile(tile)]
        else:
            return [strength_combination_for_tile(tile, strength=tile.strength + tile.production)]
    elif depth < 1:
        # if the sum of all tiles is too low
        if sum([t.strength for t in game_map.neighbors(tile)]) + tile.strength + tile.production < needed_strength:
            return []

        neighbors = [neighbor for neighbor in game_map.neighbors(current) if
                     neighbor.owner == myId and neighbor not in visited]

        next_visited = visited.union(neighbors)
        next_visited.add(current)

        def recursion_call(t):
            return get_strength_from_adjacent(t, needed_strength - tile.strength - tile.production, next_visited,
                                              depth + 1)

        neighbor_strengths = [result for neighbor in neighbors for result in recursion_call(neighbor) if
                              result[0].strength != 0]

        return merge_substrengths(neighbor_strengths)
    else:
        return []


def merge_substrengths(neighbor_strengths):
    strength_combinations = [list(combination) for combination_length in range(len(neighbor_strengths)) for
                             combination in combinations(neighbor_strengths, combination_length + 1)]
    distinct_strength_combinations = []
    for strength_combination in strength_combinations:
        tiles = tile_list(strength_combination)
        if len(tiles) == len(set(map(lambda t: (t.x, t.y), tiles))):
            distinct_strength_combinations.append(strength_combination)

    def construct_tuple(strength_combination):
        path = [combo[0] for combo in strength_combination]
        strength_sum = sum(map(itemgetter(2), path))
        production_sum = sum(map(itemgetter(3), path))
        max_time = max(map(itemgetter(4), path))

        return strength_combination_for_tile(tile, strength=strength_sum, production=production_sum, time=max_time + 1)

    return [construct_tuple(strength_combination) for strength_combination in distinct_strength_combinations]


def tile_list(combination):
    tiles = []
    for c in combinations:
        tiles.append(c[0])
        if c[1] is not None:
            tiles.extend(tile_list(c[1]))
    return tiles


def tick():
    game_map.get_frame()
    moves.clear()

    borders = list(find_borders())

    # if current_tick == 100:
    for border in borders:
        # border = borders[0]
        # logging.debug("examined border {}".format(border))
        possible_paths = get_energy_source_paths(border)
        # logging.debug("possible paths {}".format(possible_paths))

    tile_capture_moves = {tile: get_capture_moves(tile) for tile in borders}
    tile_capture_moves = dict(filter(lambda t: len(t[1]) > 0, tile_capture_moves.items()))

    tile_capture_moves = [(tile.production, capture_moves) for tile, capture_moves in tile_capture_moves.items()]
    capture_moves_dict = sorted(tile_capture_moves, reverse=True)
    capture_moves_list = map(itemgetter(1), capture_moves_dict)
    all_capture_moves = [capture_move.move for capture_moves in capture_moves_list for capture_move in capture_moves]

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
