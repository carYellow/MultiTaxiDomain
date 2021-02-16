import networkx as nx
import numpy as np
from typing import Tuple, List

TAXIS_LOCATIONS, FUELS, PASSENGERS_START_LOCATION, PASSENGERS_DESTINATIONS, PASSENGERS_STATUS = 0, 1, 2, 3, 4


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

    def get_nx(self) -> nx.Graph:
        return self.graph.copy()

    def path_cost(self, origin, dest):
        """
        Args:
            origin: coordinates of origin
            dest: coordinates of destination

        Returns:
        The cost of a path between two points.
        """
        return len(self.get_path(origin, dest)[1])


class Taxi:
    """
    Taxi wrapper for a single taxi object.
    """
    def __init__(self, taxi_env, taxi_index, assigned_passengers=None):
        self.taxi_env = taxi_env
        self.taxi_index = taxi_index
        self.env_graph = EnvGraph(taxi_env.desc.astype(str))
        self.communication_channel = []
        self.actions_queue = []
        self.assigned_passengers = assigned_passengers if assigned_passengers else []

    def compute_shortest_path(self, dest: list, origin: list = None):
        """
        Given a destination point represented by a list of [row, column], compute the shortest path to it from the
        current location of the taxi or from the origin point if given.

        Returns: - list of coordinates for the shortest path that was computed.
                 - list of actions that are required to complete the shortest path.
        """
        env_state = self.taxi_env.state
        origin = origin if origin is not None else env_state[TAXIS_LOCATIONS][self.taxi_index]
        cord_path, actions = self.env_graph.get_path(origin, dest)
        return cord_path, actions

    def get_next_step(self):
        """
        Gets the next step in the taxi's action-queue.
        """
        if self.actions_queue:
            next_action = self.actions_queue.pop(0)
            return next_action

    def get_location(self):
        """
        Returns the current location of the taxi.
        """
        return self.taxi_env.state[TAXIS_LOCATIONS][self.taxi_index]

    def get_fuel(self):
        """
        Returns the current fuel state of the taxi.
        """
        return self.taxi_env.state[FUELS][self.taxi_index]

    def path_cost(self, dest: List[int], origin: List[int] = None):
        """
        Compute the cost of the path from the taxi's current location (or from the origin point if given) to a given
        destination point.
        """
        origin = origin if origin else self.taxi_env.state[TAXIS_LOCATIONS][self.taxi_index]
        _, actions = self.env_graph.get_path(origin, dest)
        return len(actions)

    def send_taxi_to_point(self, point):
        """
        Sends the taxi to the given point. Adds all steps in the path to the actions queue of the taxi.
        Args:
            point: the location the taxi should drive to.
        """
        path_to_point = self.compute_shortest_path(dest=point)[1]
        self.actions_queue.extend(path_to_point)

    def send_taxi_to_pickup(self, passenger_index=None):
        """
        Sends the taxi to pickup passenger number `passenger_index` from her current location.
        Adds all steps in the path to the actions queue of the taxi.
        Args:
            passenger_index: the index of the passenger that should be picked up.
        """
        # Check if the taxi has an assigned passenger, if not don't do anything
        if not self.assigned_passengers and passenger_index is None:
            return
        pickup_passenger = passenger_index if passenger_index else self.assigned_passengers[0]
        passenger_location = self.taxi_env.state[PASSENGERS_START_LOCATION][pickup_passenger]
        self.send_taxi_to_point(point=passenger_location)

        # Add a `pickup` action:
        self.actions_queue.extend([(self.taxi_env.action_index_dictionary['pickup'])])

    def send_taxi_to_dropoff(self, point=None):
        """
        Sends the taxi to dropoff its passenger at the location given by `point`. If no dropoff point is given,
        the passenger will be dropped off at her destination.
        Args:
            point (optional): the point at which to dropoff the passenger. If not specified, the passenger will be
            dropped off at her destination.
        """
        if not self.assigned_passengers:
            return
        destination = point if point else self.taxi_env.state[PASSENGERS_DESTINATIONS][self.assigned_passengers[0]]
        self.send_taxi_to_point(point=destination)

        # Add a `dropoff` action:
        self.actions_queue.extend([self.taxi_env.action_index_dictionary[f'dropoff{self.assigned_passengers[0]}']])
        self.assigned_passengers.pop(0)

    def send_taxi_on_social_path(self):
        """
        :return:
        """
        self.send_taxi_to_pickup()
        self.send_taxi_to_dropoff()

    def pickup_cost(self, passenger_index):
        """
        Calculates the cost of the taxi to pickup the given passenger. The taxi calculates the cost from its current
        location if it has no allocated passengers, else from the location of the last allocated passenger.
        """
        passenger_location = self.taxi_env.state[PASSENGERS_START_LOCATION][passenger_index]
        origin = None
        # Check if the taxi has an allocated passenger. If yes, compute the cost from this passenger's location:
        if self.assigned_passengers:
            origin = self.taxi_env.state[PASSENGERS_START_LOCATION][self.assigned_passengers[-1]]

        pickup_cost = self.path_cost(dest=passenger_location, origin=origin)
        return pickup_cost

    def passenger_allocation_message(self, passenger_index):
        """
        Broadcast a message with information about the cost of the path to a specific passenger and the shortest
        path from the taxi's current location to the destination of the passenger.
        """
        pickup_cost = self.pickup_cost(passenger_index)
        message = {
            'taxi_index': self.taxi_index,
            'passenger_index': passenger_index,
            'pickup_cost': pickup_cost
        }
        return [message]

    def request_help_message(self):
        """
        Broadcast a message to all taxis, requesting for help to bring the assigned taxi to the destination.
        """
        all_messages = []
        for passenger_index in self.assigned_passengers:
            passenger_destination = self.taxi_env.state[PASSENGERS_DESTINATIONS][passenger_index]
            path_cost = self.path_cost(dest=passenger_destination)

            # Request for help if the taxi hasn't enough fuel:
            if path_cost >= self.get_fuel():
                message = {
                    'type': 'help_request',
                    'taxi_index': self.taxi_index,
                    'passenger_index': passenger_index
                }
                all_messages.append(message)
        return all_messages

    def passenger_transfer_message(self):
        """
        Broadcast a message with information about the path to the given passenger's destination.
        """
        all_messages = []
        communication_channel = []
        for incoming_message in self.communication_channel:
            if incoming_message.get('type') != 'help_request':
                communication_channel.append(incoming_message)
                continue
            passenger_index = incoming_message.get('passenger_index')
            recipient_taxi_index = incoming_message.get('taxi_index')
            passenger_destination = self.taxi_env.state[PASSENGERS_DESTINATIONS][passenger_index]
            path_cords, path_actions = self.compute_shortest_path(dest=passenger_destination)
            message = {
                'type': 'path_response',
                'taxi_index': self.taxi_index,
                'passenger_index': passenger_index,
                'shortest_path': path_cords,
                'recipient_taxi_index': recipient_taxi_index,
                'taxi_fuel': self.get_fuel()
            }
            all_messages.append(message)

        # Clear the communication channel:
        self.communication_channel = communication_channel

        return all_messages

    def decide_assignments(self):
        """
        Go over all messages and check which taxi is the closest to every passenger. The taxi assigns to itself the
        passengers that are closest to it.
        """
        pickup_cost = np.inf
        assigned_taxi = -1
        for message in self.communication_channel:
            passenger_index = message['passenger_index']
            taxi_index = message['taxi_index']
            if message['pickup_cost'] < pickup_cost:
                pickup_cost = message['pickup_cost']
                assigned_taxi = taxi_index

        if assigned_taxi == self.taxi_index:
            self.assigned_passengers.append(passenger_index)

        # Clear the communication channel:
        self.communication_channel = []

    def pickup_multiple_passengers(self):
        """
        Send the taxi to pickup every passenger that is assigned to it.
        """
        origin = self.get_location()
        for passenger in self.assigned_passengers:
            passenger_location = self.taxi_env.state[PASSENGERS_START_LOCATION][passenger]
            path_cords, path_actions = self.compute_shortest_path(dest=passenger_location, origin=origin)
            self.actions_queue.extend(path_actions)

            # Add pickup step
            self.actions_queue.append(self.taxi_env.action_index_dictionary['pickup'])

            origin = passenger_location

    def listen(self, message):
        """
        Listen to new messages broadcast by different taxis and add them to the taxi's communication channel.
        """
        self.communication_channel.extend(message)

    def set_transfer_point(self):
        """
        iterate over all messages and choose the taxi that can bring the passenger closest to the destination.
        """
        # If the communication channel is empty or the taxi has no assigned passengers the taxi didn't request for help
        if not self.communication_channel or not self.assigned_passengers:
            return

        helping_taxi_index = self.taxi_index
        remaining_dist_to_dest = self.path_cost(dest=self.taxi_env.state[PASSENGERS_DESTINATIONS][
            self.assigned_passengers[0]]) - self.get_fuel()
        transfer_point = self.taxi_env.state[PASSENGERS_DESTINATIONS][self.assigned_passengers[0]]
        current_cost = np.inf

        for message in self.communication_channel:
            helping_taxi = message.get('taxi_index')
            shortest_path = message.get('shortest_path')
            passenger_index = message.get('passenger_index')
            helping_taxi_fuel = message.get('taxi_fuel')
            cost, optimal_point, distance = self.find_best_transfer_point(to_taxi_index=helping_taxi,
                                                                          path_to_dest=shortest_path,
                                                                          passenger_index=passenger_index,
                                                                          to_taxi_fuel=helping_taxi_fuel)
            if distance <= remaining_dist_to_dest:
                if cost < current_cost:
                    helping_taxi_index = helping_taxi
                    remaining_dist_to_dest = distance
                    transfer_point = optimal_point
                    current_cost = cost

        self.communication_channel = []

        # send the taxi to the transfer point:
        self.send_taxi_to_dropoff(transfer_point)

        if helping_taxi_index != self.taxi_index:
            transfer_message = {
                'type': 'transfer_message',
                'helping_taxi': helping_taxi_index,
                'transfer_point': transfer_point,
                'taxi_index': self.taxi_index,
                'passenger_index': passenger_index
            }

            return [transfer_message]

    def find_best_transfer_point(self, to_taxi_index, passenger_index, path_to_dest, to_taxi_fuel):
        """
        Find the best point to transfer the passenger between the taxis. The best point is considered as the point
        closest to the shortest path from the current location of the `to_taxi_index` taxi to the passenger's
        destination. This point will cause the `to_taxi_index` to make the smallest possible detour.
        Args:
            to_taxi_index: the index of the taxi the passenger should be transferred to.
            passenger_index: the index of the passenger that should be transferred.
            path_to_dest: the path of the `to_taxi_index` from its current location to the destination of the passenger.
            to_taxi_fuel: the fuel level of the taxi that should take the passenger to the destination.
        Return:
              The optimal point to make the transfer at.
        """
        # Add the current location of the taxi as another optional transfer point:
        path_to_dest.insert(0, self.taxi_env.state[TAXIS_LOCATIONS][to_taxi_index])

        # -1 to avoid finishing all the `from_taxi` fuel as it will not be able to make the dropoff
        from_taxi_remaining_fuel = self.taxi_env.state[FUELS][self.taxi_index] - 1

        # A list of tuples where the first item is the off road distance the `to_taxi` will have to take from the
        # shortest computed path to the closest point the `from_taxi` can get. The second item is the furthest
        # point that the `from_taxi` can get to, based on its fuel limitations.
        off_road_distances = []
        for point in path_to_dest:
            path_cords, path_actions = self.compute_shortest_path(dest=point)
            # Add the current location of the taxi for cases where the taxi has no fuel to move:
            path_cords.insert(0, self.get_location())
            # Compute how many steps of the path the taxi can't complete because of its fuel limit:
            remaining_path = max(0, len(path_actions) - from_taxi_remaining_fuel)
            if remaining_path > 0:
                off_road_distances.append((remaining_path, path_cords[min(from_taxi_remaining_fuel,
                                                                          len(path_actions))]))
            else:
                off_road_distances.append((0, point))

        # Select the optimal point (the one with minimal off-road steps for `to_taxi`):
        cost, optimal_point = min(off_road_distances, key=lambda x: x[0])

        # Compute how far from the destination the taxi can bring the passenger:
        distance_from_destination = max(0, cost * 2 + len(path_to_dest) - to_taxi_fuel - 1)  # -1 for the extra step of
        # current location added at the beginning of this function.
        return cost, optimal_point, distance_from_destination

    def intermediate_pickup(self):
        """
        Check if the taxi should go to a transfer point and pickup a passenger from another taxi.
        """
        for message in self.communication_channel:
            transfer_point = message.get('transfer_point')
            self.send_taxi_to_point(point=transfer_point)
            self.assigned_passengers.append(message.get('passenger_index'))
        self.communication_channel = []
