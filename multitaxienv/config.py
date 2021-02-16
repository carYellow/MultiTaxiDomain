TAXI_ENVIROMENT_REWARDS = dict(
    step=1,
    no_fuel=-20,
    bad_pickup=-15,
    bad_dropoff=-15,
    bad_refuel=-10,
    pickup=50,
    standby_engine_off=-1,
    turn_engine_on=-10e6,
    turn_engine_off=-10e6,
    standby_engine_on=-1,
    intermediate_dropoff=500,
    final_dropoff=10000,
    hit_wall=-2,
    collision=-35,
    collided=-20,
    unrelated_action=-15,
    bind=-7
)

COLOR_MAP = {
            ' ': [0, 0, 0],  # Black background
            '_': [0, 0, 0],
            '0': [0, 0, 0],  # Black background beyond map walls
            '': [180, 180, 180],  # Grey board walls
            '|': [180, 180, 180],  # Grey board walls
            '+': [180, 180, 180],  # Grey board walls
            '-': [180, 180, 180],  # Grey board walls
            ':': [0, 0, 0],  # black passes board walls
            '@': [180, 180, 180],  # Grey board walls
            'P1': [254, 151, 0],  # Orange
            'P0': [100, 255, 255],  # Cyan for agents
            'F': [250, 204, 255],  # Pink
            'G': [159, 67, 255],  # Purple
            'X': [0, 0, 0],

            # Colours for agents. R value is a unique identifier
            '1': [238, 223, 16],  # Yellow
            '2': [216, 30, 54],  # Red
            '3': [204, 0, 204],  # Magenta
            '4': [2, 81, 154],  # Blue
            '5': [254, 151, 0],  # Orange
            '7': [99, 99, 255],  # Lavender
}


ALL_ACTIONS_NAMES = ['south', 'north', 'east', 'west',
                    'pickup', 'dropoff', 'bind',
                    'turn_engine_on', 'turn_engine_off',
                    'standby',
                    'refuel']

BASE_AVAILABLE_ACTIONS = ['south', 'north', 'east', 'west',
                          'pickup', 'dropoff']