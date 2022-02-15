"""Interface for the program."""
import solar_input as si
import solver

# ------------------ DATA ------------------ #
ARRAY_COST = 2900  # $/kW
TAX_MOD = 0.74
BATTERY_COST = 345  # $/kWh
RATE = 0.134  # current $/kWh
GROWTH = 1.03  # avg. growth factor/yr
SPAN = 25  # yrs
P_RETAIL_COST = si.calculate_future_power_costs(
    RATE,
    GROWTH,
    SPAN,
)
ROOF_AREA = 30  # m^2
AREA_USAGE = 5.181  # m^2/kW
PROD_DATA, ANNUAL_PROD = si.read_pvwatts("input/pvwatts_hourly.csv")  # kWh/yr
BATTERY_STORAGE_TARGET = 24  # hrs
USAGE_DATA, TOTAL_USAGE = si.read_usage("input/usage.csv")
USAGE_CON = si.generate_constraints(
    USAGE_DATA,
    BATTERY_STORAGE_TARGET,
)
PROD_CON = si.generate_constraints(
    PROD_DATA,
    BATTERY_STORAGE_TARGET,
)
max_index = si.find_maximum_difference(USAGE_CON, PROD_CON)
# ---------------- END DATA ---------------- #


def create_data_model():
    """Creates a data model to pass to the solver."""
    data = {}

    # Define variables
    data["variables"] = ["solar_capacity", "battery_capacity"]

    # Define constraints
    data["constraints"] = [
        # Constraint info, containing a list of coefficients and the bound.
        # Constraint 1:
        [[ANNUAL_PROD, 0], TOTAL_USAGE],
        # Constraint 2:
        [[AREA_USAGE, 0], ROOF_AREA],
        # Constraint 3:
        [[-PROD_CON[max_index], -1], -USAGE_CON[max_index]],
    ]

    # Define coefficients for objective function
    data["objective"] = [
        (-TAX_MOD * ARRAY_COST + P_RETAIL_COST * ANNUAL_PROD),
        -BATTERY_COST,
    ]

    # Number of variables and constraints
    data["vars"] = len(data["variables"])
    data["cons"] = len(data["constraints"])
    return data


def format_solution(solution):
    """Print the solution in a readable format."""
    obj_value = round(solution["obj_value"], 2)
    solar_capacity = round(solution["solar_capacity"], 3)
    battery_capacity = round(solution["battery_capacity"], 3)
    solar_price = round(solution["solar_capacity"] * ARRAY_COST, 2)
    battery_price = round(solution["battery_capacity"] * BATTERY_COST, 2)
    print(f"Total annual energy usage: {round(TOTAL_USAGE,3)}kWh")
    print()
    print(f"Objective value = ${obj_value} saved over {SPAN} year span.")
    print(f"Solar Capacity = {solar_capacity} kW")
    print(f"Battery Capacity = {battery_capacity} kWh")
    print()
    print(f"Cost of solar modules = ${solar_price}")
    print(f"Cost of batteries = ${battery_price}")


def main():
    """Main entry point for the program."""
    data_model = create_data_model()
    solution = solver.solve_model(data_model)
    format_solution(solution)


if __name__ == "__main__":
    main()
