import enum
from math import prod
import solar_input as si
from ortools.linear_solver import pywraplp

# ------------------ DATA ------------------ #
BIG_M = 1000000
MIN_CHARGE = 0.5
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
TIME = 24  # hrs

# Calculated Data:
PROD_DATA, TOTAL_PROD = si.read_pvwatts("input/pvwatts_hourly.csv")  # kWh/yr
USAGE_DATA, TOTAL_USAGE = si.read_usage("input/usage.csv")

USAGE_CON, USAGE_VALUES = si.generate_constraints(
    USAGE_DATA,
    TIME,
)
PROD_CON, PROD_VALUES = si.generate_constraints(
    PROD_DATA,
    TIME,
)
max_index = si.find_maximum_difference(USAGE_CON, PROD_CON)
# ---------------- END DATA ---------------- #


def solve_problem(production, usage):
    solver = pywraplp.Solver.CreateSolver("SCIP")
    infinity = solver.infinity()

    # Variables:
    x_A = solver.NumVar(0, infinity, "solar_capacity")
    x_B = solver.NumVar(0, infinity, "battery_capacity")
    B_list = [solver.NumVar(0, infinity, "charge_%i" % i) for i in range(len(usage))]
    d_in = [solver.NumVar(0, infinity, "delta_in_%i" % i) for i in range(len(usage))]
    d_out = [solver.NumVar(0, infinity, "delta_out_%i" % i) for i in range(len(usage))]
    d_c = [solver.IntVar(0, 1, "charging_%i" % i) for i in range(len(usage))]
    d_dc = [solver.IntVar(0, 1, "discharging_%i" % i) for i in range(len(usage))]

    # Constraints:
    solver.Add(TOTAL_PROD * x_A <= TOTAL_USAGE)
    solver.Add(AREA_USAGE * x_A <= ROOF_AREA)

    for i in range(len(production)):
        # solver.Add(d_in[i] <= production[i] * x_A - usage[i])
        solver.Add(d_in[i] <= production[i] * x_A - usage[i] * d_c[i])
        solver.Add(d_out[i] >= usage[i] - production[i] * x_A)

        solver.Add(B_list[i] >= x_B * MIN_CHARGE)

        solver.Add(B_list[i] <= x_B)

        solver.Add(d_out[i] <= B_list[i - 1])
        solver.Add(d_out[i] <= BIG_M * d_dc[i])

        solver.Add(d_in[i] <= x_B - B_list[i - 1])
        solver.Add(d_in[i] <= BIG_M * d_c[i])

        solver.Add(d_c[i] + d_dc[i] <= 1)
        if i != 0:
            solver.Add(B_list[i] == B_list[i - 1] + d_in[i] - d_out[i])
        else:
            solver.Add(B_list[i] == x_B)

    # Define the objective function:
    solver.Maximize(
        (-TAX_MOD * ARRAY_COST + P_RETAIL_COST * TOTAL_PROD) * x_A - BATTERY_COST * x_B
    )
    print("Solving a problem with:", end="\t")
    print(f"{solver.NumVariables()} variables", end=", ")
    print(f"{solver.NumConstraints()} constraints")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        solution = {}
        solution["obj"] = solver.Objective().Value()
        solution["x_A"] = x_A.solution_value()
        solution["x_B"] = x_B.solution_value()
        solution["B_list"] = [i.solution_value() for i in B_list]
        solution["d_in"] = [i.solution_value() for i in d_in]
        solution["d_out"] = [i.solution_value() for i in d_out]
        solution["d_c"] = [i.solution_value() for i in d_c]
        solution["d_dc"] = [i.solution_value() for i in d_dc]
        return solution
    print("The problem does not have an optimal solution.")
    return None


def main():
    # solutions = [
    #     solve_problem(PROD_VALUES[i], USAGE_VALUES[i]) for i in range(len(USAGE_VALUES))
    # ]
    # print(solutions)
    solution = solve_problem(PROD_VALUES[8487], USAGE_VALUES[8487])
    print(solution)
    # for c,v in enumerate(solution):
    #     if c > 2:
    #         print(v, [j for j in solution[v]])
    #     else:
    #         print(v, solution[v])
    # print([solutions[i]["x_A"] for i in range(len(solutions))])
    # print(max([solutions[i]["x_A"] for i in range(len(solutions))]))
    # print([solution["x_A"] * i for i in PROD_VALUES[0]])


if __name__ == "__main__":
    main()
