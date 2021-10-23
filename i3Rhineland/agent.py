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
dirs_to_coords = {"n": Position(x=0, y=-1), "s": Position(x=0, y=1), "e": Position(x=1, y=0), "w": Position(x=-1, y=0)}




game_state = None
build_location = None
delayed_movements = {}
tiles_where_unit_is_moving = {}

optimal_colony_distance_by_size = {12: 6, 16: 7, 24: 9, 32: 12}




unit_assignments = {"u_2": "Feed"}
unit_cities = {"u_2": "c_2"}
unit_target_tiles = {}

fuel_resource_weights = {Constants.RESOURCE_TYPES.WOOD: 0, Constants.RESOURCE_TYPES.COAL: 5, Constants.RESOURCE_TYPES.URANIUM: 10}
emergency_fuel_resource_weights = {Constants.RESOURCE_TYPES.WOOD: 1, Constants.RESOURCE_TYPES.COAL: 0, Constants.RESOURCE_TYPES.URANIUM: 0}

build_resource_weights = {Constants.RESOURCE_TYPES.WOOD: 10, Constants.RESOURCE_TYPES.COAL: 1, Constants.RESOURCE_TYPES.URANIUM: 0}




class Unit_data:
    
    deliver_fuel = False
    stuck = False
    

unit_data_dict = {}










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

    elif len(direction_options):
        delayed_movements[unit.id] = [direction_options[0], move_tile_options[0]]
        return rand.choice(['e', 'w', 'n', 's']), None
    else:
        logging.info("seems stuck?")
        return "c", None #game_state.map.get_cell(x= unit.pos.x, y= unit.pos.y)



# return the distance from a tile to the nearest citytile
def get_distance_from_any_city(tile, cities, width):
    # opt_dist = optimal_colony_distance_by_size[width]
    lowest_distance = math.inf
    for city in cities:
        for citytile in city.citytiles:
            dist = tile.pos.distance_to(citytile.pos)
            if dist < lowest_distance:
                lowest_distance = dist
    return lowest_distance




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
def determine_best_resource_tile(resource_tiles, unit, player, purpose, city=None):
    if purpose == "fuel":
        resource_weights = fuel_resource_weights
        if city.fuel < city.get_light_upkeep() * 10:
            resource_weights = emergency_fuel_resource_weights
            logging.info("EMERGENCY MODE")
    if purpose == "build":
        resource_weights = build_resource_weights

    closest_dist = math.inf
    closest_mat = None
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD and resource_tile.resource.amount < 300: continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(unit.pos)
        mat = resource_tile.resource.type

        if closest_resource_tile == None:
            closest_resource_tile = resource_tile
            closest_dist = dist
            closest_mat = mat

        else:
            if dist - resource_weights[mat] < closest_dist - resource_weights[closest_mat]:
                closest_resource_tile = resource_tile
                closest_dist = dist
                closest_mat = mat




        
    return closest_resource_tile


#   iterates through cities, then through each cities citytiles, to find city_tile closest to unit
def determine_closest_city_tile(player, unit, city = None):
    closest_dist = math.inf
    closest_city_tile = None
    if city == None:
        cities_list = player.cities.items()
    else:
        cities_list = [player.cities[city]]
    for city in cities_list:
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
def determine_city_expansion_location(cities, game_state, unit, city):
    logging.info('determining where to build new citytile')
    possible_city_locations = []
    for citytile in city.citytiles:
        for dir in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            pos_in_dir = Position(x=citytile.pos.x + dir[0], y=citytile.pos.y + dir[1])
            # logging.info('checking tile at ' + str(pos_in_dir) +' for existence -> ' + str(tile_on_map(pos_in_dir, game_state.map.width, game_state.map.height)))
            if tile_on_map(pos_in_dir, game_state.map.width, game_state.map.height):
                valid_tile_in_dir = game_state.map.get_cell_by_pos(pos_in_dir)
                if valid_tile_in_dir.has_resource() == False and valid_tile_in_dir.citytile == None:
                    possible_city_locations.append(valid_tile_in_dir)

    # logging.info("possible city locations: " + str(possible_city_locations))
    
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

    if closest_option == None:
        logging.info("for some reason, can't find a spot to build")
        unit_assignments[unit.id] = "Colonize"

    return closest_option



#picks a unoccupied spot for new city to be built
def determine_colony_location(cities, game_state, unit, resource_tiles):


    # lets figure this shit out
    opt_dist = optimal_colony_distance_by_size[game_state.map.width]






    possible_colony_tiles = []
    for resource_tile in resource_tiles:
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD and resource_tile.resource.amount > 300:
            for dir in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                if tile_on_map(Position(x=resource_tile.pos.x + dir[0], y=resource_tile.pos.y + dir[1]), game_state.map.width, game_state.map.height):
                    tile_in_dir = game_state.map.get_cell(x=resource_tile.pos.x + dir[0], y=resource_tile.pos.y + dir[1])
                    if tile_in_dir.citytile == None and tile_in_dir.has_resource() == False:
                        possible_colony_tiles.append(tile_in_dir)
    
    least_dist = math.inf
    least_higher_single_coordinate_dist = math.inf #used to prioritize diagonal distances over direct distances
    closest_option = None
    for colony_loc_option in possible_colony_tiles:
        option_dist = get_distance_from_any_city(colony_loc_option, cities, game_state.map.width)

        higher_single_coord_dist = max(abs(colony_loc_option.pos.x - unit.pos.x), abs(colony_loc_option.pos.y - unit.pos.y))
        if  abs(option_dist - opt_dist) < abs(least_dist - opt_dist):
            least_dist, least_higher_single_coordinate_dist, closest_option = option_dist, higher_single_coord_dist, colony_loc_option
        elif option_dist == least_dist:
            if higher_single_coord_dist < least_higher_single_coordinate_dist:
                least_dist, least_higher_single_coordinate_dist, closest_option = option_dist, higher_single_coord_dist, colony_loc_option


    # logging.info("the best option is " + str(least_dist) + "tiles from any city at " + str(closest_option.pos))
    # logging.info("for reference, tile (0, 0) is " + str(get_distance_from_any_city(game_state.map.get_cell_by_pos(Position(x=0, y=0)), cities, game_state.map.width)))
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
    def handle_unit_movement(unit, game_state, move_dir, move_tile, movement_is_picked):
        if move_tile not in tiles_where_unit_is_moving.values():
            
            action_selection = unit.move(move_dir)
            
            movement_is_picked = True

            if move_tile != None:
                actions.append(annotate.text(move_tile.pos.x, move_tile.pos.y, str(unit.id)))
                if move_tile.citytile == None:
                    tiles_where_unit_is_moving[unit.id] = move_tile

        else:
            action_selection = None

        return action_selection, movement_is_picked


    def find_orphan_new_city(unit):
        unit_assignments[unit.id] = "Colonize"












    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    cityTile_count = count_citytiles(player)
    logging.info("++++++ starting turn " + str(game_state.turn) + ". number of citytiles = " + str(cityTile_count) + "++++++")
    resource_tiles = determine_resource_tiles(game_state, height, width)
    cities = list(player.cities.values())


    units_added_this_turn = 0


    # if cityTile_count < max_cities and cities[0].fuel > min_city_fuel * cityTile_count:
        
    #     build_city = True
    
    for city in cities:
        #assign newly built workers to this city (if they are on a tile of this city)
        this_cities_workers = []
        
        for unit in player.units:


            if unit.id not in unit_cities.keys():
                if game_state.map.get_cell_by_pos(unit.pos).citytile != None:
                    if game_state.map.get_cell_by_pos(unit.pos).citytile.cityid == city.cityid:
                        unit_cities[unit.id] = city.cityid
                        logging.info(str(city.cityid) + " is claiming unit " + str(unit.id) )
            if unit.id in unit_cities.keys():
                if unit_cities[unit.id] == city.cityid:
                    this_cities_workers.append(unit)

        city_worker_count = len(this_cities_workers)

        if city_worker_count == 1:
            if city.fuel > city.get_light_upkeep() * 10:
                unit_assignments[this_cities_workers[0].id] = "Expand"
            else:
                unit_assignments[this_cities_workers[0].id] = "Feed"


        else:        
            city_size = len(city.citytiles)
            logging.info("city " + str(city.cityid) + " is " + str(city_size) + " tiles large, and it has "+ str(city_worker_count) + " workers assigned to it")

            min_feeders = max(city_size - 2, 1)
            min_expanders = 1
            min_colonizers = 1

            feeders = 0
            expanders = 0
            colonizers = 0
            for unit in this_cities_workers:
                #stuff goes here
                if feeders < min_feeders:
                    unit_assignments[unit.id] = "Feed"
                    feeders += 1
                elif expanders < min_expanders:
                    unit_assignments[unit.id] = "Expand"
                    expanders +=1
                    logging.info("making an expander")
                elif colonizers < min_colonizers:
                    unit_assignments[unit.id] = "Colonize"
                    logging.info("making a COLONIZER")

                    colonizers += 1




                
                #at the end
                if unit.id not in unit_assignments.keys():
                    unit_assignments[unit.id] = "Feed"
            



        for cityTile in city.citytiles:

            # either make a new unit or do research
            if cityTile.can_act():
                if len(player.units) + units_added_this_turn < cityTile_count:
                    actions.append(cityTile.build_worker())
                    units_added_this_turn += 1
                else:
                    actions.append(cityTile.research())


    if len(cities) == 0:
        for unit in player.units:
            if unit.id in unit_cities.keys():
                unit_cities.pop(unit.id)
            unit_assignments[unit.id] = "Colonize"




    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.id not in unit_data_dict.keys():
            unit_data_dict[unit.id] = Unit_data()

        unit_data = unit_data_dict[unit.id]
        




        if unit.id in tiles_where_unit_is_moving.keys():
            if tiles_where_unit_is_moving[unit.id].pos == unit.pos:
                # logging.info(str(unit.id) + " was able to move  ----------------<->")
                
                unit_data.stuck = False
            else:
                # logging.info(str(unit.id) + " is not where its supposed to be ----------------<->")

                unit_data_dict[unit.id].stuck = True
            tiles_where_unit_is_moving.pop(unit.id)


        if unit.id not in unit_cities.keys() or unit_cities[unit.id] not in player.cities.keys():
            if unit.id not in unit_assignments.keys() or unit_assignments[unit.id] != "Colonize":
                find_orphan_new_city(unit)


        if unit.is_worker() and unit.can_act():
            movement_is_picked = False
            action_selection = None

            if unit_data.stuck:
                dir = rand.choice(["n", "e", "s", "w"])
                move_pos = Position(x=unit.pos.x + dirs_to_coords[dir].x, y= unit.pos.y + dirs_to_coords[dir].y)
                if tile_on_map(move_pos, width, height):
                    move_tile = game_state.map.get_cell_by_pos(move_pos)
                    action_selection, movement_is_picked = handle_unit_movement(unit, game_state, dir, move_tile, movement_is_picked)
            
            else:

                if unit.id in unit_assignments.keys():
                    assignment = unit_assignments[unit.id]

                    logging.info("unit {uid} reporting for duty! duty is {ass}".format(uid=str(unit.id), ass=assignment))
                    
                    
                    
                    if assignment == "Feed": #one issue with this function is that there is no dropoff mode where the unit will empty its whole inventory. rather it will drop of for one turn and then harvest more once it has any space
                                            # Ok i think i fixed it with the second condition on the if condition
                        city = unit_cities[unit.id]
                        # logging.info("cargo space left = " + str(unit.get_cargo_space_left()))
                        if unit.get_cargo_space_left() < 5 or unit_data.deliver_fuel == True:
                            tile_for_delivery = determine_closest_city_tile(player, unit, city)
                            if tile_for_delivery.pos == unit.pos:
                                action_selection = None
                                unit_data.deliver_fuel = False
                            else:
                                move_dir, move_tile = get_directions(unit, game_state, tile_for_delivery, False)
                                action_selection, movement_is_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_is_picked)
                                unit_data.deliver_fuel = True
                        else:
                            tile_for_harvest = determine_best_resource_tile(resource_tiles, unit, player, "fuel", player.cities[city])
                            if tile_for_harvest != None:
                                if tile_for_harvest.pos == unit.pos:
                                    action_selection = None
                                else:
                                    move_dir, move_tile = get_directions(unit, game_state, tile_for_harvest, False)
                                    action_selection, movement_is_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_is_picked)
                            
                    


                    elif assignment == "Expand":
                        city = unit_cities[unit.id]
                        build_location = determine_city_expansion_location(cities, game_state, unit, player.cities[city])
                        if build_location == None: continue
                        logging.info("I want to expand my city at " + str(build_location.pos))
                        actions.append(annotate.text(build_location.pos.x, build_location.pos.y, "expand!" + str(unit.id), 16))


                        if unit.get_cargo_space_left() == 0:
                            if unit.pos == build_location.pos:
                                action_selection = unit.build_city()
                            else:
                                move_dir, move_tile = get_directions(unit, game_state, build_location, True)
                                action_selection, movement_is_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_is_picked)

                        else:
                            tile_for_harvest = determine_best_resource_tile(resource_tiles, unit, player, "build")
                            if tile_for_harvest != None:
                                if tile_for_harvest.pos == unit.pos:
                                    action_selection = None
                                else:
                                    move_dir, move_tile = get_directions(unit, game_state, tile_for_harvest, False)
                                    action_selection, movement_is_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_is_picked)

                    elif assignment == "Colonize":

                        if unit.id in unit_cities.keys():
                            unit_cities.pop(unit.id)


                        colony_location = determine_colony_location(cities, game_state, unit, resource_tiles)
                        
                        if colony_location != None:
                        
                            actions.append(annotate.text(colony_location.pos.x, colony_location.pos.y, "colonize!" + str(unit.id)))
                            
                            if unit.get_cargo_space_left() == 0:
                                if unit.pos == colony_location.pos:
                                    action_selection = unit.build_city()
                                    if unit.id in unit_cities.keys():
                                        unit_cities.pop(unit.id)
                                    if unit.id in unit_assignments.keys():
                                        unit_assignments.pop(unit.id)
                                else:
                                    move_dir, move_tile = get_directions(unit, game_state, colony_location, True)
                                    action_selection, movement_is_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_is_picked)

                            else:
                                tile_for_harvest = determine_best_resource_tile(resource_tiles, colony_location, player, "build")
                                        #if there is an error here, it very likely to be caused by this very dumb thing i'm doing where im passing in the colony_location
                                        #instead of the unit so that it picks a resource near where the colony should be built, rather than where the unit is currently
                                if tile_for_harvest != None:
                                    if tile_for_harvest.pos == unit.pos:
                                        action_selection = None
                                    else:
                                        move_dir, move_tile = get_directions(unit, game_state, tile_for_harvest, False)
                                        action_selection, movement_is_picked = handle_unit_movement(unit, game_state, move_dir, move_tile, movement_is_picked)
                        else:
                            logging.info("can't find anywhere to build a colony!!!")



                    else:
                        logging.info(str(unit.id) + "cannot report for duty, as it has none")


                        


                # i think this doesnt make sense when a unit is doing a move other than moving!! would it add a second action? if anything, shouldnt there be a second option where the units tile is added to moved_to_tiles, but another action is not appended
            
            if action_selection != None:
                actions.append(action_selection)
            
            if movement_is_picked == False:
                movement_is_picked = handle_unit_movement(unit, game_state, 'c', game_state.map.get_cell_by_pos(unit.pos), movement_is_picked)    
    
    
    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(game_state.id, 0))
    
    logging.info(" ")

    return actions
