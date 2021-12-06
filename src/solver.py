"""Module for solving functions."""
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

solver = pywraplp.Solver.CreateSolver("GLOP")
x_a1 = solver.NumVar(0, solver.infinity(), "x_a1")
x_a2 = solver.NumVar(0, solver.infinity(), "x_a2")
x_b = solver.NumVar(0, solver.infinity(), "x_b")

dc_01 = solver.IntVar(0, 1, "discharge")
c_01 = solver.IntVar(0, 1, "charge")

charge_in = solver.NumVar(0, solver.infinity(), "charge-in")
charge_out = solver.NumVar(0, solver.infinity(), "charge-out")

# Constraint 0: Utot <= K * x_a1
# Total production must not exceed total usage.
solver.Add(ANNUAL_PROD * x_a1 <= TOTAL_USAGE)

# Constraint 1: AREA_USAGE * x_a1 + AREA_USAGE * x_a2 <= ROOF_AREA
# Area used by panels must not exceed available area.
solver.Add(AREA_USAGE * x_a1 + AREA_USAGE * x_a2 <= ROOF_AREA)

# TODO: Define the state of charge of the battery.
# charge = capacity

# TODO: Determine whether battery is charging or discharging
# power supplied to battery in timestep <= available capacity of battery * charge bool
# power supplied from battery in timestep <= available capacity of battery * discharge bool

# TODO: Determine the state of charge of the battery
# charge = prev_charge + amt_charged - amt_discharged

for i in range(8760):
    continue

# TODO: Battery cannot charge and discharge at same time
# charge bool + discharge bool <= 1

# TODO: Battery cannot be overcharged or overdepleted
# amount of energy stored in battery in timestep <= battery system size

# TODO: Update charge level of battery.

# TODO: Battery must not be depleted to beneath 50% of its capacity plus 24hrs of consumption

# Production Constraint Generation:
# Difference between usage and production must not exceed battery storage.
# For each 24-hr span in a year.
if len(PROD_CON) == len(USAGE_CON):
    for i in range(len(PROD_CON)):
        solver.Add(x_b >= USAGE_CON[i] - PROD_CON[i] * (x_a1 + x_a2))
else:
    print("Constraint vectors do not match!")
    exit(0)

# Constraint 2: x_b <= Umax - (Omax * x_a1 + Omax * x_a2)
# solver.Add(x_b >= 32.68 - 3.111477 * (x_a1 + x_a2))

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
