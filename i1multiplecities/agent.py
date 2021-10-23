import math, sys
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import logging
import random as rand

logging.basicConfig(filename='agent.log', level=logging.INFO)



DIRECTIONS = Constants.DIRECTIONS
game_state = None
build_location = None
delayed_movements = {}

    ### FUNCTIONS GO HERE ###



# returns direction to location which avoids city_tiles in the way
def get_directions(unit, game_state, target_tile, avoids_friendly_city_tiles):
    if unit.id in delayed_movements.keys():
        move_info = delayed_movements.pop(unit.id)
        return move_info[0], move_info[1]
        



    # decrease x -> "w"
    # increase x -> "e"
    # decrease y -> "n"
    # decrease y -> "s"
    
    logging.info("routing to " + str(target_tile.pos))
    delta_x = unit.pos.x - target_tile.pos.x
    delta_y = unit.pos.y - target_tile.pos.y

    direction_options = []
    move_tile_options = []
    if delta_x < 0:
            direction_options.append("e")
            move_tile_options.append(game_state.map.get_cell(x= unit.pos.x + 1, y= unit.pos.y))
    
    if delta_x > 0:
            direction_options.append("w")
            move_tile_options.append(game_state.map.get_cell(x= unit.pos.x - 1, y= unit.pos.y))

    if delta_y < 0:
            direction_options.append("s")
            move_tile_options.append(game_state.map.get_cell(x= unit.pos.x, y= unit.pos.y + 1))

    if delta_y > 0:
            direction_options.append("n")
            move_tile_options.append(game_state.map.get_cell(x= unit.pos.x, y= unit.pos.y - 1))

    final_direction_options = []
    final_tile_options = []

    for i, cell_in_direction in enumerate(move_tile_options):
        enemy_city = False
        if cell_in_direction.citytile == None or not avoids_friendly_city_tiles:
            if cell_in_direction.citytile != None:
                if cell_in_direction.citytile.team != game_state.id:
                    enemy_city = True
            if enemy_city == False:
                final_direction_options.append(direction_options[i])
                final_tile_options.append(cell_in_direction)

    if len(final_direction_options) > 0:
        logging.info("found direction(s) -> directions = " + str(final_direction_options))

        return final_direction_options[0], final_tile_options[0]

    elif len(direction_options) == 1:
        delayed_movements[unit.id] = [direction_options[0], move_tile_options[0]]
        return rand.choice(['e', 'w', 'n', 's']), None
    else:
        logging.info("seems stuck?")
        return "c", None #game_state.map.get_cell(x= unit.pos.x, y= unit.pos.y)



# returns true if tile exists (is not beyond map border)
def tile_on_map(tile_pos, width, height):
    if tile_pos.x >= 0 and tile_pos.y >= 0:
        if tile_pos.x < width and tile_pos.y < height:
            return True
    return False



# creates a list of all resource tiles on the map for iteration
def determine_resource_tiles(game_state, height, width):
    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles



# iterates through resource_tiles to find the one closest to a given unit
def determine_closest_resource_tile(resource_tiles, unit, player):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD and resource_tile.resource.amount < 300: continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(unit.pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile



#   iterates through cities, then through each cities citytiles, to find city_tile closest to unit
def determine_closest_city_tile(player, unit):
    closest_dist = math.inf
    closest_city_tile = None
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile



#   iterates through player's cities, then through city's tiles to determine count of a player's cityTiles
def count_citytiles(player):
    count = 0
    for k, city in player.cities.items():
        count += len(city.citytiles)
    return count



#   picks a location upon which a new citytile should be built by worker
def determine_new_city_location(cities, game_state, unit):
    logging.info('determining where to build new city')
    location = None
    possible_city_locations = []
    for city in cities:
        if len(cities) == 1:
            for citytile in city.citytiles:
                for dir in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    pos_in_dir = Position(x=citytile.pos.x + dir[0], y=citytile.pos.y + dir[1])
                    logging.info('checking tile at ' + str(pos_in_dir) +' for existence -> ' + str(tile_on_map(pos_in_dir, game_state.map.width, game_state.map.height)))
                    if tile_on_map(pos_in_dir, game_state.map.width, game_state.map.height):
                        valid_tile_in_dir = game_state.map.get_cell_by_pos(pos_in_dir)
                        if valid_tile_in_dir.has_resource() == False and valid_tile_in_dir.citytile == None:
                            possible_city_locations.append(valid_tile_in_dir)

    logging.info("possible city locations: " + str(possible_city_locations))
    
    # find the closest option to worker (prioritizing diagonal distances over straight distances)
    least_dist = math.inf
    least_higher_single_coordinate_dist = math.inf #used to prioritize diagonal distances over direct distances
    closest_option = None
    for build_loc_option in possible_city_locations:
        option_dist = build_loc_option.pos.distance_to(unit.pos)
        higher_single_coord_dist = max(abs(build_loc_option.pos.x - unit.pos.x), abs(build_loc_option.pos.y - unit.pos.y))
        if  option_dist < least_dist:
            least_dist, least_higher_single_coordinate_dist, closest_option = option_dist, higher_single_coord_dist, build_loc_option
        elif option_dist == least_dist:
            if higher_single_coord_dist < least_higher_single_coordinate_dist:
                least_dist, least_higher_single_coordinate_dist, closest_option = option_dist, higher_single_coord_dist, build_loc_option

    return closest_option


def agent(observation, configuration):
    global game_state
    global build_location

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []


    # handles movement (probably has multiple returns since it has to deal with actions tile_where_unit_is_moving)
    def handle_unit_movement(unit, game_state, move_dir, move_tile, movement_picked):
        if move_tile not in tiles_where_unit_is_moving:
            
            actions.append(unit.move(move_dir))
            

            movement_picked = True
            if move_tile != None:
                actions.append(annotate.text(move_tile.pos.x, move_tile.pos.y, str(unit.id)))
                if move_tile.citytile == None:
                    tiles_where_unit_is_moving.append(move_tile)
        return movement_picked





    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    cityTile_count = count_citytiles(player)
    logging.info(cityTile_count)
    resource_tiles = determine_resource_tiles(game_state, height, width)
    cities = list(player.cities.values())

    max_cities = 30
    min_city_fuel = 500
    build_city = False

    tiles_where_unit_is_moving = []
    units_added_this_turn = 0


    if cityTile_count < max_cities and cities[0].fuel > min_city_fuel * cityTile_count:
        
        build_city = True


    
    
    for city in cities:
        for cityTile in city.citytiles:
            if cityTile.can_act():
                if len(player.units) + units_added_this_turn < cityTile_count:
                    actions.append(cityTile.build_worker())
                    units_added_this_turn += 1
                else:
                    actions.append(cityTile.research())

    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.is_worker() and unit.can_act():
            movement_picked = False
                    
            if unit.get_cargo_space_left() > 0:
                logging.info("looking for resources")

                closest_resource_tile = determine_closest_resource_tile(resource_tiles, unit, player)
                
                if closest_resource_tile is not None:
                    move_dir, move_tile = get_directions(unit, game_state, closest_resource_tile, False)
                    movement_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_picked)

                    # if move_tile not in tiles_where_unit_is_moving:
                    #     tiles_where_unit_is_moving.append(move_tile)
                    #     actions.append(unit.move(move_dir))
                    #     movement_picked = True

                    # actions.append(unit.move(unit.pos.direction_to(closest_resource_tile.pos)))
            else:
                
                if build_city:
                    if build_location is None:
                        actions.append(annotate.circle(game_state.id, 0))

                        build_location = determine_new_city_location(cities, game_state, unit)
                        logging.info(build_location)
                    else:
                        actions.append(annotate.circle(build_location.pos.x, build_location.pos.y))

                        if unit.pos == build_location.pos:

                            actions.append(unit.build_city())
                            build_city = False
                            build_location = None

                        else:
                            move_dir, move_tile = get_directions(unit, game_state, build_location, True)
                            movement_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_picked)
                            
                            
                            # if move_tile not in tiles_where_unit_is_moving:
                            #     tiles_where_unit_is_moving.append(move_tile)
                            #     actions.append(unit.move(move_dir))
                            #     movement_picked = True
    
                # if not build_city, and if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                elif len(player.cities) > 0:
                    logging.info('replenishing city fuel')
                    closest_city_tile = determine_closest_city_tile(player, unit)

                    if closest_city_tile is not None:
                        move_dir, move_tile = get_directions(unit, game_state, closest_city_tile, False)
                        movement_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_picked)
                        
                        
                        
                        # if move_tile not in tiles_where_unit_is_moving:
                        #     tiles_where_unit_is_moving.append(move_tile)
                        #     actions.append(unit.move(move_dir))
                        #     movement_picked = True

                        # move_dir = unit.pos.direction_to(closest_city_tile.pos)
                        # actions.append(unit.move(move_dir))


            if movement_picked == False:
                movement_picked = handle_unit_movement(unit, game_state, 'c', game_state.map.get_cell_by_pos(unit.pos), movement_picked)    
    
    
    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(game_state.id, 0))
    
    return actions
