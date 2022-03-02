import solar_input as si
import solver
from ortools.linear_solver import pywraplp

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

def solve_problem(production, usage):
    solver = pywraplp.Solver.CreateSolver("SCIP")
    # Variables:
    x_A = solver.NumVar(0, solver.infinity(), "solar_capacity")
    x_B = solver.NumVar(0, solver.infinity(), "battery_capacity")
    B_list = []
    d_in = []
    d_out = []
    d_c = []
    d_dc = []
    for i in range(len(usage)):
        B_list[i] = solver.NumVar(0, solver.infinity(), "charge_" + i)
        d_in[i] = solver.NumVar(0, solver.infinity(), "delta_in_" + i)
        d_out[i] = solver.NumVar(0, solver.infinity(), "delta_out_" + i)
        d_c[i] = solver.IntVar(0, 1, "charging")
        d_dc[i] = solver.IntVar(0, 1, "discharging")
    
    # Constraints:
    solver.Add(ANNUAL_PROD * x_A <= TOTAL_USAGE)
    solver.Add(AREA_USAGE * x_A <= ROOF_AREA)
    
    for i in range(len(usage)):
        solver.Add(-production[i] * x_A + d_in[i] <= -usage[i])
        solver.Add(-production[i] * x_A - d_out[i] <= -usage[i])
        solver.Add(d_out <= B_list[i-1:i] * d_dc[i])
        solver.Add(B_list[i] <= x_B)
        solver.Add(d_in[i] <= (x_B - B_list[i-1:i]) * d_dc[i])
        solver.Add(d_c[i] + d_dc[i] <= 1)
        solver.Add(B_list[i]<=B_list[i-1:i]+d_in[i]-d_out[i])
