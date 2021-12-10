"""Interface for the program."""
import solar_input as si
import solver

# ------------------ DATA ------------------ #
ARRAY_COST = 3000  # $/kW
TAX_MOD = 0.74
BATTERY_COST = 150  # $/kWh
P_RETAIL_COST, RETAIL_COSTS_LIST = si.calculate_future_power_costs(
    0.134,  # current $/kWh
    1.018,  # avg. growth factor/yr
    20,  # yrs
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
loc = si.find_maximum_difference(USAGE_CON, PROD_CON)
# ---------------- END DATA ---------------- #


def create_data_model():
    """Stores the data for the problem."""
    data = {}

    # Define variables
    data["variable_name"] = ["solar_capacity", "battery_capacity"]

    # Define constraints
    data["constraint_coeffs"] = [
        [ANNUAL_PROD, 0],
        [AREA_USAGE, 0],
        [PROD_CON[loc], 1],
    ]
    data["constraint_signs"] = ["<=", "<=", ">="]
    data["bounds"] = [TOTAL_USAGE, ROOF_AREA, USAGE_CON[loc]]

    # Define coefficients for objective function
    data["obj_coeffs"] = [
        (-TAX_MOD * ARRAY_COST + P_RETAIL_COST * ANNUAL_PROD),
        -BATTERY_COST,
    ]

    # Number of variables and constraints
    data["num_vars"] = 2
    data["num_constraints"] = 3
    return data


def format_solution(solution):
    """Print the solution in a readable format."""
    obj_value = round(solution["obj_value"], 2)
    solar_capacity = round(solution["solar_capacity"], 3)
    battery_capacity = round(solution["battery_capacity"], 3)
    print(f"Objective value = ${obj_value} saved over 20 year span.")
    print(f"Solar Capacity = {solar_capacity} kW")
    print(f"Battery Capacity = {battery_capacity} kWh")


def main():
    """Main entry point for the program."""
    data_model = create_data_model()
    solution = solver.solve_model(data_model)
    format_solution(solution)


if __name__ == "__main__":
    main()
