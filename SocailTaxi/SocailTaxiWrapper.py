import networkx as nx
from typing import Tuple, List

TAXIS_LOCATIONS, FUELS, PASSENGERS_START_LOCATION, PASSENGERS_DESTINATIONS, PASSENGERS_STATUS = 0, 1, 2, 3, 4
PICK_UP_ACTION, DROP_OFF_PASSENGER_ZERO_ACTION = 4, 5

class EnvGraph:
    """
    This class converts the map of the taxi-world into a Networkx graph.
    Each square in the map is represented by a node in the graph. The nodes are indexed by rows, i.e. for a 4-row by
    5-column grid, node in location [0, 2] (row-0, column-2) has index 2 and node in location [1,1] has index 6.
    """

    def __init__(self, desc: list):
        """
        Args:
            desc: Map description (list of strings)
        """

        self.rows = len(desc) - 2
        self.cols = len(desc[0]) // 2
        self.graph = nx.empty_graph(self.rows * self.cols)
        for i in self.graph.nodes:
            row, col = self.node_to_cors(i)
            if desc[row + 2][col * 2 + 1] != '-':  # Check south
                self.graph.add_edge(i, self.cors_to_node(row + 1, col))
                # In case we ever use horizontal barriers
            if desc[row + 1][col * 2 + 2] == ':':  # Check east
                self.graph.add_edge(i, self.cors_to_node(row, col + 1))

    def node_to_cors(self, node) -> List:
        """
        Converts a node index to its corresponding coordinate point on the grid.
        """
        return [node // self.cols, node % self.cols]

    def cors_to_node(self, row, col) -> int:
        """
        Converts a grid coordinate to its corresponding node in the graph.
        """
        return row * self.cols + col

    def get_path(self, origin: (int, int), target: (int, int)) -> Tuple[list, list]:
        """
        Computes the shortest path in the graph from the given origin point to the given target point.
        Returns a tuple of lists where the first list represents the coordinates of the nodes that are along the path,
        and the second list represent the actions that should be taken to make the shortest path.
        """
        node_origin, node_target = self.cors_to_node(*origin), self.cors_to_node(*target)
        if node_origin == node_target:
            return [], []

        path = nx.shortest_path(self.graph, node_origin, node_target)
        cord_path = [self.node_to_cors(node) for node in path]
        actions = []
        for node in range(len(path) - 1):
            delta = path[node + 1] - path[node]
            if delta == -1:  # West
                actions.append(3)
            elif delta == 1:  # East
                actions.append(2)
            elif delta == -self.cols:  # North
                actions.append(1)
            else:  # South
                actions.append(0)
        return cord_path[1:], actions


class SocialTaxi:
    def __init__(self, taxi_env, taxi_index, passenger_index=None):
        self.taxi_env = taxi_env
        self.taxi_index = taxi_index
        self.passenger_index = passenger_index
        self.path_cords = []
        self.path_actions = []
        self.env_graph = EnvGraph(taxi_env.desc.astype(str))
        self.previous_coordinate = self.taxi_env.state[TAXIS_LOCATIONS][self.taxi_index]
        self.previous_action = None
        self.action_cor_dict = dict()
        self.action_counter = 0

    def compute_shortest_path(self, dest: list = None):
        """
        Given a destination point represented by a list of [row, column], compute the shortest path to it from the
        current location of the taxi. If a destination point isn't specified, the shortest path to the passenger's
        destination will be computed.
        """
        env_state = self.taxi_env.state
        current_location = env_state[TAXIS_LOCATIONS][self.taxi_index]

        # If a destination point wasn't specified, go to the passenger's destination
        if not dest:
            if self.passenger_index:
                dest = env_state[PASSENGERS_DESTINATIONS][self.passenger_index]
            else:  # if the taxi has no allocated passenger, stay in place, i.e don't do any action.
                self.path_cords, self.path_actions = [], []
                return

        cord_path, actions = self.env_graph.get_path(current_location, dest)
        self.path_cords = cord_path
        self.path_actions = actions

    def get_next_step(self):
        """
        Gets the next step in the path of the shortest path that was previously computed.
        Returns a tuple where the first item is the coordinate of the next step and the second item is the action.
        """
        # Check if the last step moved the taxi - if not, it prevented a collision and should be executed again.
        # if self.taxi_env.state[TAXIS_LOCATIONS][self.taxi_index] != self.previous_coordinate:
        #     return self.previous_coordinate, self.previous_action

        if self.path_cords and self.path_actions:
            next_coordinate = self.path_cords.pop(0)
            next_action = self.path_actions.pop(0)
            self.previous_coordinate = next_coordinate
            self.previous_action = next_action
            return next_coordinate, next_action

    def update_env_state(self, new_state):
        """
        Updates the state of the environment to the new given state.
        """
        self.taxi_env = new_state



    def get_close_passengers(self, current_cor, threshold):
        """
        Finds passengers that are in the range of the given threshold. If the passengers can
        benefit from being picked up and then dropped off on the taxi's path then returns there pick up and drop off locatoin.
        :param threshold: how far can the taxi deviate from its path to pick up another passenger
        :return: pick up coordinate, drop off coordinate, social passenger index,  If there is none then none
        """
        env_state = self.taxi_env.state
        social_passenger_index, drop_off_cor, pick_up_cor = None, None, None
        for other_passenger_index in range(self.taxi_env.num_passengers):
            if other_passenger_index != self.passenger_index and env_state[PASSENGERS_STATUS][other_passenger_index] == 2:
                social_passenger_location = env_state[PASSENGERS_START_LOCATION][other_passenger_index]
                social_passenger_destination = env_state[PASSENGERS_DESTINATIONS][other_passenger_index]
                social_passenger_index = other_passenger_index
                cor_path, actions_path = self.env_graph.get_path(current_cor, social_passenger_location)
                social_passengers_current_distance_to_destination = len(self.env_graph.get_path(social_passenger_location,
                                                                                            social_passenger_destination)[0])
                if len(actions_path) <= threshold:
                    pick_up_cor = social_passenger_location
                    #TODO: compare the optimal path length from the drop_off_cor to the destinaition to the current length of path
                    drop_off_cor, distance_from_drop_off = self.get_optimal_socail_drop_off(other_passenger_index)
                    if distance_from_drop_off >= social_passengers_current_distance_to_destination:
                        return None, None, None
                    break

        return pick_up_cor, drop_off_cor, social_passenger_index



    def get_optimal_socail_drop_off(self, other_passengers_index):
        """
        Gets the optimal drop of point
        :return: 
        """
        passenger_destination = self.taxi_env.state[PASSENGERS_DESTINATIONS][other_passengers_index]
        optimal_path_cor, optimal_path_actions = self.compute_optimal_path()

        best_drop_off_cor, best_path_length = optimal_path_cor[-1], len(self.env_graph.get_path(optimal_path_cor[-1],passenger_destination)[0])

        for cor in optimal_path_cor:
            #TODO: Maybe use manhaten distence
            path_length = len(self.env_graph.get_path(cor,passenger_destination)[0])
            if path_length <= best_path_length:
                best_drop_off_cor = cor
                best_path_length = path_length

        return best_drop_off_cor, best_path_length

    def take_social_path(self, threshold):
        """
        Picks up and drops off allocated passenger, is allowed to deviate from optimal path to help out other passengers
        :param threshold: how far can the taxi deviate from its path to pick up another passenger
        :return:
        """
        env = self.taxi_env
        passenger_start_location = env.state[PASSENGERS_START_LOCATION][self.passenger_index]
        passenger_destination = env.state[PASSENGERS_DESTINATIONS][self.passenger_index]
        self.add_action_to_cor(passenger_start_location, PICK_UP_ACTION)
        self.add_action_to_cor(passenger_destination, (5+self.passenger_index))

        self.path_cords, self.path_actions = self.compute_optimal_path()


        while self.path_cords:
            cur_location = self.get_taxi_location()

            if tuple(cur_location) in self.action_cor_dict.keys():
                # TODO: check case that in one corodint two action need to be performend
                for action in self.action_cor_dict[tuple(cur_location)]:
                    self.do_action(action)

            social_pick_up_cor, social_drop_off_cor, social_passenger_index = self.get_close_passengers(cur_location, threshold)
            #GO pick up social passenger
            if social_pick_up_cor != None:
                print(f"social_pick_up_cor = {social_pick_up_cor}, social_drop_off_cor = {social_drop_off_cor}")
                _, actions_to_pick_up_social_passenger = self.env_graph.get_path(cur_location, social_pick_up_cor)
                for social_action in actions_to_pick_up_social_passenger:
                    self.do_action(social_action)

                self.do_action(PICK_UP_ACTION)

                self.path_cords, self.path_actions = self.compute_optimal_path() #compute path from new location
                self.add_action_to_cor(social_drop_off_cor, (5+social_passenger_index))

            self.do_action([self.get_next_step()[1]])


        cur_location = self.get_taxi_location()

        for action in self.action_cor_dict[tuple(cur_location)]:
            self.do_action(action)

        return self.action_counter

    def do_action(self, action):
        """
        Peforems the  given action on the Taxi Environment
        :param action:
        :return:
        """

        self.action_counter +=1
        self.taxi_env.step({f'taxi_{self.taxi_index + 1}':action})
        self.taxi_env.render()


    def add_action_to_cor(self, cor, action):
        """
        Adds action to coordinate dict
        :param cor:
        :param action:
        :return:
        """

        if tuple(cor) in self.action_cor_dict.keys():
            self.action_cor_dict[tuple(cor)].append(action) #TODO: make suer this works
        else:
            self.action_cor_dict[tuple(cor)] = [action]

    def compute_optimal_path(self):
        """
        computes optimal path to pick up and drop off taxi's designated passenger
        :return:
        """
        env_state = self.taxi_env.state
        current_location = self.get_taxi_location()

        passenger_start_location = env_state[PASSENGERS_START_LOCATION][self.passenger_index]
        passenger_destination = env_state[PASSENGERS_DESTINATIONS][self.passenger_index]

        optimal_path_cor_to_passenger, optimal_actions_to_passenger = self.env_graph.get_path(current_location, passenger_start_location)
        optimal_path_cor_to_destination, optimal_actions_to_destination = self.env_graph.get_path(passenger_start_location,passenger_destination)
        optimal_path_actions = optimal_actions_to_passenger + optimal_actions_to_destination
        optimal_path_cor = optimal_path_cor_to_passenger + optimal_path_cor_to_destination


        return optimal_path_cor, optimal_path_actions


    def get_taxi_location(self):
        """
        Gets taxi's location
        :return:
        """

        env_state = self.taxi_env.state
        current_location = env_state[TAXIS_LOCATIONS][self.taxi_index]

        return current_location