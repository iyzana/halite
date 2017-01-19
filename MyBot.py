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
search_depth = 1

LOG_FILENAME = 'randomerror.log'
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

StrengthCombination = namedtuple('StrengthCombination', 'x y strength loss time')


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


def strength_combination_for_tile(tile, strength=None, loss=None, time=0, path=None):
    if strength is None:
        strength = tile.strength
    if loss is None:
        loss = production_next_tick(tile)
    wasted_strength = max(0, strength - 255)
    return StrengthCombination(tile.x, tile.y, min(255, strength), loss + wasted_strength, time), path

# [(s1, [(s2, [...]), (s3, None)]), ...]

def get_energy_source_paths(tile):
    max_strength = sum([t.strength for t in game_map.neighbors(tile, n=(search_depth + 1)) if t.owner == myId])
    max_production = sum([t.production for n in range(search_depth) for t in game_map.neighbors(tile, n=n+1) if t.owner == myId])

    if max_strength + max_production < tile.strength:
        return []

    possible_energy_sources = [get_strength_from(neighbor, tile.strength, set()) for neighbor in game_map.neighbors(tile) if neighbor.owner == myId]

    def construct_tuple(strength_combination):
        path = [combo[0] for combo in strength_combination]
        max_time = max(map(itemgetter(4), path))
        strength_sum = sum(map(itemgetter(2), path))
        loss_sum = sum(map(itemgetter(3), path))

        return strength_combination_for_tile(tile, strength=strength_sum, loss=loss_sum,
                                             time=max_time + 1, path=strength_combination)

    distinct_strength_combinations = merge_substrengths(possible_energy_sources)

    possible_energy_sources = [construct_tuple(strength_combination) for strength_combination in distinct_strength_combinations]

    # logging.debug("all paths {}".format(possible_energy_sources))
    strong_energy_sources = [source for source in possible_energy_sources if source[0].strength > tile.strength]
    strong_energy_sources = sorted(strong_energy_sources, key=lambda item: item[0].loss + item[0].time * tile.production)
    return strong_energy_sources


def get_strength_from(tile, needed_strength, visited, depth=0, strength_gain=0): # [node]
    if tile.strength + tile.production + strength_gain > needed_strength:
        if tile.strength > needed_strength:
            return [strength_combination_for_tile(tile)]
        else:
            return [strength_combination_for_tile(tile, strength=tile.strength + tile.production + strength_gain, time=1)]
    elif depth < search_depth:
        neighbors = [neighbor for neighbor in game_map.neighbors(tile) if
                     neighbor.owner == myId and neighbor not in visited]

        next_visited = visited.union(neighbors)
        next_visited.add(tile)

        def recursion_call(t):
            return get_strength_from(t, needed_strength - tile.strength - tile.production - strength_gain, next_visited,
                                     depth + 1, strength_gain + tile.production)

        neighbor_strengths = [recursion_call(neighbor) for neighbor in neighbors] # needs check for 0 strength

        def construct_tuple(strength_combination):
            path = [combo[0] for combo in strength_combination]
            max_time = max(map(itemgetter(4), path)) + 1
            strength_sum = tile.strength + max_time * tile.production + sum(map(itemgetter(2), path))
            loss_sum = max_time * tile.production + sum(map(itemgetter(3), path))

            return strength_combination_for_tile(tile, strength=strength_sum, loss=loss_sum,
                                                 time=max_time, path=strength_combination)

        distinct_strength_combinations = merge_substrengths(neighbor_strengths)

        result = [construct_tuple(strength_combination) for strength_combination in distinct_strength_combinations]

        if tile.strength + (tile.production + strength_gain) * 2 > needed_strength:
            result.append(strength_combination_for_tile(tile, strength=tile.strength + (tile.production + strength_gain) * 2, time=2))

        result.append(strength_combination_for_tile(tile))
        if current_tick < 30:
            result.append(strength_combination_for_tile(tile, strength=tile.strength + tile.production + strength_gain, time=1))
            result.append(strength_combination_for_tile(tile, strength=tile.strength + tile.production * 2 + strength_gain * 2, time=2))

        return result
    elif tile.strength + tile.production * 2 + strength_gain * 2 > needed_strength:
        return [strength_combination_for_tile(tile, strength=tile.strength + tile.production * 2 + strength_gain * 2, time=2)]
    else:
        if current_tick < 30:
            return [strength_combination_for_tile(tile, strength=tile.strength), strength_combination_for_tile(tile, strength=tile.strength + tile.production + strength_gain, time=1), strength_combination_for_tile(tile, strength=tile.strength + tile.production * 2 + strength_gain * 2, time=2)]
        if current_tick < 60 and tile.strength != 0:
            return [strength_combination_for_tile(tile)]
        return []
        # if current_tick < 100:
        #     return [strength_combination_for_tile(tile), strength_combination_for_tile(tile, strength=tile.strength + tile.production, time=1)]
        # else:
        #     return [strength_combination_for_tile(tile)]

# [[node]]
def merge_substrengths(neighbor_strengths):
    strength_combinations = [list(combination) for combination_length in range(len(neighbor_strengths)) for
                             combination in combinations(neighbor_strengths, combination_length + 1)]
    strength_combinations = [list(flat) for item in strength_combinations for flat in product(*item)]

    distinct_strength_combinations = []
    for strength_combination in strength_combinations:
        tiles = tile_list(strength_combination)
        if len(tiles) == len(set(map(get_pos, tiles))):
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
            node = game_map.contents[parent.y][parent.x]
            border_moves.append(Move(node, STILL))
    else:
        if border_tile_moves[1]:
            for child in border_tile_moves[1]:
                border_moves.extend(get_moves(child))

    return border_moves


def get_pos(data):
    if data is Move:
        return get_pos(data.square)
    return data.x, data.y

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

    tile_capture_moves = [(tile, get_energy_source_paths(tile)) for tile in borders]
    tile_capture_moves = list(filter(lambda t: len(t[1]) > 0, tile_capture_moves))

    planned_tiles = set()

    while tile_capture_moves:
        sorted_capture_moves = sorted(tile_capture_moves, reverse=True, key=lambda t: t[0].production*(10-t[1][0][0].time)-t[1][0][0].loss-(t[0].strength / 8)) # 25 36

        best_move = sorted_capture_moves[0][1][0]

        if current_tick == 35:
        # for stuff in tile_capture_moves:
            logging.debug("sorted moves: {}".format(sorted_capture_moves))

        moves.extend(get_moves(best_move))

        planned_tiles = planned_tiles.union(map(get_pos, tile_list([best_move])))

        new_tile_capture_moves = []

        for tile, possible_moves_for_border in tile_capture_moves:
            still_possible_moves_for_border = []

            for possible_moves in possible_moves_for_border:
                moves_flat = set(map(get_pos, tile_list([possible_moves])))
                if current_tick == 35:
                    logging.debug("moves flat: {}".format(moves_flat))
                    logging.debug("planned_tiles: {}".format(planned_tiles))
                if len(moves_flat - planned_tiles) == len(moves_flat):
                    still_possible_moves_for_border.append(possible_moves)

            if still_possible_moves_for_border:
                new_tile_capture_moves.append((tile, still_possible_moves_for_border))

        tile_capture_moves = new_tile_capture_moves

        # worth = tile.production*(10-time)-tile.strength

    # distinct_moves = {}
    # for capture_move in capture_moves_list:
    #     if not any(capture_move.square.x == sq.x and capture_move.square.y == sq.y for sq in distinct_moves.keys()):
    #         distinct_moves[capture_move.square] = capture_move

    # moves.extend(distinct_moves.values())

    if borders:
        unmoved_colony = [tile for tile in game_map if (is_inner(tile)) and (should_get_out(tile))]

        for tile in unmoved_colony:
            nearest_tile = sorted(borders.copy(), key=lambda border: game_map.get_distance(border, tile))[0]

            dx = game_map.get_distance_x(tile, nearest_tile)
            dy = game_map.get_distance_y(tile, nearest_tile)

            if abs(dx) > abs(dy):
                direction = WEST if dx < 0 else EAST
            else:
                direction = SOUTH if dy > 0 else NORTH

            logging.debug("from {} to {} dx {} dy {} direction {}".format(tile, nearest_tile, dx, dy, direction))

            moves.append(Move(tile, direction))

    hlt.send_frame(moves)


def friendly_neighbors(tile):
    return len([n for n in game_map.neighbors(tile, n=search_depth+1) if n.owner == myId])


def is_inner(tile):
    return tile.owner == myId and friendly_neighbors(tile) == 2 * (search_depth + 1) * (search_depth + 2)


def should_get_out(tile):
    return tile.strength > 5 * tile.production


current_tick = 0

while True:
    logging.debug("----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- tick {}".format(current_tick))
    start = time.time()
    tick()
    current_tick += 1
    logging.debug("used time: {}ms".format(round((time.time() - start)*1000)))
