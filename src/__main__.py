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
ROOF_AREA = 30
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

    # Define constraints
    data["constraint_names"] = [
        "solar_capacity",
        "battery_capacity"
    ]
    data["constraint_coeffs"] = [
        [ANNUAL_PROD, 0],
        [AREA_USAGE, 0],
        [PROD_CON[loc], 1],
    ]

    # Define bounds
    data["bounds"] = [TOTAL_USAGE, ROOF_AREA, USAGE_CON[loc]]

    # Define coefficients for objective function
    data["obj_coeffs"] = [
        (-TAX_MOD * ARRAY_COST + P_RETAIL_COST * ANNUAL_PROD),
        -BATTERY_COST,
    ]

    # Number of variables and constraints
    data["num_vars"] = 2
    data["num_constraints"] = 2
    return data


if __name__ == "__main__":
    data_model = create_data_model()
    solver.solve_model(data_model)
