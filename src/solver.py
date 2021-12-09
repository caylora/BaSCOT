"""Module for solving functions."""
import sys

from ortools.linear_solver import pywraplp

import solar_input as si

# ------------------ DATA ------------------ #
ARRAY_COST = 3000  # $/kW
TAX_MOD = 0.74
BATTERY_COST = 150  # $/kWh
P_RETAIL_COST, RETAIL_COSTS_LIST = si.calculate_future_power_costs(
    0.134,  # current $/kWh
    1.018,  # avg. growth factor/yr
    20,  # yrs
)
P_WHOLESALE_COST = 0.0646  # $/kWh
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
# ------------------ DATA ------------------ #


def solve_model(data_model):
    """Solve a model based on the input data."""

    # Create the solver
    solver = pywraplp.Solver.CreateSolver("GLOP")

    # Define the variables

    x_a1 = solver.NumVar(0, solver.infinity(), "x_a1")
    x_a2 = solver.NumVar(0, solver.infinity(), "x_a2")
    x_b = solver.NumVar(0, solver.infinity(), "x_b")

    # Define the constraints:
    
    # Constraint 0: Utot <= K * x_a1
    # Total production must not exceed total usage.
    solver.Add(ANNUAL_PROD * x_a1 <= TOTAL_USAGE)

    # Constraint 1: AREA_USAGE * x_a1 + AREA_USAGE * x_a2 <= ROOF_AREA
    # Area used by panels must not exceed available area.
    solver.Add(AREA_USAGE * x_a1 + AREA_USAGE * x_a2 <= ROOF_AREA)

    # The system functions with a battery backup in the case of an outage.
    # Use the 24hr period with greatest difference in production and consumption,
    # and size the battery bank to provide power throughout this span.
    loc = si.find_maximum_difference(USAGE_CON, PROD_CON)

    # Constraint 2: battery size >= production multiplied by capacity subtracted from usage
    solver.Add(x_b >= USAGE_CON[loc] - PROD_CON[loc] * (x_a1 + x_a2))

    # Define objective function:
    # (-TCA + Pr * T * K)x_a1 + (-TCA + Pw * T * K)x_a2
    solver.Maximize(
        (-TAX_MOD * ARRAY_COST + P_RETAIL_COST * ANNUAL_PROD) * x_a1
        + (-TAX_MOD * ARRAY_COST + P_WHOLESALE_COST * 20 * ANNUAL_PROD) * x_a2
        - BATTERY_COST * x_b
        # + inverter cost
    )

    print(f"Number of Variables: {solver.NumVariables()}")
    print(f"Number of Constraints: {solver.NumConstraints()}")

    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        print("Solution:")
        print("Objective value =", solver.Objective().Value())
        print("x_a1 =", x_a1.solution_value(), "kW cap. for retail")
        print("x_a2 =", x_a2.solution_value(), "kW cap. for wholesale")
        print("x_b =", x_b.solution_value(), "kWh of storage")
        print("Cost of Array: $", x_a1.solution_value() * ARRAY_COST)
        print("Cost of Batteries: $", x_b.solution_value() * BATTERY_COST)
    else:
        print("The problem does not have an optimal solution.")
