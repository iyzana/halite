import hlt

from operator import itemgetter
from collections import namedtuple
from itertools import combinations, product
import logging
import time

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


def strength_combination_for_tile(tile, strength=None, production=None, time=0, path=None):
    if strength is None:
        strength = tile.strength
    if production is None:
        production = production_next_tick(tile)
    wasted_strength = max(0, strength - 255)
    return StrengthCombination(tile.x, tile.y, min(255, strength), production + wasted_strength, time), path


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
    max_strength = sum([t.strength for t in game_map.neighbors(tile, n=2) if t.owner == myId])
    max_production = sum([t.production for t in game_map.neighbors(tile) if t.owner == myId])

    if max_strength + max_production < tile.strength:
        return []

    possible_energy_sources = [get_strength_from(neighbor, tile.strength, set()) for neighbor in game_map.neighbors(tile) if neighbor.owner == myId]

    def construct_tuple(strength_combination):
        path = [combo[0] for combo in strength_combination]
        max_time = max(map(itemgetter(4), path))
        strength_sum = sum(map(itemgetter(2), path))
        production_sum = sum(map(itemgetter(3), path))

        return strength_combination_for_tile(tile, strength=strength_sum, production=production_sum,
                                             time=max_time + 1, path=strength_combination)

    distinct_strength_combinations = merge_substrengths(possible_energy_sources)

    possible_energy_sources = [construct_tuple(strength_combination) for strength_combination in distinct_strength_combinations]

    # logging.debug("all paths {}".format(possible_energy_sources))
    strong_energy_sources = [source for source in possible_energy_sources if source[0].strength >= tile.strength]
    strong_energy_sources = sorted(strong_energy_sources, key=lambda item: (item[0].time, item[0].production))
    return strong_energy_sources


def get_strength_from(tile, needed_strength, visited, depth=0):
    if tile.strength + tile.production >= needed_strength:
        if tile.strength >= needed_strength:
            return [strength_combination_for_tile(tile)]
        else:
            return [strength_combination_for_tile(tile, strength=tile.strength + tile.production, time=1)]
    elif depth < 2:
        neighbors = [neighbor for neighbor in game_map.neighbors(tile) if
                     neighbor.owner == myId and neighbor not in visited]

        next_visited = visited.union(neighbors)
        next_visited.add(tile)

        def recursion_call(t):
            return get_strength_from(t, needed_strength - tile.strength - tile.production, next_visited,
                                     depth + 1)

        neighbor_strengths = [recursion_call(neighbor) for neighbor in neighbors] # needs check for 0 strength

        def construct_tuple(strength_combination):
            path = [combo[0] for combo in strength_combination]
            max_time = max(map(itemgetter(4), path)) + 1
            strength_sum = tile.strength + max_time * tile.production + sum(map(itemgetter(2), path))
            production_sum = max_time * tile.production + sum(map(itemgetter(3), path))

            return strength_combination_for_tile(tile, strength=strength_sum, production=production_sum,
                                                 time=max_time, path=strength_combination)

        distinct_strength_combinations = merge_substrengths(neighbor_strengths)

        return [construct_tuple(strength_combination) for strength_combination in distinct_strength_combinations]
    else:
        return []


def merge_substrengths(neighbor_strengths):
    strength_combinations = [list(combination) for combination_length in range(len(neighbor_strengths)) for
                             combination in combinations(neighbor_strengths, combination_length + 1)]
    strength_combinations = [list(flat) for item in strength_combinations for flat in product(*item)]

    distinct_strength_combinations = []
    for strength_combination in strength_combinations:
        tiles = tile_list(strength_combination)
        if len(tiles) == len(set(map(lambda t: (t.x, t.y), tiles))):
            distinct_strength_combinations.append(strength_combination)

    return distinct_strength_combinations


def tile_list(combination):
    tiles = []
    for c in combination:
        tiles.append(c[0])
        if (len(c) > 1) and (c[1] is not None):
            tiles.extend(tile_list(c[1]))
    return tiles

def get_moves(border_tile_moves):
    border_moves = []
    parent = border_tile_moves[0]

    if game_map.contents[parent.y][parent.x] in list(map(itemgetter(0), moves)):
        return []

    if parent.time == 1:
        if border_tile_moves[1]:
            for sc, _ in border_tile_moves[1]:
                child = game_map.contents[sc.y][sc.x]
                border_moves.append(Move(child, game_map.get_direction(child, game_map.contents[parent.y][parent.x])))
        else:
            child = game_map.contents[border_tile_moves[0].y][border_tile_moves[0].x]
            border_moves.append(Move(child, STILL))
    else:
        for child in border_tile_moves[1]:
            border_moves.extend(get_moves(child))

    return border_moves

def tick():
    game_map.get_frame()
    moves.clear()

    borders = list(find_borders())

    # if current_tick == 100:
    # for border in borders:
        # border = borders[0]
        # logging.debug("examined border {}".format(border))
        # possible_paths = get_energy_source_paths(border)
        # logging.debug("possible paths {}".format(possible_paths))

    tile_capture_moves = [(tile, get_energy_source_paths(tile)) for tile in borders if tile.production > 0]
    tile_capture_moves = filter(lambda t: len(t[1]) > 0, tile_capture_moves)

    planned_tiles = []

    sorted_capture_moves = sorted(tile_capture_moves, reverse=True, key=lambda t: t[0].production*(10-t[1][0][0].time)-t[0].strength)

    best_move = sorted_capture_moves[0][1][0]

    planned_tiles.extend(best_move)

    capture_moves_list = list(map(lambda cm: cm[1][0], sorted_capture_moves))

    # worth = tile.production*(10-time)-tile.strength


    if capture_moves_list:
        logging.debug("capture moves: {}".format(capture_moves_list[0]))

        for border_tile_moves in capture_moves_list:
            moves.extend(get_moves(border_tile_moves))

    # distinct_moves = {}
    # for capture_move in capture_moves_list:
    #     if not any(capture_move.square.x == sq.x and capture_move.square.y == sq.y for sq in distinct_moves.keys()):
    #         distinct_moves[capture_move.square] = capture_move

    # moves.extend(distinct_moves.values())

    unmoved_colony = [tile for tile in game_map if (is_inner(tile)) and (should_get_out(tile))]
    for tile in unmoved_colony:
        moves.append(Move(tile, SOUTH if tile.production%2 else WEST))

    hlt.send_frame(moves)


def friendly_neighbors(tile):
    return len([n for n in game_map.neighbors(tile, n=2) if n.owner == myId])


def is_inner(tile):
    return tile.owner == myId and friendly_neighbors(tile) == 12


def should_get_out(tile):
    return tile.strength > 5 * tile.production


current_tick = 0

while True:
    logging.debug("----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- tick {}".format(current_tick))
    current_tick += 1
    start = time.time()
    tick()
    logging.debug("used time: {}ms".format(round((time.time() - start)*1000)))
