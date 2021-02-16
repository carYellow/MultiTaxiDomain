import numpy as np

from SocailTaxi.SocailTaxiWrapper import SocialTaxi

from multitaxienv.taxi_environment import TaxiEnv
from TaskAllocator import TaskAllocator


def create_taxis_list(env, taxis_num):
    taxis_list = []
    for i in range(taxis_num):
        wrapped_taxi = SocialTaxi(env, taxi_index=i)
        taxis_list.append(wrapped_taxi)

    return taxis_list


def main():

    taxis_num = passengers_num = 2

    env = TaxiEnv(num_taxis=taxis_num, num_passengers=passengers_num, max_fuel=None,
                  taxis_capacity=[5, 5], collision_sensitive_domain=False,
                  fuel_type_list=None, option_to_stand_by=True)

    env.reset()
    env.s = 1022
    env.render()

    #Allocating passengers to taxi's
    allocator = TaskAllocator(env)
    taxis_list = create_taxis_list(env, taxis_num)
    true_allocations_cost = allocator.passengers_allocations_cost()
    optimal_allocation = allocator.optimal_allocation_minimal_value(true_allocations_cost)
    TaskAllocator.allocate_passengers(optimal_allocation, taxis_list)


    for taxi in taxis_list:
        taxi.take_social_path(3)


if __name__ == "__main__":
    main()
