import numpy as np
import itertools
from typing import List, Dict

# Local imports
from multitaxienv.taxi_environment import TaxiEnv
from TaxiWrapper.taxi_wrapper import EnvGraph, PASSENGERS_START_LOCATION, PASSENGERS_DESTINATIONS, TAXIS_LOCATIONS


class TaskAllocator:
    def __init__(self, taxi_env):
        self.taxi_env = taxi_env
        self.env_graph = EnvGraph(taxi_env.desc.astype(str))
        self.distances = self.distances_to_all_passengers()

    def compute_shortest_path_length(self, start_point: list, dest_point: list):
        """
        Input: start_point, a list of [row, column]
               dest_point, a list of [row, column]
        Returns: The length of shortest path between the two points
        """

        cord_path, _actions = self.env_graph.get_path(start_point, dest_point)

        return(len(cord_path))
    
    def compute_total_taxi_travel_distance(self, taxi_ind, passenger_ind):
        taxi_location = self.taxi_env.state[TAXIS_LOCATIONS][taxi_ind]
        passenger_start_location = self.taxi_env.state[PASSENGERS_START_LOCATION][passenger_ind]
        passenger_dest = self.taxi_env.state[PASSENGERS_DESTINATIONS][passenger_ind]

        taxi_to_passenger_distance = self.compute_shortest_path_length(taxi_location, passenger_start_location)
        passenger_start_to_dest_distance = self.compute_shortest_path_length(passenger_start_location, passenger_dest)

        return taxi_to_passenger_distance + passenger_start_to_dest_distance
    
    def allocation_cost(self, allocation: dict):
        """
        Parameters:
            allocation - dict with taxi_index as keys and passenger_ind as values
        Returns: total cost (for all taxis) of the given allocation 
        """
        total_cost = 0.0

        for taxi_ind, passenger_ind in allocation.items():
            taxi_travel_cost = self.compute_total_taxi_travel_distance(taxi_ind, passenger_ind)
            total_cost += taxi_travel_cost
        
        return total_cost

    def distances_to_all_passengers(self):
        """
        Returns: distances - an array of size (num_taxis, num_passengers)
                            In each cell [i,j]: the total distance taxi i needs to travel
                                                to pick up passenger j and drive to her destination
        """
        taxis_locations = self.taxi_env.state[TAXIS_LOCATIONS]
        passengers_start_locations = self.taxi_env.state[PASSENGERS_START_LOCATION]
        passengers_destinations = self.taxi_env.state[PASSENGERS_DESTINATIONS]
        
        num_passengers = self.taxi_env.num_passengers
        num_taxis = self.taxi_env.num_taxis

        distances = np.full((num_taxis, num_passengers), 0)

        for passenger_ind in range(num_passengers):
            passenger_start_loc = passengers_start_locations[passenger_ind]
            passenger_dest_loc = passengers_destinations[passenger_ind]

            # start_to_dest distnace is the same for each passenger and can be re-used in computations
            passenger_start_to_dest_distance = self.compute_shortest_path_length(passenger_start_loc, passenger_dest_loc)

            for taxi_ind in range(num_taxis):
                taxi_initial_loc = taxis_locations[taxi_ind]
                taxi_to_passenger_distance = self.compute_shortest_path_length(taxi_initial_loc, passenger_start_loc)
                
                total_distance = taxi_to_passenger_distance + passenger_start_to_dest_distance

                distances[taxi_ind, passenger_ind] = total_distance

        return distances
    
    def passengers_allocations_cost(self):
        """
        Returns: a dictionary with:
                Keys: all possible taxi->passenger allocations
                Values: the associated costs, i.e. total distance all taxis will need to travel given the allocation
        
        Assumes the number of taxis is equal to the number of passengers
        """

        num_passengers = self.taxi_env.num_passengers
        num_taxis = self.taxi_env.num_taxis

        # Possible allocations; each passenger is considered as a task 
        passengers_permutations = list(itertools.permutations([i for i in range(num_passengers)]))
        
        taxis_indices = tuple([i for i in range(num_taxis)])
        allocations = []
        for passenger_perm in passengers_permutations:
            # taxis [0...n] are allocated with possisble_allocations
            allocation = [(taxi_ind, passenger_ind) for taxi_ind, passenger_ind in zip (taxis_indices, passenger_perm)]
            allocations.append(tuple(allocation))

        # Caculate cost of each allocation, given pre-calculated 'distances' matrix        
        allocations_total_distances = dict() # allocation -> cost

        for allocation in allocations:
            allocation_total_distance = 0
            for taxi_passenger in allocation:
                # taxi_passenger is a tuple: (taxi_ind, passenger_ind)
                # distances[(taxi_ind, passenger_ind)] is the distance for the given taxi and passenger
                allocation_total_distance += self.distances[taxi_passenger]
            
            allocations_total_distances[allocation] = allocation_total_distance

        return allocations_total_distances

    def optimal_allocation_minimal_value(self, allocations: dict):
        """
        Parameters: allocations - a dictionary with allocation->cost mapping
        """
        optimal_allocation = min(allocations, key=allocations.get)
        # Convert to a dictioanry 
        optimal_allocation_dict = {taxi_ind:passenger_ind for (taxi_ind,passenger_ind) in optimal_allocation}
        return optimal_allocation_dict
    
    def taxis_auction_allocation(self, biddings: list):
        """
        Parameters:
            biddings: list of size num_passengers.
                        Each element i is a dictionary with key-value {taxi_num, taxi's_bid_on_passenger_i}
                        bid value - total distance the taxi will have to travel
                        to finish the task (passenger) - smaller is better!
        Returns: A dictionary of taxi->passenger allocation.
                 The allocation is determined by a the following process:
                 While there are passengers without a taxi:
                    1. For each passenger, select the taxi with the best (lowest) bid
                    2. Remove the selected taxi from step 1 from the pool of bidding taxis
                    3. Continue to the next passenger and repeat step 1 
        """

        # Todo: consider overloading this method with another parameter, which is a function
        #       which determines what is the best bid (e.g. minimum/maximum/some other logic)
        num_passengers = self.taxi_env.num_passengers
        num_taxis = self.taxi_env.num_taxis

        allocations = {} # taxi_index -> passenger_index

        for passenger_ind in range(num_passengers):
            bids_on_passenger = biddings[passenger_ind]

            assert len(bids_on_passenger) == num_taxis
            
            # Remove taxis with allocated passengers from bidding
            for taxi_ind in allocations:
                bids_on_passenger.pop(taxi_ind)
            
            # Choose the winning taxi
            # In case of a tie - chooses the taxi with the lowest index
            winning_taxi_ind = (min(bids_on_passenger, key=bids_on_passenger.get))


            # print("allocated taxi "+ str(winning_taxi_ind) + " passeneger " + str(passenger_ind))
            allocations[winning_taxi_ind] = passenger_ind
        
        # Each passenger must be allocated with a taxi
        assert len(allocations) == num_passengers

        return allocations

    def get_taxis_bids(self, taxis_list: list):
        """
        Parameters: taxis_list - a list of BiddingTaxi objects
        Returns: a list of dictionaries.
                 The i-th dictionary contains the biddings of all taxis
                 on passenger with index i
        """

        num_passengers = self.taxi_env.num_passengers
        num_taxis = self.taxi_env.num_taxis

        assert num_taxis == len(taxis_list)

        # Each ROW i in taxis_biddings contains the bids for th i-th passenger
        taxis_biddings = np.full((num_passengers, num_taxis), 0)

        for taxi_ind ,taxi in enumerate(taxis_list):
            taxi_bids = taxi.calculate_distances_to_all_passengers()
            taxis_biddings[:, taxi_ind] = taxi_bids

        
        bids_on_passengers = []
        
        for bids in taxis_biddings:
            bids_on_current_passenger = {taxi_ind:taxi_bid for (taxi_ind, taxi_bid) in enumerate(bids)}
            bids_on_passengers.append(bids_on_current_passenger)
        
        return bids_on_passengers

    @staticmethod
    def allocate_passengers(allocation: dict, taxis: list):
        """
        Parameters: allocation - a dict with taxi_index->passenger_index
                    taxis - a list of wrapped taxi objects
        Effects: assigns each taxi with its allocated passenger
        Returns: None
        """
        for taxi_ind in range(len(taxis)):
            passenger_ind = allocation[taxi_ind]
            taxis[taxi_ind].passenger_index = passenger_ind
