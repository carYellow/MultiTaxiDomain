from multitaxienv.taxi_environment import TaxiEnv
from TaxiWrapper.taxi_wrapper import *

# Initialize a new environment with 1 taxi at a random location and display it:
env = TaxiEnv(num_taxis=1, num_passengers=1, max_fuel=None,
              taxis_capacity=None, collision_sensitive_domain=False,
              fuel_type_list=None, option_to_stand_by=True)
env.reset()
env.s = 1022
env.render()


# Initialize a new taxi object for the taxi, and send it to pick up the second passenger:
assigned_passenger = 0
taxi1 = Taxi(env, taxi_index=0, assigned_passengers=[assigned_passenger])
taxi1.send_taxi_to_pickup()

# Execute all the action of the taxi:
next_step = taxi1.get_next_step()
while next_step is not None:
    env.step({'taxi_1': next_step})
    next_step = taxi1.get_next_step()
    env.render()

# Send the taxi to dropoff the passenger at her destination:
taxi1.send_taxi_to_dropoff()
# Execute all the action of the taxi:
next_step = taxi1.get_next_step()
while next_step is not None:
    env.step({'taxi_1': next_step})
    next_step = taxi1.get_next_step()
    env.render()

